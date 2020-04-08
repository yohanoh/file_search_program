from PyQt5.QtCore import QThread, pyqtSignal, QMutex, pyqtSlot
import os
import re
from multiprocessing import Manager, freeze_support, Pool, Process, Pipe, Queue
from itertools import repeat

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

import time
from time import sleep
import math


# 권한 상승 코드 고려 필요
########################################################################################################################
# make_filelist
# - content : 넣고자 하는 파일 또는 디렉토리 명
# - path : 파일 또는 디렉토리의 경로(파일 명이나 디렉토리 명을 제외한 경로)
# - isdir : 디렉토리 이면 True, 아니면 False 로 설정
# = 사용자로부터 입력 받은 세 가지의 인자를 하나의 리스트에 넣어주는 메소드
########################################################################################################################
def make_filelist(content, path, isdir):
    
    if isdir:
        size = 0
    else:
        try:
            size = math.ceil(os.stat(os.path.join(path, content)).st_size / 1024)
        except FileNotFoundError:
            return
        except PermissionError:
            return

    temp = (content, path, size)
    return temp


def search(target_dir, result_queue):
    result_list = []

    # 속도 개선을 위한 처리(. 연산을 반복문 밖에서 선언)
    re_app = result_list.append
    math_ceil = math.ceil
    os_stat = os.stat
    os_path_join = os.path.join

    temp = (target_dir, target_dir, True)
    re_app(temp)

    try:
        # 루트 디렉토리에서 탐색하여 모든 파일 및 디렉토리 목록 스캔
        
        for path, dirs, files in os.walk(target_dir):
            if len(dirs) > 0:
                for d in dirs:
                    temp = (d, path, 0)
                    re_app(temp)

            for fname2 in files:
                temp = (fname2, path, math_ceil(os_stat(os_path_join(path, fname2)).st_size / 1024))
                re_app(temp)

    except WindowsError as el:
        print(el)
        pass
    except OSError as el:
        print(el)
        pass
    except Exception as el:
        print(el)
        pass

        
    
    if len(result_list) > 0: # 빈 드라이브는 수집하지 않기 위해
        result_queue.put(result_list)


########################################################################################################################
# init_filelist
# = 사용자의 cpu 수 * 2의 갯수에 해당하는 프로세스를 생성하고, 각 프로세스들이 서로 다른 경로의 디렉토리를 탐색해서
#   하위 파일 및 디렉토리 정보를 수집하도록 하는 함수
########################################################################################################################
def init_filelist(drive_dirs):
    freeze_support()

    manager = Manager()
    result_queue = manager.Queue()
    
    result_list = []
    jobs = []

    drive_dirs.reverse()
    try:
        for drive in drive_dirs:
            p = Process(target = search, args = (drive, result_queue, ))
            jobs.append(p)
            p.start()
    finally:
        for proc in jobs:
            proc.join()

    while result_queue.qsize() > 0: # 각 드라이브 별로 파일 정보가 저장되어있음.
        result_list += result_queue.get()
    e = time.time()

    return result_list

########################################################################################################################
# CommonThread 클래스
# 쓰레드 간 통신을 위한 클래스
# 모든 쓰레드 클래스의 부모 클래스이다.
########################################################################################################################
class CommonThread(QThread):
    running = QMutex()
    drive_dirs = re.findall(r"[A-Z]+:.*$",os.popen("mountvol /").read(),re.MULTILINE)
    

    def __init__(self):
        super().__init__()

    def set_db(self, db):
        self.db = db


########################################################################################################################
# ScanThread 클래스
# 사용자의 디렉토리를 탐색해서 파일 정보를 수집하고, 해당 정보를 DB에 넣어주는 역할을 수행하는 쓰레드 생성을 위한 클래스
########################################################################################################################
class ScanThread(CommonThread):
    finish_scan_signal = pyqtSignal(list)

    def __init__(self):
        super().__init__()

    def run(self):
        s = time.time()
        file_list = init_filelist(self.drive_dirs)
        e = time.time()
        self.finish_scan_signal.emit(file_list)
        print("scan time : ", e - s)

        s = time.time()
        self.running.lock()
        self.db.insert_filelist(file_list)
        self.running.unlock()
        e = time.time()

        print("DB insert time : ", e - s)
    
    
########################################################################################################################
# ReadDBThread 클래스
# 사용자로부터 입력 받은 문자열을 통해, 해당 문자열을 포함하는 파일명을 가진 파일의 정보를 DB로부터 넘겨받아 처리하는 클래스
########################################################################################################################
class DeleteDBThread(CommonThread):
    
    def __init__(self):
        super().__init__()
    
    def set_file_info(self, file_info):
        self.file_info = file_info

    def run(self):
        self.running.lock()
        
        file_name = os.path.basename(self.file_info)
        dir_path = os.path.dirname(self.file_info)
        self.db.delete_fileinfo(file_name, dir_path)

        self.running.unlock()


class InsertDBThread(CommonThread):
    def __init__(self):
        super().__init__()
    
    def set_file_info(self, file_info):
        self.file_info = file_info
    
    def run(self):
        self.running.lock()
        self.db.insert_fileinfo(self.file_info)
        self.running.unlock()


class ReadDBThread(CommonThread):
    finish_read_signal = pyqtSignal(list)
    

    def __init__(self):
        super().__init__()
        self.file_info = None

    def run(self):
        self.running.lock()
        result = self.db.get_all_filelist()
        self.running.unlock()
        self.finish_read_signal.emit(result)

            
class ManagerObserverThread(CommonThread):
    flag = QMutex()
    file_info = []
    detect_create_signal = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self.observer_threads = []

    def run(self):
        index = 0
        for drive in self.drive_dirs:
            self.observer_threads.append(ObserverThread())
            self.observer_threads[index].set_watchDir(drive)
            index = index + 1

        for observer in self.observer_threads:
            try:
                observer.start()
            except PermissionError:
                pass
        
        self.check_file_info()


    def check_file_info(self):
        while True:
            self.flag.lock()
            while len(self.file_info) > 0:
                self.detect_create_signal.emit(self.file_info.pop())
            self.flag.unlock()
        

class ObserverThread(CommonThread):

    def __init__(self):
        super().__init__()
        self.observer = Observer()

    def set_watchDir(self, watchDir):
        self.watchDir = watchDir

    def run(self):
        event_handler = Handler()
        self.observer.schedule(event_handler, self.watchDir, recursive=True)
        
        try:
            self.observer.start()
        except PermissionError:
            return

        try:
            while True:
                time.sleep(60)
        except PermissionError as e:
            pass

        except Exception as e:
            self.observer.stop()
            self.observer.join()

class Handler(FileSystemEventHandler, ManagerObserverThread):
#FileSystemEventHandler 클래스를 상속받음.
#아래 핸들러들을 오버라이드 함
    def control_event(self, event):
        if event.event_type == 'modified':
            pass

        if event.event_type == 'created':
            full_path = event.src_path
            
            if 'db-journal' in full_path:
                return

            file_name = os.path.basename(full_path)
            file_dir = os.path.dirname(full_path)
        
            temp = make_filelist(file_name, file_dir, os.path.isdir(full_path))
            if temp is None:
                return
        
            temp = [temp, 2]
            self.flag.lock()
            self.file_info.append(temp)
            self.flag.unlock()
    
        if event.event_type == 'deleted':
            full_path = event.src_path
            if 'db-journal' in full_path:
                return

            temp = [full_path, 3]
            self.flag.lock()
            self.file_info.append(temp)
            self.flag.unlock()

        if event.event_type == 'moved':
            print("moved")
            src_path = event.src_path
            dest_path = event.dest_path
            print(src_path)
            print(dest_path)


    def on_moved(self, event): #파일, 디렉터리가 move 되거나 rename 되면 실행
        print(event.event_type)
        #self.control_event(event)

    def on_created(self, event): #파일, 디렉터리가 생성되면 실행 -> 추가
        self.control_event(event)

    def on_deleted(self, event): #파일, 디렉터리가 삭제되면 실행 -> 파일 리스트에서 제거 후 DB에도 관련 정보 제거?
        self.control_event(event)

    def on_modified(self, event): #파일, 디렉터리가 수정되면 실행
        #self.control_event(event)
        pass

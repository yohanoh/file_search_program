from PyQt5.QtCore import QThread, pyqtSignal, QMutex
import os
import re
from multiprocessing import Manager, Process

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

import time
from time import sleep
import math


########################################################################################################################
# get_file_size
# - full_path : 파일의 절대 경로
# - isdir : 디렉토리인지를 나타내는 flag
# = 디렉토리를 일 경우 -> 파일 크기를 0 리턴
#   파일일 경우 -> 파일의 크기를 kb 단위로 올림해서 리턴 
########################################################################################################################
def get_file_size(full_path, isdir):
    
    if isdir:
        size = 0
    else:
        try:
            size = math.ceil(os.stat(full_path).st_size / 1024)
        except FileNotFoundError:
            return None
        except PermissionError:
            return None

    return size


########################################################################################################################
# search
# - target_dir : 탐색 대상이 되는 드라이브 최상위 루트 디렉토리
# - result_queue : 각 드라이브 별 쓰레드가 탐색 결과를 저장하게 될 공유 큐
# = 각 드라이브 별로 탐색을 시작하여 파일 정보를 수집하게 된다.
#   수집한 정보는 일차적으로 result_list에 넣고, 모든 수집이 끝나면 result_list를 공유 큐인 result_queue에 넣는다.
########################################################################################################################
def search(target_dir, result_queue = None):
    result_list = []

    # 속도 개선을 위한 처리(. 연산을 반복문 밖에서 선언)
    re_app = result_list.append
    math_ceil = math.ceil
    os_stat = os.stat
    os_path_join = os.path.join
    os_walk = os.walk

    # 드라이브 루트 디렉토리(c:\, e:\ 등) 에 대한 정보 저장
    temp = (target_dir, target_dir, 0)
    re_app(temp)

     # 루트 디렉토리 하위를 탐색해서 파일 정보 저장
    for path, dirs, files in os_walk(target_dir):
        try:
            if dirs:
                for d in dirs:
                    temp = (d, path, 0)
                    re_app(temp)

            for fname2 in files:
                temp = (fname2, path, math_ceil(os_stat(os_path_join(path, fname2)).st_size / 1024))
                re_app(temp)


        except WindowsError as el: # 권한 문제로 접근이 불가하면 해당 파일 스킵
            pass
        except OSError as el:
            pass

    if result_queue is None: # 단일 드라이브로 구성된 경우는
        return result_list

    if len(result_list) > 1: # 빈 드라이브는 수집하지 않기 위해
        result_queue.put(result_list)


########################################################################################################################
# init_filelist
# - drive_dirs : 탐색 대상이 되는 드라이브들(c:\, e:\ 등등)
# = 각 드라이브 별로 프로세스를 생성해서 정보를 수집하는 함수
#   각각의 프로세스는 공유 큐인 result_queue을 공유하여 결과를 저장하고, 저장된 정보를 리스트로 변환하여 리턴한다.
########################################################################################################################
def init_filelist(drive_dirs):
    manager = Manager() # 프로세스 간 동기화를 관리
    result_queue = manager.Queue() # 프로세스 간 공유 큐 지정
    
    result_list = []
    jobs = []

    if len(drive_dirs) > 1: # 드라이브가 1개보다 많으면 멀티 프로세스로 실행
        try:
            for drive in drive_dirs:
                p = Process(target = search, args = (drive, result_queue, ))
                jobs.append(p)
                p.start()
        finally:
            for proc in jobs:
                proc.join()

        while result_queue.qsize() > 0: # result_queue -> result_list 로 변환
            result_list += result_queue.get()
    else: # 드라이브가 단일이면 별도의 프로세스를 생성하지 않음
        result_list = search(drive_dirs[0])

    return result_list


########################################################################################################################
# CommonThread 클래스
# 쓰레드 간 통신을 위한 클래스
# 모든 쓰레드 클래스의 부모 클래스이다.
########################################################################################################################
class CommonThread(QThread):
    running = QMutex() # DB 에 대한 여러 쓰레드 접근을 컨트롤하기 위한 Mutex
    drive_dirs = re.findall(r"[A-Z]+:.*$",os.popen("mountvol /").read(), re.MULTILINE) # 시스템에서 드라이브 목록을 추출하기 위한 정규식
    
    def __init__(self):
        super().__init__()

    def set_db(self, db):
        self.db = db


########################################################################################################################
# ScanThread 클래스
# 사용자의 디렉토리를 탐색해서 파일 정보를 수집하고, 해당 정보를 DB에 넣어주는 역할을 수행하는 쓰레드
########################################################################################################################
class ScanThread(CommonThread):
    finish_scan_signal = pyqtSignal(list)

    def __init__(self):
        super().__init__()

    def run(self):
        print("start scan..")
        # 파일 시스템 스캔 시작
        s = time.time()
        file_list = init_filelist(self.drive_dirs)
        e = time.time()
        self.finish_scan_signal.emit(file_list)
        file_list.clear()
        print("scan time : ", e - s)

        # 스캔 결과 DB에 insert
        s = time.time()
        self.running.lock()
        self.db.insert_filelist(file_list)
        self.running.unlock()
        e = time.time()

        print("DB insert time : ", e - s)
    

########################################################################################################################
# ReadDBThread 클래스
# 초기에 프로그램 시작 시, 이미 DB가 형성되어있으면 해당 DB를 읽어오는 쓰레드
########################################################################################################################
class ReadDBThread(CommonThread):
    finish_read_signal = pyqtSignal(list)
    
    def __init__(self):
        super().__init__()

    def run(self):
        self.running.lock()
        result = self.db.get_all_filelist()
        self.running.unlock()
        self.finish_read_signal.emit(result)


########################################################################################################################
# DeleteDBThread 클래스
# 삭제된 파일 정보를 DB에서 제거하기 위한 쓰레드
########################################################################################################################
class DeleteDBThread(CommonThread):
    
    def __init__(self):
        super().__init__()

    def set_file_info(self, file_info):
        self.file_info = file_info

    def run(self):
        self.running.lock()
        
        file_name = self.file_info[0]
        dir_name = self.file_info[1]
        self.db.delete_fileinfo(file_name, dir_name)

        self.running.unlock()

########################################################################################################################
# InsertDBThread 클래스
# 추가된 파일 정보를 DB에 넣기 위한 쓰레드
########################################################################################################################
class InsertDBThread(CommonThread):
    def __init__(self):
        super().__init__()

    def set_file_info(self, file_info):
        self.file_info = file_info

    def run(self):
        self.running.lock()
        self.db.insert_fileinfo(self.file_info)
        self.running.unlock()


########################################################################################################################
# ManagerobserverThread 클래스
# 각 드라이브별 파일 변화 감지를 위한 쓰레드인 ObserverThread을 관리하는 쓰레드
# 드라이브별로 ObserverThread을 할당하고, check_changed_file_info 메소드를 통해
# ObserverThread가 수집한 변경 정보를 탐지하고, 해당 정보를 file_change_signal를 통해 UI 객체에게 보낸다.
########################################################################################################################
class ManagerObserverThread(CommonThread):
    changed_file_info = [] # 파일 변경 이력이 담기게 되는 리스트
    file_change_signal = pyqtSignal(list) # UI 객체에게 시그널을 보내기 위한 객체

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
        
        self.check_changed_file_info()

    # ObserverThread에 의해 갱신된 changed_file_info를 감지하기 위한 메소드
    def check_changed_file_info(self):
        while True:
            while len(self.changed_file_info) > 0:
                self.file_change_signal.emit(self.changed_file_info.pop())
            sleep(1)
        
########################################################################################################################
# ObserverThread 클래스
# 대상이 되는 드라이브의 파일 변화를 감지하는 쓰레드
########################################################################################################################
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
            while True:
                time.sleep(1)
        except PermissionError:
            pass
        except Exception as e:
            self.observer.stop()
            self.observer.join()

########################################################################################################################
# Handler 클래스
# ObserverThread에 의해 감지된 이벤트를 처리하기 위한 핸들러
########################################################################################################################
class Handler(FileSystemEventHandler, ManagerObserverThread):

    # 테이블 및 DB에 넣기 위한 파일 정보와 mode 값을 지정
    def insert_file(self, full_path):
        mode = 3
        file_name = os.path.basename(full_path)
        dir_name = os.path.dirname(full_path)                
        size = get_file_size(full_path, os.path.isdir(full_path))

        if size is None:
            pass
        else:
            temp = [(file_name, dir_name, size), mode]
            self.changed_file_info.append(temp)
        

    # 테이블 및 Db에서 정보 삭제를 위한 파일 정보와 mode 값을 지정
    def delete_file(self, full_path):
        mode = 4
        file_name = os.path.basename(full_path)
        dir_name = os.path.dirname(full_path)

        temp = [(file_name, dir_name), mode]
        self.changed_file_info.append(temp)

    #파일, 디렉터리가 생성되면 실행 -> 테이블 및 DB에 추가
    def on_created(self, event): 
        full_path = event.src_path

        if 'db-journal' in full_path:
            pass
        else:
            self.insert_file(full_path)

    #파일, 디렉터리가 삭제되면 실행 -> 데이블 및 DB에서 제거
    def on_deleted(self, event): 
        full_path = event.src_path

        if 'db-journal' in full_path:
            pass
        else:
            self.delete_file(full_path)

    #파일, 디렉터리가 move 되거나 rename 되면 실행 -> 이전 자료 삭제 후 새로운 자료로 갱신
    def on_moved(self, event): 
        src_path = event.src_path
        dest_path = event.dest_path

        if 'db-journal' in src_path or 'db-journal' in dest_path:
            pass
        else:
            self.insert_file(dest_path)
            self.delete_file(src_path)


class checkTime(QThread):
    timeout = pyqtSignal()

    def __init__(self):
        super().__init__()

    def run(self):
        sleep(1)
        self.timeout.emit()


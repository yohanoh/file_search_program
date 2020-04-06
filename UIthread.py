from PyQt5.QtCore import QThread, pyqtSignal, QMutex, pyqtSlot
import os
from multiprocessing import Manager, freeze_support, Pool, Process
from itertools import repeat

import time
from time import sleep
import math

# 스택에 탐색 대상 디렉토리를 넣고 탐색하는 방법도 고려..
# 권한 상승 코드 고려 필요
########################################################################################################################
# make_filelist
# - content : 넣고자 하는 파일 또는 디렉토리 명
# - path : 파일 또는 디렉토리의 경로(파일 명이나 디렉토리 명을 제외한 경로)
# - isdir : 디렉토리 이면 True, 아니면 False 로 설정
# = 사용자로부터 입력 받은 세 가지의 인자를 하나의 리스트에 넣어주는 메소드
########################################################################################################################
def make_filelist(content, path, isdir):
    temp = []

    temp.append(content)
    temp.append(path)

    if isdir:
        size = 0
    else:
        size = math.ceil(os.stat(os.path.join(path, content)).st_size / 1024)

    temp.append(size)
    return temp


# 가장 최신
########################################################################################################################
# init_filelist
# = 사용자의 cpu 수 * 2의 갯수에 해당하는 프로세스를 생성하고, 각 프로세스들이 서로 다른 경로의 디렉토리를 탐색해서
#   하위 파일 및 디렉토리 정보를 수집하도록 하는 함수
########################################################################################################################
def init_filelist():
    root_dir = "c:\\"
    result_list = search(root_dir)

    return result_list


# target_dir : 각 디스크 root_dir
def search(target_dir):
    result_list = []
    re_app = result_list.append

    temp = make_filelist(target_dir, target_dir, True)
    re_app(temp)

    try:
        # 루트 디렉토리에서 탐색하여 모든 파일 및 디렉토리 목록 스캔
        for path, dirs, files in os.walk(target_dir):
            if len(dirs) > 0:
                for d in dirs:
                    temp = make_filelist(d, path, True)
                    re_app(temp)

            for fname2 in files:
                temp = make_filelist(fname2, path, False)
                re_app(temp)

    except WindowsError as e:
        #print("win : ", e)
        pass
    except OSError as e:
        #print("os : ", e)
        pass
    except Exception as e:
        #print("exception : ", e)
        pass

    return result_list

"""
########################################################################################################################
# init_filelist
# = 사용자의 cpu 수 * 2의 갯수에 해당하는 프로세스를 생성하고, 각 프로세스들이 서로 다른 경로의 디렉토리를 탐색해서
#   하위 파일 및 디렉토리 정보를 수집하도록 하는 함수
########################################################################################################################
def init_filelist():
    root_dir = "c:\\"
    files = os.listdir(root_dir)
    filelist = []

    for file in files:
        filelist.append(os.path.join(root_dir, file))

    cpu = os.cpu_count()
    pool = Pool(cpu * 2)

    manager = Manager()
    result_list = manager.list()

    try:
        pool.starmap(search, zip(filelist, repeat(result_list)))
    finally:
        pool.close()
        pool.join()

    return result_list
"""
class CommonThread(QThread):
    running = QMutex()

    def __init__(self):
        super().__init__()

    def set_db(self, db):
        self.db = db
    

########################################################################################################################
# ScanThread 클래스
# 사용자의 디렉토리를 탐색해서 파일 정보를 수집하고, 해당 정보를 DB에 넣어주는 역할을 수행하는 쓰레드 생성을 위한 클래스
########################################################################################################################
class ScanThread(CommonThread):

    finish_scan_signal = pyqtSignal()
    
    def __init__(self):
        super().__init__()

    def run(self):
        print("run..")
        s = time.time()
        file_list = init_filelist()
        e = time.time()

        print(len(file_list))
        print("scan time : ", e - s)

        s = time.time()
        self.running.lock()
        self.db.insert_filelist(file_list)
        self.running.unlock()
        e = time.time()

        print("insert time : ", e - s)
        self.finish_scan_signal.emit()
    
    
########################################################################################################################
# ReadDBThread 클래스
# 사용자로부터 입력 받은 문자열을 통해, 해당 문자열을 포함하는 파일명을 가진 파일의 정보를 DB로부터 넘겨받아 처리하는 클래스
########################################################################################################################
class ReadDBThread(CommonThread):

    finish_read_signal = pyqtSignal(list)
    
    def __init__(self):
        super().__init__()

    def set_finding_str(self, finding_str):
        self.finding_str = finding_str
    
    def run(self, all_data = False):
        self.running.lock()
        if all_data: # 초기 테이블 표시를 위해
            result = self.db.get_all_filelist()
        else:
            result = self.db.get_filelist_by_file_name(self.finding_str)

        self.running.unlock()

        self.finish_read_signal.emit(result)

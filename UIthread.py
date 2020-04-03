from PyQt5.QtCore import *
import os
from multiprocessing import Manager, freeze_support, Pool, Process
from itertools import repeat
from queue import Queue

import time


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
    temp.append(os.path.join(path,content))
    if isdir:
        size = 0
    else:
        size = os.stat(temp[1]).st_size

    temp.append(size)
    return temp


########################################################################################################################
# search
# - pwd : 현재 파일 또는 디렉토리의 경로
# - result_list : 여러 프로세스에 의해 갱신되는 파일 리스트 들을 보관하게 되는 리스트 (프로세스 간 공유 리스트)
# = 인자로 넘겨 받은 pwd을 통해 해당 경로에 있는 것이 파일 인지 디렉토리 인지를 파악한다.
#   파일일 경우, result_list에 해당 파일에 정보를 넣어주고,
#   디렉토리일 경우, os.walk 을 통해 하위 디렉토리 및 파일 정보를 result_list 에 넣어준다.
########################################################################################################################
def search(file_abs_path, result_list, target_list):
    target_list.append(file_abs_path)
    # 누락되는 정보 확인하기        
    while len(target_list) > 0:
        front_file = target_list.pop(0)

        file_name = os.path.basename(file_abs_path)
        path = os.path.dirname(file_abs_path)

        try:
            if os.path.isdir(front_file): # 디렉토리
                temp = make_filelist(file_name, path, True)
                result_list.append(temp)
                current_file_list = os.listdir(front_file)
            else: # 파일
                temp = make_filelist(file_name, path, False)
                result_list.append(temp)
                continue

            for file_name in current_file_list:
                absolute_path = os.path.join(front_file, file_name)
                    
                if os.path.isdir(absolute_path): # 디렉토리인 경우
                    target_list.append(absolute_path)
                else: # 일반 파일인 경우
                    temp = make_filelist(file_name, front_file, False)
                    result_list.append(temp)

        except WindowsError as e:
            #print(e)
            pass
        except OSError as e:
            #print(e)
            pass
        except Exception as e:
            #print(e)
            pass


########################################################################################################################
# init_filelist
# = 사용자의 cpu 수 * 2의 갯수에 해당하는 프로세스를 생성하고, 각 프로세스들이 서로 다른 경로의 디렉토리를 탐색해서
#   하위 파일 및 디렉토리 정보를 수집하도록 하는 함수
########################################################################################################################
def init_filelist():
    manager = Manager()
    result_list = manager.list()
    target_list = manager.list()

    root_dir = "c:\\"
    files = os.listdir(root_dir)

    file_list = []
    for f in files:
        file_list.append(os.path.join(root_dir, f))
    
    cpu = os.cpu_count()
    pool = Pool(cpu * 2)

    try:
        pool.starmap(search, zip(file_list, repeat(result_list), repeat(target_list)))
    except IndexError:
        pass
    finally:
        pool.close()
        pool.join()

    return result_list


"""
########################################################################################################################
# search
# - pwd : 현재 파일 또는 디렉토리의 경로
# - result_list : 여러 프로세스에 의해 갱신되는 파일 리스트 들을 보관하게 되는 리스트 (프로세스 간 공유 리스트)
# = 인자로 넘겨 받은 pwd을 통해 해당 경로에 있는 것이 파일 인지 디렉토리 인지를 파악한다.
#   파일일 경우, result_list에 해당 파일에 정보를 넣어주고,
#   디렉토리일 경우, os.walk 을 통해 하위 디렉토리 및 파일 정보를 result_list 에 넣어준다.
########################################################################################################################
def search(file_abs_path, result_list):
    
    file_name = os.path.basename(file_abs_path)
    path = os.path.dirname(file_abs_path)

    try:
        if os.path.isdir(file_abs_path):
            temp = make_filelist(file_name, path, True)
            result_list.append(temp)
        else:
            temp = make_filelist(file_name, path, False)
            result_list.append(temp)
            return

        current_file_list = os.listdir(file_abs_path)
        for file_name in current_file_list:
            absolute_path = os.path.join(file_abs_path, file_name)
            
            if os.path.isdir(absolute_path):
                temp = make_filelist(file_name, file_abs_path, True)
                result_list.append(temp)
                search(absolute_path, result_list)
            else:
                temp = make_filelist(file_name, file_abs_path, False)
                result_list.append(temp)

    except WindowsError as e:
        pass
    except OSError as e:
        pass
    except Exception as e:
        pass


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

########################################################################################################################
# ScanThread 클래스
# 사용자의 디렉토리를 탐색해서 파일 정보를 수집하고, 해당 정보를 DB에 넣어주는 역할을 수행하는 쓰레드 생성을 위한 클래스
########################################################################################################################
class ScanThread(QThread):

    finish_scan_signal = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.scan_running = False

    def set_db(self, db):
        self.db = db

    def run(self):
        print("run..")
        s = time.time()
        file_list = init_filelist()
        e = time.time()
        
        print("scan time : ", e - s)
        self.scan_running = True

        s = time.time()
        self.db.insert_filelist(file_list)
        e = time.time()
        print("insert time: ", e - s)
        self.scan_running = False
        self.finish_scan_signal.emit()


########################################################################################################################
# ReadDBThread 클래스
# 사용자로부터 입력 받은 문자열을 통해, 해당 문자열을 포함하는 파일명을 가진 파일의 정보를 DB로부터 넘겨받아 처리하는 클래스
########################################################################################################################
class ReadDBThread(QThread):
    finish_read_signal = pyqtSignal(list)
    

    def __init__(self):
        super().__init__()   
        self.read_running = False

    def set_db(self, db):
        self.db = db

    def set_finding_str(self, finding_str):
        self.finding_str = finding_str

    def run(self, all_data = False):
        self.read_running = True
        if all_data: # 초기 테이블 표시를 위해
            result = self.db.get_all_filelist()
        else:
            result = self.db.get_filelist_by_file_name(self.finding_str)

        self.read_running = False
        self.finish_read_signal.emit(result)

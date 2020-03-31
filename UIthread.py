from PyQt5.QtCore import *
from ScanDirectory import init_filelist

import os
from multiprocessing import Manager, freeze_support, Pool, Process, Queue
from itertools import repeat
import time

# 스택에 탐색 대상 디렉토리를 넣고 탐색하는 방법도 고려..
# 권한 상승 코드 고려 필요
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


def search(pwd, result_list):
    file = os.path.basename(pwd)
    path = os.path.dirname(pwd)

    try:
        if os.path.isdir(pwd):
            temp = make_filelist(file, path, True)
            result_list.append(temp)
        else:
            temp = make_filelist(file, path, False)
            result_list.append(temp)
            return

        # 루트 디렉토리에서 탐색하여 모든 파일 및 디렉토리 목록 스캔
        for path, dirs, files in os.walk(pwd):
            if len(dirs) != 0:
                for dir in dirs:
                    temp = make_filelist(dir, path, True)
                    result_list.append(temp)

            for file in files:
                temp = make_filelist(file, path, False)
                result_list.append(temp)

    except WindowsError as e:
        #print("win : ", e)
        pass
    except OSError as e:
        #print("os : ", e)
        pass
    except Exception as e:
        pass


def init_filelist():
    #freeze_support()
    s = time.time()
    root_dir = "c:\\"
    files = os.listdir(root_dir)
    filelist = []

    for file in files:
        filelist.append(os.path.join(root_dir, file))

    cpu = os.cpu_count()
    pool = Pool(cpu * 2)

    manager = Manager()
    result_list = manager.list()

    pool.starmap(search, zip(filelist, repeat(result_list)))
    pool.close()
    pool.join()

    e = time.time()
    print("init filelist : ", e - s)
    return result_list


#전체 디렉토리를 스캔해서 새로운 파일이 있을 시, db에 저장해주는 Thread
class ScanThread(QThread):

    finish_scan_signal = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.scan_running = False

    def set_db(self, db):
        self.db = db

    def run(self):
        print("run")
        s = time.time()
        file_info = init_filelist()
        e = time.time()
        print("finish init : ", e - s)

        self.scan_running = True

        s = time.time()
        self.db.insert_filelist(file_info)
        e = time.time()
        print("finish insert : ", e - s)
        self.scan_running = False
        self.finish_scan_signal.emit(True)


#사용자가 입력한 파일 이름에 따라 해당 정보를 검색해주는 Thread
class ReadDBThread(QThread):

    finish_read_signal = pyqtSignal(list)

    def __init__(self):
        super().__init__()
        self.read_running = False

    def set_db(self, db):
        self.db = db

    def set_finding_str(self, finding_str):
        self.find_str = finding_str

    def run(self, all_data = False):
        self.read_running = True
        if all_data: # 초기 테이블 표시를 위해
            result = self.db.get_all_filelist()
        else:
            result = self.db.get_filelist_by_file_name(self.find_str)

        self.read_running = False
        self.finish_read_signal.emit(result)

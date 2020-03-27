from PyQt5.QtCore import *
from ScanDirectory import init_filelist

import os
from multiprocessing import Manager, freeze_support, Pool
from itertools import repeat
import time

# 권한 상승 코드 고려 필요
def search(pwd, result_list):
    temp = []

    """
    dir = os.path.split(pwd)
    size = 0
    temp.append(dir)
    temp.append(pwd)
    temp.append(size)
    result_list.append(temp)
    """

    try:
        # 루트 디렉토리에서 탐색하여 모든 파일 및 디렉토리 목록 스캔
        for path, dirs, files in os.walk(pwd):
            if len(dirs) != 0:
                for dir in dirs:
                    temp = []
                    temp.append(dir)
                    temp.append(os.path.join(path, dir))
                    size = 0
                    temp.append(size)
                    result_list.append(temp)

            for file in files:
                temp = []
                temp.append(file)
                temp.append(os.path.join(path, file))
                size = os.stat(temp[1]).st_size
                temp.append(size)
                result_list.append(temp)
    except OSError:
        print(path+"\\" + file)
        pass


def init_filelist():
    freeze_support()
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
    print(e - s)
    return result_list


#전체 디렉토리를 스캔해서 새로운 파일이 있을 시, db에 저장해주는 Thread
class ScanThread(QThread):

    finish_scan_signal = pyqtSignal(bool)

    def __init__(self):
        super().__init__()

    def set_db(self, db):
        self.db = db

    def run(self):
        print("run")
        file_info = init_filelist()
        print("after init")
        self.db.insert_filelist(file_info)
        print("after insert")
        self.finish_scan_signal.emit(True)


#사용자가 입력한 파일 이름에 따라 해당 정보를 검색해주는 Thread
class ReadDBThread(QThread):

    finish_read_signal = pyqtSignal(list)

    def __init__(self):
        super().__init__()

    def set_db(self, db):
        self.db = db

    def set_finding_str(self, finding_str):
        self.find_str = finding_str

    def run(self, all_data = False):
        if all_data:
            result = self.db.get_filelist_by_file_name(self.find_str)
        else:
            result = self.db.get_filelist()

        self.finish_read_signal.emit(result)

import os
from multiprocessing import Manager, freeze_support, Pool, Process, Queue
from itertools import repeat
import time
from DBManager import DBManager


# 권한 상승 코드 고려 필요
def search(pwd, result_list):

    try:
        # 루트 디렉토리에서 탐색하여 모든 파일 및 디렉토리 목록 스캔
        for path, dirs, files in os.walk(pwd):
            for file in files:
                temp = []

                temp.append(file)
                temp.append(os.path.join(path, file))
                size = os.stat(temp[1]).st_size
                temp.append(size)
                result_list.append(temp)
    except OSError:
        pass
"""

def search(pwd, result_queue):

    # 루트 디렉토리에서 탐색하여 모든 파일 및 디렉토리 목록 스캔
    for path, dirs, files in os.walk(pwd):
        for file in files:
            temp = []
            size = os.path.getsize(path)

            temp.append(file)
            temp.append(os.path.join(path, file))
            temp.append(size)
            result_queue.put(temp)
"""
def search2(pwd, result_list):

    try:
        if not os.path.isdir(pwd):
            return

        for entry in os.scandir(pwd):
            temp = []
            size = entry.stat().st_size
            file = entry.name
            path = entry.path

            temp.append(file)
            temp.append(path)
            temp.append(size)
            result_list.append(temp)

            if entry.is_dir():
                search2(path, result_list)
    except PermissionError:
        pass

def init_filelist():
    freeze_support()

    root_dir = "c:\\"
    files = os.listdir(root_dir)
    filelist = []

    for file in files:
        filelist.append(os.path.join(root_dir, file))

    """
    result_queue = Queue()
    procs = []
    for file_path in filelist:
        proc = Process(target=search, args=(file_path, result_queue))
        procs.append(proc)
        proc.start()

    for proc in procs:
        proc.join()


    """

    cpu = os.cpu_count()
    #pool = Pool(cpu * 2)
    pool = Pool(1)
    manager = Manager()
    result_list = manager.list()

    pool.starmap(search, zip(filelist, repeat(result_list)))
    pool.close()
    pool.join()

    return result_list

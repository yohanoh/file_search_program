import os
from multiprocessing import Manager, freeze_support, Pool, Process, Queue
from itertools import repeat
import time


# 권한 상승 코드 고려 필요
def search(pwd, result_list):

    """
    temp = []
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

    return list(result_list)

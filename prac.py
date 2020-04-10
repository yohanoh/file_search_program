from PyQt5.QtCore import QThread, pyqtSignal, QMutex, pyqtSlot
import os
import sys
import re
from multiprocessing import Manager, freeze_support, Pool, Process, Queue

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

import time
from time import sleep
import math



# os.walk ver
def walk_search(target_dir):
    result_list = []

    # 드라이브 루트 디렉토리(c:\, e:\ 등) 에 대한 정보 저장
    temp = (target_dir, target_dir, 0)
    result_list.append(temp)

     # 루트 디렉토리 하위를 탐색해서 파일 정보 저장
    for path, dirs, files in os.walk(target_dir):
        try:
            if len(dirs) > 0:
                for d in dirs:
                    temp = (d, path, 0)
                    result_list.append(temp)

            for fname2 in files:
                temp = (fname2, path, math.ceil(os.stat(os.path.join(path, fname2)).st_size / 1024))
                result_list.append(temp)

        except WindowsError as e1: # 권한 문제로 접근이 불가하면 해당 파일 스킵
            #print(e1)
            pass
        except OSError as el:
            #print(e1)
            pass

    return result_list


# is_dir ver
def dir_search(target_dir):
    result_list = []

    temp = (target_dir, target_dir, 0)
    result_list.append(temp)

    try:
        current_file_list = os.listdir(target_dir)
        for file_name in current_file_list:
            absolute_path = os.path.join(target_dir, file_name)
            
            if os.path.isdir(absolute_path):
                temp = (file_name, target_dir, 0)
                result_list.append(temp)
                result_list = result_list + dir_search(absolute_path)
            else:
                temp = (file_name, target_dir, math.ceil(os.stat(absolute_path).st_size / 1024))
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

    return result_list


s = time.time()
r1 = walk_search("c:\\")
e = time.time()
print("========================================================")
s1 = time.time()
r2 = dir_search("c:\\")
e1 = time.time()


print("walk : {0}, isdir : {1}, len1 : {2}, len2 : {3}".format(e - s, e1 - s1, len(r1), len(r2)))
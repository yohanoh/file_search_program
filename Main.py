from DBManager import DBManager
from ScanDirectory import init_filelist
import time

if __name__ == "__main__":
    start = time.time()
    DB = DBManager()
    file_info = init_filelist()

    scanend = time.time()
    print("scan : ", scanend - start)

    insertstart = time.time()
    DB.insert_filelist(file_info)
    end = time.time()
    print("insert : ", end - insertstart)

    sstart = time.time()
    # 사용자로부터 입력값 받고 큐
    result = DB.get_filelist_by_file_name("python")
    eend = time.time()
    print("select : ", eend - sstart)


    print("total : {0}".format(eend- start))

import sqlite3
import time
import os

class DBManager:
    def __init__(self):
        self.make_data_directory()
        self.init_db()
        # sql 속도 향상을 위한 설정값
        self.cur.execute('pragma journal_mode=wal')
        self.cur.execute('pragma cache_size = 30000')
        self.cur.execute('pragma synchronous=OFF')

        sql = "CREATE TABLE IF NOT EXISTS FileList(FILE_NAME TEXT NOT NULL, " \
              "FILE_PATH TEXT PRIMARY KEY, " \
              "FILE_SIZE INT NOT NULL)"

        self.cur.execute(sql)
        self.conn.commit()

    def make_data_directory(self):
        try:
            if not(os.path.isdir('Data')):
                os.makedirs(os.path.join("Data"))
        except OSError as e:
            if e.errno != os.errno.EEXIST:
                print("Failed to create directory")


    def init_db(self):
        self.conn = sqlite3.connect('Data\\data.db')
        self.cur = self.conn.cursor()

    def insert_filelist(self, filelist):
        self.init_db()
        self.cur.execute('BEGIN')
        self.cur.executemany("INSERT OR REPLACE INTO FileList values (?, ?, ?)", filelist)
        self.conn.commit()

    # 파일 정보를 리스트로 반환, 각 파일 정보는 튜플로 구성됨 -> [(filename1, filepath1, filesize1), ( )...]
    def get_all_filelist(self):
        self.init_db()
        s = time.time()
        query = "SELECT * FROM FileList"
        rows = self.cur.execute(query).fetchall()
        e = time.time()
        print("get total filelist : ", e - s)
        return rows

    # 사용자가 입력한 값에 따라 해당 문자열을 포함하는 파일 정보를 리턴
    def get_filelist_by_file_name(self, file_name):
        self.init_db()
        s = time.time()
        self.cur.execute('BEGIN')
        #query = "SELECT * FROM FileList WHERE FILE_NAME LIKE '%{0}%'".format(file_name)
        query = "SELECT * FROM FileList WHERE INSTR(FILE_NAME, '{0}') > 0".format(file_name)
        rows = self.cur.execute(query).fetchall()
        self.conn.commit()
        e = time.time()
        print("get file name : ", e - s)
        return rows

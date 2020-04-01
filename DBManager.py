import sqlite3
import time
import os

########################################################################################################################
# DBManger 클래스
# DB 생성 및 SQL 쿼리문을 관리하는 클래스
########################################################################################################################
class DBManager:
    def __init__(self):
        self.make_data_directory()

        # sql 속도 향상을 위한 설정값
        with sqlite3.connect('Data\\data.db') as con:
            cur = con.cursor()
            cur.execute('pragma journal_mode=wal')
            cur.execute('pragma cache_size = 30000')
            cur.execute('pragma synchronous=OFF')

            sql = "CREATE TABLE IF NOT EXISTS FileList(FILE_NAME TEXT NOT NULL, " \
                "FILE_PATH TEXT PRIMARY KEY, " \
                "FILE_SIZE INT NOT NULL)"

            cur.execute(sql)
            con.commit()

    ####################################################################################################################
    # make_data_directory
    # = 현재 디렉토리에서 Data 디렉토리가 있는지 확인 후, 없을 경우 생성해주는 메소드
    ####################################################################################################################
    def make_data_directory(self):
        try:
            if not(os.path.isdir('Data')):
                os.makedirs(os.path.join("Data"))
        except OSError as e:
            if e.errno != os.errno.EEXIST:
                print("Failed to create directory")


    ####################################################################################################################
    # insert_filelist
    # - filelist : DB에 insert할 파일 정보들 -> [(filename, filepath, filesize),()...]
    # = 인자로 받은 파일 정보를 FileList table에 insert하는 쿼리문을 수행하는 메소드
    ####################################################################################################################
    def insert_filelist(self, filelist):
        with sqlite3.connect('Data\\data.db') as con:
            cur = con.cursor()
            cur.execute('BEGIN')
            cur.executemany("INSERT OR REPLACE INTO FileList values (?, ?, ?)", filelist)
            con.commit()


    ####################################################################################################################
    # get_all_filelist
    # = FileList 테이블에 있는 모든 파일 정보를 리턴해주는 메소드
    ####################################################################################################################
    def get_all_filelist(self):
        with sqlite3.connect('Data\\data.db') as con:
            cur = con.cursor()
            query = "SELECT * FROM FileList"
            rows = cur.execute(query).fetchall()

        return rows

    ####################################################################################################################
    # get_filelist_by_file_name
    # - file_name : 파일 이름에 포함되었는지를 체크하는 문자열
    # = 인자로 받은 file_name을 포함한 파일명을 가진 파일 정보를 리턴해주는 메소드
    ####################################################################################################################
    def get_filelist_by_file_name(self, file_name):
        with sqlite3.connect('Data\\data.db') as con:
            cur = con.cursor()
            s = time.time()
            cur.execute('BEGIN')
            #query = "SELECT * FROM FileList WHERE FILE_NAME LIKE '%{0}%'".format(file_name)
            query = "SELECT * FROM FileList WHERE INSTR(FILE_NAME, '{0}') > 0".format(file_name)
            rows = cur.execute(query).fetchall()
            con.commit()
            e = time.time()
            print("get file name : ", e - s)

        return rows

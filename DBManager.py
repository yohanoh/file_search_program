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
            sql = "CREATE TABLE IF NOT EXISTS FileList(FILE_NAME TEXT NOT NULL, " \
                "FILE_PATH TEXT NOT NULL, " \
                "FILE_SIZE INT NOT NULL, PRIMARY KEY(FILE_NAME, FILE_PATH));"

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
                print("Failed to create Data directory")

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
    # insert_fileinfo
    # - fileinfo : DB에 저장하게 될 파일정보(파일 이름, 경로, 크기)
    # = 인자로 넘겨 받은 단일 파일 정보를 DB에 저장하는 메소드
    ####################################################################################################################
    def insert_fileinfo(self, fileinfo):
        with sqlite3.connect('Data\\data.db') as con:
            cur = con.cursor()
            cur.execute('BEGIN')
            query = "INSERT OR REPLACE INTO FileList values ('{0}', '{1}', {2})".format(fileinfo[0], fileinfo[1], fileinfo[2])
            cur.execute(query)
            con.commit()

    ####################################################################################################################
    # delete_fileinfo
    # - file_name : DB에서 삭제하게 될 파일의 이름
    # - dir_name : DB에서 삭제하게 될 파일의 경로
    # = 인자로 넘겨 받은 단일 파일 정보를 DB에서 삭제하는 메소드
    ####################################################################################################################
    def delete_fileinfo(self, file_name, dir_name):
        with sqlite3.connect('Data\\data.db') as con:
            cur = con.cursor()
            cur.execute('BEGIN')
            query = "DELETE FROM FileList WHERE FILE_NAME = '{0}' AND FILE_PATH = '{1}'".format(file_name, dir_name)
            cur.execute(query)
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
        
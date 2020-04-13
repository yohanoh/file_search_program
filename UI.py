import sys
import ctypes
import win32com.shell.shell as shell
import webbrowser
import subprocess
import time
from multiprocessing import freeze_support

from PyQt5.QtWidgets import QApplication, QWidget, QLineEdit, QVBoxLayout, QLabel, QTableView
from PyQt5.QtCore import pyqtSlot, QModelIndex, QAbstractTableModel, Qt

from DBManager import DBManager
from UIthread import *


########################################################################################################################
# UI 클래스
# UI 를 구성하기 위한 클래스
# UI 뿐만 아니라 각 UI 위젯 간의 시그널을 관리하기 위한 시그널 핸들러 함수도 정의하고 있다.
########################################################################################################################
class UI(QWidget):
    def __init__(self):
        super().__init__()
        self.db = DBManager()
        self.cached_file_list = [] # DB를 통해 검색하지 않고, 메모리에 올려서 검색을 수행하기 위한 파일 리스트
        self.count = 0

        # 테이블 갱신
        self.initUI()

        # 디렉토리를 탐색해서 파일 리스트를 얻은 후, DB에 insert 하는 작업까지 수행하는 쓰레드
        self.scan_thread = ScanThread()
        self.scan_thread.set_db(self.db)
        self.scan_thread.finish_scan_signal.connect(self.finish_scan)
        self.start_thread(mode = 1)

        # DB 정보를 읽기 위한 쓰레드
        self.read_db_thread = ReadDBThread()
        self.read_db_thread.set_db(self.db)
        self.read_db_thread.finish_read_signal.connect(self.finish_read)
        self.start_thread(mode = 0)

        # 새로 생성된 파일정보를 DB에 넣기 위한 쓰레드
        self.insert_db_thread = InsertDBThread()
        self.insert_db_thread.set_db(self.db)

        # 삭제된 파일정보를 DB에서 제거하기 위한 쓰레드
        self.delete_db_thread = DeleteDBThread()
        self.delete_db_thread.set_db(self.db)

        # 각 드라이브 별로 파일 변화 감지를 수행하는 쓰레드를 관리하는 쓰레드
        self.manager_observer_thread = ManagerObserverThread()
        self.manager_observer_thread.file_change_signal.connect(self.control_updated_file)
        self.start_thread(mode = 2)

        self.check_time = checkTime()
        self.check_time.timeout.connect(self.processing_time_out)

    ####################################################################################################################
    # initTable
    # = 테이블 표시를 위한 기본 설정을 하는 메소드이다.
    #   테이블의 entry를 클릭 했을 때, 파일이나 디렉토리를 실행하기 위한 이벤트(execute_file)를 연결해주고,
    #   테이블의 헤더를 클릭 했을 때 정렬 기능을 실행하기 위한 이벤트(sort_data)도 연결해준다.
    ###################################################################################################################
    def initTable(self):
        self.header_sorted_state = [False, False, False]
        self.table_model = TableModel()
        self.tableview.setSortingEnabled(True)

        self.tableview.doubleClicked.connect(self.execute_file)
        self.tableview.horizontalHeader().sectionClicked.connect(self.sort_data)


    ####################################################################################################################
    # inintUI
    # = UI를 초기화하기 위한 메소드이다.
    #   사용자 입력을 받기 위한 LineEdit, 검색된 결과 개수를 표시하기 위한 Label, 검색된 결과를 표시하기 위한 tableview
    #   위젯들을 포함한다.
    ####################################################################################################################
    def initUI(self):
        
        # 사용자 입력을 받는 위젯
        self.qle = QLineEdit(self)
        self.qle.textEdited.connect(self.update_table_data)

        # 검색된 결과의 개수를 표시하는 위젯
        self.label = QLabel(self)

        # 검색된 결과를 표시하는 테이블
        self.tableview = QTableView()
        self.initTable()

        # UI 구성
        self.vbox = QVBoxLayout()
        self.vbox.addWidget(self.qle)
        self.vbox.addWidget(self.tableview)
        self.vbox.addWidget(self.label)

        self.setLayout(self.vbox)
        self.setWindowTitle('File Search Program')
        self.setGeometry(300, 100, 1500, 800)
        self.show()


    ####################################################################################################################
    # displayFiles
    # - file_list : 테이블 상에 표시한 파일들의 정보를 담고 있는 리스트 ( 파일명, 경로, 크기를 튜플 형태로 저장)
    # = 검색 결과에 의해 갱신되는 테이블을 나타내는 메소드
    ####################################################################################################################
    def displayFiles(self, file_list):
        total = len(file_list)
        self.label.setText("총 {0} 개 검색됨".format(total))
        
        self.tableview.clearSpans()
        self.table_model.layoutAboutToBeChanged.emit()
        self.table_model.setData(file_list)
        self.table_model.layoutChanged.emit()

        self.tableview.setModel(self.table_model)
        self.tableview.resizeColumnsToContents()
    

    ########################################################################################################################
    # start_thread
    # - mode : 시작하게 될 쓰레드를 명시하기 위한 변수
    # = 인자로 받은 mode을 통해 실행할 쓰레드를 결정하고, 쓰레드를 실행한다.
    ########################################################################################################################
    def start_thread(self, mode):
        if mode == 0: #read_db_thread -> DB로부터 파일 정보 읽기
            self.read_db_thread.start()

        elif mode == 1: #scan_thread -> 파일 시스템 스캔 및 DB 저장
            self.scan_thread.start()

        elif mode == 2: #manager_observer_thread -> 파일 변화를 감지하는 Observer를 thread을 생성하고, 이벤트 처리
            self.manager_observer_thread.start()

        elif mode == 3: #insert_db_thread -> DB에 추가된 파일 정보 저장
            self.insert_db_thread.start()
        
        elif mode == 4: #delete_db_thread -> DB에서 삭제된 파일 정보 제거
            self.delete_db_thread.start()
    

    ########################################################################################################################
    # insert_fileinfo
    # - file_info : 추가하게 될 파일 정보가 들어있는 리스트(파일명, 경로, 사이즈)
    # = 인자로 받은 file_info를 통해 파일 정보를 갱신하고, 테이블을 갱신하는 메소드를 호출한다.
    ########################################################################################################################
    def insert_fileinfo(self, file_info):
        self.cached_file_list.append(file_info)
        self.update_table_data()


    ########################################################################################################################
    # delete_fileinfo
    # - file_info : 삭제하게 될 파일 정보가 들어있는 리스트(파일명, 경로)
    # = 인자로 받은 file_info를 통해 파일명과 경로명이 일치하는 파일 정보를 삭제하고, 테이블을 갱신하는 메소드를 호출한다. 
    ########################################################################################################################
    def delete_fileinfo(self, file_info):
        file_name = file_info[0]
        dir_name = file_info[1]

        for f in self.cached_file_list:
            if f[0] == file_name and f[1] == dir_name:
                self.cached_file_list.remove(f)
                break
        
        self.update_table_data()


    def processing_time_out(self):
        self.update_table_data(True)

########################################################################################################################
#     이벤트 핸들러 메소드
########################################################################################################################

    ####################################################################################################################
    # sort_data
    # - column_index : 선택 된 헤더의 column_index
    # = 헤더(File, Path, Size(kb))를 클릭했을 때 정렬을 수행하기 위한 이벤트 처리 메소드
    #   각 헤더 마다 가지고 있는 header_sorted_state 정보를 통해 해당 열에 대한 정렬 기준을 수립한다.
    #   False -> 오름 차순으로, True -> 내림 차순으로 적용
    ####################################################################################################################
    @pyqtSlot(int)
    def sort_data(self, column_index):
        self.table_model.layoutAboutToBeChanged.emit()
        table_data = self.table_model.getData()

        if self.header_sorted_state[column_index]: # 내림 차순
            table_data = sorted(table_data, key=lambda f: f[column_index] if column_index==2 else f[column_index].upper(), reverse = True)
            self.header_sorted_state[column_index] = False
        else: # 오름 차순
            table_data = sorted(table_data, key = lambda f: f[column_index] if column_index==2 else f[column_index].upper())
            self.header_sorted_state[column_index] = True

        self.table_model.setData(table_data)
        self.table_model.layoutChanged.emit()


    ####################################################################################################################
    # execute_file
    # - signal : 선택된 tableview의 entry에 대한 정보를 담고 있는 QModeIndex 객체
    # = 테이블 상에서 entry을 더블 클릭했을 때 파일 실행 또는 디렉토리 열기를 수행하기 위한 이벤트 처리 메소드
    #   경로를 더블 클릭 시 -> 해당 디렉토리 열기
    #   파일명 또는 사이즈를 더블 클릭 시 -> 해당 파일 실행
    ####################################################################################################################
    @pyqtSlot(QModelIndex)
    def execute_file(self, signal):
        row = signal.row()
        col = signal.column()

        if col == 1: # 파일 경로 더블 클릭 -> 해당 디렉토리 열기
            index = signal.sibling(row, col)
            index_dict = self.table_model.itemData(index)
            path = index_dict.get(0)
        else: # 파일 명 더블 클릭 -> 해당 파일 실행
            findex = signal.sibling(row, 0)
            findex_dict = self.table_model.itemData(findex)
            file_name = findex_dict.get(0)

            pindex = signal.sibling(row, 1)
            pindex_dict = self.table_model.itemData(pindex)
            path = pindex_dict.get(0)
            path = path + "\\" + file_name

        webbrowser.open(path)


    ####################################################################################################################
    # finish_scan
    # = scan_thread의 동작이 완료되었을 때을 위한 이벤트 처리 메소드
    #   start_thread 메소드를 통해 파일 변화를 감지하는 manager_observer_thread를 실행한다.
    #   또한 파일 시스템 스캔을 통해 얻은 파일 정보를 cached_file_list에 갱신한다.
    #   사용자 입력값에 따라 변경사항을 테이블에 표시한다.
    ####################################################################################################################
    @pyqtSlot(list)
    def finish_scan(self, file_list):
        self.finish_scan_flag = True
        self.cached_file_list = file_list
        self.update_table_data()


    ########################################################################################################################
    # finish_read
    # = read_db_thread 에 의해 프로그램 시작 후, DB에서 파일 정보를 읽어왔을 때 시그널을 받게 되는 메소드
    #   수집된 파일 정보를 나타내는 cached_file_list를 갱신하고, 해당 값을 테이블에 표시한다.
    ########################################################################################################################
    @pyqtSlot(list)
    def finish_read(self, file_list):
        self.cached_file_list = file_list
        self.displayFiles(file_list)


    ########################################################################################################################
    # update_table_data
    # = 사용자 입력값 변경 시 또는 파일 정보에 변화가 생겼을 때, 입력값을 기준으로 테이블에 표시할 파일 정보를 생성하는 메소드
    #   생성된 파일 정보를 displayFiles 메소드를 통해 테이블 나타낸다.
    ########################################################################################################################
    @pyqtSlot()
    def update_table_data(self, time_out = False):
        text = self.qle.text().upper()
        
        if self.count < 2 and len(text) > 0 and not time_out:
            # time check
            self.count = self.count + 1
            self.check_time.start()
            return
        
        self.count = 0
        
        # file_list의 첫번째 항목인 file_name을 토대로 text 값을 포함하고 있으면 displayed_file_list에 추가한다.
        
        displayed_file_list = [file_info for file_info in self.cached_file_list if text in file_info[0].upper()]
        self.displayFiles(displayed_file_list)

    ########################################################################################################################
    # control_updated_file
    # - file_infos : 파일 변경 감지에 따라 대상이 되는 파일 정보가 저장되어있는 리스트이며
    #   0번 인덱스는 실질적인 파일 정보가 들어가 있고,
    #   1번 인덱스에는 어떠한 파일 변경 이벤트가 발생했는지를 나타낸다.
    # = file_infos를 통해 파일 변경 이벤트를 구분하고, 각 이벤트에 맞게 테이블 갱신 및 DB 갱신을 수행하는 메소드를 호출한다.
    ########################################################################################################################
    @pyqtSlot(list)
    def control_updated_file(self, file_infos):
        mode = file_infos[1]
        file_info = file_infos[0]

        if mode == 3: # insert
            self.insert_fileinfo(file_info)
            self.insert_db_thread.set_file_info(file_info)

        elif mode == 4: # delete
            self.delete_fileinfo(file_info)
            self.delete_db_thread.set_file_info(file_info)

        self.start_thread(mode)


########################################################################################################################
# TableModel 클래스
# QAbstractTableModel 인터페이스를 상속받아 세부 메소드를 구현하고 있다.
# View - Model 관점에서 View는 단지 데이터를 나타내기 위한 객체이며, Model은 데이터 처리 또는 정의를 나타내는 객체이다.
# 이러한 Model의 객체에 대한 정의를 내리는 클래스이다.
########################################################################################################################
class TableModel(QAbstractTableModel):

    def __init__(self):
        super(TableModel, self).__init__()

    def setData(self, filelist):
        self._data = filelist

    def getData(self):
        return self._data

    def data(self, index, role):
        if role == Qt.DisplayRole:
            return self._data[index.row()][index.column()]

    def rowCount(self, index):
        return len(self._data)
    
    def columnCount(self, index):
        return 3


########################################################################################################################
# is_admin
# = 프로그램이 관리자 권한으로 실행되었는지 확인하기 위한 함수
########################################################################################################################
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

if __name__ == '__main__':
    freeze_support()

    # 실행 파일을 권리자 권한으로 수행하기 위해 사용하는 코드
    """
    if not is_admin(): 
        script = os.path.abspath(sys.argv[0])
        params = ' '.join([script] + sys.argv[1:])
    
        shell.ShellExecuteEx(nShow = 1, lpVerb = 'runas', lpFile = sys.executable, lpParameters=params)
        sys.exit()
    """
    
    try:
        app = QApplication(sys.argv)
        ex = UI()
        sys.exit(app.exec_())
    finally:
        pid = os.getpid()
        spid = str(pid)
        
        subprocess.run(args = ['taskkill', '/F', '/T', '/PID', spid], shell = False)
    
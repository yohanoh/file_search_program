import sys
import ctypes

from PyQt5.QtWidgets import QApplication, QWidget, QLineEdit, QVBoxLayout, QLabel, QTableView
from PyQt5.QtCore import pyqtSlot, QModelIndex, QAbstractTableModel, Qt
from DBManager import DBManager
import webbrowser

from UIthread import *
from multiprocessing import freeze_support

import time

########################################################################################################################
# UI 클래스
# UI 를 구성하기 위한 클래스
# UI 뿐만 아니라 각 UI 위젯 간의 시그널을 관리하기 위한 시그널 핸들러 함수도 정의하고 있다.
########################################################################################################################
class UI(QWidget):
    def __init__(self):
        super().__init__()
        self.DB = DBManager()
        self.file_list = []
        self.update_file_list = []

        self.manager_observer_thread = ManagerObserverThread()
        self.manager_observer_thread.detect_create_signal.connect(self.insert_file_info)

        # DB 정보를 읽기 위한 쓰레드
        self.read_db_thread = ReadDBThread()
        self.read_db_thread.set_db(self.DB)
        self.read_db_thread.finish_read_signal.connect(self.displayFiles)

        # 디렉토리를 탐색해서 파일 리스트를 얻은 후, DB에 insert 하는 작업까지 수행하는 쓰레드
        self.scan_thread = ScanThread()
        self.scan_thread.set_db(self.DB)
        self.scan_thread.finish_scan_signal.connect(self.finish_scan)
        self.start_scan_thread()
        
        self.first_displayed_flag = False
        
        self.initUI()


    ####################################################################################################################
    # initTable
    # = 테이블 표시를 위한 기본 설정을 하는 메소드이다.
    #   테이블의 entry를 클릭 했을 때, 파일이나 디렉토리를 실행하기 위한 이벤트(execute_file)를 연결해주고,
    #   테이블의 헤더를 클릭 했을 때 정렬 기능을 실행하기 위한 이벤트(sort_data)도 연결해준다.
    ####################################################################################################################
    def initTable(self):
        self.header_sorted_state = [False, False, False]
        self.table_model = TableModel()
        self.tableview.setSortingEnabled(True)
        self.start_read_db_thread()
        
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
        self.qle.textEdited.connect(self.update_table)

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

        if self.header_sorted_state[column_index]: # 오름 차순 정렬
            table_data = sorted(table_data, key = lambda f: f[column_index] if column_index==2 else f[column_index].upper())
            self.header_sorted_state[column_index] = False
        
        else: # 내림 차순 정렬
            table_data = sorted(table_data, key=lambda f: f[column_index] if column_index==2 else f[column_index].upper(), reverse = True)
            self.header_sorted_state[column_index] = True

        self.table_model.setData(table_data)
        self.table_model.layoutChanged.emit()

    ####################################################################################################################
    # execute_file
    # - signal : 선택된 tableview의 entry에 대한 정보를 담고 있는 QModeIndex 객체
    # = 테이블 상에서 entry을 더블 클릭했을 때 파일 실행을 수행하기 위한 이벤트 처리 메소드
    #   선택된 entry의 경로명을 토대로 파일을 실행하거나 디렉토리를 연다.
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
    #   백그라운드에서 계속 디렉토리 스캔을 수행하기 위해 다시 scan_thred을 실행한다.
    ####################################################################################################################
    @pyqtSlot(list)
    def finish_scan(self, file_list):
        print("scan completed!!")
        self.manager_observer_thread.start()

        if not self.first_displayed_flag: # 테이블에 아무런 정보가 없으면 갱신
            self.displayFiles(file_list)
        else: # 한 번이라도 테이블 갱신이 있었다면, file_list만 갱신해준다.
            self.file_list = file_list
        

    ####################################################################################################################
    # displayFiles
    # - file_list : 테이블 상에 표시한 파일들의 정보를 담고 있는 리스트 (파일 정보는 파일명, 경로, 크기를 튜플 형태로 저장)
    # = read_db_thread에 의해 db에서 파일 정보를 읽어왔을 때을 위한 이벤트 처리 메소드
    #   file_list를 통해 몇 개의 파일을 넘겨 받았는지를 Qlabel 위젯에 표시한다.
    #   또한 데이터를 표시하는 QtableView 에 기본 정보을 clear 해준 후, 데이터를 표시한다.
    ####################################################################################################################
    @pyqtSlot(list)
    def displayFiles(self, file_list):
        total = len(file_list)
        self.label.setText("총 {0} 개 검색됨".format(total))

        if not self.first_displayed_flag : self.file_list = file_list
        if total > 0: self.first_displayed_flag = True
        
        self.tableview.clearSpans()
        self.table_model.layoutAboutToBeChanged.emit()
        self.table_model.setData(file_list)
        self.table_model.layoutChanged.emit()

        self.tableview.setModel(self.table_model)
        self.tableview.resizeColumnsToContents()

    @pyqtSlot()
    def update_table(self):
        text = self.qle.text()

        # file_list의 첫번째 항목인 file_name을 토대로 text 값을 포함하고 있으면 displayed_file_list에 추가한다.
        displayed_file_list = [file_info for file_info in self.file_list if text.upper() in file_info[0].upper()]

        self.displayFiles(displayed_file_list)
        

    ####################################################################################################################
    # start_read_db_thread
    # - all_data : 디폴트 값으로 False로 설정되어있고, True로 설정되어있는 경우 DB에 저장되어있는 모든 파일 정보를 읽어온다.
    # = 사용자로부터 입력값이 발생했을 때을 위한 이벤트 처리 메소드
    #   scan_thread 나 read_db_thread 가 동작하고 있지 않을 경우, 사용자로부터 입력받은 문자열을 포함한 파일 정보를
    #   DB로부터 읽어온다.
    ####################################################################################################################
    def start_read_db_thread(self):
        self.read_db_thread.start()

    ####################################################################################################################
    # start_scan_thread
    # = 디렉토리 스캔을 수행하는 scan_thread 실행시키기 위한 메소드
    ####################################################################################################################
    def start_scan_thread(self):
        print("start scan")
        self.scan_thread.start()

    @pyqtSlot(tuple)
    def insert_file_info(self, file_info):
        self.file_list.append(file_info)
        self.update_file_list.append(file_info)    

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


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


if __name__ == '__main__':
    freeze_support()

    if not is_admin():
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, __file__, None, 1)
    
    
    app = QApplication(sys.argv)
    ex = UI()
    sys.exit(app.exec_())
    
import sys
from PyQt5.QtWidgets import QApplication, QWidget, QLineEdit, QVBoxLayout, QLabel, QTableView
from PyQt5.QtCore import *
from DBManager import DBManager
import webbrowser
import pandas as pd

from UIthread import ScanThread, ReadDBThread
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

        # DB 정보를 읽기 위한 쓰레드
        self.read_db_thread = ReadDBThread()
        self.read_db_thread.set_db(self.DB)
        self.read_db_thread.finish_read_signal.connect(self.displayFiles)

        # 디렉토리를 탐색해서 파일 리스트를 얻은 후, DB에 insert 하는 작업까지 수행하는 쓰레드
        self.scan_thread = ScanThread()
        self.scan_thread.set_db(self.DB)
        self.scan_thread.finish_scan_signal.connect(self.finish_scan)
        self.start_scan_thread()
        self.first_print = False

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
        self.start_read_db_thread(all_data=True)

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
        self.qle.textEdited.connect(self.start_read_db_thread)

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
        self.setGeometry(800, 200, 1500, 1000)
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

        if self.header_sorted_state[column_index]:
            self.table_model._data = self.table_model._data.sort_values(self.table_model.headers[column_index], ascending=False)
            self.header_sorted_state[column_index] = False
        else:
            self.table_model._data = self.table_model._data.sort_values(self.table_model.headers[column_index])
            self.header_sorted_state[column_index] = True

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

        index = signal.sibling(row, 1)
        index_dict = self.table_model.itemData(index)
        path = index_dict.get(0)

        webbrowser.open(path)

    ####################################################################################################################
    # finish_scan
    # = scan_thread의 동작이 완료되었을 때을 위한 이벤트 처리 메소드
    #   백그라운드에서 계속 디렉토리 스캔을 수행하기 위해 다시 scan_thred을 실행한다.
    ####################################################################################################################
    @pyqtSlot()
    def finish_scan(self):
        self.start_read_db_thread(all_data=True)
        print("scan completed!!")
        self.start_scan_thread()

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
        if total > 0: self.first_print = True

        self.tableview.clearSpans()

        self.table_model.layoutAboutToBeChanged.emit()
        self.table_model.setDataFrame(file_list)
        self.table_model.layoutChanged.emit()

        self.tableview.setModel(self.table_model)
        self.tableview.resizeColumnsToContents()

    ####################################################################################################################
    # start_read_db_thread
    # - all_data : 디폴트 값으로 False로 설정되어있고, True로 설정되어있는 경우 DB에 저장되어있는 모든 파일 정보를 읽어온다.
    # = 사용자로부터 입력값이 발생했을 때을 위한 이벤트 처리 메소드
    #   scan_thread 나 read_db_thread 가 동작하고 있지 않을 경우, 사용자로부터 입력받은 문자열을 포함한 파일 정보를
    #   DB로부터 읽어온다.
    ####################################################################################################################
    @pyqtSlot()
    def start_read_db_thread(self, all_data=False):
        if self.read_db_thread.read_running or self.scan_thread.scan_running:
            time.sleep(0.1)
            
        self.read_db_thread.set_finding_str(self.qle.text())
        self.read_db_thread.start(all_data)

    ####################################################################################################################
    # start_scan_thread
    # = 디렉토리 스캔을 수행하는 scan_thread 실행시키기 위한 메소드
    ####################################################################################################################
    def start_scan_thread(self):
        print("start scan")
        self.scan_thread.start()

########################################################################################################################
# TableModel 클래스
# QAbstractTableModel 인터페이스를 상속받아 세부 메소드를 구현하고 있다.
# View - Model 관점에서 View는 단지 데이터를 나타내기 위한 객체이며, Model은 데이터에 처리 또는 정의를 나타내는 객체이다.
# 이러한 Model의 객체에 대한 정의를 내리는 클래스이다.
########################################################################################################################
class TableModel(QAbstractTableModel):
    def __init__(self):
        super(TableModel, self).__init__()
        self.headers = ["File", "Path", "Size(bytes)"]

    def setDataFrame(self, filelist):
        self._data = pd.DataFrame(filelist, columns=self.headers)

    def data(self, index, role):
        if role == Qt.DisplayRole:
            row = index.row()
            col = index.column()
            value = self._data.iloc[row, col]

            return QVariant(str(value))

    def rowCount(self, parent=None):
        return len(self._data.index)

    def columnCount(self, parent=None):
        return len(self._data.columns.values)

    def headerData(self, section, orientation, role):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return str(self._data.columns[section])


if __name__ == '__main__':
    freeze_support()
    app = QApplication(sys.argv)
    ex = UI()
    sys.exit(app.exec_())

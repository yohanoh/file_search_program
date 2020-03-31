import sys
from PyQt5.QtWidgets import QApplication, QWidget, QLineEdit, QVBoxLayout, QLabel, QTableView
from PyQt5.QtCore import *
from DBManager import DBManager
from UIthread import ScanThread, ReadDBThread
from multiprocessing import freeze_support
import webbrowser
import time
import pandas as pd

#from UI_handler import *

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

        self.initUI()

    ####################################################################################################################
    # setTableData
    # - file_list : DB로 SQL 쿼리문을 통해 획득한, 테이블에 표시할 파일 정보(이름, 경로, 사이즈) 가 저장되어 있는 리스트
    # = file_list를 넘겨 받아 몇 개에 파일을 넘겨 받았는지를 label 위젯에 표시한다.
    #   데이터를 표시하는 tableview 에 기존 정보가 포함되어 있을 수 있으므로 clear 해준 후, 데이터를 표시한다.
    ####################################################################################################################
    def setTableData(self, file_list):
        total = len(file_list)
        self.label.setText("총 {0} 개 검색됨".format(total))
        self.tableview.clearSpans()

        self.table_model.setDataFrame(file_list)
        self.tableview.setModel(self.table_model)
        self.tableview.resizeColumnsToContents()

    ####################################################################################################################
    # setTable
    # = 테이블 표시를 위한 기본 설정을 하는 메소드이다.
    #   테이블의 entry를 클릭 했을 때, 파일이나 디렉토리를 실행하기 위한 이벤트(execute_file)를 연결해주고,
    #   테이블의 헤더를 클릭 했을 때 정렬 기능을 실행하기 위한 이벤트(sort_data)도 연결해준다.
    ####################################################################################################################
    def setTable(self):
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
        self.setTable()

        # UI 구성
        self.vbox = QVBoxLayout()
        self.vbox.addWidget(self.qle)
        self.vbox.addWidget(self.tableview)
        self.vbox.addWidget(self.label)

        self.setLayout(self.vbox)
        self.setWindowTitle('File Search Program')
        self.setGeometry(800, 200, 1500, 1000)
        self.show()

    ####################################################################################################################
    # 이벤트 핸들러 메소드
    ####################################################################################################################
    @pyqtSlot(int)
    def sort_data(self, column_index):
        print("sort")
        s = time.time()
        self.table_model.layoutAboutToBeChanged.emit()
        if self.header_sorted_state[column_index]:
            self.table_model._data = self.table_model._data.sort_values(self.table_model.headers[column_index])
            self.header_sorted_state[column_index] = False
        else:
            self.table_model._data = self.table_model._data.sort_values(self.table_model.headers[column_index], ascending=False)
            self.header_sorted_state[column_index] = True
        e = time.time()
        print("sorting time : ", e - s)

        self.table_model.layoutChanged.emit()

    # 숫자 정렬 구현하기... 숫자도 문자로 인식해서 정렬중..
    @pyqtSlot(QModelIndex)
    def execute_file(self, signal):
        row = signal.row()

        index = signal.sibling(row, 1)
        index_dict = self.table_model.itemData(index)
        path = index_dict.get(0)

        webbrowser.open(path)

    @pyqtSlot(bool)
    def finish_scan(self, check):
        print("scan completed!!")
        pass


    @pyqtSlot(list)
    def displayFiles(self, file_list):
        try:
            self.setTableData(file_list)
        except Exception as e:
            print("dis : ", e)

    # 사용자의 입력값이 변경될 때 실행되는 메소드
    @pyqtSlot()
    def start_read_db_thread(self, all_data=False):
        while self.scan_thread.scan_running or self.read_db_thread.read_running:
            text = self.qle.text()
            length = len(text)
            text = text[:length - 1]
            self.qle.setText(text)
            return

        self.read_db_thread.set_finding_str(self.qle.text())
        self.read_db_thread.start(all_data)

    @pyqtSlot()
    def start_scan_thread(self):
        self.scan_thread.start()


class TableModel(QAbstractTableModel):
    def __init__(self):
        super(TableModel, self).__init__()
        self.headers = ["File", "Path", "Size(KB)"]

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

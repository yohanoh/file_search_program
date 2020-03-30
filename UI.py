import sys
from PyQt5.QtWidgets import QApplication, QWidget, QTableWidget, QLineEdit, QVBoxLayout, QTableWidgetItem, QLabel, QTableView
from PyQt5.QtCore import *
from DBManager import DBManager
from UIthread import ScanThread, ReadDBThread
from multiprocessing import freeze_support
import webbrowser
import time
import pandas as pd

#from UI_handler import *


class UI(QWidget):
    def __init__(self):
        super().__init__()
        self.DB = DBManager()

        self.read_db_thread = ReadDBThread()
        self.read_db_thread.set_db(self.DB)
        self.read_db_thread.finish_read_signal.connect(self.displayFiles)

        self.scan_thread = ScanThread()
        self.scan_thread.set_db(self.DB)
        self.scan_thread.finish_scan_signal.connect(self.finish_scan)
        #self.start_scan_thread()

        self.initUI()

    """
    def setTable(self):
        column_headers = ['파일 이름', '파일 경로', '크기(KB)']
        self.tableWidget.setHorizontalHeaderLabels(column_headers)
        self.tableWidget.setColumnCount(3)
        self.header_sorted_state = [False, False, False]

        self.tableWidget.cellDoubleClicked.connect(self.execute_file)
        self.tableWidget.horizontalHeader().sectionClicked.connect(self.sort_data)

        self.start_read_db_thread(all_data = True)

    def setTableData(self, file_list):
        num_of_rows = len(file_list)
        self.tableWidget.setRowCount(num_of_rows)
        self.label.setText(str(num_of_rows) + " 개 검색됨")
        row = 0

        for file in file_list:
            name = file[0]
            path = file[1]
            size = str(file[2])

            self.tableWidget.setItem(row, 0, QTableWidgetItem(name))
            self.tableWidget.setItem(row, 1, QTableWidgetItem(path))
            self.tableWidget.setItem(row, 2, QTableWidgetItem(size))
            row = row + 1
            #if row == 20 :
             #   break

        self.tableWidget.resizeColumnsToContents()
        self.tableWidget.horizontalHeader().setStretchLastSection(True)

    """

    def setTableData(self, data):
        total = len(data)
        self.label.setText("총 {0} 개 검색됨".format(total))
        self.table_model.setData(data)
        self.tableview.setModel(self.table_model)
        self.tableview.resizeColumnsToContents()


    def setTable(self):
        self.table_model = TableModel()
        self.start_read_db_thread(all_data=True)
        self.tableview.doubleClicked.connect(self.execute_file)

    # 사용자 UI 초기화를 담당하는 메소드
    def initUI(self):

        # 사용자 입력을 받는 위젯
        self.qle = QLineEdit(self)
        self.qle.textEdited.connect(self.start_read_db_thread)

        # 검색된 결과의 개수를 표시하는 위젯
        self.label = QLabel(self)

        # 검색된 결과를 표시하는 위젯
        #self.tableWidget = QTableWidget(self)
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


    # 숫자 정렬 구현하기... 숫자도 문자로 인식해서 정렬중..
    @pyqtSlot(int)
    def sort_data(self, logicalIndex):
        s = time.time()
        if (self.header_sorted_state[logicalIndex]):
            self.tableview.sortItems(logicalIndex, Qt.AscendingOrder)
            self.header_sorted_state[logicalIndex] = False
        else:
            self.tableview.sortItems(logicalIndex, Qt.DescendingOrder)
            self.header_sorted_state[logicalIndex] = True
        e = time.time()
        print(e - s)

    @pyqtSlot()
    def execute_file(self):
        current_row = self.tableview.selectionModel().currentIndex().row()
        path = self.tableview.index(current_row, 1)
        print(path)
        webbrowser.open(path)

    @pyqtSlot(bool)
    def finish_scan(self, check):
        print("finish scan")
        pass

    @pyqtSlot(list)
    def displayFiles(self, file_list):
        self.setTableData(file_list)

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

    def setData(self, data):
        self._data = data

    def data(self, index, role):
        if role == Qt.DisplayRole:
            return self._data[index.row()][index.column()]

    def rowCount(self, index):
        return len(self._data)

    def columnCount(self, index):
        if len(self._data) == 0:
            return 0

        return len(self._data[0])


if __name__ == '__main__':
    freeze_support()
    app = QApplication(sys.argv)
    ex = UI()
    sys.exit(app.exec_())

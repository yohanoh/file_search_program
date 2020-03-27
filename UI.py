import sys
from PyQt5.QtWidgets import QApplication, QWidget, QTableWidget, QLineEdit, QVBoxLayout, QTableWidgetItem, QLabel
from PyQt5.QtCore import *
from DBManager import DBManager
from UIthread import ScanThread, ReadDBThread
from multiprocessing import freeze_support
import webbrowser


class UI(QWidget):

    def __init__(self):
        super().__init__()

        self.DB = DBManager()
        self.running = False
        self.scan_running = False

        self.read_db_thread = ReadDBThread()
        self.read_db_thread.set_db(self.DB)
        self.read_db_thread.finish_read_signal.connect(self.displayFiles)

        self.scan_thread = ScanThread()
        self.scan_thread.set_db(self.DB)
        self.scan_thread.finish_scan_signal.connect(self.finish_scan)
        #self.start_scan_thread()

        self.initUI()

    def setTable(self):
        column_headers = ['파일 이름', '파일 경로', '크기(KB)']
        self.tableWidget = QTableWidget(self)
        self.tableWidget.setHorizontalHeaderLabels(column_headers)
        self.tableWidget.setColumnCount(3)
        self.tableWidget.cellDoubleClicked.connect(self.execute_file)
        self.read_db_thread.start(True)


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

        self.tableWidget.resizeColumnsToContents()
        self.tableWidget.horizontalHeader().setStretchLastSection(True)

    # 사용자 UI 초기화를 담당하는 메소드
    def initUI(self):

        self.qle = QLineEdit(self)
        #self.qle.textChanged.connect(self.start_read_db_thread)
        self.qle.textEdited.connect(self.start_read_db_thread)

        self.label = QLabel(self)

        self.vbox = QVBoxLayout()
        self.vbox.addWidget(self.qle)
        self.vbox.addWidget(self.label)

        self.setTable()
        self.vbox.addWidget(self.tableWidget)

        self.setLayout(self.vbox)
        self.setWindowTitle('File Search Program')
        self.setGeometry(800, 200, 1500, 1000)
        self.show()

    @pyqtSlot()
    def execute_file(self):
        current_row = self.tableWidget.currentRow()
        path = self.tableWidget.item(current_row, 1).text()
        webbrowser.open(path)

    @pyqtSlot(bool)
    def finish_scan(self, check):
        self.scan_running = False
        print("finish scan")
        pass

    @pyqtSlot(list)
    def displayFiles(self, file_list):
        self.running = False
        self.setTableData(file_list)

    # 사용자의 입력값이 변경될 때 실행되는 메소드
    @pyqtSlot()
    def start_read_db_thread(self):
        while self.running:
            text = self.qle.text()
            length = len(text)
            text = text[:length-1]
            self.qle.setText(text)
            return

        self.running = True
        self.read_db_thread.set_finding_str(self.qle.text())
        self.read_db_thread.start()

    @pyqtSlot()
    def start_scan_thread(self):
        self.scan_running = True
        self.scan_thread.start()


if __name__ == '__main__':
    freeze_support()
    app = QApplication(sys.argv)
    ex = UI()
    sys.exit(app.exec_())

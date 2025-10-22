import sys
from PyQt6 import QtWidgets
from PyQt6.QtWidgets import QMainWindow, QDialog, QApplication, QStyleFactory
from PyQt6.uic import load_ui
from persistentdata import PersistentData
import bbsdialog
import stationiddialog


class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow,self).__init__()
        self.settings = PersistentData()
        if self.settings.getProfileBool("ShowStationIdAtStartup"):
            self.OnStationId()
        load_ui.loadUi("mainwindow.ui",self)
        self.cNew.clicked.connect(self.OnNewMessage)
        self.actionBBS.triggered.connect(self.OnBbsSetup)
        self.actionStation_ID.triggered.connect(self.OnStationId)

    def OnNewMessage(self):
        print("Hello world")
    def OnBbsSetup(self):
        bd = bbsdialog.BbsDialog(self.settings,self)
        bd.exec()
        #UpdateStatusBar()
    def OnStationId(self):
        sid = stationiddialog.StationIdDialog(self.settings,self)
        sid.exec()
        #UpdateStatusBar()



if __name__ == "__main__": 
    app = QApplication(sys.argv)
    app.setStyle(QStyleFactory.create("Fusion"))
    mainwindow = MainWindow()
    mainwindow.show()
    sys.exit(app.exec())

import sys
from PyQt6 import QtWidgets
from PyQt6.QtCore import QDateTime, pyqtSignal
from PyQt6.QtWidgets import QMainWindow
from PyQt6.uic import load_ui
from persistentdata import PersistentData

class ReadMessageDialog(QMainWindow):
    def __init__(self,pd,parent=None):
        super(ReadMessageDialog,self).__init__(parent)
        self.pd = pd
        load_ui.loadUi("readmessagedialog.ui",self)
    def setData(self,h,m):
        self.cBbs.setText(h[5])
        self.cFrom.setText(h[3])
        self.cTo.setText(h[4])
        self.cSubject.setText(h[7])
        self.cReceived.setText(h[9])
        self.cSent.setText(h[8])
        self.cMessageBody.setPlainText(m)

import sys
from PyQt6 import QtWidgets
from PyQt6.QtCore import QDateTime, pyqtSignal
from PyQt6.QtWidgets import QMainWindow
from PyQt6.uic import load_ui
from persistentdata import PersistentData
from mailfolder import MailBoxHeader

class ReadMessageDialog(QMainWindow):
    def __init__(self,pd,parent=None):
        super(ReadMessageDialog,self).__init__(parent)
        self.pd = pd
        load_ui.loadUi("readmessagedialog.ui",self)
    def setData(self,h,m):
        self.cBbs.setText(h.mBbs)
        self.cFrom.setText(h.mFrom)
        self.cTo.setText(h.mTo)
        self.cSubject.setText(h.mSubject)
        self.cReceived.setText(MailBoxHeader.toOutpostDate(h.mDateReceived))
        self.cSent.setText(MailBoxHeader.toOutpostDate(h.mDateSent))
        self.cMessageBody.setPlainText(m)

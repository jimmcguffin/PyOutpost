import sys
from PyQt6 import QtWidgets
from PyQt6.QtCore import QDateTime, pyqtSignal
from PyQt6.QtWidgets import QMainWindow
from PyQt6.uic import load_ui
from persistentdata import PersistentData
from mailfolder import MailBoxHeader

class ReadMessageDialog(QMainWindow):
    def __init__(self,pd,parent=None):
        super().__init__(parent)
        self.pd = pd
        load_ui.loadUi("readmessagedialog.ui",self)
    def prepopulate(self,h,m):
        self.cBbs.setText(h.bbs)
        self.cFrom.setText(h.from_addr)
        self.cTo.setText(h.to_addr)
        self.cSubject.setText(h.subject)
        self.cReceived.setText(MailBoxHeader.to_outpost_date(h.date_received))
        self.cSent.setText(MailBoxHeader.to_outpost_date(h.date_sent))
        self.cMessageBody.setPlainText(m)

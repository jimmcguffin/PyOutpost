import sys
from PyQt6 import QtWidgets
from PyQt6.QtCore import QDateTime, pyqtSignal
from PyQt6.QtWidgets import QMainWindow
from PyQt6.uic import load_ui
from persistentdata import PersistentData
from mailfolder import MailBoxHeader

class NewPacketMessage(QMainWindow):
    signalNewOutgoingMessage = pyqtSignal(MailBoxHeader,str)
    def __init__(self,pd,parent=None):
        super().__init__(parent)
        self.pd = pd
        load_ui.loadUi("newpacketmessage.ui",self)
        t = self.pd.getProfile("MessageSettings/DefaultNewMessageType","P")
        if t == "P": self.cMessageTypePrivate.setChecked(True)
        elif t == "B": self.cMessageTypeBulletin.setChecked(True)
        elif t == "N": self.cMessageTypeNts.setChecked(True)
        else: self.cNewDefaultPrivate.setChecked(True)
        self.actionSend.triggered.connect(self.onSend)
        self.cSend.clicked.connect(self.onSend)
        self.cBBS.setText(self.pd.getBBS("ConnectName"))
        self.cFrom.setText(self.pd.getActiveCallSign()) # gets user or tactical
        subject = self.pd.makeStandardSubject()
        self.cSubject.setText(subject)
    def setInitalData(self,subject,message,urgent=False):
        self.cSubject.setText(subject)
        self.cMessage.setPlainText(message)
        self.cUrgent.setChecked(urgent)
    def onSend(self):
        message = self.cMessage.toPlainText()
        if not message:
            message = '\n'
        else:
            if message[-1] != '\n':
                message += '\n'
        mbh = MailBoxHeader()
        mbh.urgent = "Y" if self.cUrgent.isChecked() else ""
        if self.cMessageTypeBulletin.isChecked(): mbh.type = "B"
        elif self.cMessageTypeNts.isChecked(): mbh.type = "N"
        else: mbh.type = "" # blank means private
        mbh.from_addr = self.cFrom.text()
        mbh.to_addr = self.cTo.text()
        mbh.bbs = self.cBBS.text()
        #mbh.local_id = ""
        mbh.subject = self.cSubject.text()
        mbh.date_sent = MailBoxHeader.normalized_date()
        #mbh.date_received = "" # in ISO-8601 format
        mbh.size = len(message)
        self.signalNewOutgoingMessage.emit(mbh,message)
        self.close()

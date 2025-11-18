import sys
from PyQt6 import QtWidgets
from PyQt6.QtCore import QDateTime, pyqtSignal
from PyQt6.QtWidgets import QMainWindow
from PyQt6.uic import load_ui
from persistentdata import PersistentData
from mailfolder import MailBoxHeader, MailFlags

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
    def setInitialData(self,subject,message,urgent=False):
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
        h1 = f"Date: {MailBoxHeader.to_in_mail_date()}"
        h2 = f"From: {self.cFrom.text()}"
        h3 = f"To: {self.cTo.text()}"
        h4 = f"Subject: {self.cSubject.text()}"
        urg = ""
        if self.cUrgent.isChecked():
            mbh.flags |= MailFlags.IS_URGENT.value
            urg = "!URG!"
        message = f"{h1}\n{h2}\n{h3}\n{h4}\n\n{urg}{message}"
        # want this to work however we get the message, so support all of "\r\n", "\r", "\n"
        #message = message.replace("\r\n","\n").replace("\r","\n").replace("\n","\r\n")
        message = message.replace("\r\n","\n").replace("\r","\n") # if you want just "\n" in mail file
        if self.cMessageTypeBulletin.isChecked(): mbh.set_type(1)
        elif self.cMessageTypeNts.isChecked(): mbh.set_type(2)
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

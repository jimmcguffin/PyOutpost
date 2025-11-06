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
        super(NewPacketMessage,self).__init__(parent)
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
        mbh.mUrgent = "Y" if self.cUrgent.isChecked() else ""
        if self.cMessageTypeBulletin.isChecked(): mbh.mType = "B"
        elif self.cMessageTypeNts.isChecked(): mbh.mType = "N"
        else: mbh.mType = "" # blank means private
        mbh.mFrom = self.cFrom.text()
        mbh.mTo = self.cTo.text()
        mbh.mBbs = self.cBBS.text()
        #mbh.mLocalId = ""
        mbh.mSubject = self.cSubject.text()
        mbh.mDateSent = MailBoxHeader.normalizedDate()
        #mbh.mDateReceived = "" # in ISO-8601 format
        mbh.mSize = len(message)
        self.signalNewOutgoingMessage.emit(mbh,message)
        self.close()

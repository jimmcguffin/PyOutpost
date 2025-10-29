import sys
from PyQt6 import QtWidgets
from PyQt6.QtCore import QDateTime, pyqtSignal
from PyQt6.QtWidgets import QMainWindow
from PyQt6.uic import load_ui
from persistentdata import PersistentData

class NewPacketMessage(QMainWindow):
    signalNewMessage = pyqtSignal(str,str,str)
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
        subject = ""
        if self.pd.getProfileBool("MessageSettings/AddMessageNumber"):
            subject += self.pd.getUserCallSign("MessagePrefix")
        f = self.pd.getProfile("MessageSettings/Hyphenation_flag")
        if f == 0:
            subject += str(self.pd.getAndIncrementNextMessageNumber())
        elif f == 1:
            subject += "-"+str(self.pd.getAndIncrementNextMessageNumber())
        elif f == 2:
            dt = QDateTime.currentDateTime()
            subject += dt.toString("yyMMddHHmmss")
        if self.pd.getProfileBool("MessageSettings/AddCharacter"):
            subject += self.pd.getProfile("MessageSettings/CharacterToAdd")
        if self.pd.getProfileBool("MessageSettings/AddMessageNumberSeparator"):
            subject += ":"
        self.cSubject.setText(subject)

    def onSend(self):
        message = self.cMessage.toPlainText()
        self.signalNewMessage.emit(self.cTo.text(),self.cSubject.text(),message)

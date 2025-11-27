import sys
from PyQt6 import QtWidgets
from PyQt6.QtWidgets import QDialog, QInputDialog
from PyQt6.uic import load_ui
from persistentdata import PersistentData

class StationIdDialog(QDialog):
    def __init__(self,pd,parent=None):
        super(StationIdDialog,self).__init__(parent)
        self.pd = pd
        load_ui.loadUi("stationiddialog.ui",self)
        self.tabWidget.setCurrentIndex(0)
        self.cCurrentProfile.setText(self.pd.getActiveProfile())
        self.loadUserCallSigns()
        self.need_save1 = False
        self.load1()
        self.loadTacticalCallSigns()
        self.need_save2 = False
        self.load2()
        self.cUseTactical.setChecked(self.pd.getProfileBool("UseTacticalCallSign"))
        self.cShowAtStartup.setChecked(self.pd.getProfileBool("ShowStationIdAtStartup"))
        self.cUserCallSign.currentTextChanged.connect(self.onUserCallSignChanged)
        self.cTacticalCallSign.currentTextChanged.connect(self.onTacticalCallSignChanged)
        self.cNewUser.clicked.connect(self.onNewUserClicked)
        self.cNewTactical.clicked.connect(self.onNewTacticalClicked)

    def accept(self):
        self.save1()
        self.save2()
        self.pd.setProfile("UseTacticalCallSign",self.cUseTactical.isChecked())
        self.pd.setProfile("ShowStationIdAtStartup",self.cShowAtStartup.isChecked())
        return super().accept()
    
    def loadUserCallSigns(self):
        self.cUserCallSign.blockSignals(True)
        self.cUserCallSign.clear()
        csl = self.pd.getUserCallSigns()
        self.cUserCallSign.addItems(csl)
        ucs = self.pd.getActiveUserCallSign()
        self.cUserCallSign.setCurrentText(ucs)
        self.cUserCallSign.blockSignals(False)
        
    def load1(self):
        self.need_save1 = True
        self.cUserName.setText(self.pd.getUserCallSign("Name"))
        self.cUserMessageIdPrefix.setText(self.pd.getUserCallSign("MessagePrefix"))
       
    def save1(self):
        if self.need_save1 == False: return
        self.pd.setUserCallSign("Name",self.cUserName.text())
        self.pd.setUserCallSign("MessagePrefix",self.cUserMessageIdPrefix.text())
        self.need_save1 = False
    
    def loadTacticalCallSigns(self):
        self.cTacticalCallSign.blockSignals(True)
        self.cTacticalCallSign.clear()
        csl = self.pd.getTacticalCallSigns()
        self.cTacticalCallSign.addItems(csl)
        ucs = self.pd.getActiveTacticalCallSign()
        self.cTacticalCallSign.setCurrentText(ucs)
        self.cTacticalCallSign.blockSignals(False)
        
    def load2(self):
        self.need_save2 = True
        self.cTacticalName.setText(self.pd.getTacticalCallSign("Name"))
        self.cTacticalMessageIdPrefix.setText(self.pd.getTacticalCallSign("MessagePrefix"))

    def save2(self):
        if self.need_save2 == False: return
        self.pd.setTacticalCallSign("Name",self.cTacticalName.text())
        self.pd.setTacticalCallSign("MessagePrefix",self.cTacticalMessageIdPrefix.text())
        self.need_save2 = False
    
    def onUserCallSignChanged(self,str):
        self.save1()
        self.pd.setActiveUserCallSign(str)
        self.load1()

    def onTacticalCallSignChanged(self,str):
        self.save2()
        self.pd.setActiveTacticalCallSign(str)
        self.load2()

    def onNewUserClicked(self):
        text, ok = QInputDialog.getText(self,"New User Call Sign","New call sign")
        if ok and text:
            prefix = text[-3:] if len(text) >= 3 else text
            self.pd.addUserCallSign(text,"",prefix)
            self.loadUserCallSigns()
            self.cUserCallSign.setCurrentText(text)
            self.cUserMessageIdPrefix.setText(prefix)
            if self.cTacticalCallSign.count() == 0:
                self.pd.setActiveUserCallSign(str)

    def onNewTacticalClicked(self):
        text, ok = QInputDialog.getText(self,"New Tactical Call Sign","New call sign")
        if ok and text:
            prefix = text[-3:] if len(text) >= 3 else text
            self.pd.addTacticalCallSign(text,"",prefix)
            self.loadTacticalCallSigns()
            self.cTacticalCallSign.setCurrentText(text)
            self.cTacticalMessageIdPrefix.setText(prefix)
            if self.cTacticalCallSign.count() == 0:
                self.pd.setActiveTacticalCallSign(text)


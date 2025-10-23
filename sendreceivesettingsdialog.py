import sys
from PyQt6 import QtWidgets
from PyQt6.QtWidgets import QDialog, QInputDialog
from PyQt6.uic import load_ui
from persistentdata import PersistentData

class SendReceiveSettingsDialog(QDialog):
    def __init__(self,pd,parent=None):
        super(SendReceiveSettingsDialog,self).__init__(parent)
        self.pd = pd
        load_ui.loadUi("sendreceivesettingsdialog.ui",self)
        self.tabWidget.setCurrentIndex(0)
        self.need_save = False
        self.load()
        #self.cX.currentTextChanged.connect(self.onXChanged)
        #self.cNewX.clicked.connect(self.onNewXClicked)

    def accept(self):
        self.save()
        return super().accept()
    
    def load(self):
        a = self.pd.getProfile("SRSettings/Automation/Automation")
        if a == "Manual": self.cManual.setChecked(True)
        elif a == "EveryN": self.cEveryN.setChecked(True)
        elif a == "EveryX": self.cEveryX.setChecked(True)
        else: self.cManual.setChecked(True)
        self.cEveryNTime.setValue(int(self.pd.getProfile("SRSettings/Automation/EveryN","0")))
        self.cEveryXList.setText(self.pd.getProfile("SRSettings/Automation/EveryX"))
        self.cSendImmediate.setChecked(self.pd.getProfileBool("SRSettings/Automation/SendImmediate"))
        sr = self.pd.getProfile("SRSettings/Button")
        if sr == "SendReceive": self.cSendReceive.setChecked(True)
        elif sr == "SendOnly": self.cSendOnly.setChecked(True)
        elif sr == "ReceiveOnly": self.cReceiveOnly.setChecked(True)
        else: self.cSendReceive.setChecked(True)
        self.need_save = True
       
    def save(self):
        if not self.need_save: return
        if self.cManual.isChecked():
            self.pd.setProfile("SRSettings/Automation/Automation","Manual")
        elif self.cEveryN.isChecked():
            self.pd.setProfile("SRSettings/Automation/Automation","EveryN")
        elif self.cEveryX.isChecked():
            self.pd.setProfile("SRSettings/Automation/Automation","EveryX")
        else:
            self.pd.setProfile("SRSettings/Automation/Automation","Manual")
        self.pd.setProfile("SRSettings/Automation/EveryN",str(self.cEveryNTime.value()));
        self.pd.setProfile("SRSettings/Automation/EveryX",self.cEveryXList.text())
        self.pd.setProfile("SRSettings/Automation/SendImmediate",self.cSendImmediate.isChecked())
        if self.cSendReceive.isChecked():
            self.pd.setProfile("SRSettings/Button","SendReceive")
        elif self.cSendOnly.isChecked():
            self.pd.setProfile("SRSettings/Button","SendOnly")
        elif self.cReceiveOnly.isChecked():
            self.pd.setProfile("SRSettings/Button","ReceiveOnly")
        else:
            self.pd.setProfile("SRSettings/Button","SendReceive")
        self.need_save = False
    
#  def onXChanged(self,str):
#       self.save()
#       self.pd.setX(str)
#      self.load()
#
#   def onNewXClicked(self):
#       text, ok = QInputDialog.getText(self,"New User Call Sign","New call sign")
#       if ok and text:
#           prefix = text[-3:] if len(text) >= 3 else text
#           self.pd.addUserCallSign(text,"",prefix)
#           self.loadUserCallSigns()
#           self.cUserCallSign.setCurrentText(text)

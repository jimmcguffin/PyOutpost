import sys
from PyQt6 import QtWidgets
from PyQt6.QtWidgets import QDialog, QInputDialog
from PyQt6.uic import load_ui
from persistentdata import PersistentData

class InterfaceDialog(QDialog):
    def __init__(self,pd,parent=None):
        super().__init__(parent)
        self.pd = pd
        load_ui.loadUi("interfacedialog.ui",self)
        self.tabWidget.setCurrentIndex(0)
        self.need_save = False
        self.loadInterfaces()
        self.load()
        self.cInterfaceName.currentTextChanged.connect(self.onInterfaceChanged)
        self.cNew.clicked.connect(self.onNewClicked)

    def accept(self):
        self.save()
        return super().accept()
    
    def loadInterfaces(self):
        self.cInterfaceName.blockSignals(True)
        self.cInterfaceName.clear()
        self.cInterfaceName.addItems(self.pd.getInterfaces())
        self.cInterfaceName.setCurrentText(self.pd.getActiveInterface())
        self.cInterfaceName.blockSignals(False)
    
    def load(self):
        # this happens later	self.cComPort.setCurrentText(self.pd.GetInterface("ComPort","Com1"))
        # page 1
        self.cDescription.setPlainText(self.pd.getInterface("Description"))
        # page 2
        self.cPromptCommand.setText(self.pd.getInterface("PromptCommand"))
        self.cPromptTimeout.setText(self.pd.getInterface("PromptTimeout"))
        self.cPromptConnected.setText(self.pd.getInterface("PromptConnected"))
        self.cPromptDisconnected.setText(self.pd.getInterface("PromptDisconnected"))
        # page 3
        self.cCommandMyCall.setText(self.pd.getInterface("CommandMyCall"))
        self.cCommandConnect.setText(self.pd.getInterface("CommandConnect"))
        self.cCommandRetry.setText(self.pd.getInterface("CommandRetry"))
        self.cCommandConvers.setText(self.pd.getInterface("CommandConvers"))
        self.cCommandDayTime.setText(self.pd.getInterface("CommandDayTime"))
        self.cIncludeCommandPrefix.setChecked(self.pd.getInterfaceBool("IncludeCommandPrefix"))
        self.cCommandPrefix.setText(self.pd.getInterface("CommandPrefix"))
        # page 4
        self.cAlwaysSendInitCommands.setChecked(self.pd.getInterfaceBool("AlwaysSendInitCommands"))
        sl1 = self.pd.getInterface("CommandsBefore")
        sl2 = self.pd.getInterface("CommandsAfter")
        self.cCommandsBefore.clear()
        self.cCommandsAfter.clear()
        if sl1:
            for s in sl1: 
                self.cCommandsBefore.appendPlainText(s)
        if sl2:
            for s in sl2: 
                self.cCommandsAfter.appendPlainText(s)
        # page 5
        self.cBaud.setCurrentText(self.pd.getInterface("Baud"))
        self.cParity.setCurrentText(self.pd.getInterface("Parity"))
        self.cDataBits.setCurrentText(self.pd.getInterface("DataBits"))
        self.cStopBits.setCurrentText(self.pd.getInterface("StopBits"))
        self.cFlowControl.setCurrentText(self.pd.getInterface("FlowControl"))
        self.need_save = True
       
    def save(self):
        if not self.need_save: return
        # page 1
        self.pd.setInterface("Description",self.cDescription.toPlainText())
        # page 2
        self.pd.setInterface("PromptCommand",self.cPromptCommand.text())
        self.pd.setInterface("PromptTimeout",self.cPromptTimeout.text())
        self.pd.setInterface("PromptConnected",self.cPromptConnected.text())
        self.pd.setInterface("PromptDisconnected",self.cPromptDisconnected.text())
        # page 3
        self.pd.setInterface("CommandMyCall",self.cCommandMyCall.text())
        self.pd.setInterface("CommandConnect",self.cCommandConnect.text())
        self.pd.setInterface("CommandRetry",self.cCommandRetry.text())
        self.pd.setInterface("CommandConvers",self.cCommandConvers.text())
        self.pd.setInterface("CommandDayTime",self.cCommandDayTime.text())
        self.pd.setInterface("IncludeCommandPrefix",self.cIncludeCommandPrefix.isChecked())
        self.pd.setInterface("CommandPrefix",self.cCommandPrefix.text())
        # page 4
        self.pd.setInterface("AlwaysSendInitCommands",self.cAlwaysSendInitCommands.isChecked())
        cb = self.cCommandsBefore.toPlainText()
        ca = self.cCommandsAfter.toPlainText()
        self.pd.setBBS("CommandsBefore",cb.splitlines())
        self.pd.setBBS("CommandsAfter",ca.splitlines())
        # page 5
        self.pd.setInterface("ComPort",self.cComPort.currentText())
        self.pd.setInterface("Baud",self.cBaud.currentText())
        self.pd.setInterface("Parity",self.cParity.currentText())
        self.pd.setInterface("DataBits",self.cDataBits.currentText())
        self.pd.setInterface("StopBits",self.cStopBits.currentText())
        self.pd.setInterface("FlowControl",self.cFlowControl.currentText())

        self.need_save = False
    
    def onInterfaceChanged(self,str):
        self.save()
        self.pd.setActiveInterface(str)
        self.load()

    def onNewClicked(self):
        text, ok = QInputDialog.getText(self,"New Interface","New interface")
        if ok and text:
            prefix = text[-3:] if len(text) >= 3 else text
            self.pd.addUserCallSign(text,"",prefix)
            self.loadUserCallSigns()
            self.cUserCallSign.setCurrentText(text)

    def setComPortList(self,ports):
        self.cComPort.clear()
        self.cComPort.addItems(ports)
        # select the one that matches best
        tmp = self.pd.getInterface("ComPort")
        if tmp:
            for i in range(len(ports)):
                if ports[i].startswith(tmp):
                    self.cComPort.setCurrentIndex(i)
        #self.cComPort.setCurrentText()
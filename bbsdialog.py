import sys
from PyQt6 import QtWidgets
from PyQt6.QtWidgets import QDialog, QInputDialog
from PyQt6.uic import load_ui
from persistentdata import PersistentData

class BbsDialog(QDialog):
    def __init__(self,pd,parent=None):
        super().__init__(parent)
        self.pd = pd
        load_ui.loadUi("bbsdialog.ui",self)
        self.tabWidget.setCurrentIndex(0)
        self.need_save = False
        self.loadBBSs()
        self.load()
        self.cBbsName.currentTextChanged.connect(self.onBbsNameChanged)
        self.cNew.clicked.connect(self.onNewClicked)

    def accept(self):
        self.save()
        return super().accept()
    
    def loadBBSs(self):
        self.cBbsName.blockSignals(True)
        self.cBbsName.clear()
        self.cBbsName.addItems(self.pd.getBBSs())
        self.cBbsName.setCurrentText(self.pd.getActiveBBS())
        self.cBbsName.blockSignals(False)
    
    def load(self):
        self.need_save = True
        # page 1
        self.cConnectName.setText(self.pd.getBBS("ConnectName"))
        self.cDescription.setPlainText(self.pd.getBBS("Description"))
        # page 2
        # page 3
        self.cCommandSend.setText(self.pd.getBBS("CommandSend"))
        self.cCommandSendBulletin.setText(self.pd.getBBS("CommandSendBulletin"))
        self.cCommandSendNTS.setText(self.pd.getBBS("CommandSendNTS"))
        self.cCommandListMine.setText(self.pd.getBBS("CommandListMine"))
        self.cCommandListBulletin.setText(self.pd.getBBS("CommandListBulletin"))
        self.cCommandListNts.setText(self.pd.getBBS("CommandListNts"))
        self.cCommandListFiltered.setText(self.pd.getBBS("CommandListFiltered"))
        self.cCommandRead.setText(self.pd.getBBS("CommandRead"))
        self.cCommandDelete.setText(self.pd.getBBS("CommandDelete"))
        self.cCommandBye.setText(self.pd.getBBS("CommandBye"))
        # page 4
        if self.pd.getBBSBool("AlwaysSendInitCommands"):
            self.cAlwaysSendInitCommands.setChecked(True)
        else:
            self.cNeverSendInitCommands.setChecked(True)
        sl1 = self.pd.getBBS("CommandsBefore")
        sl2 = self.pd.getBBS("CommandsAfter")
        self.cCommandsBefore.clear()
        self.cCommandsAfter.clear()
        if sl1:
            for s in sl1: 
                self.cCommandsBefore.appendPlainText(s)
        if sl2:
            for s in sl2: 
                self.cCommandsAfter.appendPlainText(s)
        # page 5
        self.cRetrievePrivateMessages.setChecked(self.pd.getBBSBool("RetrievePrivateMessages"))
        self.cRetrieveNtsMessages.setChecked(self.pd.getBBSBool("RetrieveNtsMessages"))
        self.cRetrieveBulletins.setChecked(self.pd.getBBSBool("RetrieveBulletins"))
        self.cSkipNtsMessagesThatISend.setChecked(self.pd.getBBSBool("SkipNtsMessagesThatISend"))
        self.cSkipBulletinsThatISend.setChecked(self.pd.getBBSBool("SkipBulletinsThatISend"))
        self.cKeepMessagesOnBBS.setChecked(self.pd.getBBSBool("KeepMessagesOnBBS"))
        b = self.pd.getBBS("RetrieveBulletins_flag")
        if b == "All":
            self.cAllNewBulletins.setChecked(True)
        elif b == "Selected":
            self.cSelectedBulletins.setChecked(True)
        elif b == "Custom":
            self.cCustomRetrieval.setChecked(True)
        else:
            self.cAllNewBulletins.setChecked(True)
        # page 6

    def save(self):
        if not self.need_save: return
        # page 1
        print(f"current bbs is {self.pd.getActiveBBS()} Writing {self.cDescription.toPlainText()} to file")
        self.pd.setBBS("ConnectName",self.cConnectName.text())
        self.pd.setBBS("Description",self.cDescription.toPlainText())
        # page 2
        # page 3
        self.pd.setBBS("CommandSend",self.cCommandSend.text())
        self.pd.setBBS("CommandSendBulletin",self.cCommandSendBulletin.text())
        self.pd.setBBS("CommandSendNTS",self.cCommandSendNTS.text())
        self.pd.setBBS("CommandListMine",self.cCommandListMine.text())
        self.pd.setBBS("CommandListBulletin",self.cCommandListBulletin.text())
        self.pd.setBBS("CommandListNts",self.cCommandListNts.text())
        self.pd.setBBS("CommandListFiltered",self.cCommandListFiltered.text())
        self.pd.setBBS("CommandRead",self.cCommandRead.text())
        self.pd.setBBS("CommandDelete",self.cCommandDelete.text())
        self.pd.setBBS("CommandBye",self.cCommandBye.text())
        # page 4
        self.pd.setBBS("AlwaysSendInitCommands",self.cAlwaysSendInitCommands.isChecked())
        cb = self.cCommandsBefore.toPlainText()
        ca = self.cCommandsAfter.toPlainText()
        self.pd.setBBS("CommandsBefore",cb.splitlines())
        self.pd.setBBS("CommandsAfter",ca.splitlines())
        # page 5
        self.pd.setBBS("RetrievePrivateMessages",self.cRetrievePrivateMessages.isChecked())
        self.pd.setBBS("RetrieveNtsMessages",self.cRetrieveNtsMessages.isChecked())
        self.pd.setBBS("RetrieveBulletins",self.cRetrieveBulletins.isChecked())
        self.pd.setBBS("SkipNtsMessagesThatISend",self.cSkipNtsMessagesThatISend.isChecked())
        self.pd.setBBS("SkipBulletinsThatISend",self.cSkipBulletinsThatISend.isChecked())
        self.pd.setBBS("KeepMessagesOnBBS",self.cKeepMessagesOnBBS.isChecked())
        if self.cAllNewBulletins.isChecked():
            self.pd.setBBS("RetrieveBulletins_flag","All")
        elif self.cSelectedBulletins.isChecked():
            self.pd.setBBS("RetrieveBulletins_flag","Selected")
        elif self.cCustomRetrieval.isChecked():
            self.pd.setBBS("RetrieveBulletins_flag","Custom")
        else:
            self.pd.setBBS("RetrieveBulletins_flag","All")
        # page 6

        self.need_save = False
    
    def onBbsNameChanged(self,str):
        self.save()
        self.pd.setActiveBBS(str)
        self.load()

    def onNewClicked(self):
        text, ok = QInputDialog.getText(self,"New BBS","New BBS")
        if ok and text:
            self.pd.addBBS(text,"")
            self.loadBBSs()
            self.cBbsName.setCurrentText(text)
            if self.cBbsName.count() == 1:
                self.cBbsName.currentTextchanged(text)

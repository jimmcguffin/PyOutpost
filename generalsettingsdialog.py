import sys
from PyQt6 import QtWidgets
from PyQt6.QtWidgets import QDialog, QInputDialog
from PyQt6.uic import load_ui
from persistentdata import PersistentData

class GeneralSettingsDialog(QDialog):
    def __init__(self,pd,parent=None):
        super(GeneralSettingsDialog,self).__init__(parent)
        self.pd = pd
        load_ui.loadUi("GeneralSettingsdialog.ui",self)
        self.tabWidget.setCurrentIndex(0)
        self.need_save = False
        self.load()

    def accept(self):
        self.save()
        return super().accept()
    
    def load(self):
        self.need_save = True
        self.cShowStationIdAtStartup.setChecked(self.pd.getProfileBool("ShowStationIdAtStartup"))
        self.cShowTimeAtStartup.setChecked(self.pd.getProfileBool("ShowTimeAtStartup"))
        self.cFolder_1.setText(self.pd.getProfile("GeneralSettings/Folder1","Folder 1"))
        self.cFolder_2.setText(self.pd.getProfile("GeneralSettings/Folder2","Folder 2"))
        self.cFolder_3.setText(self.pd.getProfile("GeneralSettings/Folder3","Folder 3"))
        self.cFolder_4.setText(self.pd.getProfile("GeneralSettings/Folder4","Folder 4"))
        self.cFolder_5.setText(self.pd.getProfile("GeneralSettings/Folder5","Folder 5"))
    def save(self):
        if not self.need_save: return
        self.pd.setProfile("ShowStationIdAtStartup",self.cShowStationIdAtStartup.isChecked())
        self.pd.setProfile("ShowTimeAtStartup",self.cShowTimeAtStartup.isChecked())
        self.pd.setProfile("GeneralSettings/Folder1",self.cFolder_1.text())
        self.pd.setProfile("GeneralSettings/Folder2",self.cFolder_2.text())
        self.pd.setProfile("GeneralSettings/Folder3",self.cFolder_3.text())
        self.pd.setProfile("GeneralSettings/Folder4",self.cFolder_4.text())
        self.pd.setProfile("GeneralSettings/Folder5",self.cFolder_5.text())
        self.need_save = False
    

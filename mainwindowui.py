import sys
from PyQt6 import QtWidgets
from PyQt6.QtWidgets import QMainWindow, QDialog, QInputDialog, QApplication, QStyleFactory, QLabel, QFrame, QStatusBar
from PyQt6.uic import load_ui
from PyQt6.QtSerialPort import QSerialPortInfo
from persistentdata import PersistentData
import bbsdialog
import interfacedialog
import stationiddialog
import sendreceivesettingsdialog
import messagesettingsdialog


class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow,self).__init__()
        self.settings = PersistentData()
        self.settings.setActiveProfile("Outpost") # todo: 
        if self.settings.getProfileBool("ShowStationIdAtStartup"):
            self.OnStationId()
        load_ui.loadUi("mainwindow.ui",self)
        self.cNew.clicked.connect(self.OnNewMessage)
        self.actionBBS.triggered.connect(self.OnBbsSetup)
        self.actionInterface.triggered.connect(self.OnInterfaceSetup)
        self.actionStation_ID.triggered.connect(self.OnStationId)
        self.actionSend_Receive_Settings.triggered.connect(self.onSendReceiveSettings)
        self.actionMessage_Settings.triggered.connect(self.onMessageSettings)
        self.cProfile.currentTextChanged.connect(self.onProfileChanged)
        self.actionNewProfile.triggered.connect(self.onNewProfile)
        self.cStatusLeft = QLabel()
        self.cStatusLeft.setFrameShape(QFrame.Shape.Panel)
        self.cStatusLeft.setFrameShadow(QFrame.Shadow.Sunken)
        self.cStatusCenter = QLabel()
        self.cStatusCenter.setFrameShape(QFrame.Shape.Panel)
        self.cStatusCenter.setFrameShadow(QFrame.Shadow.Sunken)
        self.cStatusRight1 = QLabel("R1")
        self.cStatusRight1.setFrameShape(QFrame.Shape.Panel)
        self.cStatusRight1.setFrameShadow(QFrame.Shadow.Sunken)
        self.cStatusRight2 = QLabel("R2")
        self.cStatusRight2.setFrameShape(QFrame.Shape.Panel)
        self.cStatusRight2.setFrameShadow(QFrame.Shadow.Sunken)
        self.cStatusBar = QStatusBar()
        self.cStatusBar.addWidget(self.cStatusLeft,100)
        self.cStatusBar.addWidget(self.cStatusCenter,800)
        self.cStatusBar.addPermanentWidget(self.cStatusRight1,100)
        self.cStatusBar.addPermanentWidget(self.cStatusRight2,100)
        self.setStatusBar(self.cStatusBar)
        self.updateProfileList()
        self.updateStatusBar()

    def onProfileChanged(self,p):
        self.settings.setActiveProfile(p)
        self.updateStatusBar()
    def onNewProfile(self):
        text, ok = QInputDialog.getText(self,"New Profile","New profile name")
        if ok and text:
            self.settings.addProfile(text)
            self.updateProfileList()
    def OnNewMessage(self):
        print("Hello world")
    def OnBbsSetup(self):
        bd = bbsdialog.BbsDialog(self.settings,self)
        bd.exec()
        self.updateStatusBar()
    def OnInterfaceSetup(self):
        sps = QSerialPortInfo.availablePorts()
        l = []
        for sp in sps:
             print(f"port {sp.portName()} {sp.description()}")
             l.append(sp.portName())
        id = interfacedialog.InterfaceDialog(self.settings,self)
        id.setComPortList(l)
        id.exec()
        self.updateStatusBar()
    def OnStationId(self):
        sid = stationiddialog.StationIdDialog(self.settings,self)
        sid.exec()
        self.updateStatusBar()
    def updateStatusBar(self):
        l1 = self.settings.getActiveCallSign(True)
        l2 = self.settings.getActiveBBS()
        l3 = self.settings.getActiveInterface()
        l4 = self.settings.getInterface("ComPort")
        self.cStatusCenter.setText(f"{l1} -- {l2} -- {l3} ({l4})")
    def updateProfileList(self):
        ap = self.settings.getActiveProfile()
        self.cProfile.blockSignals(True)
        self.cProfile.clear()
        p = self.settings.getProfiles()
        self.cProfile.addItems(p)
        self.cProfile.setCurrentText(ap)
        self.cProfile.blockSignals(False)
        self.settings.setActiveProfile(ap)
    def onSendReceiveSettings(self):
        srsd = sendreceivesettingsdialog.SendReceiveSettingsDialog(self.settings,self)
        srsd.exec()
    def onMessageSettings(self):
        msd = messagesettingsdialog.MessageSettingsDialog(self.settings,self)
        msd.exec()


if __name__ == "__main__": 
    app = QApplication(sys.argv)
    app.setStyle(QStyleFactory.create("Fusion"))
    mainwindow = MainWindow()
    mainwindow.show()
    sys.exit(app.exec())

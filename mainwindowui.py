import sys
from PyQt6 import QtWidgets
from PyQt6.QtCore import Qt, QIODeviceBase
from PyQt6.QtWidgets import QMainWindow, QInputDialog, QApplication, QStyleFactory, QLabel, QFrame, QStatusBar, QTableWidgetItem, QHeaderView, QMessageBox
from PyQt6.uic import load_ui
from PyQt6.QtSerialPort import QSerialPortInfo, QSerialPort
from persistentdata import PersistentData
import bbsdialog
import interfacedialog
import stationiddialog
import sendreceivesettingsdialog
import messagesettingsdialog
import newpacketmessage
import readmessagedialog
from mailfolder import MailFolder
from operator import itemgetter
from tncparser import KantronicsKPC3Plus
from enum import Enum
from serialstream import SerialStream

class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow,self).__init__()
        self.settings = PersistentData()
        self.settings.setActiveProfile("Outpost") # todo: 
        if self.settings.getProfileBool("ShowStationIdAtStartup"):
            self.OnStationId()
        load_ui.loadUi("mainwindow.ui",self)
        self.cNew.clicked.connect(self.onNewMessage)
        self.actionNew_Message.triggered.connect(self.onNewMessage)
        self.actionBBS.triggered.connect(self.OnBbsSetup)
        self.actionInterface.triggered.connect(self.OnInterfaceSetup)
        self.actionStation_ID.triggered.connect(self.OnStationId)
        self.actionSend_Receive_Settings.triggered.connect(self.onSendReceiveSettings)
        self.actionMessage_Settings.triggered.connect(self.onMessageSettings)
        self.cProfile.currentTextChanged.connect(self.onProfileChanged)
        self.actionNewProfile.triggered.connect(self.onNewProfile)
        self.cMailList.cellDoubleClicked.connect(self.onReadMessage)
        self.cMailList.horizontalHeader().sectionClicked.connect(self.onSortMail)
        self.actionSend_Receive.triggered.connect(self.onSendReceive)
        self.cSendReceive.clicked.connect(self.onSendReceive)
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
        self.mailSortIndex = 0
        self.mailSortBackwards = False
        self.mailIndex = []
        self.mailfolder = MailFolder()
        self.mailfolder.load("Inbox.mail")
        self.updateMailList()

    def onProfileChanged(self,p):
        self.settings.setActiveProfile(p)
        self.updateStatusBar()
    def onNewProfile(self):
        text, ok = QInputDialog.getText(self,"New Profile","New profile name")
        if ok and text:
            self.settings.addProfile(text)
            self.updateProfileList()
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
    def onSortMail(self,i):
        if self.mailSortIndex == i:
            self.mailSortBackwards = not self.mailSortBackwards
        else:
            if i >= 0 and i < 9:
                self.mailSortIndex = i
                self.mailSortBackwards = False # not sure if this is desired, maybe keep array of these
        print(f"sort {self.mailSortIndex} {self.mailSortBackwards}")
        self.updateMailList()
    def updateMailList(self):
        tmpindex = self.mailSortIndex+1 # now 1 to 10 but we don't use 9
        if tmpindex == 9: tmpindex = 10
        headers = sorted(self.mailfolder.getHeaders(),key=itemgetter(tmpindex), reverse=self.mailSortBackwards)
        self.mailIndex.clear()
        self.cMailList.clearContents()
        self.cMailList.setColumnWidth(0,40)
        self.cMailList.setColumnWidth(1,40)
        self.cMailList.setColumnWidth(2,200)
        self.cMailList.setColumnWidth(3,200)
        self.cMailList.setColumnWidth(4,60)
        self.cMailList.setColumnWidth(5,60)
        self.cMailList.setColumnWidth(6,240)
        self.cMailList.setColumnWidth(7,140)
        self.cMailList.setColumnWidth(8,40)
        n = len(headers)
        self.cMailList.setRowCount(n)
        for i in range(n):
            self.mailIndex.append(headers[i][0])
            self.cMailList.setItem(i,0,QTableWidgetItem(headers[i][1]))
            self.cMailList.setItem(i,1,QTableWidgetItem(headers[i][2]))
            self.cMailList.setItem(i,2,QTableWidgetItem(headers[i][3]))
            self.cMailList.setItem(i,3,QTableWidgetItem(headers[i][4]))
            self.cMailList.setItem(i,4,QTableWidgetItem(headers[i][5]))
            self.cMailList.setItem(i,5,QTableWidgetItem(headers[i][6]))
            self.cMailList.setItem(i,6,QTableWidgetItem(headers[i][7]))
            self.cMailList.setItem(i,7,QTableWidgetItem(headers[i][8]))
            # this version does not show the date received
            self.cMailList.item(i,7).setTextAlignment(Qt.AlignmentFlag.AlignRight) # // to match the original
            self.cMailList.setItem(i,8,QTableWidgetItem(str(headers[i][10])))
            self.cMailList.item(i,8).setTextAlignment(Qt.AlignmentFlag.AlignRight)
        self.cMailList.resizeRowsToContents()

    def onSendReceiveSettings(self):
        srsd = sendreceivesettingsdialog.SendReceiveSettingsDialog(self.settings,self)
        srsd.exec()
    def onMessageSettings(self):
        msd = messagesettingsdialog.MessageSettingsDialog(self.settings,self)
        msd.exec()
    def onNewMessage(self):
        tmp = newpacketmessage.NewPacketMessage(self.settings,self)
        tmp.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        tmp.signalNewMessage.connect(self.onHandleNewMessage)
        tmp.show()
        tmp.raise_()
    def onHandleNewMessage(self,s1,s2,s3):
        self.outGoingMessages.append({s1,s2,s3})
    def onReadMessage(self,row,col):
        tmp = readmessagedialog.ReadMessageDialog(self.settings,self)
        tmp.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        if row < 0 or row >= len(self.mailIndex): return
        h,m = self.mailfolder.getMessage(self.mailIndex[row])
        if not h: return
        tmp.setData(h,m)
        tmp.show()
        tmp.raise_()
    def openSerialPort(self):
        # get all relevant settings - remember that at this point they are all strings
        port = self.settings.getInterface("ComPort")
        baud = self.settings.getInterface("Baud")
        parity = self.settings.getInterface("Parity")
        databits = self.settings.getInterface("DataBits")
        stopbits =self.settings.getInterface("StopBits")
        flowcontrol = self.settings.getInterface("FlowControl")
        flowcontrolflag = True
        self.serialport = QSerialPort()
        self.serialport.setPortName(port)
        self.serialport.setBaudRate(int(baud))
        if not parity: parity = "N"
        match parity.upper()[0]:
            case 'E': self.serialport.setParity(QSerialPort.Parity.EvenParity)
            case 'O': self.serialport.setParity(QSerialPort.Parity.OddParity)
            case 'M': self.serialport.setParity(QSerialPort.Parity.MarkParity)
            case 'S': self.serialport.setParity(QSerialPort.Parity.SpaceParity)
            case _:   self.serialport.setParity(QSerialPort.Parity.NoParity)
        match databits:
            case '5': self.serialport.setDataBits(QSerialPort.DataBits.Data5)
            case '6': self.serialport.setDataBits(QSerialPort.DataBits.Data6)
            case '7': self.serialport.setDataBits(QSerialPort.DataBits.Data7)
            case _:   self.serialport.setDataBits(QSerialPort.DataBits.Data8)
        match stopbits:
            case "1":   self.serialport.setStopBits(QSerialPort.StopBits.OneStop)
            case "1.5": self.serialport.setStopBits(QSerialPort.StopBits.OneStop)
            case "2":   self.serialport.setStopBits(QSerialPort.StopBits.OneStop)
            case _:     self.serialport.setStopBits(QSerialPort.StopBits.OneStop)
        if not flowcontrol: flowcontrol = "R"
        flowcontrolflag = flowcontrol.upper()[0]
        match flowcontrolflag:
            case 'N': self.serialport.setFlowControl(QSerialPort.FlowControl.NoFlowControl)
            case _:   self.serialport.setFlowControl(QSerialPort.FlowControl.HardwareControl)
        f = self.serialport.open(QIODeviceBase.OpenModeFlag.ReadWrite)
        if not f:
            print(f"open serial port {self.serialport.portName()} failed, returned {self.serialport.errorString()}")
            return False
        print(f"open serial port {self.serialport.portName()} succeeded {self.serialport.baudRate()} {self.serialport.parity()} {self.serialport.dataBits()} {self.serialport.stopBits()} {self.serialport.flowControl()}")
        if flowcontrolflag != 'R':
            self.serialport.setDataTerminalReady(True)
            self.serialport.setRequestToSend(True)
        return True
    def onSendReceive(self):
        f = self.openSerialPort()
        if not f:
            QMessageBox.critical(self,"Error",f"Error {self.serialport.errorString()} opening serial port");
            return
        self.sdata = bytearray()
        self.tncParser = KantronicsKPC3Plus(self.settings,self)
        #self.bbsParser = Nos2Parser(self.settings,self)
        self.serialStream = SerialStream(self.serialport)
        self.tncParser.startSession(self.serialStream)

if __name__ == "__main__": 
    app = QApplication(sys.argv)
    app.setStyle(QStyleFactory.create("Fusion"))
    mainwindow = MainWindow()
    mainwindow.show()
    sys.exit(app.exec())

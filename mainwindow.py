import sys
from PyQt6 import QtWidgets
from PyQt6.QtCore import Qt, QIODeviceBase
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QMainWindow, QInputDialog, QApplication, QStyleFactory, QLabel, QFrame, QStatusBar, QTableWidgetItem, QHeaderView, QMessageBox, QMenu
from PyQt6.uic import load_ui
from PyQt6.QtSerialPort import QSerialPortInfo, QSerialPort
from persistentdata import PersistentData
import bbsdialog
import interfacedialog
import stationiddialog
import sendreceivesettingsdialog
import messagesettingsdialog
import generalsettingsdialog
import newpacketmessage
import readmessagedialog
import formdialog
from mailfolder import MailFolder, MailBoxHeader
from operator import attrgetter
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
        self.actionNew_Message.triggered.connect(self.onNewMessage)
        self.actionXSC_Check_In_Out_Message.triggered.connect(lambda: self.onNewForm("CheckInCheckOut","CheckInCheckOut"))
        self.actionXSC_ICS_213_Message.triggered.connect(lambda: self.onNewForm("ICS-213_Message_Form_v20220119-1","ICS213"))
        self.actionXSC_Damage_Assessment.triggered.connect(lambda: self.onNewForm("Damage_Assessment_v20250812","DmgAsmt"))
        self.actionBBS.triggered.connect(self.OnBbsSetup)
        self.actionInterface.triggered.connect(self.OnInterfaceSetup)
        self.actionStation_ID.triggered.connect(self.OnStationId)
        self.actionSend_Receive_Settings.triggered.connect(self.onSendReceiveSettings)
        self.actionMessage_Settings.triggered.connect(self.onMessageSettings)
        self.actionGeneral_Settings.triggered.connect(self.onGeneralSettings)
        self.actionDelete.triggered.connect(self.onDeleteMessages)
        self.cProfile.currentTextChanged.connect(self.onProfileChanged)
        self.actionNewProfile.triggered.connect(self.onNewProfile)
        self.cMailList.cellDoubleClicked.connect(self.onReadMessage)
        self.cMailList.customContextMenuRequested.connect(self.onMailListRightClick)
        self.cMailList.horizontalHeader().sectionClicked.connect(self.onSortMail)
        self.actionSend_Receive.triggered.connect(self.onSendReceive)

        self.cNew.clicked.connect(self.onNewMessage)
        #self.cOpen.clicked.connect(self.onNewMessage)
        self.cArchive.clicked.connect(self.onArchiveMessages)
        self.cDelete.clicked.connect(self.onDeleteMessages)
        #self.cPrint.clicked.connect(self.onDeleteMessages)
        self.cSendReceive.clicked.connect(self.onSendReceive)

        self.cInTray.clicked.connect(lambda: self.onSelectFolder("InTray"))
        self.cOutTray.clicked.connect(lambda: self.onSelectFolder("OutTray"))
        self.cSentMessages.clicked.connect(lambda: self.onSelectFolder("Sent"))
        self.cArchived.clicked.connect(lambda: self.onSelectFolder("Archived"))
        self.cDrafMessages.clicked.connect(lambda: self.onSelectFolder("Draft"))
        self.cDeleted.clicked.connect(lambda: self.onSelectFolder("Deleted"))
        self.cFolder1.clicked.connect(lambda: self.onSelectFolder("Folder1"))
        self.cFolder2.clicked.connect(lambda: self.onSelectFolder("Folder2"))
        self.cFolder3.clicked.connect(lambda: self.onSelectFolder("Folder3"))
        self.cFolder4.clicked.connect(lambda: self.onSelectFolder("Folder4"))
        self.cFolder5.clicked.connect(lambda: self.onSelectFolder("Folder5"))
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
        #self.cStatusBar = QStatusBar()
        self.cStatusBar.addWidget(self.cStatusLeft,100)
        self.cStatusBar.addWidget(self.cStatusCenter,800)
        self.cStatusBar.addPermanentWidget(self.cStatusRight1,100)
        self.cStatusBar.addPermanentWidget(self.cStatusRight2,100)
        #self.setStatusBar(self.cStatusBar)
        self.updateProfileList()
        self.updateStatusBar()
        self.mailSortIndex = 0
        self.mailSortBackwards = False
        self.mailIndex = []
        self.mailfolder = MailFolder()
        self.currentFolder = "InTray"
        self.mailfolder.load(self.currentFolder)
        self.updateMailList()
        # need to add the folder list in several places
        self.cFolder1.setText(self.settings.getProfile("GeneralSettings/Folder1","Folder 1"))
        self.cFolder2.setText(self.settings.getProfile("GeneralSettings/Folder2","Folder 2"))
        self.cFolder3.setText(self.settings.getProfile("GeneralSettings/Folder3","Folder 3"))
        self.cFolder4.setText(self.settings.getProfile("GeneralSettings/Folder4","Folder 4"))
        self.cFolder5.setText(self.settings.getProfile("GeneralSettings/Folder5","Folder 5"))
        # the first two (in/out) are already there
        self.menuMove_to_Folder.addAction("Sent Messages")
        self.menuMove_to_Folder.addAction("Archive")
        self.menuMove_to_Folder.addAction("Draft Messages")
        self.menuMove_to_Folder.addAction("Deleted")
        self.menuMove_to_Folder.addAction(self.settings.getProfile("GeneralSettings/Folder1","Folder 1"))
        self.menuMove_to_Folder.addAction(self.settings.getProfile("GeneralSettings/Folder2","Folder 2"))
        self.menuMove_to_Folder.addAction(self.settings.getProfile("GeneralSettings/Folder3","Folder 3"))
        self.menuMove_to_Folder.addAction(self.settings.getProfile("GeneralSettings/Folder4","Folder 4"))
        self.menuMove_to_Folder.addAction(self.settings.getProfile("GeneralSettings/Folder5","Folder 5"))
        tmp = self.menuMove_to_Folder.actions()
        tmp[0].triggered.connect(lambda: self.onMoveToFolder("InTray"))
        tmp[1].triggered.connect(lambda: self.onMoveToFolder("OutTray"))
        tmp[2].triggered.connect(lambda: self.onMoveToFolder("Sent"))
        tmp[3].triggered.connect(lambda: self.onMoveToFolder("Archived"))
        tmp[4].triggered.connect(lambda: self.onMoveToFolder("Draft"))
        tmp[5].triggered.connect(lambda: self.onMoveToFolder("Deleted"))
        tmp[6].triggered.connect(lambda: self.onMoveToFolder("Folder1"))
        tmp[7].triggered.connect(lambda: self.onMoveToFolder("Folder2"))
        tmp[8].triggered.connect(lambda: self.onMoveToFolder("Folder3"))
        tmp[9].triggered.connect(lambda: self.onMoveToFolder("Folder4"))
        tmp[10].triggered.connect(lambda: self.onMoveToFolder("Folder5"))
        self.menuCopy_to_Folder.addAction("Sent Messages")
        self.menuCopy_to_Folder.addAction("Archive")
        self.menuCopy_to_Folder.addAction("Draft Messages")
        self.menuCopy_to_Folder.addAction("Deleted")
        self.menuCopy_to_Folder.addAction(self.settings.getProfile("GeneralSettings/Folder1","Folder 1"))
        self.menuCopy_to_Folder.addAction(self.settings.getProfile("GeneralSettings/Folder2","Folder 2"))
        self.menuCopy_to_Folder.addAction(self.settings.getProfile("GeneralSettings/Folder3","Folder 3"))
        self.menuCopy_to_Folder.addAction(self.settings.getProfile("GeneralSettings/Folder4","Folder 4"))
        self.menuCopy_to_Folder.addAction(self.settings.getProfile("GeneralSettings/Folder5","Folder 5"))
        tmp = self.menuCopy_to_Folder.actions()
        tmp[0].triggered.connect(lambda: self.onCopyToFolder("InTray"))
        tmp[1].triggered.connect(lambda: self.onCopyToFolder("OutTray"))
        tmp[2].triggered.connect(lambda: self.onCopyToFolder("Sent"))
        tmp[3].triggered.connect(lambda: self.onCopyToFolder("Archived"))
        tmp[4].triggered.connect(lambda: self.onCopyToFolder("Draft"))
        tmp[5].triggered.connect(lambda: self.onCopyToFolder("Deleted"))
        tmp[6].triggered.connect(lambda: self.onCopyToFolder("Folder1"))
        tmp[7].triggered.connect(lambda: self.onCopyToFolder("Folder2"))
        tmp[8].triggered.connect(lambda: self.onCopyToFolder("Folder3"))
        tmp[9].triggered.connect(lambda: self.onCopyToFolder("Folder4"))
        tmp[10].triggered.connect(lambda: self.onCopyToFolder("Folder5"))
        pass
    def onSelectFolder(self,s):
        self.currentFolder = s
        self.mailfolder.load(self.currentFolder)
        self.updateMailList()
    def onMoveToFolder(self,s):
        indexlist = []
        for item in self.cMailList.selectedItems():
            if item.column() == 0:
                indexlist.append(item.row())
        self.mailfolder.copyMail(indexlist,s)
        self.mailfolder.deleteMail(indexlist)
        self.updateMailList()
    def onCopyToFolder(self,s):
        indexlist = []
        for item in self.cMailList.selectedItems():
            if item.column() == 0:
                indexlist.append(item.row())
        self.mailfolder.copyMail(indexlist,s)
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
            l.append(f"{sp.portName()} / {sp.description()}") #sp.portName())
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
        l4 = self.settings.getInterface("ComPort").partition("/")[0].rstrip()
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
        tmpindex = self.mailSortIndex+2 # now 2 to 10
        #if tmpindex == 9: tmpindex = 10
        if 2 <= tmpindex <= 10:
            keyname = ["mUrgent","mType","mFrom","mTo","mBbs","mLocalId","mSubject","mDateSent","mSize"][tmpindex-2]
            headers = sorted(self.mailfolder.getHeaders(),key=attrgetter(keyname), reverse=self.mailSortBackwards)
        else:
            headers = self.mailfolder.getHeaders()
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
            self.mailIndex.append(headers[i].mIndex)
            self.cMailList.setItem(i,0,QTableWidgetItem(headers[i].mUrgent))
            self.cMailList.setItem(i,1,QTableWidgetItem(headers[i].mType))
            self.cMailList.setItem(i,2,QTableWidgetItem(headers[i].mFrom))
            self.cMailList.setItem(i,3,QTableWidgetItem(headers[i].mTo))
            self.cMailList.setItem(i,4,QTableWidgetItem(headers[i].mBbs))
            self.cMailList.setItem(i,5,QTableWidgetItem(headers[i].mLocalId))
            self.cMailList.setItem(i,6,QTableWidgetItem(headers[i].mSubject))
            self.cMailList.setItem(i,7,QTableWidgetItem(MailBoxHeader.toOutpostDate(headers[i].mDateSent)))
            # this version does not show the date received
            self.cMailList.item(i,7).setTextAlignment(Qt.AlignmentFlag.AlignRight) # // to match the original
            self.cMailList.setItem(i,8,QTableWidgetItem(str(headers[i].mSize)))
            self.cMailList.item(i,8).setTextAlignment(Qt.AlignmentFlag.AlignRight)
            if headers[i].mIsNew == "Y":
                font =  self.cMailList.item(i,0).font()
                font.setBold(True)
                for j in range(9):
                    self.cMailList.item(i,j).setFont(font)
        self.cMailList.resizeRowsToContents()

    def onSendReceiveSettings(self):
        srsd = sendreceivesettingsdialog.SendReceiveSettingsDialog(self.settings,self)
        srsd.exec()
    def onMessageSettings(self):
        msd = messagesettingsdialog.MessageSettingsDialog(self.settings,self)
        msd.exec()
    def onGeneralSettings(self):
        msd = generalsettingsdialog.GeneralSettingsDialog(self.settings,self)
        msd.exec()
        # redraw the folder names in case they have changed
        self.cFolder1.setText(self.settings.getProfile("GeneralSettings/Folder1","Folder 1"))
        self.cFolder2.setText(self.settings.getProfile("GeneralSettings/Folder2","Folder 2"))
        self.cFolder3.setText(self.settings.getProfile("GeneralSettings/Folder3","Folder 3"))
        self.cFolder4.setText(self.settings.getProfile("GeneralSettings/Folder4","Folder 4"))
        self.cFolder5.setText(self.settings.getProfile("GeneralSettings/Folder5","Folder 5"))
    def onNewMessage(self):
        tmp = newpacketmessage.NewPacketMessage(self.settings,self)
        tmp.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        tmp.signalNewOutgoingMessage.connect(self.onHandleNewOutgoingMessage)
        tmp.show()
        tmp.raise_()
    def onNewForm(self,form,formid):
        tmp = formdialog.FormDialog(self.settings,form,formid,self)
        tmp.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        tmp.signalNewOutgoingMessage.connect(self.onHandleNewOutgoingFormMessage)
        tmp.show()
        tmp.raise_()
    def onHandleNewOutgoingMessage(self,mbh,m):
        self.mailfolder.addMail(mbh,m,"OutTray")
        self.updateMailList()
    def onHandleNewOutgoingFormMessage(self,subject,m,urgent):
        tmp = newpacketmessage.NewPacketMessage(self.settings,self)
        tmp.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        tmp.signalNewOutgoingMessage.connect(self.onHandleNewOutgoingMessage)
        tmp.setInitalData(subject,m,urgent)
        tmp.show()
        tmp.raise_()
    def onReadMessage(self,row,col):
        if row < 0 or row >= len(self.mailIndex): return
        h,m = self.mailfolder.getMessage(self.mailIndex[row])
        if not h: return
        # is this a regular text message or a form?
        # for now, decide based on subject, but would be better to use message body
        s = h.mSubject.split("_")
        if len(s) >= 3 and s[2].startsWith("CheckIn"):
            tmp = formdialog.FormDialog(self.settings,"CheckInCheckOut","CheckInCheckOut",self)
            tmp.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
            tmp.setData(h,m)
            tmp.signalNewOutgoingMessage.connect(self.onHandleNewOutgoingFormMessage)
            tmp.show()
            tmp.raise_()
        elif len(s) >= 3 and s[2].startsWith("CheckOut"):
            tmp = formdialog.FormDialog(self.settings,"CheckInCheckOut","CheckInCheckOut",self)
            tmp.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
            tmp.setData(h,m)
            tmp.signalNewOutgoingMessage.connect(self.onHandleNewOutgoingFormMessage)
            tmp.show()
            tmp.raise_()
        elif len(s) >= 4 and s[2] == "ICS213":
            tmp = formdialog.FormDialog(self.settings,"ICS-213_Message_Form_v20220119-1","ICS213",self)
            tmp.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
            tmp.setData(h,m)
            tmp.signalNewOutgoingMessage.connect(self.onHandleNewOutgoingFormMessage)
            tmp.show()
            tmp.raise_()
        elif len(s) >= 4 and s[2] == "DmgAsmt":
            tmp = formdialog.FormDialog(self.settings,"Damage_Assessment_v20250812","DmgAsmt",self)
            tmp.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
            tmp.setData(h,m)
            tmp.signalNewOutgoingMessage.connect(self.onHandleNewOutgoingFormMessage)
            tmp.show()
            tmp.raise_()
        else:
            tmp = readmessagedialog.ReadMessageDialog(self.settings,self)
            tmp.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
            tmp.setData(h,m)
            tmp.show()
            tmp.raise_()
        if self.mailfolder.markAsNew(self.mailIndex[row],False):
            self.updateMailList()
    def openSerialPort(self):
        # get all relevant settings - remember that at this point they are all strings
        port = self.settings.getInterface("ComPort").partition('/')[0].rstrip()
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
        self.tncParser.signalNewIncomingMessage.connect(self.onNewIncomingMessage)
        self.tncParser.startSession(self.serialStream)
    def onNewIncomingMessage(self,mbh,m):
        self.mailfolder.addMail(mbh,m,"InTray")
        self.updateMailList()
    def onDeleteMessages(self):
        indexlist = []
        for item in self.cMailList.selectedItems():
            if item.column() == 0:
                indexlist.append(item.row())
        self.mailfolder.copyMail(indexlist,"Deleted")
        self.mailfolder.deleteMail(indexlist)
        self.updateMailList()
    def onArchiveMessages(self):
        indexlist = []
        for item in self.cMailList.selectedItems():
            if item.column() == 0:
                indexlist.append(item.row())
        self.mailfolder.copyMail(indexlist,"Archived")
        self.mailfolder.deleteMail(indexlist)
        self.updateMailList()
    def onMailListRightClick(self,pos):
        item = self.cMailList.itemAt(pos)
        if not item: return
        row = item.row();
        if row < 0: return
        mailindex = self.mailIndex[row]
        m = QMenu(self)
        a1 = QAction("Open",self)
        m.addAction(a1)
        mm = QMenu("Open Enhanced",self)
        a2 = QAction("as Text",self)
        mm.addAction(a2)
        a3 = QAction("in Client",self)
        mm.addAction(a3)
        m.addMenu(mm)
        a4 = QAction("Print",self)
        m.addAction(a4)
        a5 = QAction("Save As...",self)
        m.addAction(a5)
        a6 = QAction("Save As. No Headers...",self)
        m.addAction(a6)
        a7 = QAction("Mark as Unread",self)
        m.addAction(a7)
        a8 = QAction("Mark as Read",self)
        m.addAction(a8)
        m.addSeparator()
        a9 = QAction("Archive",self)
        m.addAction(a9)
#         a1 = m.addAction("Open",self)
#         mm = m.addMenu("Open Enhanced",self)
#         a2 = mm.addAction("as Text",self)
#         a3 = mm.addAction("in Client",self)
#         a4 = m.addAction("Print",self)
#         a5 = m.addAction("Save As...",self)
#         a6 = m.addAction("Save As. No Headers...",self)
#         a7 = m.addAction("Mark as Unread",self)
#         a8 = m.addAction("Mark as Read",self)
#         m.addSeparator(self)
#         a9 = m.addAction("Archive",self)
# #        mm = m.addMenu("Archive")
#         a10 = m.addAction("Print",self)
        r = m.exec(self.cMailList.mapToGlobal(pos))
        if r == a1:
            self.onReadMessage(row,0)
        elif r == a7:
            if self.mailfolder.markAsNew(mailindex,True):
                self.updateMailList()
        elif r == a8:
            if self.mailfolder.markAsNew(mailindex,False):
                self.updateMailList()
        pass

if __name__ == "__main__": 
    app = QApplication(sys.argv)
    app.setStyle(QStyleFactory.create("Fusion"))
    mainwindow = MainWindow()
    mainwindow.show()
    sys.exit(app.exec())

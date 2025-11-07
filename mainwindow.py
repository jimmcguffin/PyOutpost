import sys
from PyQt6 import QtWidgets
from PyQt6.QtCore import Qt, QIODeviceBase
from PyQt6.QtGui import QAction, QPalette, QColor
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
from mailfolder import MailFolder, MailBoxHeader, MailFlags
from operator import attrgetter
from tncparser import KantronicsKPC3Plus
from enum import Enum
from serialstream import SerialStream

class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow,self).__init__()
        self.settings = PersistentData()
        # self.settings.clear()
        # special things that have to be done the first time
        firsttime = False
        if not self.settings.getUserCallSigns():
            text, ok = QInputDialog.getText(self,"First Time User","Enter your FCC call sign")
            if ok and text:
                firsttime = True
                self.resetAllToSccStandard(firsttime,text)
            else:
                return

        self.settings.start()
        self.settings.setActiveProfile("Outpost") # todo: 
        if self.settings.getProfileBool("ShowStationIdAtStartup") or not self.settings.getActiveUserCallSign() or firsttime:
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
        self.actionReset_all_to_SCC_standard.triggered.connect(self.resetAllToSccStandard)
        self.cNew.clicked.connect(self.onNewMessage)
        #self.cOpen.clicked.connect(self.onNewMessage)
        self.cArchive.clicked.connect(self.onArchiveMessages)
        self.cDelete.clicked.connect(self.onDeleteMessages)
        #self.cPrint.clicked.connect(self.onDeleteMessages)
        self.cSendReceive.clicked.connect(self.onSendReceive)

        self.cInTray.clicked.connect(lambda: self.onSelectFolder(MailFlags.FolderInTray))
        self.cOutTray.clicked.connect(lambda: self.onSelectFolder(MailFlags.FolderOutTray))
        self.cSentMessages.clicked.connect(lambda: self.onSelectFolder(MailFlags.FolderSent))
        self.cArchived.clicked.connect(lambda: self.onSelectFolder(MailFlags.FolderArchive))
        self.cDrafMessages.clicked.connect(lambda: self.onSelectFolder(MailFlags.FolderDraft))
        self.cDeleted.clicked.connect(lambda: self.onSelectFolder(MailFlags.FolderDeleted))
        self.cFolder1.clicked.connect(lambda: self.onSelectFolder(MailFlags.Folder1))
        self.cFolder2.clicked.connect(lambda: self.onSelectFolder(MailFlags.Folder2))
        self.cFolder3.clicked.connect(lambda: self.onSelectFolder(MailFlags.Folder3))
        self.cFolder4.clicked.connect(lambda: self.onSelectFolder(MailFlags.Folder4))
        self.cFolder5.clicked.connect(lambda: self.onSelectFolder(MailFlags.Folder5))
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
        self.currentFolder = MailFlags.FolderInTray
        self.mailfolder.load()
        self.updateMailList()
        # need to add the folder list in several places
        f = [
            self.settings.getProfile("GeneralSettings/Folder1","Folder 1"),
            self.settings.getProfile("GeneralSettings/Folder2","Folder 2"),
            self.settings.getProfile("GeneralSettings/Folder3","Folder 3"),
            self.settings.getProfile("GeneralSettings/Folder4","Folder 4"),
            self.settings.getProfile("GeneralSettings/Folder5","Folder 5"),
        ]
        self.cFolder1.setText(f[0])
        self.cFolder2.setText(f[1])
        self.cFolder3.setText(f[2])
        self.cFolder4.setText(f[3])
        self.cFolder5.setText(f[4])
        # the first two (in/out) are already there
        self.menuMove_to_Folder.actions()[0].triggered.connect(lambda: self.onMoveToFolder(MailFlags.FolderInTray))
        self.menuMove_to_Folder.actions()[1].triggered.connect(lambda: self.onMoveToFolder(MailFlags.FolderOutTray))
        self.menuMove_to_Folder.addAction("Sent Messages").triggered.connect(lambda: self.onMoveToFolder(MailFlags.Folderent))
        self.menuMove_to_Folder.addAction("Archive").triggered.connect(lambda: self.onMoveToFolder(MailFlags.FolderArchived))
        self.menuMove_to_Folder.addAction("Draft Messages").triggered.connect(lambda: self.onMoveToFolder(MailFlags.FolderDraft))
        self.menuMove_to_Folder.addAction("Deleted").triggered.connect(lambda: self.onMoveToFolder(MailFlags.FolderDeleted))
        self.menuMove_to_Folder.addAction(f[0]).triggered.connect(lambda: self.onMoveToFolder(MailFlags.Folder1))
        self.menuMove_to_Folder.addAction(f[1]).triggered.connect(lambda: self.onMoveToFolder(MailFlags.Folder2))
        self.menuMove_to_Folder.addAction(f[2]).triggered.connect(lambda: self.onMoveToFolder(MailFlags.Folder3))
        self.menuMove_to_Folder.addAction(f[3]).triggered.connect(lambda: self.onMoveToFolder(MailFlags.Folder4))
        self.menuMove_to_Folder.addAction(f[4]).triggered.connect(lambda: self.onMoveToFolder(MailFlags.Folder5))

        self.menuCopy_to_Folder.actions()[0].triggered.connect(lambda: self.onCopyToFolder(MailFlags.FolderInTray))
        self.menuCopy_to_Folder.actions()[1].triggered.connect(lambda: self.onCopyToFolder(MailFlags.FolderOutTray))
        self.menuCopy_to_Folder.addAction("Sent Messages").triggered.connect(lambda: self.onCopyToFolder(MailFlags.FolderSent))
        self.menuCopy_to_Folder.addAction("Archive").triggered.connect(lambda: self.onCopyToFolder(MailFlags.FolderArchived))
        self.menuCopy_to_Folder.addAction("Draft Messages").triggered.connect(lambda: self.onCopyToFolder(MailFlags.FolderDraft))
        self.menuCopy_to_Folder.addAction("Deleted").triggered.connect(lambda: self.onCopyToFolder(MailFlags.FolderDeleted))
        self.menuCopy_to_Folder.addAction(f[0]).triggered.connect(lambda: self.onCopyToFolder(MailFlags.Folder1))
        self.menuCopy_to_Folder.addAction(f[1]).triggered.connect(lambda: self.onCopyToFolder(MailFlags.Folder2))
        self.menuCopy_to_Folder.addAction(f[2]).triggered.connect(lambda: self.onCopyToFolder(MailFlags.Folder3))
        self.menuCopy_to_Folder.addAction(f[3]).triggered.connect(lambda: self.onCopyToFolder(MailFlags.Folder4))
        self.menuCopy_to_Folder.addAction(f[4]).triggered.connect(lambda: self.onCopyToFolder(MailFlags.Folder5))
    def onSelectFolder(self,folder):
        self.currentFolder = folder
        self.updateMailList()
    def onMoveToFolder(self,folder):
        indexlist = []
        for item in self.cMailList.selectedItems():
            if item.column() == 0:
                indexlist.append(self.mailIndex[item.row()])
        # if moving from deleted to deleted, just delete
        if self.currentFolder == MailFlags.FolderDeleted and folder == MailFlags.FolderDeleted:
            self.mailfolder.deleteMail(indexlist)
        else:
            self.mailfolder.moveMail(indexlist,self.currentFolder,folder)
        self.updateMailList()
    def onCopyToFolder(self,folder):
        indexlist = []
        for item in self.cMailList.selectedItems():
            if item.column() == 0:
                indexlist.append(self.mailIndex[item.row()])
        self.mailfolder.copyMail(indexlist,folder)
        self.updateMailList()
    def onMarkAsNew(self,index,mark):
        self.mailfolder.markAsNew(index,mark)
        self.updateMailList()
    def onProfileChanged(self,p):
        self.settings.setActiveProfile(p)
        self.updateStatusBar()
    def onNewProfile(self):
        text, ok = QInputDialog.getText(self,"New Profile","New profile name")
        if ok and text:
            self.settings.copyProfile(text)
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
        if not hasattr(self,'cStatusCenter'): return
        l1 = self.settings.getActiveCallSign(True)
        l2 = self.settings.getActiveBBS()
        l3 = self.settings.getActiveInterface()
        l4 = ""
        cp = self.settings.getInterface("ComPort")
        if (cp): l4 = cp.partition("/")[0].rstrip()
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
            headers = sorted(self.mailfolder.getHeaders(self.currentFolder),key=attrgetter(keyname), reverse=self.mailSortBackwards)
        else:
            headers = self.mailfolder.getHeaders(self.currentFolder)
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
            if headers[i].isNew():
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
        # todo: need to fix up the menu items as well
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
        self.mailfolder.addMail(mbh,m,MailFlags.FolderOutTray)
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
        port = self.settings.getInterface("ComPort")
        if not port:
            return False
        port = port.partition('/')[0].rstrip()
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
        port = self.settings.getInterface("ComPort")
        if not port:
            QMessageBox.critical(self,"Error",f"Error serial port has not been configuired, go to Setup/Interface")
            return
        # port = port.partition('/')[0].rstrip()

        f = self.openSerialPort()
        if not f:
            QMessageBox.critical(self,"Error",f"Error {self.serialport.errorString()} opening serial port")
            return
        self.sdata = bytearray()
        self.tncParser = KantronicsKPC3Plus(self.settings,self)
        #self.bbsParser = Nos2Parser(self.settings,self)
        self.serialStream = SerialStream(self.serialport)
        self.tncParser.signalNewIncomingMessage.connect(self.onNewIncomingMessage)
        self.tncParser.startSession(self.serialStream)
    def onNewIncomingMessage(self,mbh,m):
        self.mailfolder.addMail(mbh,m,MailFlags.FolderInTray)
        self.updateMailList()
    def onDeleteMessages(self):
        indexlist = []
        for item in self.cMailList.selectedItems():
            if item.column() == 0:
                indexlist.append(self.mailIndex[item.row()])
        self.mailfolder.moveMail(indexlist,self.currentFolder,MailFlags.FolderDeleted)
        self.updateMailList()
    def onArchiveMessages(self):
        indexlist = []
        for item in self.cMailList.selectedItems():
            if item.column() == 0:
                indexlist.append(self.mailIndex[item.row()])
        self.mailfolder.moveMail(indexlist,self.currentFolder,MailFlags.FolderArchive)
        self.updateMailList()
    def onMailListRightClick(self,pos):
        item = self.cMailList.itemAt(pos)
        if not item: return
        row = item.row()
        if row < 0: return
        mailindex = self.mailIndex[row]
        m = QMenu(self)
        m.addAction("Open").triggered.connect(lambda: self.onReadMessage(row,0))
        mm = QMenu("Open Enhanced",self)
        mm.addAction("as Text").setEnabled(False)
        mm.addAction("in Client").setEnabled(False)
        m.addMenu(mm)
        m.addAction("Print").setEnabled(False)
        m.addAction("Save As...").setEnabled(False)
        m.addAction("Save As. No Headers...").setEnabled(False)
        m.addAction("Mark as Unread").triggered.connect(lambda: self.onMarkAsNew(mailindex,True))
        m.addAction("Mark as Read").triggered.connect(lambda: self.onMarkAsNew(mailindex,False))

        m.addSeparator()
        m.addAction("Archive")
        f = [
            self.settings.getProfile("GeneralSettings/Folder1","Folder 1"),
            self.settings.getProfile("GeneralSettings/Folder2","Folder 2"),
            self.settings.getProfile("GeneralSettings/Folder3","Folder 3"),
            self.settings.getProfile("GeneralSettings/Folder4","Folder 4"),
            self.settings.getProfile("GeneralSettings/Folder5","Folder 5"),
        ]
        mm = QMenu("Move To",self)
        mm.addAction("In Tray").triggered.connect(lambda: self.onMoveToFolder(MailFlags.FolderInTray))
        mm.addAction("Out Tray").triggered.connect(lambda: self.onMoveToFolder(MailFlags.FolderOutTray))
        mm.addAction("Sent Messages").triggered.connect(lambda: self.onMoveToFolder(MailFlags.FolderSent))
        mm.addAction("Archive").triggered.connect(lambda: self.onMoveToFolder(MailFlags.FolderArchived))
        mm.addAction("Draft Messages").triggered.connect(lambda: self.onMoveToFolder(MailFlags.FolderDraft))
        mm.addAction("Deleted").triggered.connect(lambda: self.onMoveToFolder(MailFlags.FolderDeleted))
        mm.addAction(f[0]).triggered.connect(lambda: self.onMoveToFolder(MailFlags.Folder1))
        mm.addAction(f[1]).triggered.connect(lambda: self.onMoveToFolder(MailFlags.Folder2))
        mm.addAction(f[2]).triggered.connect(lambda: self.onMoveToFolder(MailFlags.Folder3))
        mm.addAction(f[3]).triggered.connect(lambda: self.onMoveToFolder(MailFlags.Folder4))
        mm.addAction(f[4]).triggered.connect(lambda: self.onMoveToFolder(MailFlags.Folder5))
        m.addMenu(mm)

        mm = QMenu("Copy To",self)
        mm.addAction("In Tray").triggered.connect(lambda: self.onCopyToFolder(MailFlags.FolderInTray))
        mm.addAction("Out Tray").triggered.connect(lambda: self.onCopyToFolder(MailFlags.FolderOutTray))
        mm.addAction("Sent Messages").triggered.connect(lambda: self.onCopyToFolder(MailFlags.FolderSent))
        mm.addAction("Archive").triggered.connect(lambda: self.onCopyToFolder(MailFlags.FolderArchived))
        mm.addAction("Draft Messages").triggered.connect(lambda: self.onCopyToFolder(MailFlags.FolderDraft))
        mm.addAction("Deleted").triggered.connect(lambda: self.onCopyToFolder(MailFlags.FolderDeleted))
        mm.addAction(f[0]).triggered.connect(lambda: self.onCopyToFolder(MailFlags.Folder1))
        mm.addAction(f[1]).triggered.connect(lambda: self.onCopyToFolder(MailFlags.Folder2))
        mm.addAction(f[2]).triggered.connect(lambda: self.onCopyToFolder(MailFlags.Folder3))
        mm.addAction(f[3]).triggered.connect(lambda: self.onCopyToFolder(MailFlags.Folder4))
        mm.addAction(f[4]).triggered.connect(lambda: self.onCopyToFolder(MailFlags.Folder5))
        m.addMenu(mm)
        m.addSeparator()
        m.addAction("Delete").triggered.connect(lambda: self.onMoveToFolder(MailFlags.FolderDeleted))

        r = m.exec(self.cMailList.mapToGlobal(pos))
        # if r == a1:
        #     self.onReadMessage(row,0)
        # elif r == a7:
        #     if self.mailfolder.markAsNew(mailindex,True):
        #         self.updateMailList()
        # elif r == a8:
        #     if self.mailfolder.markAsNew(mailindex,False):
        #         self.updateMailList()
        # pass

    def resetAllToSccStandard(self,firsttime=False,callsign="",name="",prefix=""): # if callsign is blank, will ask
        if not callsign:
            callsign, ok = QInputDialog.getText(self,"Call Sign","Your FCC call sign")
            if ok and callsign:
                prefix = callsign[-3:] if len(callsign) >= 3 else callsign
            else:
                return
        # clear out all settings!
        self.settings.clear()
        self.settings.save()
        self.settings.addProfile("Outpost")
        self.settings.addBBS("XSC_W1XSC-1","W1XSC-1","Santa Clara County ARES/RACES Packet System.  Located in San Jose.  JNOS.")
        self.settings.setActiveBBS(self.settings.getBBSs()[0])
        self.settings.addBBS("XSC_W2XSC-1","W2XSC-1","Santa Clara County ARES/RACES Packet System.  Located on Crystal Peak (South County).  JNOS.")
        self.settings.addBBS("XSC_W3XSC-1","W3XSC-1","Santa Clara County ARES/RACES Packet System.  Located in Palo Alto.  JNOS.")
        self.settings.addBBS("XSC_W4XSC-1","W4XSC-1","Santa Clara County ARES/RACES Packet System.  Located on Frazier Peak (above Milpitas).  JNOS.")
        self.settings.addBBS("XSC_W5XSC-1","W5XSC-1","Santa Clara County ARES/RACES Packet System.  Used for training, back-up, etc.  JNOS.")
        self.settings.addBBS("XSC_W6XSC-1","W6XSC-1","Santa Clara County ARES/RACES Packet System.  Used for testing, etc.  JNOS.")
        self.settings.addInterface("XSC_Kantronics_KPC3-Plus","KPC3+ TNC for use with Santa Clara County's BBS System. Verify the COM port setting for your system.")
        self.settings.setActiveInterface(self.settings.getInterfaces()[0])
        for p in KantronicsKPC3Plus.getDefaultPrompts():
            self.settings.setInterface(p[0],p[1])
        self.settings.setInterface("AlwaysSendInitCommands",True)
        self.settings.setInterface("IncludeCommandPrefix",False)
        for p in KantronicsKPC3Plus.getDefaultCommands():
            self.settings.setInterface(p[0],p[1])
        self.settings.setInterface("CommandPrefix","")
        self.settings.setInterface("CommandsBefore",KantronicsKPC3Plus.getDefaultBeforeInitCommands())
        self.settings.setInterface("CommandsAfter",KantronicsKPC3Plus.getDefaultAfterInitCommands())
        self.settings.setInterface("Baud","9600")
        self.settings.setInterface("Parity","None")
        self.settings.setInterface("DataBits","8")
        self.settings.setInterface("StopBits","1")
        self.settings.setInterface("FlowControl","RTS/DTS")
        self.settings.addInterface("XSC_Kantronics_KPC3","KPC3 (NOT the 3+ version) TNC for use with Santa Clara County's BBS System. Verify the COM port setting for your system.")
        # more interfaces go here
        self.settings.addUserCallSign(callsign,name,prefix)
        # ?? is this needed? self.settings.setActiveProfile("Outpost") # the default profile
        self.settings.setActiveUserCallSign(self.settings.getUserCallSigns()[0])

        self.settings.setProfile("MessageSettings/DefaultNewMessageType","P")
        self.settings.setProfile("MessageSettings/AddMessageNumber",True)
        self.settings.setProfile("MessageSettings/Hyphenation_flag","1")
        self.settings.setProfile("MessageSettings/AddCharacter",True)
        self.settings.setProfile("MessageSettings/CharacterToAdd","P")
        self.settings.setProfile("MessageSettings/AddMessageNumberToInbound",True)

        if not firsttime:
            self.updateStatusBar()
            self.on_actionStation_ID_triggered() # if firsttime, will happen a little later




if __name__ == "__main__": 
    app = QApplication(sys.argv)
    app.setStyle(QStyleFactory.create("Fusion"))
    darkmode = False
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == "-dark":
            darkmode = True
        # elif sys.argv[i] == "-x":
        #     i += 1
        #     z = int(sys.argv[i])
        i += 1
        
    if darkmode:
        p = QPalette()
        p.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
        p.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
        p.setColor(QPalette.ColorRole.Base, QColor(42, 42, 42)) # the color of QTableWidgets
        p.setColor(QPalette.ColorRole.AlternateBase, QColor(66, 66, 66))
        p.setColor(QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.white)
        p.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
        p.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
        p.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
        p.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
        p.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
        p.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
        p.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
        p.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.white)
        app.setPalette(p)

    mainwindow = MainWindow()
    mainwindow.show()
    sys.exit(app.exec())

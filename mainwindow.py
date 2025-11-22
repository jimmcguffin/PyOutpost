# pylint:  disable="line-too-long,missing-function-docstring,multiple-statements,no-name-in-module"

import sys
from enum import Enum
from operator import attrgetter
from urllib.parse import quote_plus,unquote_plus

from PyQt6.QtCore import Qt,QIODeviceBase
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
import searchdialog
from mailfolder import MailFolder, MailBoxHeader, MailFlags, FieldsToSearch
from tncparser import KantronicsKPC3Plus
from bbsparser import Jnos2Parser
from serialstream import SerialStream
from globalsignals import global_signals

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = PersistentData()
        self.serialport = QSerialPort()
        self.sdata = bytearray()
        self.serialStream = SerialStream(self.serialport)
        self.tnc_parser = None
        self.tempory_status_bar_message = ""
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
        self.forms = []
        try:
            with open("forms.csv","rt",encoding="windows-1252") as file:
                for line in file.readlines():
                    line = line.rstrip()
                    if not line: continue
                    if line[0] == '#': continue
                    f = line.split(",")
                    if len(f) < 3: continue
                    index = len(self.forms)
                    self.forms.append(f)
                    action = self.menuForms.addAction(f[0])
                    action.setProperty("FormIndex",index)
                    action.triggered.connect(self.onNewForm)
                    #self.menuForms.addAction(f[0]).triggered.connect(lambda: self.onNewForm(index))
        except FileNotFoundError:
            pass
        self.actionBBS.triggered.connect(self.OnBbsSetup)
        self.actionInterface.triggered.connect(self.OnInterfaceSetup)
        self.actionStation_ID.triggered.connect(self.OnStationId)
        self.actionSend_Receive_Settings.triggered.connect(self.on_send_receive_settings)
        self.actionMessage_Settings.triggered.connect(self.onMessageSettings)
        self.actionGeneral_Settings.triggered.connect(self.onGeneralSettings)
        self.actionDelete.triggered.connect(self.onDeleteMessages)
        self.cProfile.currentTextChanged.connect(self.onProfileChanged)
        self.actionNewProfile.triggered.connect(self.onNewProfile)
        self.cMailList.cellDoubleClicked.connect(self.onReadMessage)
        self.cMailList.customContextMenuRequested.connect(self.onMailListRightClick)
        self.cMailList.horizontalHeader().sectionClicked.connect(self.onSortMail)
        self.actionSearch.triggered.connect(self.on_search)
        self.actionSend_Receive.triggered.connect(lambda: self.on_send_receive(True,True,True))
        self.actionSend_Receive_No_Bulletins.triggered.connect(lambda: self.on_send_receive(True,True,False))
        self.actionSend_Only.triggered.connect(lambda: self.on_send_receive(True,False,False))
        self.actionReceive_Only.triggered.connect(lambda: self.on_send_receive(False,True,False)) # not sure about the last False
        self.actionReset_all_to_SCC_standard.triggered.connect(self.resetAllToSccStandard)
        self.cNew.clicked.connect(self.onNewMessage)
        #self.cOpen.clicked.connect(self.onNewMessage)
        self.cArchive.clicked.connect(self.onArchiveMessages)
        self.cDelete.clicked.connect(self.onDeleteMessages)
        #self.cPrint.clicked.connect(self.onDeleteMessages)
        self.cSearch.clicked.connect(self.on_search)
        self.cSendReceive.clicked.connect(lambda: self.on_send_receive(True,True,True))
        self.cSendOnly.clicked.connect(lambda: self.on_send_receive(True,False,False))
        self.cReceiveOnly.clicked.connect(lambda: self.on_send_receive(False,True,False))

        self.cInTray.clicked.connect(lambda: self.onSelectFolder(MailFlags.FOLDER_IN_TRAY))
        self.cOutTray.clicked.connect(lambda: self.onSelectFolder(MailFlags.FOLDER_OUT_TRAY))
        self.cSentMessages.clicked.connect(lambda: self.onSelectFolder(MailFlags.FOLDER_SENT))
        self.cArchived.clicked.connect(lambda: self.onSelectFolder(MailFlags.FOLDER_ARCHIVE))
        self.cDrafMessages.clicked.connect(lambda: self.onSelectFolder(MailFlags.FOLDER_DRAFT))
        self.cDeleted.clicked.connect(lambda: self.onSelectFolder(MailFlags.FOLDER_DELETED))
        self.cFolder1.clicked.connect(lambda: self.onSelectFolder(MailFlags.FOLDER_1))
        self.cFolder2.clicked.connect(lambda: self.onSelectFolder(MailFlags.FOLDER_2))
        self.cFolder3.clicked.connect(lambda: self.onSelectFolder(MailFlags.FOLDER_3))
        self.cFolder4.clicked.connect(lambda: self.onSelectFolder(MailFlags.FOLDER_4))
        self.cFolder5.clicked.connect(lambda: self.onSelectFolder(MailFlags.FOLDER_5))
        self.cFolderSearchResults.clicked.connect(lambda: self.onSelectFolder(MailFlags.FOLDER_SEARCH_RESULTS))
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
        #GlobalSignals().status_bar_message.connect(self.on_status_bar_message)
        #self.setStatusBar(self.cStatusBar)
        self.updateProfileList()
        self.updateStatusBar()
        self.mailSortIndex = 0
        self.mailSortBackwards = False
        self.mailIndex = []
        self.mailfolder = MailFolder()
        self.currentFolder = MailFlags.FOLDER_IN_TRAY
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
        self.menuMove_to_Folder.actions()[0].triggered.connect(lambda: self.onMoveToFolder(MailFlags.FOLDER_IN_TRAY))
        self.menuMove_to_Folder.actions()[1].triggered.connect(lambda: self.onMoveToFolder(MailFlags.FOLDER_OUT_TRAY))
        self.menuMove_to_Folder.addAction("Sent Messages").triggered.connect(lambda: self.onMoveToFolder(MailFlags.FOLDER_SENT))
        self.menuMove_to_Folder.addAction("Archive").triggered.connect(lambda: self.onMoveToFolder(MailFlags.FOLDER_ARCHIVE))
        self.menuMove_to_Folder.addAction("Draft Messages").triggered.connect(lambda: self.onMoveToFolder(MailFlags.FOLDER_DRAFT))
        self.menuMove_to_Folder.addAction("Deleted").triggered.connect(lambda: self.onMoveToFolder(MailFlags.FOLDER_DELETED))
        self.menuMove_to_Folder.addAction(f[0]).triggered.connect(lambda: self.onMoveToFolder(MailFlags.FOLDER_1))
        self.menuMove_to_Folder.addAction(f[1]).triggered.connect(lambda: self.onMoveToFolder(MailFlags.FOLDER_2))
        self.menuMove_to_Folder.addAction(f[2]).triggered.connect(lambda: self.onMoveToFolder(MailFlags.FOLDER_3))
        self.menuMove_to_Folder.addAction(f[3]).triggered.connect(lambda: self.onMoveToFolder(MailFlags.FOLDER_4))
        self.menuMove_to_Folder.addAction(f[4]).triggered.connect(lambda: self.onMoveToFolder(MailFlags.FOLDER_5))

        self.menuCopy_to_Folder.actions()[0].triggered.connect(lambda: self.onCopyToFolder(MailFlags.FOLDER_IN_TRAY))
        self.menuCopy_to_Folder.actions()[1].triggered.connect(lambda: self.onCopyToFolder(MailFlags.FOLDER_OUT_TRAY))
        self.menuCopy_to_Folder.addAction("Sent Messages").triggered.connect(lambda: self.onCopyToFolder(MailFlags.FOLDER_SENT))
        self.menuCopy_to_Folder.addAction("Archive").triggered.connect(lambda: self.onCopyToFolder(MailFlags.FOLDER_ARCHIVE))
        self.menuCopy_to_Folder.addAction("Draft Messages").triggered.connect(lambda: self.onCopyToFolder(MailFlags.FOLDER_DRAFT))
        self.menuCopy_to_Folder.addAction("Deleted").triggered.connect(lambda: self.onCopyToFolder(MailFlags.FOLDER_DELETED))
        self.menuCopy_to_Folder.addAction(f[0]).triggered.connect(lambda: self.onCopyToFolder(MailFlags.FOLDER_1))
        self.menuCopy_to_Folder.addAction(f[1]).triggered.connect(lambda: self.onCopyToFolder(MailFlags.FOLDER_2))
        self.menuCopy_to_Folder.addAction(f[2]).triggered.connect(lambda: self.onCopyToFolder(MailFlags.FOLDER_3))
        self.menuCopy_to_Folder.addAction(f[3]).triggered.connect(lambda: self.onCopyToFolder(MailFlags.FOLDER_4))
        self.menuCopy_to_Folder.addAction(f[4]).triggered.connect(lambda: self.onCopyToFolder(MailFlags.FOLDER_5))
        global_signals.signal_new_outgoing_text_message.connect(self.onHandleNewOutgoingMessage)
        global_signals.signal_new_outgoing_form_message.connect(self.onHandleNewOutgoingFormMessage)

    def closeEvent(self, event):
        if self.mailfolder.needs_cleaning():
            self.mailfolder.clean() # erases items in folder X
        event.accept()

    def onSelectFolder(self,folder:MailFlags):
        self.currentFolder = folder
        self.updateMailList()

    def onMoveToFolder(self,folder:MailFlags):
        indexlist = []
        for item in self.cMailList.selectedItems():
            if item.column() == 0:
                indexlist.append(self.mailIndex[item.row()])
        # if moving from deleted to deleted, move to FOLDER_NONE
        if self.currentFolder == MailFlags.FOLDER_DELETED and folder == MailFlags.FOLDER_DELETED:
            folder = MailFlags.FOLDER_NONE
        self.mailfolder.move_mail(indexlist,self.currentFolder,folder)
        self.updateMailList()
    def onCopyToFolder(self,folder):
        indexlist = []
        for item in self.cMailList.selectedItems():
            if item.column() == 0:
                indexlist.append(self.mailIndex[item.row()])
        self.mailfolder.copy_mail(indexlist,folder)
        self.updateMailList()
    def onMarkAsNew(self,index,mark):
        self.mailfolder.mark_as_new(index,mark)
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
        iddlg = interfacedialog.InterfaceDialog(self.settings,self)
        iddlg.setComPortList(l)
        iddlg.exec()
        self.updateStatusBar()
    def OnStationId(self):
        sid = stationiddialog.StationIdDialog(self.settings,self)
        sid.exec()
        self.updateStatusBar()
    def updateStatusBar(self):
        if not hasattr(self,'cStatusCenter'): return
        if self.tempory_status_bar_message:
            self.cStatusCenter.setText(self.tempory_status_bar_message)
        else:
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
            if 0 <= i < 9:
                self.mailSortIndex = i
                self.mailSortBackwards = False # not sure if this is desired, maybe keep array of these
        print(f"sort {self.mailSortIndex} {self.mailSortBackwards}")
        self.updateMailList()
    def updateMailList(self):
        tmpindex = self.mailSortIndex+2 # now 2 to 10
        #if tmpindex == 9: tmpindex = 10
        if 2 <= tmpindex <= 10:
            keyname = ["urgent","type_str","from_addr","to_addr","bbs","local_id","subject","date_sent","size"][tmpindex-2]
            headers = sorted(self.mailfolder.get_headers(self.currentFolder),key=attrgetter(keyname), reverse=self.mailSortBackwards)
        else:
            headers = self.mailfolder.get_headers(self.currentFolder)
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
            urgent = ""
            if headers[i].urgent:
                urgent = "!!"
                # display line in red
            self.mailIndex.append(headers[i].index)
            self.cMailList.setItem(i,0,QTableWidgetItem(urgent))
            self.cMailList.setItem(i,1,QTableWidgetItem(headers[i].type_str))
            self.cMailList.setItem(i,2,QTableWidgetItem(headers[i].from_addr))
            self.cMailList.setItem(i,3,QTableWidgetItem(headers[i].to_addr))
            self.cMailList.setItem(i,4,QTableWidgetItem(headers[i].bbs))
            self.cMailList.setItem(i,5,QTableWidgetItem(headers[i].local_id))
            self.cMailList.setItem(i,6,QTableWidgetItem(headers[i].subject))
            self.cMailList.setItem(i,7,QTableWidgetItem(MailBoxHeader.to_outpost_date(headers[i].date_sent)))
            # this version does not show the date received
            self.cMailList.item(i,7).setTextAlignment(Qt.AlignmentFlag.AlignRight) # // to match the original
            self.cMailList.setItem(i,8,QTableWidgetItem(str(headers[i].size)))
            self.cMailList.item(i,8).setTextAlignment(Qt.AlignmentFlag.AlignRight)
            if headers[i].is_new():
                font =  self.cMailList.item(i,0).font()
                font.setBold(True)
                for j in range(9):
                    self.cMailList.item(i,j).setFont(font)
        self.cMailList.resizeRowsToContents()

    def on_send_receive_settings(self):
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
        tmp.show()
        tmp.raise_()
    def onNewForm(self):
        widget = self.sender()
        index = widget.property("FormIndex")
        tmp = formdialog.FormDialog(self.settings,self.forms[index][2],self.forms[index][1],self)
        tmp.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        tmp.show()
        tmp.raise_()
    def onHandleNewOutgoingMessage(self,mbh,m):
        # log activity
        mbh.flags |= MailFlags.IS_OUTGOING.value
        self.mailfolder.add_mail(mbh,m,MailFlags.FOLDER_OUT_TRAY)
        # log this
        try:
            with open("activity.log","ab") as file:
                s = f"s,{mbh.date_sent},{mbh.from_addr},{mbh.to_addr},{mbh.local_id},{quote_plus(mbh.subject)}\n"
                file.write(s.encode("windows-1252"))
        except FileNotFoundError:
            pass
        self.updateMailList()

    def onHandleNewOutgoingFormMessage(self,subject,m,urgent):
        tmp = newpacketmessage.NewPacketMessage(self.settings,self)
        tmp.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        tmp.setInitialData(subject,m,urgent)
        tmp.show()
        tmp.raise_()

    def onReadMessage(self,row,_):
        if row < 0 or row >= len(self.mailIndex): return
        h,m = self.mailfolder.get_message(self.mailIndex[row])
        if not h: return
        # is this a regular text message or a form?
        # for now, decide based on subject, but would be better to use message body
        isform = False
        if not h.subject.startswith("DELIVERED"):
            s = h.subject.split("_")
            if len(s) >= 3:
                for f in self.forms:
                    # one form was two entries for the name
                    f1,_,_ = f[1].partition(" or ")
                    if s[2] == f1 or s[2] == f[2]:
                        isform = True
                        tmp = formdialog.FormDialog(self.settings,f[2],f[1],self)
                        tmp.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
                        tmp.setData(h,m)
                        tmp.show()
                        tmp.raise_()
                        break
        if not isform:
            tmp = readmessagedialog.ReadMessageDialog(self.settings,self)
            tmp.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
            tmp.setData(h,m)
            tmp.show()
            tmp.raise_()
        if self.mailfolder.mark_as_new(self.mailIndex[row],False):
            self.updateMailList()
    
    def on_read_message_text(self,row):
        if row < 0 or row >= len(self.mailIndex): return
        h,m = self.mailfolder.get_message(self.mailIndex[row])
        if not h: return
        tmp = readmessagedialog.ReadMessageDialog(self.settings,self)
        tmp.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        tmp.setData(h,m)
        tmp.show()
        tmp.raise_()
        if self.mailfolder.mark_as_new(self.mailIndex[row],False):
            self.updateMailList()

    def on_read_message_form(self,row):
        # the just calls the auto-detector that double-clicking calls
        self.onReadMessage(self,row,0)

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
            case "1.5": self.serialport.setStopBits(QSerialPort.StopBits.OneAndHalfStop)
            case "2":   self.serialport.setStopBits(QSerialPort.StopBits.TwoStop)
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
    
    def on_send_receive(self,send:bool,recv:bool,recv_bulletins:bool):
        # if a cycle was in progress, cancel it
        if self.tnc_parser:
            self.on_end_send_receive()
        port = self.settings.getInterface("ComPort")
        if not port:
            QMessageBox.critical(self,"Error",f"Error serial port has not been configuired, go to Setup/Interface")
            return
        # port = port.partition('/')[0].rstrip()

        f = self.openSerialPort()
        if not f:
            QMessageBox.critical(self,"Error",f"Error {self.serialport.errorString()} opening serial port")
            return
        self.tnc_parser = KantronicsKPC3Plus(self.settings,self)
        #self.bbsParser = Nos2Parser(self.settings,self)
        self.serialStream = SerialStream(self.serialport)
        global_signals.signal_new_incoming_message.connect(self.onNewIncomingMessage)
        global_signals.signal_message_sent.connect(self.on_message_sent)
        self.tnc_parser.signalDisconnected.connect(self.on_end_send_receive)
        self.tnc_parser.signal_status_bar_message.connect(self.on_status_bar_message)
        srflags = 0
        if send:
            srflags |= 1
        if recv:
            srflags |= 2
        if recv_bulletins:
            srflags |= 4
        self.tnc_parser.start_session(self.serialStream,srflags)

    def on_end_send_receive(self):
        #self.serialport.close()
        # this causes a loop # self.tnc_parser.end_session()
        self.serialStream.reset()
        self.serialStream = None
        self.tnc_parser = None

    def onNewIncomingMessage(self,mbh:MailBoxHeader,m):
        self.mailfolder.add_mail(mbh,m,MailFlags.FOLDER_IN_TRAY)
        # log this
        try:
            with open("activity.log","ab") as file:
                s = f"r,{mbh.date_received},{mbh.from_addr},{mbh.to_addr},{mbh.local_id},{quote_plus(mbh.subject)}\n"
                file.write(s.encode("windows-1252"))
        except FileNotFoundError:
            pass
        self.updateMailList()

    def on_message_sent(self,index:int):
        indexlist = [index]
        self.mailfolder.move_mail(indexlist,MailFlags.FOLDER_OUT_TRAY,MailFlags.FOLDER_SENT)
        self.updateMailList()

    def onDeleteMessages(self):
        indexlist = []
        for item in self.cMailList.selectedItems():
            if item.column() == 0:
                indexlist.append(self.mailIndex[item.row()])
        self.mailfolder.move_mail(indexlist,self.currentFolder,MailFlags.FOLDER_DELETED)
        self.updateMailList()

    def onArchiveMessages(self):
        indexlist = []
        for item in self.cMailList.selectedItems():
            if item.column() == 0:
                indexlist.append(self.mailIndex[item.row()])
        self.mailfolder.move_mail(indexlist,self.currentFolder,MailFlags.FOLDER_ARCHIVE)
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
        mm.addAction("as Text").triggered.connect(lambda: self.on_read_message_text(row))  #.setEnabled(False)
        mm.addAction("in a Form").triggered.connect(lambda: self.on_read_message_form(row))  #.setEnabled(False)
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
        mm.addAction("In Tray").triggered.connect(lambda: self.onMoveToFolder(MailFlags.FOLDER_IN_TRAY))
        mm.addAction("Out Tray").triggered.connect(lambda: self.onMoveToFolder(MailFlags.FOLDER_OUT_TRAY))
        mm.addAction("Sent Messages").triggered.connect(lambda: self.onMoveToFolder(MailFlags.FOLDER_SENT))
        mm.addAction("Archive").triggered.connect(lambda: self.onMoveToFolder(MailFlags.FOLDER_ARCHIVE))
        mm.addAction("Draft Messages").triggered.connect(lambda: self.onMoveToFolder(MailFlags.FOLDER_DRAFT))
        mm.addAction("Deleted").triggered.connect(lambda: self.onMoveToFolder(MailFlags.FOLDER_DELETED))
        mm.addAction(f[0]).triggered.connect(lambda: self.onMoveToFolder(MailFlags.FOLDER_1))
        mm.addAction(f[1]).triggered.connect(lambda: self.onMoveToFolder(MailFlags.FOLDER_2))
        mm.addAction(f[2]).triggered.connect(lambda: self.onMoveToFolder(MailFlags.FOLDER_3))
        mm.addAction(f[3]).triggered.connect(lambda: self.onMoveToFolder(MailFlags.FOLDER_4))
        mm.addAction(f[4]).triggered.connect(lambda: self.onMoveToFolder(MailFlags.FOLDER_5))
        m.addMenu(mm)

        mm = QMenu("Copy To",self)
        mm.addAction("In Tray").triggered.connect(lambda: self.onCopyToFolder(MailFlags.FOLDER_IN_TRAY))
        mm.addAction("Out Tray").triggered.connect(lambda: self.onCopyToFolder(MailFlags.FOLDER_OUT_TRAY))
        mm.addAction("Sent Messages").triggered.connect(lambda: self.onCopyToFolder(MailFlags.FOLDER_SENT))
        mm.addAction("Archive").triggered.connect(lambda: self.onCopyToFolder(MailFlags.FOLDER_ARCHIVE))
        mm.addAction("Draft Messages").triggered.connect(lambda: self.onCopyToFolder(MailFlags.FOLDER_DRAFT))
        mm.addAction("Deleted").triggered.connect(lambda: self.onCopyToFolder(MailFlags.FOLDER_DELETED))
        mm.addAction(f[0]).triggered.connect(lambda: self.onCopyToFolder(MailFlags.FOLDER_1))
        mm.addAction(f[1]).triggered.connect(lambda: self.onCopyToFolder(MailFlags.FOLDER_2))
        mm.addAction(f[2]).triggered.connect(lambda: self.onCopyToFolder(MailFlags.FOLDER_3))
        mm.addAction(f[3]).triggered.connect(lambda: self.onCopyToFolder(MailFlags.FOLDER_4))
        mm.addAction(f[4]).triggered.connect(lambda: self.onCopyToFolder(MailFlags.FOLDER_5))
        m.addMenu(mm)
        m.addSeparator()
        m.addAction("Delete").triggered.connect(lambda: self.onMoveToFolder(MailFlags.FOLDER_DELETED))

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
        self.settings.addBBS("XSC_W2XSC-1","W2XSC-1","Santa Clara County ARES/RACES Packet System.  Located on Crystal Peak (South County).  JNOS.")
        self.settings.addBBS("XSC_W3XSC-1","W3XSC-1","Santa Clara County ARES/RACES Packet System.  Located in Palo Alto.  JNOS.")
        self.settings.addBBS("XSC_W4XSC-1","W4XSC-1","Santa Clara County ARES/RACES Packet System.  Located on Frazier Peak (above Milpitas).  JNOS.")
        self.settings.addBBS("XSC_W5XSC-1","W5XSC-1","Santa Clara County ARES/RACES Packet System.  Used for training, back-up, etc.  JNOS.")
        self.settings.addBBS("XSC_W6XSC-1","W6XSC-1","Santa Clara County ARES/RACES Packet System.  Used for testing, etc.  JNOS.")
        for bbs in self.settings.getBBSs():
            self.settings.setActiveBBS(bbs)
            for dc in Jnos2Parser.get_default_commands.items():
                self.settings.setBBS(dc[0],dc[1])
        self.settings.setActiveBBS(self.settings.getBBSs()[0])

        self.settings.addInterface("XSC_Kantronics_KPC3-Plus","KPC3+ TNC for use with Santa Clara County's BBS System. Verify the COM port setting for your system.")
        self.settings.setActiveInterface(self.settings.getInterfaces()[0])
        for p in KantronicsKPC3Plus.getDefaultPrompts():
            self.settings.setInterface(p[0],p[1])
        self.settings.setInterface("AlwaysSendInitCommands",True)
        self.settings.setInterface("IncludeCommandPrefix",False)
        for dc in KantronicsKPC3Plus.get_default_commands.items():
            self.settings.setInterface(dc[0],dc[1])
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
            self.OnStationId() # if firsttime, will happen a little later
    def on_status_bar_message(self,s):
        self.tempory_status_bar_message = s
        self.updateStatusBar()

    def on_search(self):
        self.cFolderSearchResults.setEnabled(False)
        sd = searchdialog.SearchDialog(self.settings,self)
        if sd.exec() != 1:
            return
        folders_to_search = self.currentFolder
        if sd.fields_to_search & FieldsToSearch.ALL_FOLDERS.value:
            folders_to_search = MailFlags.FOLDER_SEARCHABLE
        if self.mailfolder.search(sd.search,sd.fields_to_search,folders_to_search):
            self.cFolderSearchResults.setEnabled(True)
            self.cFolderSearchResults.setChecked(True)
            self.onSelectFolder(MailFlags.FOLDER_SEARCH_RESULTS)


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
        
    # if darkmode: # the forms look vary bad in this mode
    #     p = QPalette()
    #     p.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
    #     p.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
    #     p.setColor(QPalette.ColorRole.Base, QColor(42, 42, 42)) # the color of QTableWidgets
    #     p.setColor(QPalette.ColorRole.AlternateBase, QColor(66, 66, 66))
    #     p.setColor(QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.white)
    #     p.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
    #     p.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
    #     p.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
    #     p.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
    #     p.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
    #     p.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
    #     p.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
    #     p.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.white)
    #     app.setPalette(p)

    mainwindow = MainWindow()
    mainwindow.show()
    sys.exit(app.exec())

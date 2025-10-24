import sys
from PyQt6 import QtWidgets
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMainWindow, QDialog, QInputDialog, QApplication, QStyleFactory, QLabel, QFrame, QStatusBar, QTableWidgetItem
from PyQt6.uic import load_ui
from PyQt6.QtSerialPort import QSerialPortInfo
from persistentdata import PersistentData
import bbsdialog
import interfacedialog
import stationiddialog
import sendreceivesettingsdialog
import messagesettingsdialog
import newpacketmessage
from mailfolder import MailFolder

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
        self.mailfolder = MailFolder()
        self.mailfolder.load("Inbox.mail")
        self.updateMailList()
        self.outGoingMessages = []

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

    def updateMailList(self):
        headers = self.mailfolder.getHeaders()
        # this is c++ code that sorts the list
        # std::vector<int> h(headers.size());
        # iota(h.begin(),h.end(),0);
        # sort(h.begin(),h.end(),[this,headers](int a, int b)
        #     {
        #     switch (m_MailSortIndex)
        #         {
        #         case 0: return headers[a].m_U < headers[b].m_U;
        #         case 1: return headers[a].m_Type < headers[b].m_Type;
        #         case 2: return headers[a].m_From < headers[b].m_From;
        #         case 3: return headers[a].m_To < headers[b].m_To;
        #         case 4: return headers[a].m_BBS < headers[b].m_BBS;
        #         case 5: return headers[a].m_LocalId < headers[b].m_LocalId;
        #         case 6: return headers[a].m_Subject < headers[b].m_Subject;
        #         case 7: return headers[a].m_Date < headers[b].m_Date;
        #         case 8: return headers[a].m_Size < headers[b].m_Size;
        #         default: assert(0); return true;
        #         }
        #     });
        # if (m_MailSortBackwards) std::reverse(h.begin(),h.end());
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
            j = i # when sorting works, use this j = h[i];
            self.cMailList.setItem(i,0,QTableWidgetItem(headers[j][1]))
            self.cMailList.setItem(i,1,QTableWidgetItem(headers[j][2]))
            self.cMailList.setItem(i,2,QTableWidgetItem(headers[j][3]))
            self.cMailList.setItem(i,3,QTableWidgetItem(headers[j][4]))
            self.cMailList.setItem(i,4,QTableWidgetItem(headers[j][5]))
            self.cMailList.setItem(i,5,QTableWidgetItem(headers[j][6]))
            self.cMailList.setItem(i,6,QTableWidgetItem(headers[j][7]))
            self.cMailList.setItem(i,7,QTableWidgetItem(headers[j][8]))
            # this version does not show the date received
            self.cMailList.item(i,7).setTextAlignment(Qt.AlignmentFlag.AlignRight) # // to match the original
            self.cMailList.setItem(i,8,QTableWidgetItem(str(headers[j][10])))
            self.cMailList.item(i,8).setTextAlignment(Qt.AlignmentFlag.AlignRight)
        self.cMailList.resizeRowsToContents()

    def onSendReceiveSettings(self):
        srsd = sendreceivesettingsdialog.SendReceiveSettingsDialog(self.settings,self)
        srsd.exec()
    def onMessageSettings(self):
        msd = messagesettingsdialog.MessageSettingsDialog(self.settings,self)
        msd.exec()
    def onNewMessage(self):
        tmp = newpacketmessage.NewPacketMessage(self.settings,self.outGoingMessages,self)
        tmp.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        tmp.signalNewMessage.connect(self.onHandleNewMessage)
        tmp.show()
        tmp.raise_()
    def onHandleNewMessage(self,s1,s2,s3):
        print(s1,s2,s3)

if __name__ == "__main__": 
    app = QApplication(sys.argv)
    app.setStyle(QStyleFactory.create("Fusion"))
    mainwindow = MainWindow()
    mainwindow.show()
    sys.exit(app.exec())

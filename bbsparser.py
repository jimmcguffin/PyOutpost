from PyQt6.QtCore import QObject, pyqtSignal
from persistentdata import PersistentData
from serialstream import SerialStream
import re
from mailfolder import MailFolder, MailBoxHeader

class BbsMessage():
    def __init__(self,s,h=None):
        self.whatToSend = s
        self.handler = h # gets called when responded to

class BbsParser(QObject):
    signalTimeout = pyqtSignal()
    signalDisconnected = pyqtSignal()
    signalNewIncomingMessage = pyqtSignal(MailBoxHeader,str)
    signalOutgingMessageSent= pyqtSignal()
    def __init__(self,pd,parent=None):
        super(BbsParser,self).__init__(parent)
        self.pd = pd
        self.stuffToSend = list()
        self.itemsSent = list() # they get moved to the "Sent" folder
    def startSession(self,ss):
        self.serialStream = ss
        self.serialStream.lineEnd = b">\r\n"
        self.serialStream.signalLineRead.disconnect()
        self.serialStream.signalLineRead.connect(self.onResponse)        
        self.serialStream.signalDisconnected.connect(self.onDisconnected)
    def endSession(self):
        return
    def onDisconnected(self):
        self.signalDisconnected.emit() 

class Jnos2Parser(BbsParser):
    def __init__(self,pd,parent=None):
        super(Jnos2Parser,self).__init__(pd,parent)
        self.outtray = MailFolder()
    def startSession(self,ss):
        super().startSession(ss)
        self.stuffToSend.append(BbsMessage("")) # there is a prompt/terminator that will arrive without being told
        self.stuffToSend.append(BbsMessage("x\r")) # this toggles long/short prompt, but we don't know the current state
        self.stuffToSend.append(BbsMessage("xa\r"))
        self.stuffToSend.append(BbsMessage("xm 0\r"))
        # if there are outgoing messages send them now
        # this may turn out to be a bad idea but for now I read from the OutTray file
        self.outtray.load("OutTray")
        for i in range(0,len(self.outtray.mail)):
            mbh,m = self.outtray.getMessage(i)
            m2 = m.replace("\r\n","\r").replace("\n","\r") # make sure there are no linefeeds
            if not m2.endswith('\r'): m2 += '\r'
            self.stuffToSend.append(BbsMessage(f"sp {mbh.mTo}\r{mbh.mSubject}\r{m2}/EX\r"),lambda: self.itemsSent.append(i))
            #self.stuffToSend.append(BbsMessage("")) # aborb the useless line of text that follows
        self.stuffToSend.append(BbsMessage("la\r",self.handleList))
        #	self.stuffToSend.append(BbsMessage("a XSCPERM\r",self.handleArea))
        #	self.stuffToSend.append(BbsMessage("la\r",self.handleList))
        #	self.stuffToSend.pushappend_back(BbsMessage("a XSCEVENT\r",self.handleList))
        #	self.stuffToSend.append(BbsMessage("la\r",self.handleList))
        #	self.stuffToSend.append(BbsMessage("a ALLXSC\r",self.handleArea))
        #	self.stuffToSend.append(BbsMessage("la\r",self.handleList))

        # start things going
        self.serialStream.write(self.stuffToSend[0].whatToSend)

    def onResponse(self,r):
        if not self.stuffToSend:
            return # nothing expected
        # this is probably/hopefully the response to the front element
        query = self.stuffToSend[0].whatToSend
        # todo: code here used to match reply to query but not it appears to be gone
        # should match up to first \n
        qbase = query.partition("\r")[0]
        print(f"<<{query.replace("\r","|").replace("\n","|")}>> returned <<{r.replace("\r","|").replace("\n","|")}>>")
        if (r.startswith(qbase)):
            print("Matches")
        else:
            print("Doesn't match")
        if self.stuffToSend[0].handler:
            self.stuffToSend[0].handler(r)
        del self.stuffToSend[0:1]
        if self.stuffToSend:
            self.serialStream.write(self.stuffToSend[0].whatToSend)
    def handleList(self,r):
        # if we get here, it means that all of the outgoing messages have been sent
        if self.itemsSent:
            self.outtray.copyMail(self.itemsSent,"Sent")
            self.outtray.deleteMail(self.itemsSent)
            self.itemsSent.clear()
        print(f"got list {r}")
        # sample "la\r\nMail area: kw6w\r\n1 message  -  1 new\r\n\St.  #  TO            FROM     DATE   SIZE SUBJECT\r\n> N   1 kw6w@w1xsc.sc pkttue   Oct 15  747 DELIVERED: W6W-303P_P_ICS213_Shutti\r\nArea: kw6w Current msg# 1.\r\n" +terminator
        # or "la\r\nMail area: xscperm\r\n4 messages  -  4 new\r\nSt.  #  TO            FROM     DATE   SIZE SUBJECT\r\n> N   1 xscperm       xsceoc   Nov 27 5962 SCCo XSC Tactical Calls v191127    \r\n  N   2 xscperm       xsceoc   Sep  5 1932 SCCo Packet Frequencies v200905    \r\n  N   3 xscperm       xsceoc   Aug 13 2768 SCCo Packet Subject Line v220803   \r\n  N   4 xscperm       xsceoc   Aug  9 4326 SCCo Packet Tactical Calls v2024080\r\nArea: xscperm Current msg# 1.\r\n?,A,B,C,CONV,D,E,F,H,I,IH,IP,J,K,L,M,N,NR,O,P,PI,R,S,T,U,V,W,X,Z " >>
        lines = r.splitlines()
        if len(lines) < 3: return
        # line 0 is just the la command
        # line 1 will have the mail area
        area = ""
        words = lines[1].split()
        if words and words[0] == "Mail" and words[1] == "area:":
            area = words[2]
        # line 2 will have the counts
        nmessages = 0
        m = re.match(r"(\d+) message",lines[2])
        if m: nmessages = int(m.groups()[0])
        for i  in range(nmessages):
            tmp = f"r {i+1}\r"
            self.stuffToSend.append(BbsMessage(tmp,self.handleRead))
        self.stuffToSend.append(BbsMessage("bye\r"))
        pass
    def handleArea(self,r):
        print(f"got area {r}")
        pass
    def handleRead(self,r):
        print(f"got read {r}")
        lines = r.splitlines()
        if lines and lines[-1] == "": lines.pop()
        # discard up until last blank line
        while len(lines) >= 2 and lines[-1] != "": lines.pop()
        nl = len(lines)
        mbh = MailBoxHeader()
        inheader = True
        messagebody = ""
        for i in range(2,nl):
            if lines[i] == "" and inheader: # the blank line that separates header from body
                inheader = False
            elif (inheader):
                l,s,r = lines[i].partition(':')
                l = l.strip()
                r = r.strip()
                if l == "Date":
                    mbh.mDateSent = MailBoxHeader.normalizedDate(r)
                elif l == "From":
                    mbh.mFrom = r
                elif l == "To":
                    mbh.mTo = r
                elif l == "Subject":
                    mbh.mSubject = r
            else:
                messagebody += lines[i] + "\r\n"
        if not messagebody: return
        mbh.mIsNew = "Y"
        # todo: figure out the "urgent" flag and the message type
        mbh.mBbs = self.pd.getBBS("ConnectName")
        mbh.mDateReceived = MailBoxHeader.normalizedDate()
        mbh.mSize = len(messagebody)
        self.signalNewIncomingMessage.emit(mbh,messagebody)
        # todo: then delete the message from the server
from PyQt6.QtCore import QObject, pyqtSignal
from persistentdata import PersistentData
from serialstream import SerialStream
import re
from mailfolder import MailFolder, MailBoxHeader, MailFlags

# there is a list of these in the parser
# they are executed one at a time
# if there is a "mWhatToSend"", it is sent
# then it waits until a response is received, which must match what was sent (due to echo mode)
# then it calls "mHandler"
class BbsSequenceStep():
    def __init__(self,s,h=None,data=None):
        self.mWhatToSend = s # can be blank
        self.mHandler = h # gets called when responded to, can be None
        # arbitrary data item that can be passed to the handler (after the reply value)
        self.mData = data
class BbsSequenceImmediateStep():
    def __init__(self,h,data=None):
        self.mHandler = h # gets called as soon as the sequencer gets to this item
        # arbitrary data item that can be passed to the handler (as the only value)
        self.hData = data


# at any given time, "bbsSequence" is a mix of BbsSequenceSteps and BbsSequenceImmediateSteps, but the first entry as always a BbsSequenceStep that has 
# already sent its mWhatToSend value and is awaiting the reply. There are two times this this is briefly not true:
# 1 - the sequence is empty and a new bbsSequence has just been pushed
# 2 - the front step has just been removed. Now the checkSequence should consume all BbsSequenceImmediateSteps until it gets to a BbsSequenceStep and then 
# send the new mWhatToSend so that it is "normalled-up"
class BbsParser(QObject):
    signalTimeout = pyqtSignal()
    signalDisconnected = pyqtSignal()
    signalNewIncomingMessage = pyqtSignal(MailBoxHeader,str)
    signalOutgingMessageSent= pyqtSignal()
    def __init__(self,pd,parent=None):
        super(BbsParser,self).__init__(parent)
        self.pd = pd
        self.bbsSequence = list() # an list of BbsSequenceSteps
        self.stepinprogress = False
        self.itemsSent = list() # they get moved to the "Sent" folder
        self.messagesRead = list()
    def startSession(self,ss):
        self.serialStream = ss
        self.serialStream.lineEnd = b">\r\n"
        self.serialStream.signalLineRead.disconnect()
        self.serialStream.signalLineRead.connect(self.onResponse)        
        self.serialStream.signalDisconnected.connect(self.onDisconnected)
    def endSession(self):
        return
    def addStep(self,step): # argument is a BbsSequenceStep or a BbsSequenceImmediateStep
        # things are different if the sequence is empty
        if self.bbsSequence:
            self.bbsSequence.append(step) # it is not empty, just add it
        else:
            if isinstance(step,BbsSequenceImmediateStep):
                step.mHandler(step.hData)
            else:
                self.bbsSequence.append(step)
                self.serialStream.write(self.bbsSequence[0].mWhatToSend)
        # self.bbsSequence.append(step)
        # self.checkSequence()
    # call this when items have been removed and there is a new "front"
    def checkSequence(self):
        # if there are immediate-mode comamnds, do them
        while self.bbsSequence and isinstance(self.bbsSequence[0],BbsSequenceImmediateStep):
            if self.bbsSequence[0].mHandler: # I think this will always be true
                self.bbsSequence[0].mHandler(self.bbsSequence[0].hData)
            del self.bbsSequence[0:1]
        if len(self.bbsSequence) > 0:
            assert isinstance(self.bbsSequence[0],BbsSequenceStep)
            self.serialStream.write(self.bbsSequence[0].mWhatToSend)
    def onDisconnected(self):
        self.signalDisconnected.emit() 

class Jnos2Parser(BbsParser):
    def __init__(self,pd,parent=None):
        super(Jnos2Parser,self).__init__(pd,parent)
        self.outtray = MailFolder()
    def startSession(self,ss):
        super().startSession(ss)
        self.addStep(BbsSequenceStep("",self.startSession2)) # there is a prompt/terminator that will arrive without being told
    def startSession2(self,r,data=None):  
        # if the initial prompt is long, change it to short
        if r.find("A,B,C,") >= 0:
            self.addStep(BbsSequenceStep("x\r")) # this toggles long/short prompt
        self.addStep(BbsSequenceStep("xa\r"))
        self.addStep(BbsSequenceStep("xm 0\r"))
        self.addStep(BbsSequenceImmediateStep(self.sendOutgoing))
    def sendOutgoing(self,data=None):
        # if there are outgoing messages send them now
        # this may turn out to be a bad idea but for now I read from the OutTray file
        self.outtray.load("OutTray")
        for i in range(0,len(self.outtray.mail)):
            mbh,m = self.outtray.getMessage(i)
            m2 = m.replace("\r\n","\r").replace("\n","\r") # make sure there are no linefeeds
            if not m2.endswith('\r'): m2 += '\r'
            self.addStep(BbsSequenceStep(f"sp {mbh.mTo}\r{mbh.mSubject}\r{m2}/EX\r",self.handleSent,i))
        self.addStep(BbsSequenceImmediateStep(self.sendLists))
    def sendLists(self,data=None):
        self.addStep(BbsSequenceStep("la\r",self.handleList))
        #	self.addStep(BbsSequenceStep("a XSCPERM\r",self.handleArea))
        #	self.addStep(BbsSequenceStep("la\r",self.handleList))
        #	self.addStep(BbsSequenceStep("a XSCEVENT\r",self.handleList))
        #	self.BbsSequenceStep("la\r",self.handleList))
        #	self.addStep(BbsSequenceStep("a ALLXSC\r",self.handleArea))
        #	self.addStep(BbsSequenceStep("la\r",self.handleList))
    def onResponse(self,r):
        if not self.bbsSequence:
            return # nothing expected
        # this is probably/hopefully the response to the front element
        query = self.bbsSequence[0].mWhatToSend
        # todo: code here used to match reply to query but not it appears to be gone
        # should match up to first \n
        qbase = query.partition("\r")[0]
        print(f"<<{query.replace("\r","|").replace("\n","|")}>> returned <<{r.replace("\r","|").replace("\n","|")}>>")
        if (r.startswith(qbase)):
            print("Matches")
        else:
            print("Doesn't match")
        if self.bbsSequence[0].mHandler:
            self.bbsSequence[0].mHandler(r,self.bbsSequence[0].mData)
        del self.bbsSequence[0:1]
        self.checkSequence()
    def handleList(self,r,data=None):
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
            self.addStep(BbsSequenceStep(tmp,self.handleRead,i))
        self.addStep(BbsSequenceImmediateStep(self.killReadMessages))
#        self.addStep(BbsSequenceStep("bye\r"))
        pass
    def killReadMessages(self,data=None):
        if self.messagesRead:
            k = "k"
            for m in self.messagesRead:
                k += " "
                k += str(m)
            self.addStep(BbsSequenceStep(k))
        self.addStep(BbsSequenceStep("bye\r"))
    def handleArea(self,r,data=None):
        print(f"got area {r}")
        pass
    def handleRead(self,r,data):
        print(f"got read {r}")
        if r.startswith("r "):
            self.messagesRead.append(data)
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
        mbh.mFlags = MailFlags.IsNew.value | MailFlags.FolderInTray.value
        # todo: figure out the "urgent" flag and the message type
        mbh.mBbs = self.pd.getBBS("ConnectName")
        mbh.mDateReceived = MailBoxHeader.normalizedDate()
        mbh.mSize = len(messagebody)
        self.signalNewIncomingMessage.emit(mbh,messagebody)
        # todo: then delete the message from the server
    def handleSent(self,r,i):
        self.itemsSent.append(i)
    
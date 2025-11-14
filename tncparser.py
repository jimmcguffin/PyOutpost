from PyQt6.QtCore import QObject, pyqtSignal
from persistentdata import PersistentData
from serialstream import SerialStream
from bbsparser import Jnos2Parser
from mailfolder import MailBoxHeader


class TncDevice(QObject):
    signalConnected = pyqtSignal()
    signalTimeout = pyqtSignal()
    signalDisconnected = pyqtSignal()
    signalNewIncomingMessage = pyqtSignal(MailBoxHeader,str)
    signalOutgingMessageSent = pyqtSignal() # mostly so that mainwinow can repaint mail list if it is viewing the OutTrat
    def __init__(self,pd,parent=None):
        super().__init__(parent)
        self.pd = pd
        self.messageQueue = list()
    def startSession(self,ss):
        self.serialStream = ss
        self.serialStream.signalLineRead.connect(self.onResponse)        
        self.serialStream.signalConnected.connect(self.onConnected)        
    def endSession(self):
        return

    def send(self,b):
        self.messageQueue.append(b)

# maybe this class should be called TAPR
# todo: need to implement time-out/retry stuff in both this class and bbsparser
class KantronicsKPC3Plus(TncDevice):
    def __init__(self,pd,parent=None):
        super().__init__(pd,parent)

    def startSession(self,ss):
        super().startSession(ss)
        self.serialStream.lineEnd = b"cmd:"
        mycall = f"{self.pd.getInterface("CommandMyCall")} {self.pd.getActiveCallSign()}\r"
        connectstr = f"{self.pd.getInterface("CommandConnect")} {self.pd.getBBS("ConnectName")}\r"
        # these are internally generated
        # messageQueue.append(b"\r") // flush out any half-written commands
#        self.messageQueue.append("\x03\r")
        self.messageQueue.append("\03\r")
        self.messageQueue.append("disconnect\r")
        self.messageQueue.append("echo on\r")
        self.messageQueue.append(mycall)
        self.messageQueue.append("monitor off\r")
        # these come from the dialog
        for s in self.pd.getInterface("CommandsBefore"):
            self.messageQueue.append(s+"\r")
        self.messageQueue.append(connectstr)

        # start things going
        #qDebug() << "writing" << self.messageQueue.front() << '\n'
        self.serialStream.write(self.messageQueue[0])

    def onResponse(self,r):
        # this is probably the reponse to the front element
        if not self.messageQueue: return
        query = self.messageQueue[0]
        # ignore any ctrl-c's
        if query[0] == '\03': query = query[1:]
        print(f"<<{query.replace("\r","|")}>> returned <<{r.replace("\r","|").replace("\n","|")}>>")
        if r.startswith(query):
            del self.messageQueue[0:1]
            if self.messageQueue:
                self.serialStream.write(self.messageQueue[0])
        else:
            print("spurious")

    def onConnected(self):
        print("Connected!")
        # give control over to BBS parser
        self.bbsParser = Jnos2Parser(self.pd,self)
        self.bbsParser.signalDisconnected.connect(self.onDisconnected)
        self.bbsParser.signalNewIncomingMessage.connect(self.onNewIncomingMessage)
        self.bbsParser.signalOutgingMessageSent.connect(lambda: self.onOutgoingMessageSent.emit())
        self.bbsParser.startSession(self.serialStream)

    def onNewIncomingMessage(self,mbh,m):
        self.signalNewIncomingMessage.emit(mbh,m)

    def onDisconnected(self):
        print("Disconnected!")
        self.bbsParser.signalDisconnected.disconnect()
        self.bbsParser.signalNewIncomingMessage.disconnect()
        self.serialStream.signalLineRead.connect(self.onResponse) # point this back to us
        self.serialStream.lineEnd = b"cmd:" # and reset this
        # self.signalDisconnected.emit() # todo: do final closing bits then emit this

    @staticmethod
    def getDefaultPrompts():
        return  [
			("PromptCommand","cmd:"),
			("PromptTimeout","*** retry count exceeded"),
			("PromptConnected","*** CONNECTED"),
			("PromptDisconnected","*** DISCONNECTED"),
            ]   

    @staticmethod
    def getDefaultCommands():
         return (
				("CommandMyCall","my"),
				("CommandConnect","connect"),
				("CommandRetry","retry"),
				("CommandConvers","convers"),
				("CommandDayTime","daytime"),
         )
    
    @staticmethod
    def getDefaultBeforeInitCommands():
        return [
            "INTFACE TERMINAL",
            "CD SOFTWARE",
            "NEWMODE ON",
            "8BITCONV ON",
            "BEACON EVERY 0",
            "SLOTTIME 10",
            "PERSIST 63",
            "PACLEN 128",
            "MAXFRAME 2",
            "FRACK 6",
            "RETRY 8",
            "CHECK 30",
            "TXDELAY 40",
            "XFLOW OFF",
            "SENDPAC $05",
            "CR OFF",
            "PACTIME AFTER 2",
            "CPACTIME ON",
            "STREAMEV OFF",
            "STREAMSW $00",
        ]

    @staticmethod
    def getDefaultAfterInitCommands():
        return [
            "SENDPAC $0D",
            "CR ON",
            "PACTIME AFTER 10",
            "CPACTIME OFF",
            "STREAMSW $7C"
        ]

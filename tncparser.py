from PyQt6.QtCore import QObject, pyqtSignal
from persistentdata import PersistentData
from serialstream import SerialStream
from bbsparser import Jnos2Parser

class TncDevice(QObject):
    signalConnected = pyqtSignal()
    signalTimeout = pyqtSignal()
    signalDisconnected = pyqtSignal()
    def __init__(self,pd,parent=None):
        super(TncDevice,self).__init__(parent)
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

#		int Process(const char *pstart, const char *pend); // returns # of bytes consumed, possibly OR'd with KEEP_PROCESSING
#	protected:
#		PersistentData *m_pPersistentData = nullptr;
#		QSerialPort *m_pSerialPort = nullptr;
#		std::deque<std::string> m_StuffToSend;
#	};


class KantronicsKPC3Plus(TncDevice):
    def __init__(self,pd,parent=None):
        super(KantronicsKPC3Plus,self).__init__(pd,parent)

    def startSession(self,ss):
        super().startSession(ss)
        self.serialStream.lineEnd = "cmd:"
        mycall = f"{self.pd.getInterface("CommandMyCall")} {self.pd.getActiveCallSign()}\r"
        connectstr = f"{self.pd.getInterface("CommandConnect")} {self.pd.getBBS("ConnectName")}\r"
        # these are internally generated
        # messageQueue.append(b"\r"); // flush out any half-written commands
#        self.messageQueue.append("\x03\r")
        self.messageQueue.append("\03\r")
        self.messageQueue.append("disconnect\r")
        self.messageQueue.append("beacon every 0\r")
        self.messageQueue.append("echo on\r")
        self.messageQueue.append(mycall)
        self.messageQueue.append("monitor off\r")
        # these come from the dialog
        for s in self.pd.getInterface("CommandsBefore"):
            self.messageQueue.append(s+"\r")
        self.messageQueue.append(connectstr)

        # start things going
        #qDebug() << "writing" << self.messageQueue.front() << '\n';
        self.serialStream.write(self.messageQueue[0])

    def onResponse(self,r):
        # this is probably the reponse to the front element
        if not self.messageQueue: return
        query = self.messageQueue[0]
        # ignore any ctrl-c's
        if query[0] == '\03': query = query[1:]
        print(f"<<{query.replace("\r","|")}>> returned <<{r.replace("\r","|")}>>")
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
        self.bbsParser.startSession(self.serialStream)

    def onDisconnected(self):
        print("Disconnected!")
        self.bbsParser.signalDisconnected.disconnect()
        self.serialStream.signalLineRead.connect(self.onResponse) # point this back to us
        self.serialStream.lineEnd = "cmd:" # and reset this


#     def process(self,data):
#         cmd = b"cmd:"
#         cs = b"*** CONNECTED"
#         ds = b"*** DISCONNECTED"
#         bytesconsumed = 0
#         for i in range(len(data)):
#             bytesleft = len(data)-i
# #            if i == 0 or data[i-1] == b'\r' and bytesleft >= 4:
# #            if bytesleft >= 4 and data[i] == b"c" and data[i+1] == b"m" and data[i+2] == b"d" and data[i+3] == b":":
#             if bytesleft >= len(cmd) and data[i:i+len(cmd)] == cmd:
#                     # could emit a signal here but for now I ignore responses
#                     bytesconsumed = i+4
#                     # sometimes there are spurious prompts
#                     if i == 0:  return bytesconsumed, True
#                     if self.messageQueue:
#                         response = data[0:bytesconsumed]
#                         #if response.startswith(b"cmd"):
#                         #    print("response")
#                         # this is probably the reponse to the front element
#                         #print(f"<<{self.messageQueue[0].decode().replace("\r","|")}>> returned <<{response.decode().replace("\r","|")}>>")
#                         if response.startswith(self.messageQueue[0]):
#                             del self.messageQueue[0:1]
#                             if self.messageQueue:
#                                 self.serialPort.write(self.messageQueue[0])
#                     # return bytesconsumed, True
#             elif bytesleft >= len(cs) and data[i:i+len(cs)] == cs:
#                 self.signalConnected.emit()
#                 return bytesconsumed+len(cs), True
#             elif bytesleft >= len(ds) and data[i:i+len(ds)] == ds:
#                 return bytesconsumed+len(ds), True
#         return bytesconsumed, False
              



#                     # sometimes there are spurious prompts
#                     if i == 0:  return bytesconsumed, True
#                     if self.messageQueue:
#                         response = self.sdata [0:bytesconsumed]
#                         #if response.startswith(b"cmd"):
#                         #    print("response")
#                         # this is probably the reponse to the front element
#                         #print(f"<<{self.messageQueue[0].decode().replace("\r","|")}>> returned <<{response.decode().replace("\r","|")}>>")
#                         if response.startswith(self.messageQueue[0]):
#                             del self.messageQueue[0:1]
#                             if self.messageQueue:
#                                 self.serialPort.write(self.messageQueue[0])
#                     # return bytesconsumed, True

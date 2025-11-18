# pylint:  disable="line-too-long,missing-function-docstring,multiple-statements,no-name-in-module"

from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from persistentdata import PersistentData
from serialstream import SerialStream
from bbsparser import Jnos2Parser
from mailfolder import MailBoxHeader
#from globalsignals import GlobalSignals

class TncDevice(QObject):
    signalConnected = pyqtSignal()
    signalTimeout = pyqtSignal()
    signalDisconnected = pyqtSignal()
    signalNewIncomingMessage = pyqtSignal(MailBoxHeader,str)
    signalOutgingMessageSent = pyqtSignal() # mostly so that mainwinow can repaint mail list if it is viewing the OutTray
    signal_status_bar_message = pyqtSignal(str) # send "" to revert to default status bar
    def __init__(self,pd,parent=None):
        super().__init__(parent)
        self.pd = pd
        self.messageQueue = list()
        self.using_echo = False
        self.bbs_parser = None
        self.special_disconnect_value = "*** Disconnect\r" # tells the session to end
    def startSession(self,ss):
        self.serialStream = ss
        self.serialStream.signalLineRead.connect(self.onResponse)        
        self.serialStream.signalConnected.connect(self.onConnected)        
        self.serialStream.signalDisconnected.connect(self.onDisconnected)
        self.signal_status_bar_message.emit("Initializing TNC")
    def endSession(self):
        self.messageQueue.clear()
        self.signal_status_bar_message.emit("")
        self.signalDisconnected.emit()
        return

    def send(self,b):
        self.messageQueue.append(b)
        if len(self.messageQueue) == 1:
            if self.messageQueue[0] == self.special_disconnect_value:
                self.endSession()
            else:
                self.serialStream.write(self.messageQueue[0])

    @staticmethod
    def starts_with_ignore_case(str1, str2): # if str1 starts with str2
        l = len(str2)
        str1 = str1[0:l].upper()
        str2 = str2.upper()
        return str1 == str2

    @staticmethod
    def matches_ignore_case(str1, str2): # if str2 is a prefix of str1
        l = len(str2)
        str1 = str1[0:l].upper()
        str2 = str2.upper()
        return str1 == str2
# when I write some tests: mactches_ignore_case("disconnect","d") should return True
#                          mactches_ignore_case("disconnect","dis") should return True
#                          mactches_ignore_case("disconnect","disp") should return False


# maybe this class should be called TAPR
# todo: need to implement time-out/retry stuff in both this class and bbsparser
class KantronicsKPC3Plus(TncDevice):
    def __init__(self,pd,parent=None):
        super().__init__(pd,parent)

    def startSession(self,ss):
        super().startSession(ss)
        self.serialStream.line_end = b"cmd:"
        self.serialStream.include_line_end_in_reply = self.using_echo
        mycall = f"{self.get_command("CommandMyCall")} {self.pd.getActiveCallSign()}\r"
        connectstr = f"{self.get_command("CommandConnect")} {self.pd.getBBS("ConnectName")}\r"
        # these are internally generated
        # self.send(b"\r") // flush out any half-written commands
        self.send("\x03\r")
        self.send("disconnect\r")
        if self.using_echo:
            self.send("echo on\r")
        else:
            self.send("echo off\r")
        self.send(mycall)
        self.send("monitor off\r")
        # these come from the dialog
        if self.pd.getInterfaceBool("AlwaysSendInitCommands"):
            for s in self.pd.getInterface("CommandsBefore"):
                s = s.strip()
                if s:
                    self.send(s+"\r")
        self.send(connectstr)

        # start things going
        #qDebug() << "writing" << self.messageQueue.front() << '\n'
        # self.serialStream.write(self.messageQueue[0])

    def is_valid_query_response(self,q,r):
        if self.using_echo: # is much simpler in this case
            # ignore any ctrl-c's
            if q[0] == '\x03': q = q[1:]
            print(f"TNC: <<{q.replace("\r","|")}>> returned <<{r.replace("\r","|").replace("\n","|")}>>")
            return r.startswith(q)
        else:
            q = q.rstrip()
            r = r.rstrip()
            # any response to a ctrl-c is fine
            if q and q[0] == '\x03':
                return True
            print(f"TNC: <<{q.replace("\r","|")}>> returned <<{r.replace("\r","|").replace("\n","|")}>>")
            # pick off the first word of each item
            q1,_,_ = q.partition(" ")
            r1,_,_ = r.partition(" ")
            if self.matches_ignore_case(r1,q1):
                return True
            # there are some things that don't match well
            elif self.matches_ignore_case("disconnect",q1):
                if not r or "DISCONNECT" in r: # r is the entire response, not just the first word
                    return True
            elif self.matches_ignore_case("mycall",q1):
                if not r or r == "Not while connected": # for some reason, there is no reply tp mycall, unless you are already cinnected
                    return True
            elif self.matches_ignore_case("connect",q1) and not r: # connect has no immediate response
                return True
            return False

    def onResponse(self,r):
        # this is probably the reponse to the front element
        if not self.messageQueue: return
        # # handle confused responses first
        # if "\r\nEH?" in r:
        #     print("TNC: EH resposne, resending")
        #     self.serialStream.write(self.messageQueue[0]) # resend the last command?
        #     return
        if self.is_valid_query_response(self.messageQueue[0],r):
            del self.messageQueue[0:1]
            if self.messageQueue:
                if self.messageQueue[0] == self.special_disconnect_value:
                    self.endSession()
                else:
                    self.serialStream.write(self.messageQueue[0])
        else:
            print("spurious")
            # maybe try sending again?
            # self.serialStream.write(self.messageQueue[0]) this did NOT work

    def onConnected(self):
        print("Connected!")
        # give control over to BBS parser
        self.bbs_parser = Jnos2Parser(self.pd,self.using_echo,self)
        self.bbs_parser.signalDisconnected.connect(self.onDisconnected)
        self.bbs_parser.signalNewIncomingMessage.connect(self.onNewIncomingMessage)
        self.bbs_parser.signalOutgingMessageSent.connect(lambda: self.onOutgoingMessageSent.emit())
        self.bbs_parser.signal_status_bar_message.connect(lambda s: self.signal_status_bar_message.emit(s))
        self.bbs_parser.start_session(self.serialStream)

    def onNewIncomingMessage(self,mbh,m):
        self.signalNewIncomingMessage.emit(mbh,m)

    def onDisconnected(self):
        # if we never actually connected, there will not be a bbs_parser
        if not self.bbs_parser:
            return # this happens at startup sometimes - the TNC was holding on to it from a previous session
        print("TNC got disconnected!")
        self.signal_status_bar_message.emit("Resetting TNC")
        self.bbs_parser.signalDisconnected.disconnect()
        self.bbs_parser.signalNewIncomingMessage.disconnect()
        self.bbs_parser = None
        self.serialStream.signalLineRead.connect(self.onResponse) # point this back to us
        self.serialStream.line_end = b"cmd:" # and reset this
        self.serialStream.include_line_end_in_reply = self.using_echo # and this
        if self.pd.getInterfaceBool("AlwaysSendInitCommands"):
            for s in self.pd.getInterface("CommandsAfter"):
                s = s.strip()
                if s:
                    self.send(s+"\r")
        self.send(self.special_disconnect_value)

    @staticmethod
    def getDefaultPrompts():
        return  [
			("PromptCommand","cmd:"),
			("PromptTimeout","*** retry count exceeded"),
			("PromptConnected","*** CONNECTED"),
			("PromptDisconnected","*** DISCONNECTED"),
            ]   

    def get_command(self,s):
        c = self.pd.getInterface(s)
        if c:
            return c
        if s in self.get_default_commands():
            return self.get_default_commands()[s]
        return "<"+s+">" # this will never work but it will show in the log as a problem

    @staticmethod
    def getDefaultCommands():
         return {
				"CommandMyCall":"my",
				"CommandConnect":"connect",
				"CommandRetry":"retry",
				"CommandConvers":"convers",
				"CommandDayTime":"daytime",
         }
    
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

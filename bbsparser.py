# pylint:  disable="line-too-long,missing-function-docstring,multiple-statements,no-name-in-module"

from PyQt6.QtCore import QObject, pyqtSignal
from mailfolder import MailFolder, MailBoxHeader, MailFlags

# the general sequence is:
# sent the startup commands
# send any outgoing messages
# get any incoming mail
# kill any messages read
# send delivery confirmations for messages read
# send the shutdown commands
# emit signalDisconnected to end session
# any of these steps can be skipped via various settings


# there is a list of these in the parser
# they are executed one at a time
# if there is a "what_to_send"", it is sent
# then it waits until a response is received, which must match what was sent (due to echo mode)
# then it calls "handler"
class BbsSequenceStep():
    def __init__(self,s,h=None,data=None):
        self.what_to_send = s # can be blank
        self.handler = h # gets called when responded to, can be None
        # arbitrary data item that can be passed to the handler (after the reply value)
        self.data = data
class BbsSequenceImmediateStep():
    def __init__(self,h,data=None):
        self.handler = h # gets called as soon as the sequencer gets to this item
        # arbitrary data item that can be passed to the handler (as the only value)
        self.data = data


# at any given time, "bbsSequence" is a mix of BbsSequenceSteps and BbsSequenceImmediateSteps, but the first entry as always a BbsSequenceStep that has
# already sent its what_to_send value and is awaiting the reply. There are two times this this is briefly not true:
# 1 - the sequence is empty and a new bbsSequence has just been pushed
# 2 - the front step has just been removed. Now the check_sequence should consume all BbsSequenceImmediateSteps until it gets to a BbsSequenceStep and then
# send the new what_to_send so that it is "normalled-up"
class BbsParser(QObject):
    signalTimeout = pyqtSignal()
    signalDisconnected = pyqtSignal()
    signalNewIncomingMessage = pyqtSignal(MailBoxHeader,str)
    signalOutgingMessageSent= pyqtSignal()
    signal_status_bar_message = pyqtSignal(str)
    def __init__(self,pd,using_echo,parent=None):
        super().__init__(parent)
        self.pd = pd
        self.bbs_sequence = [] # a list of BbsSequenceSteps
        self.stepinprogress = False
        self.items_sent = [] # they get moved to the "Sent" folder
        self.messages_read = []
        self.serial_stream = None # later will be set to a SerialStream
        self.using_echo = using_echo

    def start_session(self,ss):
        self.serial_stream = ss
        self.serial_stream.line_end = b") >\r\n" # this matches what the original outpost uses
        self.serial_stream.include_line_end_in_reply = True
        self.serial_stream.signalLineRead.disconnect()
        self.serial_stream.signalLineRead.connect(self.on_response)
        self.serial_stream.signalDisconnected.connect(self.on_disconnected)
        self.signal_status_bar_message.emit("Initializing the BBS")

    def end_session(self):
        print("BBS emitting disconnect")
        self.signalDisconnected.emit()

    def add_step(self,step): # argument is a BbsSequenceStep or a BbsSequenceImmediateStep
        # things are different if the sequence is empty
        if self.bbs_sequence:
            self.bbs_sequence.append(step) # it is not empty, just add it
        else:
            if isinstance(step,BbsSequenceImmediateStep):
                step.handler(step.data)
            else:
                self.bbs_sequence.append(step)
                if self.bbs_sequence[0].what_to_send:
                    self.serial_stream.write(self.bbs_sequence[0].what_to_send)
        # self.bbs_sequence.append(step)
        # self.check_sequence()

    # call this when items have been removed and there is a new "front"
    def check_sequence(self):
        # if there are immediate-mode comamnds, do them
        while self.bbs_sequence and isinstance(self.bbs_sequence[0],BbsSequenceImmediateStep):
            if self.bbs_sequence[0].handler: # I think this will always be true
                self.bbs_sequence[0].handler(self.bbs_sequence[0].data)
            del self.bbs_sequence[0:1]
        if len(self.bbs_sequence) > 0:
            assert isinstance(self.bbs_sequence[0],BbsSequenceStep)
            if self.bbs_sequence[0].what_to_send:
                self.serial_stream.write(self.bbs_sequence[0].what_to_send)

    def on_disconnected(self):
        print("BBS got disconnected")
        self.end_session()

class Jnos2Parser(BbsParser):
    def __init__(self,pd,using_echo,parent=None):
        super().__init__(pd,using_echo,parent)
        self.mailfolder = MailFolder()
        self.current_area = ""
    def start_session(self,ss):
        super().start_session(ss)
        self.add_step(BbsSequenceStep("",self.start_session2)) # there is a prompt/terminator that will arrive without being told

    def start_session2(self,r,_=None):
        # if the initial prompt is long, change it to short
        if r.find("A,B,C,") >= 0:
            self.add_step(BbsSequenceStep("x\r")) # this toggles long/short prompt
        #self.add_step(BbsSequenceStep("xa\r"))
        if self.pd.getBBSBool("AlwaysSendInitCommands"):
            # these come from the dialog
            for s in self.pd.getBBS("CommandsBefore"):
                s = s.strip()
                if s:
                    self.add_step(BbsSequenceStep(s+"\r"))
        self.add_step(BbsSequenceImmediateStep(self.send_outgoing))

    def send_outgoing(self,_=None):
        # if there are outgoing messages send them now
        # this may turn out to be a bad idea but for now I read directly from the mail file
        self.mailfolder.load()
        headers = self.mailfolder.get_headers(MailFlags.FOLDER_OUT_TRAY)
        if headers:
            self.signal_status_bar_message.emit("Sending out messages")
            for i in range(len(headers)):
                mbh,m = self.mailfolder.get_message(i)
                m2 = m.replace("\r\n","\r").replace("\n","\r") # make sure there are no linefeeds
                if not m2.endswith('\r'): m2 += '\r'
                self.add_step(BbsSequenceStep(f"{self.get_command("CommandSend")} {mbh.to_addr}\r{mbh.subject}\r{m2}/EX\r",self.handle_sent,i))
        self.add_step(BbsSequenceImmediateStep(self.send_lists))

    def send_lists(self,_=None):
        self.signal_status_bar_message.emit("Reading messages")
        self.add_step(BbsSequenceStep("la\r",self.handle_list))
        #	self.add_step(BbsSequenceStep("a XSCPERM\r",self.handle_area))
        #	self.add_step(BbsSequenceStep("la\r",self.handle_list))
        #	self.add_step(BbsSequenceStep("a XSCEVENT\r",self.handle_area))
        #	self.add+step(BbsSequenceStep("la\r",self.handle_list))
        #	self.add_step(BbsSequenceStep("a ALLXSC\r",self.handle_area))
        #	self.add_step(BbsSequenceStep("la\r",self.handle_list))

    def on_response(self,r):
        if not self.bbs_sequence:
            return # nothing expected
        # this is probably/hopefully the response to the front element
        query = self.bbs_sequence[0].what_to_send
        # todo: code here used to match reply to query but not it appears to be gone
        # should match up to first \n
        qbase = query.partition("\r")[0]
        print(f"bbs: <<{query.replace("\r","|").replace("\n","|")}>> returned <<{r.replace("\r","|").replace("\n","|")}>>")
        # when there is no echo, commands here never match up
        if self.using_echo:
            if r.startswith(qbase):
                print("Matches")
            else:
                print("Doesn't match")
        if self.bbs_sequence[0].handler:
            self.bbs_sequence[0].handler(r,self.bbs_sequence[0].data)
        del self.bbs_sequence[0:1]
        self.check_sequence()

    def handle_list(self,r,_=None):
        # if we get here, it means that all of the outgoing messages have been sent
        if self.items_sent:
            self.mailfolder.move_mail(self.items_sent,MailFlags.FOLDER_SENT)
            self.items_sent.clear()
        print(f"got list {r}")
        # sample "la\r\nMail area: kw6w\r\n1 message  -  1 new\r\n\St.  #  TO            FROM     DATE   SIZE SUBJECT\r\n> N   1 kw6w@w1xsc.sc pkttue   Oct 15  747 DELIVERED: W6W-303P_P_ICS213_Shutti\r\nArea: kw6w Current msg# 1.\r\n" +terminator
        # or "la\r\nMail area: xscperm\r\n4 messages  -  4 new\r\nSt.  #  TO            FROM     DATE   SIZE SUBJECT\r\n> N   1 xscperm       xsceoc   Nov 27 5962 SCCo XSC Tactical Calls v191127    \r\n  N   2 xscperm       xsceoc   Sep  5 1932 SCCo Packet Frequencies v200905    \r\n  N   3 xscperm       xsceoc   Aug 13 2768 SCCo Packet Subject Line v220803   \r\n  N   4 xscperm       xsceoc   Aug  9 4326 SCCo Packet Tactical Calls v2024080\r\nArea: xscperm Current msg# 1.\r\n?,A,B,C,CONV,D,E,F,H,I,IH,IP,J,K,L,M,N,NR,O,P,PI,R,S,T,U,V,W,X,Z " >>
        lines = r.splitlines()
        if len(lines) >= 2:
            #asume no echo
            area_line = 0
            message_counts_line = 1
            first_message_line = 4
            if self.using_echo:
                area_line += 1
                message_counts_line += 1
                first_message_line += 1
            words = lines[area_line].split()
            if len(words) >= 2 and words[0] == "Area:":
                self.current_area = words[1]
            elif len(words) >= 3 and words[0] == "Mail" and words[1] == "area:":
                self.current_area = words[2]
            # # line "message_counts_line" will have the counts
            # nmessages = 0
            # m = re.match(r"(\d+) message",lines[message_counts_line])
            # if m: nmessages = int(m.groups()[0])
            # for i  in range(nmessages):
            #     tmp = f"r {i+1}\r"
            #     self.add_step(BbsSequenceStep(tmp,self.handleRead,i))

            # the code above assumes that all messages are consecutively numbered 1-n, which it turns out is not necessarily true
            # let's ignore the message count and just count the lines as we find them
            # line 3 is blank, 4 has the column headers
            for l in lines[first_message_line:]:
                # the first char might be a ">" which indicates the current message, we dont care about that, and then a space
                words = l[2:].split(None,7) # the date will span multiple words
                # word[0] is the message number
                # word[1] is the to_addr
                # word[2] is the from_adddr
                # word[3] is the month
                # word[4] is the day
                # word[5] is the size
                # everything after this is the subject
                if len(words) >= 2 and words[0] in ("Y","N") and words[1].isdigit():
                    # todo: we might consider checking if we already have this message, but it might be hard when there is
                    # only a partial subject and weird date formats, so for now read (and later kill) all of them
                    if len(words) >= 8:
                        self.mailfolder.load()
                        maybematch = self.mailfolder.is_possibly_a_duplicate(words[2],words[3],words[7].rstrip())
                        print(f"matcher says {maybematch},{words[7].rstrip()}")
                        if maybematch:
                            continue
                    mn = int(words[1])
                    tmp = f"{self.get_command("CommandRead")} {mn}\r"
                    self.add_step(BbsSequenceStep(tmp,self.handle_read,mn))
        # there are now 0 or more read commands in the list
        # issue the command that will kill them after they are read
        self.add_step(BbsSequenceImmediateStep(self.kill_read_messages))

    def kill_read_messages(self,_=None):
        # only kill read messages on own area
        callsign = self.pd.getActiveCallSign(False)
        if self.current_area == callsign:
            if self.messages_read:
                k = self.get_command("CommandDelete")
                for m in self.messages_read:
                    k += " "
                    k += str(m)
                k += "\r"
                self.add_step(BbsSequenceStep(k))
            self.messages_read.clear()
        if self.current_area != "xscperm":
            self.add_step(BbsSequenceStep("a XSCPERM\r",self.handle_area))
            self.add_step(BbsSequenceStep("la\r",self.handle_list))
        else:
            self.add_step(BbsSequenceImmediateStep(self.send_after_commands))

    def send_after_commands(self,_=None):
        if self.pd.getBBSBool("AlwaysSendInitCommands"):
            # these come from the dialog
            for s in self.pd.getBBS("CommandsAfter"):
                s = s.strip()
                if s:
                    self.add_step(BbsSequenceStep(s+"\r"))
        #if running in tactical mode, send real id
        callsign = self.pd.getActiveCallSign(True)
        if " as " in callsign:
            self.add_step(BbsSequenceStep(f"# this is {callsign}\r"))
        self.add_step(BbsSequenceStep(self.get_command("CommandBye")+"\r")) # this will trigger the *** disconnect message

    def handle_area(self,r,_=None):
        print(f"got area {r}")
        pass

    def handle_read(self,r,data):
        print(f"got read {r}")
        firstchar = "r" if self.using_echo else "M"
        if r.startswith(firstchar):
            self.messages_read.append(data)
        lines = r.splitlines()
        if lines and lines[-1] == "": lines.pop()
        # discard up until last blank line
        while len(lines) >= 2 and lines[-1] != "": lines.pop()
        mbh = MailBoxHeader()
        inheader = True
        messagebody = ""
        for line in lines[1:]:
            if line == "" and inheader: # the blank line that separates header from body
                inheader = False
            elif inheader:
                l,_,r = line.partition(':')
                l = l.strip()
                r = r.strip()
                if l == "Date":
                    mbh.date_sent = MailBoxHeader.normalized_date(r)
                elif l == "From":
                    mbh.from_addr = r
                elif l == "To":
                    mbh.to_addr = r
                elif l == "Subject":
                    mbh.subject = r
            else:
                # if this is the first line of the message body, look for the !URG! tag
                if not messagebody:
                    if line.startswith("!URG!"):
                        mbh.flags |= MailFlags.IS_URGENT.value
                        line = line[5:] # remove the !URG!, maybe remove others as well "!*!"
                # messagebody += line + "\r\n"
                messagebody += line + "\n"
        if not messagebody: return
        mbh.flags |= MailFlags.IS_NEW.value | MailFlags.FOLDER_IN_TRAY.value
        mbh.bbs = self.pd.getBBS("ConnectName")
        mbh.date_received = MailBoxHeader.normalized_date()
        mbh.size = len(messagebody)
        self.signalNewIncomingMessage.emit(mbh,messagebody)

    def handle_sent(self,r,i):
        self.items_sent.append(i)

    def get_command(self,s):
        c = self.pd.getBBS(s)
        if c:
            return c
        if s in self.get_default_commands():
            return self.get_default_commands()[s]
        return "<"+s+">" # this will never work but it will show in the log as a problem

    @staticmethod
    def get_default_commands():
        return {
				"CommandBye":"B",
				"CommandDelete":"K",
				"CommandListBulletin":"LB",
				"CommandListFiltered":"L>",
				"CommandListNts":"LT",
				"CommandRead":"R",
				"CommandSend":"SP",
				"CommandSendBulletin":"SB",
				"CommandSendNts":"ST",
         }

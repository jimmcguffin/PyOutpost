# pylint:  disable="line-too-long,missing-function-docstring,multiple-statements,no-name-in-module"

import datetime
from PyQt6.QtCore import QObject, pyqtSignal
from my_mailbox import MailBox, MailBoxHeader, MailFlags
from globalsignals import global_signals

# the general sequence is:
# send the startup commands
# send any outgoing messages
# get any incoming mail
# kill any messages read
# send delivery confirmations for messages read
# send the shutdown commands
# emit signalDisconnected to end session
# any of these steps can be skipped via various settings


# there is a list of these in the parser
# first, the "what_to_send" (if any) is sent over the serial port
# then, when the response comes back, the handler is called with the reponse
class BbsSequenceStep():
    def __init__(self,s,h=None,data=None):
        self.what_to_send = s # can be blank
        self.handler = h # gets called when responded to, can be None
        # arbitrary data item that can be passed to the handler (after the reply value)
        self.data = data

class BbsSequenceStepNoResonse(): # I think only "BYE" uses this
    def __init__(self,s):
        self.what_to_send = s

# when this gets to the front, waits until all responses have been recieved, then it calls the handler
class BbsSequenceSync():
    def __init__(self,h=None,data=None):
        self.handler = h # gets called as soon as the sequencer gets to this item
        # arbitrary data item that can be passed to the handler (as the only value)
        self.data = data

# at any given time, "bbs_sequence" is a mix of BbsSequenceSteps, but the first entry will always be a BbsSequenceSync
# once a BbsSequenceStep gets to the front, it's contents will be send and then the BbsSequenceStep object will be moved to the bbs_pending list
# note that all BbsSequence items except BbsSequenceSync are asyncronous - they immediately return, often before the messsage has been sent to
# the serial port
class BbsParser(QObject):
    signalTimeout = pyqtSignal()
    signalDisconnected = pyqtSignal()
    signalOutgingMessageSent= pyqtSignal()
    signal_status_bar_message = pyqtSignal(str)
    def __init__(self,pd,using_echo,parent=None):
        super().__init__(parent)
        self.pd = pd
        self.bbs_sequence = [] # a list of BbsSequenceSteps (and similar)
        self.bbs_pending = [] # a list of BbsSequenceSteps that are awaiting a response
        self.messages_to_be_killed = []
        self.messages_to_be_acknowledged = []
        self.serial_stream = None # later will be set to a SerialStream
        self.using_echo = using_echo
        self.srflags = 0

    def start_session(self,ss,srflags:int):
        self.serial_stream = ss
        self.srflags = srflags
        self.serial_stream.line_end = b") >\r\n" # this matches what the original outpost uses, does now wotk if TNC is set for long prompts ("Z >\r\n" would be work)
        self.serial_stream.include_line_end_in_reply = True
        self.serial_stream.signalLineRead.disconnect()
        self.serial_stream.signalLineRead.connect(self.on_response)
        self.serial_stream.signalDisconnected.connect(self.on_disconnected)
        self.signal_status_bar_message.emit("Initializing the BBS")

    def end_session(self):
        self.bbs_sequence.clear() # forget any unfinished business
        self.bbs_pending.clear()
        print("BBS emitting disconnect")
        self.signalDisconnected.emit()

    def add_step(self,step): # argument is a BbsSequenceStep, a BbsSequenceStepNoResonse, or a BbsSequenceSync
        assert(isinstance(step,(BbsSequenceStep,BbsSequenceStepNoResonse,BbsSequenceSync)))
        self.bbs_sequence.append(step) # just add it to the end
        # now check the front (which might be the thing we just pushed)
        self.check_sequence()

    # adds to the front of the list, this happens when new steps are needed in response to commands, eg when we get a "la", when then insert the read commands
    def push_step(self,step): # argument is a BbsSequenceStep, a BbsSequenceStepNoResonse, or a BbsSequenceSync
        assert(isinstance(step,(BbsSequenceStep,BbsSequenceStepNoResonse,BbsSequenceSync)))
        self.bbs_sequence.insert(0,step)
        # now check the front (which might be the thing we just pushed)
        self.check_sequence()

    # call this when items have been add or removed or when bbs_pending has been changed
    def check_sequence(self):
        while self.bbs_sequence:
            step = self.bbs_sequence[0]
            if isinstance(step,BbsSequenceStep):
                del self.bbs_sequence[0:1]
                self.bbs_pending.append(step)
                if step.what_to_send:
                    self.serial_stream.write(step.what_to_send)
            elif isinstance(step,BbsSequenceStepNoResonse):
                del self.bbs_sequence[0:1]
                if step.what_to_send:
                    self.serial_stream.write(step.what_to_send)
            elif isinstance(step,BbsSequenceSync):
                if self.bbs_pending:
                    return # will get stuck here until all pendings are handled
                del self.bbs_sequence[0:1]
                if step.handler: # I think this will always be true
                    step.handler(step.data)

    def on_disconnected(self):
        print("BBS got disconnected")
        self.end_session()

class Jnos2Parser(BbsParser):
    def __init__(self,pd,using_echo,parent=None):
        super().__init__(pd,using_echo,parent)
        self.home_area = self.pd.getActiveCallSign(False).upper()
        self.current_area = ""
        self.areas_to_read = []
    def start_session(self,ss,srflags):
        super().start_session(ss,srflags)
        self.add_step(BbsSequenceStep("",self.start_session2)) # there is a prompt/terminator that will arrive without being told

    def start_session2(self,r,_=None):
        # if the initial prompt is the long type, change it to short
        if r.find("A,B,C,") >= 0:
            self.add_step(BbsSequenceStep("x\r")) # this toggles long/short prompt
        if not r.find("Area:"):
            self.add_step(BbsSequenceStep("xa\r")) # this toggles the area display
        # set up the basic steps, remember that some of these will have additional steps inserted in front of them
        self.add_step(BbsSequenceSync(self.send_before_commands))
        self.add_step(BbsSequenceSync())
        if self.srflags & 1: # send
            self.add_step(BbsSequenceSync(self.send_outgoing))
        if self.srflags & 2: # recv
            self.add_step(BbsSequenceStep("la\r",self.handle_list)) # reads the "home" list, will insert new read and kill messages
            self.add_step(BbsSequenceSync(self.kill_read_messages))
            self.add_step(BbsSequenceSync(self.send_confirmations))
            if self.srflags & 4: # recv bulletins
                self.add_step(BbsSequenceStep("a XSCPERM\r"))
                self.add_step(BbsSequenceStep("la\r",self.handle_list))
                self.add_step(BbsSequenceSync())
                self.add_step(BbsSequenceStep("a XSCEVENT\r"))
                self.add_step(BbsSequenceStep("la\r",self.handle_list))
                self.add_step(BbsSequenceSync())
                # not until L> works  ("ALLXSC")
        self.add_step(BbsSequenceSync(self.send_after_commands))

    def send_outgoing(self,_=None):
        # if there are outgoing messages send them now
        # this may turn out to be a bad idea but for now I read directly from the mail file
        mailbox = MailBox()
        mailbox.load()
        indexes = mailbox.get_header_indexes(MailFlags.FOLDER_OUT_TRAY)
        if indexes:
            self.signal_status_bar_message.emit("Sending out messages")
            for index in indexes:
                mbh,m = mailbox.get_message(index)
                m2 = m.replace("\r\n","\r").replace("\n","\r") # make sure there are no linefeeds
                if not m2.endswith('\r'): m2 += '\r'
                self.push_step(BbsSequenceStep(f"{self.get_command("CommandSend")} {mbh.to_addr}\r{mbh.subject}\r{m2}/EX\r",self.handle_sent,index))

    # def send_lists(self,_=None):
    #     if self.srflags & 2:
    #         self.signal_status_bar_message.emit("Reading messages")
    #         self.add_step(BbsSequenceStep("la\r",self.handle_list))
    #     else:
    #         # this must be a send-only cycle, so skip list/read/confirm steps


    def on_response(self,r):
        if not self.bbs_pending:
            return # nothing expected
        # this is probably/hopefully the response to the front element
        query = self.bbs_pending[0].what_to_send
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
        step = self.bbs_pending.pop(0)
        if step.handler:
            step.handler(r,step.data)
        self.check_sequence()

    def handle_list(self,r,_=None):
        # if we get here, it means that all of the outgoing messages have been sent
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
                self.current_area = words[1].upper()
            elif len(words) >= 3 and words[0] == "Mail" and words[1] == "area:":
                self.current_area = words[2].upper()
            # line 2 is blank, 3 has the column headers
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
                    # matching works ok for bulletins but not so good for the regular mail area
                    callsign = self.pd.getActiveCallSign(False).upper()
                    if self.current_area != callsign:
                        if len(words) >= 8:
                            mailbox = MailBox()
                            mailbox.load()
                            maybematch = mailbox.is_possibly_a_duplicate(words[2],words[3],words[7].rstrip())
                            print(f"matcher says {maybematch},{words[7].rstrip()}")
                            if maybematch:
                                continue
                    mn = int(words[1])
                    tmp = f"{self.get_command("CommandRead")} {mn}\r"
                    self.push_step(BbsSequenceStep(tmp,self.handle_read,mn))
                    self.push_step(BbsSequenceSync()) # wait until done

    def kill_read_messages(self,_=None):
        # only kill read messages on own area
        callsign = self.pd.getActiveCallSign(False).upper()
        if self.current_area == callsign:
            if self.messages_to_be_killed:
                k = self.get_command("CommandDelete")
                for m in self.messages_to_be_killed:
                    k += " "
                    k += str(m)
                k += "\r"
                self.add_step(BbsSequenceStep(k))
        self.messages_to_be_killed.clear()

    def send_confirmations(self,_=None):
        self.signal_status_bar_message.emit("Sending delivery confirmations")
        d = datetime.datetime.now()
        date = "{:%m/%d/%Y}".format(d)
        time = "{:%H:%M}".format(d)
        for mbh in self.messages_to_be_acknowledged:
            subject = f"DELIVERED: {mbh.subject}"
            b1 = f"!LMI!{mbh.local_id}!DR!{date} {time}\n"
            b2 = f"Your Message\nTo: {mbh.from_addr}\n"
            b3 = f"Subject: {mbh.subject}\n"
            b4 = f"was delivered on {date} {time}\r"
            b5 = f"Recipient's Local Message ID: {mbh.local_id}\r"
            rmessagebody = f"{b1}{b2}{b3}{b4}{b5}"
            self.push_step(BbsSequenceStep(f"{self.get_command("CommandSend")} {mbh.from_addr}\r{subject}\r{rmessagebody}/EX\r"))
            #global_signals.signal_new_outgoing_text_message.emit(mbh,rmessagebody)

    def send_before_commands(self,_=None):
        if self.pd.getBBSBool("AlwaysSendInitCommands"):
            # these come from the dialog
            for s in self.pd.getBBS("CommandsBefore"):
                s = s.strip()
                if s:
                    self.add_step(BbsSequenceStep(s+"\r"))
            self.add_step(BbsSequenceSync())

    def send_after_commands(self,_=None):
        if self.pd.getBBSBool("AlwaysSendInitCommands"):
            # these come from the dialog
            for s in self.pd.getBBS("CommandsAfter"):
                s = s.strip()
                if s:
                    self.add_step(BbsSequenceStep(s+"\r"))
            self.add_step(BbsSequenceSync())
        #if running in tactical mode, send real id
        callsign = self.pd.getActiveCallSign(True)
        if " as " in callsign:
            self.add_step(BbsSequenceStep(f"# this is {callsign}\r"))
            self.add_step(BbsSequenceSync())
        self.add_step(BbsSequenceStepNoResonse(self.get_command("CommandBye")+"\r")) # this will trigger the *** disconnect message

    def handle_read(self,r,data):
        print(f"got read {r}")
        firstchar = "r" if self.using_echo else "M"
        in_home_area = self.current_area == self.home_area
        if r.startswith(firstchar) and in_home_area:
            self.messages_to_be_killed.append(data)
        lines = r.splitlines()
        if lines and lines[-1] == "": lines.pop()
        # discard up until last blank line
        while len(lines) >= 2 and lines[-1] != "": lines.pop()
        mbh = MailBoxHeader()
        inheader = True
        isfirst = True
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
                if isfirst:
                    if line.startswith("!URG!"):
                        mbh.flags |= MailFlags.IS_URGENT.value
                        line = line[5:] # remove the !URG!, maybe remove others as well "!*!"
                    isfirst = False
                messagebody += line + "\n"
        if not messagebody: return
        mbh.flags |= MailFlags.IS_NEW.value | MailFlags.FOLDER_IN_TRAY.value
        if in_home_area and not mbh.subject.startswith("DELIVERED:"):
            if self.pd.getProfileBool("MessageSettings/AddMessageNumberToInbound"):
                mbh.local_id = self.pd.make_standard_local_id()
        mbh.bbs = self.pd.getBBS("ConnectName")
        mbh.date_received = MailBoxHeader.normalized_date()
        mbh.size = len(messagebody)
        global_signals.signal_new_incoming_message.emit(mbh,messagebody)
        # decide if we want to send a delivery confirmation
        # this code is cut/pasted from newpacketmessage
        if in_home_area and not mbh.subject.startswith("DELIVERED:"):
            self.messages_to_be_acknowledged.append(mbh)

    def handle_sent(self,r,i):
        global_signals.signal_message_sent.emit(i)

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

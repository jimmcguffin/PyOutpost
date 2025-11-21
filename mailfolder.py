import datetime
import os
from urllib.parse import quote_plus,unquote_plus
from enum import Enum

# headers (items in same order as display)
# */flagbits/From/To/BBS/LocalId/Subject/DateSent/DateReceived/Size

# the flags are held in a 24 bit number
# the low 11 bits are the folders that the mail is currently in
# 1 bit unused (maybe a 12th folder)
# then the "type" as 2 bits
# bit 22 is the urgent flag
# the high bit (23) is New(Unread)

class MailFlags(Enum):
    FOLDER_IN_TRAY = 1<<0
    FOLDER_OUT_TRAY = 1<<1
    FOLDER_SENT = 1<<2
    FOLDER_ARCHIVE = 1<<3
    FOLDER_DRAFT = 1<<4
    FOLDER_DELETED = 1<<5 # currently, the next time the app ends, these are removed unless there are copies in other folders
    FOLDER_1 = 1<<6
    FOLDER_2 = 1<<7
    FOLDER_3 = 1<<8
    FOLDER_4 = 1<<9
    FOLDER_5 = 1<<10
    FOLDER_X = 1<<11 # the next time the app ends, these are removed
    FOLDER_BITS = 0xfff # all above bits
    TYPE_BIT_0 = 1<<12 # these are used to make a 2-bit field, see code
    TYPE_BIT_1 = 1<<13
    # 2 exta bits here, maybe allow more types
    IS_OUTGOING = 1<<16 # this means it was originally a message created and sent by this program
    # 5 exta bits here
    IS_URGENT = 1<<22
    IS_NEW = 1<<23

class MailBoxHeader:
    def __init__(self,s="",oh=0,om=0):
        self.index = 0
        self.flags = 0 # bit encoded, includes New/unread and folder bit mask
        self.from_addr = ""
        self.to_addr = ""
        self.bbs = ""
        self.local_id = ""
        self.subject = ""
        self.date_sent = "" # in ISO-8601 format
        self.date_received = "" # in ISO-8601 format
        self.size = 0 # size of the actual mail that follows
        self.offset_to_header = 0 # offset in file to start of this header
        self.offset_to_message_body = 0 # offset in file to start of the message body
        s = s.rstrip()
        if s and len(s) > 2 and s[0:2] == "*/":
            tmp = s.split("/")
            if len(tmp) >= 10:
                for index in range(2,7):
                    tmp[index]= unquote_plus(tmp[index])
                self.flags = int(tmp[1],16)
                self.from_addr = tmp[2]
                self.to_addr = tmp[3]
                self.bbs = tmp[4]
                self.local_id = tmp[5]
                self.subject = tmp[6]
                self.date_sent = tmp[7]
                self.date_received = tmp[8]
                self.size = int(tmp[9])
                self.offset_to_header = oh
                self.offset_to_message_body = om
            else:
                pass
        else:
            pass

    def __eq__(self, other):
        if isinstance(other, MailBoxHeader):
            return self.from_addr == other.from_addr and self.to_addr == other.to_addr and self.subject == other.subject and self.date_sent == other.date_sent and self.size == other.size
        return False

    def to_string(self):
        r = f"*/{self.flags:06x}/{quote_plus(self.from_addr)}/{quote_plus(self.to_addr)}/{quote_plus(self.bbs)}/{quote_plus(self.local_id)}/{quote_plus(self.subject)}/{self.date_sent}/{self.date_received}/{self.size}\n"
        return r

    @staticmethod
    def to_outpost_date(s):
		# the display date used by Outpost has a different format
        if not s: return ""
        dt = datetime.datetime.fromisoformat(s)
        return "{:%m/%d/%Y %H:%M}".format(dt)

    @staticmethod
    def to_in_mail_date(d=""):
		# the date used inside mail headers has another formet
        # if d is None, return current date/time
        if not d:
            d = datetime.datetime.now()
        return "{:%a, %d %b %Y %H:%M:%S %Z}".format(d)

    @staticmethod
    def normalized_date(d="") -> str:
        # try to make sense out of any date format, return a string in ISO-8601 format
        # here is what the current BBS sends: Thu, 09 Oct 2025 09:58:36 PDT, which is known as RFC 2822
        # here is another format, used by ctime(): Mon Oct 11 17:10:55 2021
        # since these is the only examples I have at the moment, it only supports those two
        # todo: use more of the built-in datetime methods

        # if d is None, return current date/time
        if not d:
            d = datetime.datetime.now()
            return "{:%Y-%m-%dT%H:%M:%S}".format(d)

        yy = 0
        mm = 0
        dd = 0
        h = 0
        m = 0
        s = 0

        def month_to_int(s) -> int:
            months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
            if not s in months:
                return 0
            return months.index(s) + 1
#        # if there is a comma, discard everything up to and including it
#        tmp = d.find(",")
#        if tmp: d = d[i+tmp:].lstrip()
        # in both formats, we don't care about the stuff before the first space
        tmp = d.find(" ")
        if tmp: d = d[tmp+1:].lstrip()
        if not d: return ""
        if d[0].isdigit():
            # must be type 1, 09 Oct 2025 09:58:36 PDT
            i = d.split()
            if len(i) >= 4:
                yy = int(i[2])
                mm = month_to_int(i[1])
                dd = int(i[0])
                j = i[3].split(':')
                if len(j) >= 2:
                    h = int(j[0])
                    m = int(j[1])
                    if len(j) >= 3:
                        s = int(j[2])
        else:
            # must be type 2, Oct 11 17:10:55 2021
            i = d.split()
            if len(i) >= 4:
                yy = int(i[3])
                mm = month_to_int(i[0])
                dd = int(i[1])
                j = i[3].split(i[2],':')
                if len(j) >= 2:
                    h = int(j[0])
                    m = int(j[1])
                    if len(j) >= 3:
                        s = int(j[2])
        if yy < 100: yy += 2000
        if 1 <= mm <= 12 and 1 <= dd <= 31 and  0 <= h < 24 and 0 <= m < 60 and 0 <=  s < 60:
            d = datetime.datetime(yy,mm,dd,h,m,s)
            return "{:%Y-%m-%dT%H:%M:%S}".format(d)
        return ""
    def is_new(self) -> bool:
        return bool(self.flags & MailFlags.IS_NEW.value)
    def is_urgent(self) -> bool:
        return bool(self.flags & MailFlags.IS_URGENT.value)
    def is_outgoing(self) -> bool:
        return bool(self.flags & MailFlags.IS_OUTGOING.value)
    def get_type(self) -> int:
        v = 0
        if self.flags & MailFlags.TYPE_BIT_0.value:
            v |= 1
        if self.flags & MailFlags.TYPE_BIT_1.value:
            v |= 2
        return v
    def get_type_str(self) -> str:
        return ["","B","NTS","DRAFT"][self.get_type()]
    def set_type(self,t) -> None:
        self.flags &= ~(MailFlags.TYPE_BIT_0.value|MailFlags.TYPE_BIT_1.value)
        if t & 1:
            self.flags |= MailFlags.TYPE_BIT_0.value
        if t & 2:
            self.flags |= MailFlags.TYPE_BIT_1.value
    # these make the sorted fucntion work in the mail display
    @property
    def urgent(self) -> bool:
        return bool(self.flags & MailFlags.IS_URGENT.value)
    @property
    def type_str(self) -> str:
        t = self.get_type()
        return ["","B","NTS","DRAFT"][t]

class MailFolder:
    def __init__(self):
        super().__init__()
        self.mail = [] # a list of MailBoxHeader objects

    def needs_cleaning(self) -> bool:
        keepers = MailFlags.FOLDER_BITS.value - MailFlags.FOLDER_DELETED.value - MailFlags.FOLDER_X.value # if a message has any of these bit set, keep it
        for index in range (len(self.mail)):
            if not self.mail[index].flags & keepers:
                return True
        return False

    def clean(self): # erases  items in Folder "X", should run at start or end (or both)
        # self.load() # not neededif at end
        keepers = MailFlags.FOLDER_BITS.value - MailFlags.FOLDER_DELETED.value - MailFlags.FOLDER_X.value # if a message has any of these bit set, keep it
        # first, copy all the mail that will not be deleted
        # file = tempfile.TemporaryFile()
        file = open("PyOutpost.mail.tmp","wb")
        for index in range (len(self.mail)):
            print(f"{bool(self.mail[index].flags & keepers)} {self.mail[index].flags&0xfff:03x} {self.mail[index].subject}")
            if self.mail[index].flags & keepers:
                mbh,m = self.get_message(index)
                file.write(mbh.to_string().encode("windows-1252"))
                file.write(m.encode("windows-1252"))
        file.close()
        os.remove("PyOutpost.mail")
        os.rename("PyOutpost.mail.tmp","PyOutpost.mail")
        # self.load() # caller needs to do this if at start, if at end, no need

    def load(self):
        self.mail.clear()
        try:
            with open("PyOutpost.mail","rb") as file:
                while True:
                    oh = file.tell()
                    l = file.readline().decode("windows-1252")
                    if not l: break
                    if len(l) > 10 and l[0:2] == "*/":
                        om = file.tell()
                        mbh = MailBoxHeader(l,oh,om)
                        if mbh:
                            mbh.index = len(self.mail)
                            self.mail.append(mbh)
                            file.seek(om+mbh.size)
        except FileNotFoundError:
            pass

    def reload(self):
        return self.load()

    def add_mail(self,mbh,message,folder:MailFlags): # mbh is a MailBoxHeader
        # before adding, look of we already have this one
        for m in self.mail:
            if m == mbh:
                # todo: add folder to flags
                return
        mbh.flags |= folder.value
        with open("PyOutpost.mail","ab") as file:
            # the size should be of the encoded data
            message = message.encode("windows-1252")
            mbh.size = len(message)
            mbh.offset_to_header = file.tell()
            file.write(mbh.to_string().encode("windows-1252"))
            mbh.offset_to_message_body = file.tell()
            file.write(message) # it has already been encoded above
        mbh.index = len(self.mail)
        self.mail.append(mbh)

    # all of the below functions are slightly dangerout in that they carefully read the header line and then update it in-place
    # this only works because the flags item is a fixed size (4 hex chars)

    def copy_mail(self,indexlist,tofolder:MailFlags):
        try:
            with open("PyOutpost.mail","rb+") as file:
                for index in indexlist:
                    if not 0 <= index < len(self.mail): continue # ignore any out-of-range values
                    self.mail[index].flags |= tofolder.value
                    newflags = f"*/{self.mail[index].flags:06x}/".encode("windows-1252")
                    assert(len(newflags)) == 9
                    offset = self.mail[index].offset_to_header
                    file.seek(offset)
                    # read the next 9 bytes just to see if we are in the right spot
                    oldflags = file.read(9)
                    if len(oldflags) == 9 and oldflags.startswith(b"*/") and oldflags != newflags:
                        file.seek(offset)
                        file.write(newflags)
        except FileNotFoundError:
            pass

    def move_mail(self,indexlist,fromfolder:MailFlags,tofolder:MailFlags): # frommailbox can be multiple or none, tomailbox can be multiple
        try:
            with open("PyOutpost.mail","rb+") as file:
                for index in indexlist:
                    if not 0 <= index < len(self.mail): continue # ignore any out-of-range values
                    self.mail[index].flags &= ~fromfolder.value
                    self.mail[index].flags |= tofolder.value
                    newflags = f"*/{self.mail[index].flags:06x}/".encode("windows-1252")
                    assert(len(newflags)) == 9
                    offset = self.mail[index].offset_to_header
                    file.seek(offset)
                    # read the next 79 bytes just to see if we are in the right spot
                    oldflags = file.read(9)
                    if len(oldflags) == 9 and oldflags.startswith(b"*/") and oldflags != newflags:
                        file.seek(offset)
                        file.write(newflags)
        except FileNotFoundError:
            pass

    # returns a MailBoxHeader and a string containing the mail (may change this to a bytearray)
    def get_message(self,n):
        if not 0 <= n < len(self.mail): return [],""
        offset = self.mail[n].offset_to_message_body
        msize = self.mail[n].size
        try:
            with open("PyOutpost.mail","rb") as file:
                file.seek(offset)
                return self.mail[n],file.read(msize).decode("windows-1252")
        except FileNotFoundError:
            return [],""

    def mark_as_new(self,index,mark=True): # mark as read is equivalemt tp mark_as_new(n,False), returns True if changed
        if not 0 <= index < len(self.mail): return False
        if mark:
            if self.mail[index].flags & MailFlags.IS_NEW.value: return False
            self.mail[index].flags |= MailFlags.IS_NEW.value
        else:
            if not self.mail[index].flags & MailFlags.IS_NEW.value: return False
            self.mail[index].flags &= ~MailFlags.IS_NEW.value
        newflags = f"*/{self.mail[index].flags:06x}/".encode("windows-1252")
        assert(len(newflags)) == 9
        offset = self.mail[index].offset_to_header
        try:
            with open("PyOutpost.mail","rb+") as file:
                file.seek(offset)
                # read the next 9 bytes just to see if we are in the right spot
                oldflags = file.read(9)
                if len(oldflags) == 9 and oldflags.startswith(b"*/") and oldflags != newflags:
                    file.seek(offset)
                    file.write(newflags)
        except FileNotFoundError:
            pass
        return True

    def get_headers(self,folder:MailFlags): 
        r = []
        for m in self.mail:
            if m.flags & folder.value:
                print(f"{m.flags&0xfff:03x} {m.subject}")
                r.append(m)
        return r

    def get_header_indexes(self,folder:MailFlags): 
        r = []
        for m in self.mail:
            if m.flags & folder.value:
                print(f"{m.flags&0xfff:03x} {m.subject}")
                r.append(m.index)
        return r

    # this was copied from tncparser, I don't know the recommended way to store loose functions
    @staticmethod
    def matches_ignore_case(str1, str2): # if str2 is a prefix of str1
        l = len(str2)
        str1 = str1[0:l].upper()
        str2 = str2.upper()
        return str1 == str2

    def is_possibly_a_duplicate(self,to_addr:str,from_addr:str,subject:str) -> bool:
        for m in self.mail:
            if self.matches_ignore_case(m.to_addr,to_addr) and self.matches_ignore_case(m.from_addr,from_addr) and self.matches_ignore_case(m.subject,subject):
                return True
        return False
            


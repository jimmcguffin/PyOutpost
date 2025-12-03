import datetime
import os
import math
import sqlite3
from enum import Enum
from fnmatch import fnmatch

# headers (items in same order as display)
# */flagbits/From/To/BBS/LocalId/Subject/DateSent/DateReceived/Size

# the flags are held in a 24 bit number
# the low 11 bits are the folders that the mail is currently in
# 1 bit unused (maybe a 12th folder)
# then the "type" as 2 bits
# bit 22 is the urgent flag
# the high bit (23) is New(Unread)

class MailFlags(Enum):
    FOLDER_NONE = 0 # the next time the app ends, these are removed
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
    FOLDER_SEARCH_RESULTS = 1<<11
    FOLDER_BITS = 0xfff # all above bits
    FOLDER_SEARCHABLE = 0x7ff # all above bits except search results
    FOLDER_SEARCHABLE_EX = 0x7ff-FOLDER_DELETED # all above bits except search results and deleted
    TYPE_BIT_0 = 1<<12 # these are used to make a 2-bit field, see code
    TYPE_BIT_1 = 1<<13
    # 2 exta bits here, maybe allow more types
    IS_OUTGOING = 1<<16 # this means it was originally a message created and sent by this program
    # 5 exta bits here
    IS_URGENT = 1<<22
    IS_NEW = 1<<23

class FieldsToSearch(Enum):
    SUBJECT = 1<<0
    MESSAGE = 1<<1
    LOCAL_MSG_ID = 1<<2
    FROM = 1<<3
    TO = 1<<4
    BBS = 1<<5
    ALL_FOLDERS = 1<<6 # not really a field
    ALL_FOLDERS_EX = 1<<7

class MailBoxHeader:
    def __init__(self,id=0,flags=0,from_addr="",to_addr="",bbs="",local_id="",subject="",date_sent="",date_received="",size=0,_=None): # last item is to handle SELECT * results
        self.index = id # shoule be called id, but older version used index
        self.flags = flags # bit encoded, includes New/unread and folder bit mask
        self.from_addr = from_addr
        self.to_addr = to_addr
        self.bbs = bbs
        self.local_id = local_id
        self.subject = subject
        self.date_sent = date_sent # in ISO-8601 format
        self.date_received = date_received # in ISO-8601 format
        self.size = size # size of the actual mail

    def __eq__(self, other):
        if isinstance(other, MailBoxHeader):
            #z =  self.from_addr == other.from_addr and self.to_addr == other.to_addr and self.subject == other.subject and self.date_sent == other.date_sent and self.size == other.size and self.size == other.size
            #print(f"{z}: {self.from_addr}/{other.from_addr} {self.to_addr}/{other.to_addr} {self.subject}/{other.subject} {self.date_sent}/{other.date_sent} {self.size}/{other.size}")
            return self.from_addr == other.from_addr and self.to_addr == other.to_addr and self.subject == other.subject and self.date_sent == other.date_sent and self.size == other.size
        return False

    @staticmethod
    def to_outpost_date(s):
		# the display date used by Outpost has a different format
        if not s: return ""
        dt = datetime.datetime.fromisoformat(s)
        return "{:%m/%d/%Y %H:%M}".format(dt)

    @staticmethod
    def to_in_mail_date(d=""):
		# the date used inside mail headers has another format
        # if d is None, return current date/time
        if not d:
            d = datetime.datetime.now()
        return "{:%a, %d %b %Y %H:%M:%S %Z}".format(d)

    @staticmethod
    def normalized_date(d="") -> str:
        # try to make sense out of any date format, return a string in ISO-8601 format
        # here is what the current BBS sends: Thu, 09 Oct 2025 09:58:36 PDT, which is known as RFC 2822
        # here is another format, used by ctime(): Mon Oct 11 17:10:55 2021
        # outpost sends date/time as floating number of days since 1900
        # since these is the only examples I have at the moment, it only supports those two
        # todo: use more of the built-in datetime methods

        # if d is None, return current date/time
        if not d:
            d = datetime.datetime.now()
            return "{:%Y-%m-%dT%H:%M:%S}".format(d)
        if isinstance(d,float):
            if not d:
                return ""
            # fdays,days = math.modf(d)
            # fhours,hours = math.modf(fdays*24)
            # fmins,mins = math.modf(fhours*60)
            # _,secs = math.modf(fmins*60)
            d0 = datetime.datetime(1900,1,1)
            d1 = datetime.timedelta(d-2) # why -2? No explanation, I had to to make the times match
            return "{:%Y-%m-%dT%H:%M:%S}".format(d0+d1)
        
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

class MailBox:
    def __init__(self):
        super().__init__()
        self.connection = sqlite3.connect("messages.db")
        
        self.cursor = self.connection.cursor()
        self.cursor.execute("""CREATE TABLE IF NOT EXISTS messages(
            id INTEGER PRIMARY KEY,
            flags INTEGER NOT NULL,
            from_addr NVARCHAR(64),
            to_addr NVARCHAR(64),
            bbs NVARCHAR(64),
            local_id NVARCHAR(64),
            subject NVARCHAR(256),
            date_sent CHAR(19),
            date_received CHAR(19),
            size INTEGER,
            message BLOB NOT NULL
            )""")
    

    def needs_cleaning(self) -> bool:
        return True

    def clean(self): # erases  items in Folder "X", should run at start or end (or both)
        keepers = MailFlags.FOLDER_BITS.value - MailFlags.FOLDER_DELETED.value - MailFlags.FOLDER_SEARCH_RESULTS.value # if a message has any of these bit set, keep it
        self.cursor.execute("DELETE FROM messages WHERE NOT flags & ?",(keepers,))
        self.connection.commit()

    def load(self):
        pass

    def add_mail(self,mbh:MailBoxHeader,message:str,folder:MailFlags): # mbh is a MailBoxHeader
        # before adding, look if we already have this one
        # the version of this in my_mailbox only checks the header items, not the message body, for now this one too
        self.cursor.execute("SELECT * FROM messages WHERE subject == ?",(mbh.subject,))
        items = self.cursor.fetchall()
        for item in items:
            m = MailBoxHeader(*item)
            # already screened out the subject with SELECT, now check remaining fields
            if m == mbh:
                return True
        mbh.flags |= folder.value
        mbh.size = len(message)
        self.cursor.execute("INSERT INTO messages (flags,from_addr,to_addr,bbs,local_id,subject,date_sent,date_received,size,message)"
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (mbh.flags,mbh.from_addr,mbh.to_addr,mbh.bbs,mbh.local_id,mbh.subject,mbh.date_sent,mbh.date_received,len(message),message))
        self.connection.commit()

    def copy_mail(self,indexlist,tofolder:MailFlags):
        for index in indexlist:
            self.cursor.execute("SELECT flags FROM messages WHERE id == ?",(index,))
            flags, = self.cursor.fetchone()
            if flags != None:
                flags |= tofolder.value
                self.cursor.execute("UPDATE messages SET flags = ? WHERE id = ?;",(flags,index,))
                self.connection.commit()

    def move_mail(self,indexlist,fromfolder:MailFlags,tofolder:MailFlags): # fromfolder can be multiple or none, tofolder can be multiple
        for index in indexlist:
            self.cursor.execute("SELECT flags FROM messages WHERE id == ?",(index,))
            flags, = self.cursor.fetchone()
            if flags != None:
                flags &= ~fromfolder.value
                flags |= tofolder.value
                self.cursor.execute("UPDATE messages SET flags = ? WHERE id = ?;",(flags,index,))
                self.connection.commit()

    # returns a MailBoxHeader and a string containing the message
    def get_message(self,n) -> tuple[MailBoxHeader,str]:
        self.cursor.execute("SELECT * FROM messages WHERE id == ?",(n,))
        r = self.cursor.fetchone()
        if r == None:
            return MailBoxHeader(),""
        mbh = MailBoxHeader(*r)
        return mbh,r[-1]

    def mark_as_new(self,index,mark=True): # mark as read is equivalemt tp mark_as_new(n,False), returns True if changed
        self.cursor.execute("SELECT flags FROM messages WHERE id == ?",(index,))
        flags, = self.cursor.fetchone()
        if flags != None:
            if mark:
                if flags & MailFlags.IS_NEW.value: return False
                flags |= MailFlags.IS_NEW.value
            else:
                if not flags & MailFlags.IS_NEW.value: return False
                flags &= ~MailFlags.IS_NEW.value
            self.cursor.execute("UPDATE messages SET flags = ? WHERE id = ?;",(flags,index,))
            self.connection.commit()

    def get_headers(self,folder:MailFlags):
        r = []
        self.cursor.execute("SELECT * FROM messages WHERE flags & ?",(folder.value,))
        rows = self.cursor.fetchall()
        for row in rows:
            r.append(MailBoxHeader(*row))
        return r

    def get_header_indexes(self,folder:MailFlags): 
        r = []
        self.cursor.execute("SELECT id FROM messages WHERE flags & ?",(folder.value,))
        rows = self.cursor.fetchall()
        for row in rows:
            r.append(row[0])
        return r

    def search(self,searchstr:str,fields_to_search:FieldsToSearch,folders:MailFlags):
        # first step is to clear out the search results folder
        original_indexlist = self.get_header_indexes(MailFlags.FOLDER_SEARCH_RESULTS)
        #if original_indexlist:
        #    self.move_mail(original_indexlist,MailFlags.FOLDER_SEARCH_RESULTS,MailFlags.FOLDER_NONE)
        # because we are using file name matching, we need to prefix with a "*"
        if not searchstr:
            return False
        if searchstr[0] != "*":
            searchstr = "*" + searchstr
        if searchstr[-1] != "*":
            searchstr = searchstr + "*"
        indexlist = self.get_header_indexes(folders)
        foundlist = []
        for index in indexlist:
            found = False
            self.cursor.execute("SELECT * FROM messages WHERE id == ?",(index,))
            r = self.cursor.fetchone()
            mbh = MailBoxHeader(*r)
            if fields_to_search & FieldsToSearch.SUBJECT.value:
                if fnmatch(mbh.subject,searchstr):
                    found = True
            if fields_to_search & FieldsToSearch.LOCAL_MSG_ID.value and not found:
                if fnmatch(mbh.local_id,searchstr):
                    found = True
            if fields_to_search & FieldsToSearch.FROM.value and not found:
                if fnmatch(mbh.from_addr,searchstr):
                    found = True
            if fields_to_search & FieldsToSearch.TO.value and not found:
                if fnmatch(mbh.to_addr,searchstr):
                    found = True
            if fields_to_search & FieldsToSearch.BBS.value and not found:
                if fnmatch(mbh.bbs,searchstr):
                    found = True
            if fields_to_search & FieldsToSearch.MESSAGE.value and not found:
                if fnmatch(r[-1],searchstr):
                    found = True
            if found:
                foundlist.append(index)
        if not foundlist:
            return False
        if original_indexlist:
            self.move_mail(original_indexlist,MailFlags.FOLDER_SEARCH_RESULTS,MailFlags.FOLDER_NONE)
        self.copy_mail(foundlist,MailFlags.FOLDER_SEARCH_RESULTS)
        return True

    # this was copied from tncparser, I don't know the recommended way to store loose functions
    @staticmethod
    def matches_ignore_case(str1, str2): # if str2 is a prefix of str1
        l = len(str2)
        str1 = str1[0:l].upper()
        str2 = str2.upper()
        return str1 == str2

    # this only checks the items that we get from the "LA" commands, which are the first "n" letters of the to, from, and subject fields
    # it is only used with the items in the bulletin areas, which do not chsnge often and we don't want to read them redundantly
    def is_possibly_a_duplicate(self,to_addr:str,from_addr:str,subject:str) -> bool:
        self.cursor.execute("SELECT to_addr, from_addr, subject FROM messages")
        items = self.cursor.fetchall()
        for item in items:
            t,f,s = item
            if self.matches_ignore_case(t,to_addr) and self.matches_ignore_case(f,from_addr) and self.matches_ignore_case(s,subject):
                return True
        return False
            


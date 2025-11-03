from urllib.parse import quote_plus,unquote_plus
import tempfile
import datetime
import os

# struct MailBoxHeader
# 	{
# //	bool FromString(const QByteArray &s);
# 	MailBoxHeader(void) {};
# 	MailBoxHeader(const QByteArray &s, qint64 offset);
# 	bool operator == (const MailBoxHeader &other) const 
# 		{
# 		// the Offset does not need to match, but everything else does
# 		return (m_U == other.m_U && m_Type == other.m_Type && m_From == other.m_From && m_To == other.m_To && m_BBS == other.m_BBS && m_LocalId == other.m_LocalId && m_Subject == other.m_Subject && m_Date == other.m_Date && m_Size == other.m_Size);	
# 		}
# 	std::string ToString(void) const;

# 	std::string m_U; // not sure what this is
# 	std::string m_Type;
# 	std::string m_From;
# 	std::string m_To;
# 	std::string m_BBS;
# 	std::string m_LocalId; // not sure what this is
# 	std::string m_Subject;
# 	std::string m_Date; // in ISO-8601 format
# 	qint64 m_Size = 0;
# 	qint64 m_Offset = 0; // offset to start of header
# 	static std::string NormalizedDate(std::string d); // converts various formats into ISO-8601
# 	std::string ToOutpostDate(void) const
# 		{
# 		// the display date used by Outpost has a different format
# 		int Y=0,M=0,D=0,h=0,m=0,s=0;
# 		if (sscanf(m_Date.c_str(),"%d-%d-%dT%d:%d:%d",&Y,&M,&D,&h,&m,&s) == 6)
# 			{
# 			char buffer[64];
# 			snprintf(buffer,sizeof(buffer),"%d/%d/%04d %02d:%02d",M,D,Y,h,m);	
# 			return buffer;
# 			}
# 		else
# 			return m_Date;
# 		}
# 	};

# headers (items in same order as display)
# */U/Type/From/To/BBS/LocalId/Subject/Date/Size

class MailBoxHeader:
    def __init__(self,s="",oh=0,om=0):
        self.mIndex = 0
        self.mIsNew = "N" # "Y"=new/unread, "N"=read
        self.mUrgent = ""
        self.mType = ""
        self.mFrom = ""
        self.mTo = ""
        self.mBbs = ""
        self.mLocalId = ""
        self.mSubject = ""
        self.mDateSent = "" # in ISO-8601 format
        self.mDateReceived = "" # in ISO-8601 format
        self.mSize = 0 # size of the actual mail that follows
        self.mOffsetToHeader = 0 # offset in file to start of this header
        self.mOffsetToMessageBody = 0 # offset in file to start of the message body
        s = s.rstrip()
        if s and len(s) > 2 and s[0:2] == "*/":
            tmp = s.split("/")
            if len(tmp) >= 12:
                for index in range(2,10):
                    tmp[index]= unquote_plus(tmp[index])
                self.mIsNew = tmp[1]
                self.mUrgent = tmp[2]
                self.mType = tmp[3]
                self.mFrom = tmp[4]
                self.mTo = tmp[5]
                self.mBbs = tmp[6]
                self.mLocalId = tmp[7]
                self.mSubject = tmp[8]
                self.mDateSent = tmp[9]
                self.mDateReceived = tmp[10]
                self.mSize = int(tmp[11])
                self.mOffsetToHeader = oh
                self.mOffsetToMessageBody = om
            else:
                pass
        else:
            pass
    
    def __eq__(self, other):
        if isinstance(other, MailBoxHeader):
            return self.mFrom == other.mFrom and self.mTo == other.mTo and self.mSubject == other.mSubject and self.mDateSent == other.mDateSent and self.mSize == other.mSize
        return False
    
    def toString(self):
        r = f"*/{self.mIsNew}/{quote_plus(self.mUrgent)}/{quote_plus(self.mType)}/{quote_plus(self.mFrom)}/{quote_plus(self.mTo)}/{quote_plus(self.mBbs)}/{self.mLocalId}/{quote_plus(self.mSubject)}/{self.mDateSent}/{self.mDateReceived}/{self.mSize}\n";
        return r
    @staticmethod
    def toOutpostDate(s):
		# the display date used by Outpost has a different format
        if not s: return ""
        dt = datetime.datetime.fromisoformat(s)
        return "{:%m/%d/%Y %H:%M}".format(dt)
    @staticmethod
    def monthToInt(s):
        if s == "Jan": return 1
        elif s == "Feb": return 2
        elif s == "Mar": return 3
        elif s == "Apr": return 4
        elif s == "May": return 5
        elif s == "Jun": return 6
        elif s == "Jul": return 7
        elif s == "Aug": return 8
        elif s == "Sep": return 9
        elif s == "Oct": return 10
        elif s == "Nov": return 11
        elif s == "Dec": return 12
        else: return 0
    @staticmethod
    def normalizedDate(d=""):
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
                mm = MailBoxHeader.monthToInt(i[1])
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
                mm = MailBoxHeader.monthToInt(i[0])
                dd = int(i[1])
                j = i[3].split(i[2],':')
                if len(j) >= 2:
                    h = int(j[0])
                    m = int(j[1])
                    if len(j) >= 3:
                        s = int(j[2])
        r = ""
        if yy < 100: yy += 2000;
        if mm >= 1 and mm <= 12 and dd >= 1 and dd <= 31 and h >= 0 and h < 24 and m >= 0 and m < 60 and s >=0  and s < 60:
            d = datetime.datetime(yy,mm,dd,h,m,s)
            return "{:%Y-%m-%dT%H:%M:%S}".format(d)

class MailFolder:
    def __init__(self):
        super(MailFolder,self).__init__()
        self.mail = [] # a list of MailBoxHeader objects
        self.filename = ""
    def load(self,fn):
        self.mail.clear()
        self.filename = fn
        try:
            with open(self.filename+".mail","rb") as file:
                while (True):
                    oh = file.tell()
                    l = file.readline().decode()
                    if not l: break
                    if len(l) > 10 and l[0:2] == "*/":
                        om = file.tell()
                        mbh = MailBoxHeader(l,oh,om)
                        if (mbh):
                            mbh.mIndex = len(self.mail)
                            self.mail.append(mbh)
                            file.seek(om+mbh.mSize)
        except FileNotFoundError:
            pass

    def addMail(self,mbh,message,folder): # mbh is a MailBoxHeader
        if folder == self.filename:
            # before adding, look of we already have this one
            for m in self.mail:
                if m == mbh:
                    return
            with open(self.filename+".mail","ab") as file:
                mbh.mSize = len(message)
                mbh.mOffsetToHeader = file.tell()
                file.write(mbh.toString().encode())
                mbh.mOffsetToMessageBody = file.tell()
                file.write(message.encode())
            mbh.mIndex = len(self.mail)
            self.mail.append(mbh)
        else:
            target = MailFolder()
            target.load(folder)
            # before adding, look of we already have this one
            for m in target.mail:
                if m == mbh:
                    return
            with open(target.filename+".mail","ab") as file:
                mbh.mSize = len(message)
                mbh.mOffsetToHeader = file.tell()
                file.write(mbh.toString().encode())
                mbh.mOffsetToMessageBody = file.tell()
                file.write(message.encode())

    def copyMail(self,indexlist,tomailbox): # to move mail, call copyMail followed by deleteMail with same indexlist
        # open input and output files
        outfile = open(tomailbox+".mail","ab")
        for index in indexlist:
            if 0 <= index < len(self.mail):
                mbh,m = self.getMessage(index)
                outfile.write(mbh.toString().encode())
                outfile.write(m.encode())
        outfile.close()

    def deleteMail(self,indexlist):
        # first, copy all the mail that will not be deleted
        # file = tempfile.TemporaryFile()
        file = open(self.filename+".tmp","wb")
        for index in range (len(self.mail)):
            if not index in indexlist:
                mbh,m = self.getMessage(index)
                file.write(mbh.toString().encode())
                file.write(m.encode())
        file.close()
        os.remove(self.filename+".mail")
        os.rename(self.filename+".tmp",self.filename+".mail")
        self.load(self.filename)

    def getMessage(self,n):
        if not 0 <= n < len(self.mail): return [],""
        offset = self.mail[n].mOffsetToMessageBody
        msize = self.mail[n].mSize
        try:
            with open(self.filename+".mail","rb") as file:
                file.seek(offset)
                return self.mail[n],file.read(msize).decode()
        except FileNotFoundError:
            return [],""

    def markAsNew(self,n,mark=True): # mark as read is markAsNew(n,False), returns True if changed
        if not 0 <= n < len(self.mail): return False
        m = "Y" if mark else "N"
        expectedh = b"*/N" if mark else b"*/Y" 
        newh = b"*/Y" if mark else b"*/N" 
        # if already new/notnew, return
        if self.mail[n].mIsNew == m: return False
        self.mail[n].mIsNew = m
        # this is a delicate operation, need to read the header and then update it in-place
        offset = self.mail[n].mOffsetToHeader
        try:
            with open(self.filename+".mail","rb+") as file:
                file.seek(offset)
                # read the next 3 bytes just to see if we are in the right spot
                h = file.read(3)
                if len(h) == 3 and h == expectedh:
                    file.seek(offset)
                    file.write(newh)
        except FileNotFoundError:
            pass
        return True

    def getHeaders(self): return self.mail

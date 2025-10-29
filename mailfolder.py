from urllib.parse import quote_plus,unquote_plus
import datetime

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
    def __init__(self,s="",o=0):
        self.mIndex = 0
        self.mU = ""
        self.mType = ""
        self.mFrom = ""
        self.mTo = ""
        self.mBbs = ""
        self.mLocalId = ""
        self.mSubject = ""
        self.mDateSent = "" # in ISO-8601 format
        self.mDateReceived = "" # in ISO-8601 format
        self.mSize = 0 # size of the actual mail that follows
        self.mOffset = 0 # offset in file to start of the message body
        s = s.rstrip()
        if s and len(s) > 2 and s[0:2] == "*/":
            tmp = s.split("/")
            if len(tmp) >= 11:
                for index in range(1,9):
                    tmp[index]= unquote_plus(tmp[index])
                self.mU = tmp[1]
                self.mType = tmp[2]
                self.mFrom = tmp[3]
                self.mTo = tmp[4]
                self.mBbs = tmp[5]
                self.mLocalId = tmp[6]
                self.mSubject = tmp[7]
                self.mDateSent = tmp[8]
                self.mDateReceived = tmp[9]
                self.mSize = int(tmp[10])
                self.mOffset = o
            else:
                pass
        else:
            pass
    def toString(self):
        r = f"*/{quote_plus(self.mU)}/{quote_plus(self.mType)}/{quote_plus(self.mFrom)}/{quote_plus(self.mTo)}/{quote_plus(self.mBbs)}/{self.mLocalId}/{quote_plus(self.mSubject)}/{self.mDateSent}/{self.mDateReceived}/{self.mSize}\n";
        return r
    @staticmethod
    def toOutpostDate(s):
		# the display date used by Outpost has a different format
#        d,s,t = self.mDateSent.partition('T')
#        if not s:
#            d,s,t = self.mDateSent.partition(' ') # is some cases the T is not there
#        d = d.split('-')
#        t = t.split(':')
#        dt = datetime.datetime(int(d[0]),int(d[1]),int(d[2]),int(t[0]),int(t[1]),int(t[2]))
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
            with open(self.filename,"rb") as file:
                while l := file.readline().decode():
                    if len(l) > 10 and l[0:2] == "*/":
                        mbh = MailBoxHeader(l,file.tell())
                        if (mbh):
                            mbh.mIndex = len(self.mail)
                            self.mail.append(mbh)
                            file.seek(mbh.mOffset+mbh.mSize)
        except FileNotFoundError:
            pass
    def addMail(self,mbh,message): # mbh is a MailBoxHeader
        # before adding, look of we already have this one
        for m in self.mail:
            if m == mbh:
                return
        with open(self.filename,"ab") as file:
            mbh.mSize = len(message)
            mbh.mOffset = file.tell()
            file.write(mbh.toString().encode())
            file.write(message.encode())
        mbh.mIndex = len(self.mail)
        self.mail.append(mbh)
    def getMessage(self,n):
        if n < 0 or n >= len(self.mail): return [],""
        m = ""
        offset = int(self.mail[n].mOffset)
        msize = int(self.mail[n].mSize)
        with open(self.filename,"rb") as file:
            file.seek(offset)
            return self.mail[n],file.read(msize).decode()
    def getHeaders(self): return self.mail

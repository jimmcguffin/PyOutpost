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
# 	static std::string NormalizeDate(std::string d); // converts various formats into ISO-8601
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
        self.mOffset = 0 # offset in file to start of this header
        s = s.rstrip()
        if s and len(tmp) > 2 and s[0] == '*' and s[1] == '/':
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
                self.mSize = tmp[10]
                self.mOffset = o
    def toString(self):
        r = f"*/{quote_plus(self.mU)}/{quote_plus(self.mType)}/{quote_plus(self.mFrom)}/{quote_plus(self.mTo)}/{quote_plus(self.mBbs)}/{self.mLocalId}/{quote_plus(self.m_Subject)}/{self.m_DateSent}/{self.mDateReceived}/{self.mSize}\n";
        return r
    @staticmethod
    def monthToInt(s):
        if s == "Jan": M = 1
        elif s == "Feb": M = 2
        elif s == "Mar": M = 3
        elif s == "Apr": M = 4
        elif s == "May": M = 5
        elif s == "Jun": M = 6
        elif s == "Jul": M = 7
        elif s == "Aug": M = 8
        elif s == "Sep": M = 9
        elif s == "Oct": M = 10
        elif s == "Nov": M = 11
        elif s == "Dec": M = 12
        else: return 0
    @staticmethod
    def normalizeDate(d):
        # try to make sense out of any date format, return a string in ISO-8601 format
        # here is what the current BBS sends: Thu, 09 Oct 2025 09:58:36 PDT, which is known as RFC 2822
        # here is another format, used by ctime(): Mon Oct 11 17:10:55 2021
        # since these is the only examples I have at the moment, it only supports those two

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
                j = i[3].split(i[3],':')
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
            return "{:%Y-%m-%d %H:%M:%S}".format(d)
class MailFolder:
    def __init__(self):
        super(MailFolder,self).__init__()
        self.mail = [] # a list of MailBoxHeader objects
        self.filename = ""
    def load(self,fn):
        self.mail.clear()
        self.filename = fn
        try:
            with open(self.filename,"r") as file:
                while l := file.readline():
                    if len(l) > 10 and l[0] == '*' and l[1] == '/':
                        m = MailBoxHeader(l,file.tell())
                        if (m):
                            self.mail.append(m)
                            file.seek(m.mOffset+m.mSize)
        except FileNotFoundError:
            pass
    def addMail(self,mbh,message): # mbh is a MailBoxHeader
        # before adding, look of we already have this one
        for m in self.mail:
            if m == mbh:
                return
        with open(self.filename,"a") as file:
            mbh.mSize = len(message)
            mbh.mOffset = file.tell()
            file.write(mbh.toString())
            file.write(message)
        self.mail.append(mbh)
    def getMessage(self,n):
        if n < 0 or n >= len(self.mail): return [],""
        m = ""
        offset = int(self.mail[n].offset)
        msize = int(self.mail[n][10])
        with open(self.filename,"r") as file:
            file.seek(offset)
            return self.mail[n],file.read(msize)
    def getHeaders(self): return self.mail
    def toFileHeader(self,h):
        r = "*"
        for i in range(1,9):
            r += "/"+quote_plus(h[1],'/')
        r += "/"+str(h[10])
        return r;


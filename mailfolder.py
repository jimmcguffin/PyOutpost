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

class MailFolder:
    def __init__(self):
        super(MailFolder,self).__init__()
        self.mail = []
        self.filename = ""
    def load(self,fn):
        self.mail.clear()
        self.filename = fn
        with open(self.filename,"r") as file:
            while l := file.readline():
                l.rstrip()
                if len(l) > 10 and l[0] == '*' and l[1] == '/':
                    f = l.split("/")
                    if len(f) >= 10:
                        offset = file.tell()
                        # change the last string (size of mail) to a number
                        msize = int(f[10])
                        f[10] = msize
                        f.append(offset)
                        self.mail.append(f)
                        file.seek(offset+msize)
    #def addMail(const MailBoxHeader &mbh, const std::string &messag)"load"
    def getMessage(self,n):
        if n < 0 or n >= len(self.mail): return [],""
        m = ""
        offset = int(self.mail[n][11])
        msize = int(self.mail[n][10])
        with open(self.filename,"r") as file:
            file.seek(offset)
            return self.mail[n],file.read(msize)
                             
    def getHeaders(self): return self.mail



        
			
# 		MailBox(void) {}
# 		~MailBox() {}
# 		void Init(void);
# 		void AddMail(const MailBoxHeader &mbh, const std::string &messag);
# 		std::pair<MailBoxHeader, std::string> GetMessage(int n);
# //		std::vector<MailBoxHeader> GetHeaders(void) const { return m_Headers; } // makes a copy, might change this later
# 		const std::vector<MailBoxHeader> &GetHeaders(void) const { return m_Headers; } // doesn't make a copy, not thread-safe
# 	private:
# //		QTableWidget *m_pTable = nullptr;
# 		std::vector<MailBoxHeader> m_Headers;
# 	};


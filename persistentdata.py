from PyQt6.QtCore import QSettings, QDateTime

class PersistentData():
    def __init__(self):
        self.settings = QSettings("OpenOutpost","OpenOutpost")

    def start(self): # this gets called once we know things are "normal"
        ap = self.settings.value("ActiveProfile","Outpost") # "Outpost" is the default profile
        self.activeProfile = ap
        self.activeUserCallSign = self.getProfile("ActiveUserCallSign")
        self.activeTacticalCallSign = self.getProfile("ActiveTacticalCallSign")
        self.activeBBS = self.getProfile("ActiveBBS")
        self.activeInterface = self.getProfile("ActiveInterface")
        #save()
    def clear(self):
        self.settings.clear()
    def save(self):
        self.settings.sync()
	# profiles
    def addProfile(self,name): # just creates an empty profile, only used when running the first time
        self.settings.setValue(f"Profiles/{name}/ActiveUserCallSign","")
        self.activeProfile = name
        self.settings.setValue("ActiveProfile",name)
    def copyProfile(self,name): # makes the new one the active profile and copies serveral values
        ucs = self.activeUserCallSign
        tcs = self.activeTacticalCallSign
        bbs = self.activeBBS
        interface = self.activeInterface
        self.activeProfile = name
        self.setProfile("ActiveUserCallSign",ucs)
        if tcs: self.setProfile("ActiveTacticalCallSign",tcs)
        self.setProfile("ActiveBBS",bbs)
        self.setProfile("ActiveInterface",interface)
        self.setActiveProfile(name)
    def getProfiles(self):
        self.settings.beginGroup("Profiles")
        r = self.settings.childGroups()
        self.settings.endGroup()
        return r
    def getActiveProfile(self): return self.activeProfile
    def setActiveProfile(self,s):
        self.activeProfile = s
        self.settings.setValue("ActiveProfile",s)
        self.activeUserCallSign = self.getProfile("ActiveUserCallSign")
        if not self.activeUserCallSign:
            l = self.getUserCallSigns()
            if l: self.setActiveUserCallSign(l[0])
            else: self.setActiveUserCallSign("")
        self.activeTacticalCallSign = self.getProfile("ActiveTacticalCallSign")
        if not self.activeTacticalCallSign:
            self.setActiveTacticalCallSign("") # it is OK for these to be blank
        self.activeBBS = self.getProfile("ActiveBBS")
        if not self.activeBBS:
            l = self.getBBSs()
            if l: self.setActiveBBS(l[0])
            else: self.setActiveBBS("TEMP")
        self.activeInterface = self.getProfile("ActiveInterface")
        if not self.activeInterface:
            l = self.getInterfaces()
            if l: self.setActiveInterface(l[0])
            else: self.setActiveInterface("TEMP")
    def getProfile(self,s,default=""): return self.settings.value(f"Profiles/{self.activeProfile}/{s}",default)
    def getProfileBool(self,s,default=False): 
        # here is a difference between platforms
        # windows does not have boolens in the registry, so it use strings "true"/"false"
        # apples do have native bools
        # this will attempt tp handle both
        v = self.settings.value(f"Profiles/{self.activeProfile}/{s}",default)
        if isinstance(v,str): return True if v == "true" or v == "True" or v == "1" else False
        return bool(v)
    def setProfile(self,s,value): self.settings.setValue(f"Profiles/{self.activeProfile}/{s}",value)
    def getNextMessageNumber(self,increment=True):
        r = self.settings.value("NextMessageNumber",0)
        if increment:
            n = r + 1
            if n < r: n = 0 # n has overflowed
            self.settings.setValue("NextMessageNumber",n)
        return r

    # call signs
    def addUserCallSign(self,callsign,name,messageprefix):
        self.settings.setValue(f"UserCallSigns/{callsign}/Name",name)
        self.settings.setValue(f"UserCallSigns/{callsign}/MessagePrefix",messageprefix)
    def getUserCallSigns(self):
        self.settings.beginGroup("UserCallSigns")
        r = self.settings.childGroups()
        self.settings.endGroup()
        # we need at least one - make a fake one if needed
#        if len(r) == 0:
#            self.addUserCallSign("TEMP","Temporary call sign","TMP")
#            r.append("TEMP")
        return r
    # special version of call sign getter that returns the user or the tactical, whichever is appropriate
    def getActiveCallSign(self,forstatusbar=False):
        if self.getProfileBool("UseTacticalCallSign"):
            if forstatusbar:
                return self.activeUserCallSign  + " as " + self.activeTacticalCallSign
            else:
                return self.activeTacticalCallSign
        else:
            return self.activeUserCallSign
    def getActiveCallSignName(self):
        if self.getProfileBool("UseTacticalCallSign"):
            return self.getTacticalCallSign("Name")
        else:
            return self.getUserCallSign("Name")
    def getActiveUserCallSign(self): return self.activeUserCallSign
    def setActiveUserCallSign(self,s): 
        self.activeUserCallSign = s
        self.setProfile("ActiveUserCallSign",s)
    def getUserCallSign(self,s): return self.settings.value(f"UserCallSigns/{self.activeUserCallSign}/{s}")
    def setUserCallSign(self,s,value): self.settings.setValue(f"UserCallSigns/{self.activeUserCallSign}/{s}",value)

    # tactical call signs
    def addTacticalCallSign(self,callsign,name,messageprefix):
        self.settings.setValue("TacticalCallSigns/"+callsign+"/Name",name)
        self.settings.setValue("TacticalCallSigns/"+callsign+"/MessagePrefix",messageprefix)
    def getTacticalCallSigns(self):
        self.settings.beginGroup("TacticalCallSigns")
        r = self.settings.childGroups()
        self.settings.endGroup()
        return r
    def getActiveTacticalCallSign(self): return self.activeTacticalCallSign
    def setActiveTacticalCallSign(self,s): 
        self.activeTacticalCallSign = s
        self.settings.setValue("Profiles/"+self.activeProfile+"/ActiveTacticalCallSign",s)
    def getTacticalCallSign(self,s): return self.settings.value(f"TacticalCallSigns/{self.activeTacticalCallSign}/{s}")
    def setTacticalCallSign(self,s,value): self.settings.setValue(f"TacticalCallSigns/{self.activeTacticalCallSign}/{s}",value)

    # BBSs
    def getBBSs(self):
        self.settings.beginGroup("BBSs")
        r = self.settings.childGroups()
        self.settings.endGroup()
        return r
    def addBBS(self,name,connectname,description=""):
        self.settings.setValue(f"BBSs/{name}/ConnectName",connectname)
        self.settings.setValue(f"BBSs/{name}/Description",description)
    def setActiveBBS(self,s):
        self.activeBBS = s
        self.settings.setValue(f"Profiles/{self.activeProfile}/ActiveBBS",s)
    def getActiveBBS(self): return self.activeBBS
    def getBBS(self,s): return self.settings.value(f"BBSs/{self.activeBBS}/{s}")
    def getBBSBool(self,s): return True if self.settings.value(f"BBSs/{self.activeBBS}/{s}") == "true" else False
    def setBBS(self,s,value): self.settings.setValue(f"BBSs/{self.activeBBS}/{s}",value)
    # Interfaces
    def getInterfaces(self):
        self.settings.beginGroup("Interfaces")
        r = self.settings.childGroups()
        self.settings.endGroup()
        return r
    def addInterface(self,name,description=""):
        self.settings.setValue(f"Interfaces/{name}/Description",description)
    def setActiveInterface(self,s):
        self.activeInterface = s
        self.settings.setValue(f"Profiles/{self.activeProfile}/ActiveInterface",s)
    def getActiveInterface(self): return self.activeInterface
    def getInterface(self,s): return self.settings.value(f"Interfaces/{self.activeInterface}/{s}")
    def getInterfaceBool(self,s): return True if self.settings.value(f"Interfaces/{self.activeInterface}/{s}") == "true" else False
    def setInterface(self,s,value): self.settings.setValue(f"Interfaces/{self.activeInterface}/{s}",value)
    # some convenience functions
    def makeStandardSubject(self,increment=True):
        mn = self.getNextMessageNumber(increment)
        subject = ""
        if self.getProfileBool("MessageSettings/AddMessageNumber"):
            subject += self.getUserCallSign("MessagePrefix")
        f = self.getProfile("MessageSettings/Hyphenation_flag")
        if f == "0":
            subject += f"{mn:03}"
        elif f == "1":
            subject += f"-{mn:03}"
        elif f == "2":
            dt = QDateTime.currentDateTime()
            subject += dt.toString("yyMMddHHmmss")
        if self.getProfileBool("MessageSettings/AddCharacter"):
            subject += self.getProfile("MessageSettings/CharacterToAdd")
        if self.getProfileBool("MessageSettings/AddMessageNumberSeparator"):
            subject += ":"
        return subject

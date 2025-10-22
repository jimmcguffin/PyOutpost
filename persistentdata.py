from PyQt6.QtCore import QSettings

class PersistentData():
    def __init__(self):
        self.settings = QSettings("OpenOutpost","OpenOutpost")
        ap = self.settings.value("ActiveProfile","Outpost") # "Outpost" is the default profile
        self.activeProfile = ap
        self.activeUserCallSign = self.getProfile("ActiveUserCallSign")
        self.activeTacticalCallSign = self.getProfile("ActiveTacticalCallSign")
        self.activeBBS = self.getProfile("ActiveBBS")
        self.activeInterface = self.getProfile("/ActiveInterface")
        #save()

    def save(self):
        self.settings.sync()
	# profiles
    def getProfile(self,str): return self.settings.value(f"Profiles/{self.activeProfile}/{str}")
    def getProfileBool(self,str): return True if self.settings.value(f"Profiles/{self.activeProfile}/{str}") == "true" else False
    def setProfile(self,str,value): self.settings.setValue(f"Profiles/{self.activeProfile}/{str}",value)

    # call signs
    def addUserCallSign(self,callsign,name,messageprefix):
        self.settings.setValue(f"UserCallSigns/{callsign}/Name",name)
        self.settings.setValue(f"UserCallSigns/{callsign}/MessagePrefix",messageprefix)
    def getUserCallSigns(self):
        self.settings.beginGroup("UserCallSigns")
        r = self.settings.childGroups()
        self.settings.endGroup()
        # we need at least one - make a fake one if needed
        if len(r) == 0:
            self.addUserCallSign("TEMP","Temporary call sign","TMP")
            r.push_back("TEMP")
        return r
    def getActiveUserCallSign(self): return self.activeUserCallSign
    def setActiveUserCallSign(self,str): 
        self.activeUserCallSign = str
        self.setProfile("ActiveUserCallSign",str)
    def getUserCallSign(self,str): return self.settings.value(f"UserCallSigns/{self.activeUserCallSign}/{str}")
    def setUserCallSign(self,str,value): self.settings.setValue(f"UserCallSigns/{self.activeUserCallSign}/{str}",value)

    # tactical call signs
    def addTacticalCallSign(self,callsign,name,messageprefix):
        self.settings.setValue("TacticalCallSigns/"+callsign+"/Name",name)
        self.settings.setValue("TacticalCallSigns/"+callsign+"/MessagePrefix",messageprefix)
    def getTacticalCallSigns(self):
        self.settings.beginGroup("TacticalCallSigns")
        r = self.settings.childGroups()
        self.settings.endGroup()
        # we need at least one - make a fake one if needed
        if len(r) == 0:
            self.addTacticalCallSign("TEMP","Temporary call sign","TMP")
            r.push_back("TEMP")
        return r
    def getActiveTacticalCallSign(self): return self.activeTacticalCallSign
    def setActiveTacticalCallSign(self,str): 
        self.activeTacticalCallSign = str
        self.settings.setValue("Profiles/"+self.activeProfile+"/ActiveTacticalCallSign",str)
    def getTacticalCallSign(self,str): return self.settings.value(f"TacticalCallSigns/{self.activeTacticalCallSign}/{str}")
    def setTacticalCallSign(self,str,value): self.settings.setValue(f"TacticalCallSigns/{self.activeTacticalCallSign}/{str}",value)

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
        self.settings.setValue(f"Profiles/{self.activeProfile}/ActiveBBS",str)
    def getActiveBBS(self): return self.activeBBS
    def getBBS(self,str): return self.settings.value(f"BBSs/{self.activeBBS}/{str}")
    def getBBSBool(self,str): return True if self.settings.value(f"BBSs/{self.activeBBS}/{str}") == "true" else False
    def setBBS(self,str,value): self.settings.setValue(f"BBSs/{self.activeBBS}/{str}",value)
    # Interfaces
    def getInterface(self,str): return self.settings.value(f"Interfaces/{self.activeInterface}/{str}")
    def setInterface(self,str,value): self.settings.setValue(f"Interfaces/{self.activeInterface}/{str}",value)

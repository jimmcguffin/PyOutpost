import sys
from PyQt6 import QtWidgets
from PyQt6 import QtCore
from PyQt6.QtCore import Qt, pyqtSignal, QObject
from PyQt6.QtWidgets import QMainWindow, QLineEdit, QWidget, QPlainTextEdit, QCheckBox, QRadioButton, QButtonGroup, QComboBox, QFrame
from PyQt6.QtGui import QPixmap, QPalette, QColor, QFont
from PyQt6.uic import load_ui
from persistentdata import PersistentData
from mailfolder import MailBoxHeader
import datetime

class FormItem(QObject):
    def __init__(self,parent,f):
        super().__init__(parent)
        self.parent = parent
        self.widget = QWidget(parent)
        self.label = f[0]
        self.fieldname = f[1]
        self.valid = None
        self.validator = ""
        self.subjectlinesource = "Subject"
        if f[3] == "Y" and f[5] != "0":
        #if f[5] != "0": # this shows all of boxes that have been defined
            self.valid = QFrame(parent) 
            # expand the coordinates a litle
            e = 4
            x0 = int(f[5])-e
            y0 = int(f[6])-e
            x1 = int(f[7])+e
            y1 = int(f[8])+e
            self.valid.setGeometry(x0,y0,x1-x0+1,y1-y0+1)
            self.valid.setStyleSheet("QFrame { border: 6px solid #C02020;}")
            self.valid.setFrameStyle(QFrame.Shape.Box|QFrame.Shadow.Plain)
            self.valid.hide()
            self.validator = f[4] # possibly a custom validator
    def getValue(self): pass

class FormItemString(FormItem):
    signalValidityCheck = pyqtSignal(FormItem)
    def __init__(self,parent,f):
        super().__init__(parent,f)
        self.widget = QLineEdit("",parent) # or f[1]
        x0 = int(f[5])
        y0 = int(f[6])
        x1 = int(f[7])
        y1 = int(f[8])
        self.widget.setGeometry(x0,y0,x1-x0+1,y1-y0+1)
        font = QFont()
        #font =  self.cMailList.item(i,0).font()
        font.setBold(True)
        self.widget.setFont(font)
        palette = self.widget.palette()
        palette.setColor(QPalette.ColorRole.Text,QColor("blue"))
        self.widget.setPalette(palette)
        self.widget.textChanged.connect(lambda: self.signalValidityCheck.emit(self))
    def getValue(self):
        return self.widget.text()
    def setValue(self,value):
        return self.widget.setText(value)

class FormItemMultiString(FormItem):
    signalValidityCheck = pyqtSignal(FormItem)
    def __init__(self,parent,f):
        super().__init__(parent,f)
        self.widget = QPlainTextEdit(parent)
        x0 = int(f[5])
        y0 = int(f[6])
        x1 = int(f[7])
        y1 = int(f[8])
        self.widget.setGeometry(x0,y0,x1-x0+1,y1-y0+1)
        self.widget.setPlainText("") # or f[1]
        font = QFont()
        font.setBold(True)
        self.widget.setFont(font)
        palette = self.widget.palette()
        palette.setColor(QPalette.ColorRole.Text,QColor("blue"))
        self.widget.setPalette(palette)
        self.widget.textChanged.connect(lambda: self.signalValidityCheck.emit(self))
    def getValue(self):
        return self.widget.toPlainText().replace("]","`]").replace("\n","\\n")
    def setValue(self,value):
        return self.widget.setText(value.replace("`]","]").replace("\\n","\n"))

class FormItemRadioButtons(FormItem): # always multiple buttons
    signalValidityCheck = pyqtSignal(FormItem)
    def __init__(self,parent,f):
        super().__init__(parent,f)
        default_height = 14
        nb = (len(f)-9)//5
        self.widget = QButtonGroup(parent)
        self.values = []
        for i in range (nb):
            j = i*5+9
            tmpwidget = QRadioButton("                ",parent)
            x0 = int(f[j+1])
            y0 = int(f[j+2])
            x1 = int(f[j+3])
            y1 = int(f[j+4])
            if x1 == 0:
                x1 = x0 + 64
            if y1 == 0:
                y1 = y0 + 14
            tmpwidget.setGeometry(x0,y0,x1-x0+1,y1-y0+1)
            self.widget.addButton(tmpwidget,i)
            palette = tmpwidget.palette()
            palette.setColor(QPalette.ColorRole.Text,QColor("blue"))
            tmpwidget.setPalette(palette)
            self.values.append(f[j])
        self.widget.idClicked.connect(lambda: self.signalValidityCheck.emit(self))
    def getValue(self):
        index = self.widget.checkedId()
        if index < 0: return ""
        return self.values[index]
    def setValue(self,value):
        for i in range(len(self.values)):
            if self.values[i] == value:
                self.widget.button(i).setChecked(True)

class FormItemCheckBox(FormItem):
    signalValidityCheck = pyqtSignal(FormItem)
    def __init__(self,parent,f):
        super().__init__(parent,f)
        self.widget = QCheckBox("                ",parent) # or f[1]
        x0 = int(f[5])
        y0 = int(f[6])
        x1 = int(f[7])
        y1 = int(f[8])
        if x1 == 0:
            x1 = x0 + 64
        if y1 == 0:
            y1 = y0 + 14
        self.widget.setGeometry(x0,y0,x1-x0+1,y1-y0+1)
        palette = self.widget.palette()
        palette.setColor(QPalette.ColorRole.Text,QColor("blue"))
        self.widget.setPalette(palette)
        self.widget.clicked.connect(lambda: self.signalValidityCheck.emit(self))
    def getValue(self):
        return self.widget.isChecked()
    def setValue(self,value):
        return self.widget.setChecked(value)

class FormItemDropDown(FormItem):
    signalValidityCheck = pyqtSignal(FormItem)
    def __init__(self,parent,f):
        super().__init__(parent,f)
        self.widget = QComboBox(parent) # or f[1]
        x0 = int(f[5])
        y0 = int(f[6])
        x1 = int(f[7])
        y1 = int(f[8])
        self.widget.setGeometry(x0,y0,x1-x0+1,y1-y0+1)
        n = len(f)-9
        for i in range(n):
            self.widget.addItem(f[i+9])
        self.widget.setCurrentIndex(-1)
        self.widget.setEditable(True)
        palette = self.widget.palette()
        palette.setColor(QPalette.ColorRole.Text,QColor("blue"))
        self.widget.setPalette(palette)
        self.widget.currentTextChanged.connect(lambda: self.signalValidityCheck.emit(self))
    def getValue(self):
        return self.widget.currentText() 
    def setValue(self,value):
        return self.widget.setCurrentText(value)

class FormDialog(QMainWindow):
    signalNewOutgoingMessage = pyqtSignal(str,str,bool)
    def __init__(self,pd,form,formid,parent=None):
        super(FormDialog,self).__init__(parent)
        self.pd = pd
        self.formid = formid
        load_ui.loadUi("formdialog.ui",self)
        pm = QPixmap(form+".png")
        # w = pm.width()
        # h = pm.height()
        # fw = self.cForm.width()
        # # find a good integer scale factor
        # s = w//fw
        # pm = pm.scaled(w//2,h//2,Qt.AspectRatioMode.KeepAspectRatioByExpanding,Qt.TransformationMode.SmoothTransformation)
        #self.cform.set
        self.cForm.setPixmap(pm)
        self.scrollArea.setWidget(self.cForm)
        self.headers = []
        self.footers = []
        self.fields = []
        self.fieldid = {}  # a dictionary that maps the field id to the index
        self.fieldname = {}  # a dictionary that maps the field name to the index
        section = 0 # 1 = headers, 2 = footers, 3 = fields, 4 = dependencies
        try:
            with open(form+".desc","rt") as file:
                while l := file.readline():
                        l = l.rstrip()
                        if len(l) < 2: continue
                        if l[0:2] == '//': continue
                        if l == "[Headers]":
                            section = 1
                            continue
                        elif l == "[Footers]":
                            section = 2
                            continue
                        elif l == "[Fields]":
                            section = 3
                            continue
                        elif l == "[Dependencies]":
                            section = 4
                            continue
                        if section == 1:
                            self.headers.append(l)
                        elif section == 2:
                            self.footers.append(l)
                        elif section == 3:
                            f = l.split(",")
                            # typical line: 12.,Message,mstr,Y,valid,52,105,807,677
                            # fields:       0   1       2    3 4     5  6   7   8
                            if len(f) >= 9:
                                index = len(self.fields)
                                if f[0] and f[0][0] == '*':
                                    self.subjectlinesource = f[1]
                                    f[0] = f[0][1:]
                                if f[2] == "str":
                                    self.fields.append(FormItemString(self.cForm,f))
                                elif f[2] == "mstr":
                                    self.fields.append(FormItemMultiString(self.cForm,f))
                                elif f[2] == "rb":
                                    self.fields.append(FormItemRadioButtons(self.cForm,f))
                                elif f[2] == "cb":
                                    self.fields.append(FormItemCheckBox(self.cForm,f))
                                elif f[2] == "dd":
                                    self.fields.append(FormItemDropDown(self.cForm,f))
                                if len(self.fields) > index: #something was added, add to dictionaries
                                    self.fieldid[f[0]] = index
                                    self.fieldname[f[1]] = index
                                    self.fields[index].signalValidityCheck.connect(self.updateSingle)

                        elif section == 4:
                            pass
        except FileNotFoundError:
            pass 
        subject = self.pd.makeStandardSubject()
        self.setFieldByName("MessageNumber",subject)
        #self.setFieldByName("Handling","PRIORITY") #test
        # special handing for this non-conforming form
        if self.formid == "CheckInCheckOut":
            self.setFieldByName("UserCall",self.pd.getActiveUserCallSign())
            self.setFieldByName("UserName",self.pd.getUserCallSign("Name"))
            self.setFieldByName("TacticalCall",self.pd.getActiveTacticalCallSign())
            self.setFieldByName("TacticalName",self.pd.getTacticalCallSign("Name"))
            self.setFieldByName("UseTacticalCall",self.pd.getProfileBool("UseTacticalCallSign"))
        else:
            d = datetime.datetime.now()
            self.setFieldByName("Date","{:%m/%d/%Y}".format(d))
            self.setFieldByName("Time","{:%H:%M}".format(d))
            self.setFieldByName("OpDate","{:%m/%d/%Y}".format(d))
            self.setFieldByName("OpTime","{:%H:%M}".format(d))
            self.setFieldByName("OpName",self.pd.getActiveCallSignName())
            self.setFieldByName("OpCall",self.pd.getActiveCallSign())

        self.cSend.clicked.connect(self.onSend)
        self.updateAll()

    @staticmethod
    def DateValid(s):
        try:
            datetime.datetime.strptime(s,"%m/%d/%Y")
            return True
        except ValueError:
            return False         
    
    @staticmethod
    def TimeValid(s):
        try:
            datetime.datetime.strptime(s,"%H:%M")
            return True
        except ValueError:
            return False         

    @staticmethod
    def TelValid(s):
        # simple test, must be 7 or 10 digits, 0, 1, or 2 "-" but np other characters
        nd = 0
        nh = 0
        for c in s:
            if c.isdigit():
                nd += 1
            elif c == "-":
                nh += 1;
            else:
                return False
        return True if  nd == 7 or nd == 10 and nh <= 2 else False

    @staticmethod
    def NumValid(s):
        if not s or s.startswith("0"): return False
        return s.isdigit()

    def updateSingle(self,f):
        if (f.valid):
            v = f.getValue().lstrip().rstrip()
            if f.validator and hasattr(self,f.validator):
                func = getattr(self,f.validator)
                if callable(func):
                    v = func(v)  # v is now a bool but that is all we need
            if v:
                f.valid.hide()
            else:
                f.valid.show()

    def updateAll(self):
        for f in self.fields:
            self.updateSingle(f)

    # this gets called when reading an existing form
    def setData(self,h,m):
        # we need to process the messaage
        lines = m.splitlines()
        for line in lines:
            id,tmp,r = line.partition(":")
            r = r.lstrip()
            if not r or r[0] != '[' or r[-1] != ']': continue
            self.setFieldById(id,r[1:-1])

    def setFieldById(self,fname,value):
        if fname in self.fieldid:
            self.fields[self.fieldid[fname]].setValue(value)
    def getFieldById(self,fname):
        if fname in self.fieldid:
            return self.fields[self.fieldid[fname]].getValue()
        else:
            return ""
    def setFieldByName(self,fname,value):
        if fname in self.fieldname:
            self.fields[self.fieldname[fname]].setValue(value)
    def getFieldByName(self,fname):
        if fname in self.fieldname:
            return self.fields[self.fieldname[fname]].getValue()
        else:
            return ""
        
    def onSend(self):
        # checkincheckout is comepletely different than any other
        if self.formid == "CheckInCheckOut":
            handling = "R"
            line1 = self.getFieldByName("Type") + " "
            line2 = ""
            usetactical = True if self.getFieldByName("UseTacticalCall") else False
            if usetactical:
                line1 += self.getFieldByName("TacticalCall") + ",  " + self.getFieldByName("TacticalName")
                line2 = self.getFieldByName("UserCall") + " , " + self.getFieldByName("UserName")
                message = line1 + "\n" + line2 + "\n"
            else:
                line1 += self.getFieldByName("UserCall") + " , " + self.getFieldByName("UserName")
                message = line1 + "\n"

            subject = self.getFieldByName("MessageNumber") + "_" + handling[0] + "_" + line1
        else:
            message = ""
            for h in self.headers:
                message += h + "\n"
            for f in self.fields:
                v = f.getValue()
                if v:
                    message += f"{f.label}: [{v}]\n"
            for f in self.footers:
                message += f + "\n"
            handling = self.getFieldByName("Handling")
            if not handling: handling = "?"
            subject = self.getFieldByName("MessageNumber") + "_" + handling[0] + "_" + self.formid + "_" + self.getFieldByName(self.subjectlinesource) 
        self.signalNewOutgoingMessage.emit(subject,message,handling[0] == 'I')
        self.close()

        

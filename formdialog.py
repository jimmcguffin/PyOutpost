import sys
from PyQt6 import QtWidgets
from PyQt6 import QtCore
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QMainWindow, QLineEdit, QWidget, QPlainTextEdit, QCheckBox, QRadioButton, QButtonGroup, QComboBox
from PyQt6.QtGui import QPixmap, QPalette, QColor, QFont
from PyQt6.uic import load_ui
from persistentdata import PersistentData
from mailfolder import MailBoxHeader
import datetime

class FormItem():
    def __init__(self,parent,f):
        self.parent = parent
        self.widget = QWidget()
        self.label = f[0]
        self.fieldname = f[1]
    def getValue(self): pass

class FormItemString(FormItem):
    def __init__(self,parent,f):
        super().__init__(parent,f)
        self.widget = QLineEdit("",parent) # or f[1]
        x0 = int(f[3])
        y0 = int(f[4])
        x1 = int(f[5])
        y1 = int(f[6])
        self.widget.setGeometry(x0,y0,x1-x0+1,y1-y0+1)
        font = QFont()
        #font =  self.cMailList.item(i,0).font()
        font.setBold(True)
        self.widget.setFont(font)
        palette = self.widget.palette()
        palette.setColor(QPalette.ColorRole.Text,QColor("blue"))
        self.widget.setPalette(palette)
    def getValue(self):
        return self.widget.text()
    def setValue(self,value):
        return self.widget.setText(value)

class FormItemMultiString(FormItem):
    def __init__(self,parent,f):
        super().__init__(parent,f)
        self.widget = QPlainTextEdit(parent)
        x0 = int(f[3])
        y0 = int(f[4])
        x1 = int(f[5])
        y1 = int(f[6])
        self.widget.setGeometry(x0,y0,x1-x0+1,y1-y0+1)
        self.widget.setPlainText("") # or f[1]
        font = QFont()
        font.setBold(True)
        self.widget.setFont(font)
        palette = self.widget.palette()
        palette.setColor(QPalette.ColorRole.Text,QColor("blue"))
        self.widget.setPalette(palette)
    def getValue(self):
        return self.widget.toPlainText()
    def setValue(self,value):
        return self.widget.setText(value)

class FormItemRadioButtons(FormItem): # always multiple buttons
    def __init__(self,parent,f):
        super().__init__(parent,f)
        nb = (len(f)-7)//5
        self.widget = QButtonGroup(parent)
        self.values = []
        for i in range (nb):
            j = i*5+7
            tmpwidget = QRadioButton(parent)
            x0 = int(f[j+1])
            y0 = int(f[j+2])
            x1 = int(f[j+3])
            y1 = int(f[j+4])
            if x1 == 0: x1 = x0 +14
            if y1 == 0: y1 = y0 +14
            tmpwidget.setGeometry(x0,y0,x1-x0+1,y1-y0+1)
            self.widget.addButton(tmpwidget,i)
            palette = tmpwidget.palette()
            palette.setColor(QPalette.ColorRole.Text,QColor("blue"))
            tmpwidget.setPalette(palette)
            self.values.append(f[j])
    def getValue(self):
        index = self.widget.checkedId()
        if index < 0: return ""
        return self.values[index]
    def setValue(self,value):
        for i in range(len(self.values)):
            if self.values[i] == value:
                self.widget.button(i).setChecked(True)

class FormItemCheckBox(FormItem):
    def __init__(self,parent,f):
        super().__init__(parent,f)
        self.widget = QCheckBox("",parent) # or f[1]
        x0 = int(f[3])
        y0 = int(f[4])
        x1 = int(f[5])
        y1 = int(f[6])
        if x1 == 0: x1 = x0 +14
        if y1 == 0: y1 = y0 +14
        self.widget.setGeometry(x0,y0,x1-x0+1,y1-y0+1)
        palette = self.widget.palette()
        palette.setColor(QPalette.ColorRole.Text,QColor("blue"))
        self.widget.setPalette(palette)
    def getValue(self):
        return self.widget.text()
    def setValue(self,value):
        return self.widget.setText(value)

class FormItemDropDown(FormItem):
    def __init__(self,parent,f):
        super().__init__(parent,f)
        self.widget = QComboBox(parent) # or f[1]
        x0 = int(f[3])
        y0 = int(f[4])
        x1 = int(f[5])
        y1 = int(f[6])
        self.widget.setGeometry(x0,y0,x1-x0+1,y1-y0+1)
        n = len(f)-7
        for i in range(n):
            self.widget.addItem(f[i+7])
        self.widget.setEditable(True)
        palette = self.widget.palette()
        palette.setColor(QPalette.ColorRole.Text,QColor("blue"))
        self.widget.setPalette(palette)
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
                            # typical line: 12.,Message,mstr,52,105,807,677
                            # fields:       0   1       2    3  4   5   6
                            if len(f) >= 7:
                                index = len(self.fields)
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

                        elif section == 4:
                            pass
        except FileNotFoundError:
            pass 
        subject = ""
        if self.pd.getProfileBool("MessageSettings/AddMessageNumber"):
            subject += self.pd.getUserCallSign("MessagePrefix")
        f = self.pd.getProfile("MessageSettings/Hyphenation_flag")
        if f == "0":
            subject += str(self.pd.getAndIncrementNextMessageNumber())
        elif f == "1":
            subject += "-"+str(self.pd.getAndIncrementNextMessageNumber())
        elif f == "2":
            dt = QDateTime.currentDateTime()
            subject += dt.toString("yyMMddHHmmss")
        if self.pd.getProfileBool("MessageSettings/AddCharacter"):
            subject += self.pd.getProfile("MessageSettings/CharacterToAdd")
        if self.pd.getProfileBool("MessageSettings/AddMessageNumberSeparator"):
            subject += ":"
        self.setFieldByName("MessageNumber",subject)
        #self.setFieldByName("Handling","PRIORITY") #test
        d = datetime.datetime.now()
        self.setFieldByName("Date","{:%m/%d/%Y}".format(d))
        self.setFieldByName("Time","{:%H:%M}".format(d))
        self.setFieldByName("OpDate","{:%m/%d/%Y}".format(d))
        self.setFieldByName("OpTime","{:%H:%M}".format(d))
        self.setFieldByName("OpName",self.pd.getActiveCallSignName())
        self.setFieldByName("OpCall",self.pd.getActiveCallSign())

        self.cSend.clicked.connect(self.onSend)
    
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
        # subject comes from different places sometimes
        subjectfieldname = "Subject"
        if self.formid == "DmgAsmt": subjectfieldname = "Address"
        subject = self.getFieldByName("MessageNumber") + "_" + handling[0] + "_" + self.formid + "_" + self.getFieldByName(subjectfieldname) 
        self.signalNewOutgoingMessage.emit(subject,message,handling[0] == 'I')
        self.close()

        

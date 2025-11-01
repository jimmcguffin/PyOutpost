import sys
from PyQt6 import QtWidgets
from PyQt6 import QtCore
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QMainWindow, QLineEdit, QWidget, QPlainTextEdit, QCheckBox, QRadioButton, QButtonGroup
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
        nb = (len(f)-3)//5
        self.widget = QButtonGroup(parent)
        self.values = []
        for i in range (nb):
            tmpwidget = QRadioButton(parent)
            x0 = int(f[i*5+4])
            y0 = int(f[i*5+5])
            x1 = int(f[i*5+6])
            y1 = int(f[i*5+7])
            tmpwidget.setGeometry(x0,y0,x1-x0+1,y1-y0+1)
            self.widget.addButton(tmpwidget,i)
            # font = QFont()
            # font.setBold(True)
            # self.widget.setFont(font)
            palette = tmpwidget.palette()
            palette.setColor(QPalette.ColorRole.Text,QColor("blue"))
            tmpwidget.setPalette(palette)
            self.values.append(f[i*5+3])
    def getValue(self):
        index = self.widget.checkedId()
        if index < 0: return ""
        return self.values[index]
    def setValue(self,value):
        for i in range(len(self.values)):
            if self.values[i] == value:
                self.widget.button(i).setChecked(True)

class FormDialog(QMainWindow):
    signalNewOutgoingMessage = pyqtSignal(str,str,bool)
    def __init__(self,pd,form,parent=None):
        super(FormDialog,self).__init__(parent)
        self.pd = pd
        self.formid = "ICS213"
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
        self.field = {}
        section = 0 # 1 = headers, 2 = footers, 3 = fields
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
                        if section == 1:
                            self.headers.append(l)
                        elif section == 2:
                            self.footers.append(l)
                        elif section == 3:
                            f = l.split(",")
                            # typical line: 12.,Message,mstr,52,105,807,677
                            # fields:       0   1       2    3  4   5   6
                            if len(f) >= 7:
                                if f[2] == "str":
                                    # add to dictionary
                                    self.field[f[1]] = len(self.fields)
                                    self.fields.append(FormItemString(self.cForm,f))
                                elif f[2] == "mstr":
                                    # add to dictionary
                                    self.field[f[1]] = len(self.fields)
                                    self.fields.append(FormItemMultiString(self.cForm,f))
                                elif f[2] == "rb":
                                    # add to dictionary
                                    self.field[f[1]] = len(self.fields)
                                    self.fields.append(FormItemRadioButtons(self.cForm,f))
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
        self.setField("MessageNumber",subject)
        #self.setField("Handling","PRIORITY") #test
        d = datetime.datetime.now()
        self.setField("Date","{:%m/%d/%Y}".format(d))
        self.setField("Time","{:%H:%M}".format(d))
        self.setField("OpDate","{:%m/%d/%Y}".format(d))
        self.setField("OpTime","{:%H:%M}".format(d))
        self.setField("OpName",self.pd.getActiveCallSignName())
        self.setField("OpCall",self.pd.getActiveCallSign())

        self.cSend.clicked.connect(self.onSend)

    def setField(self,fname,value):
        # for i in range(len(self.fields)):
        #     if self.fields[i].fieldname == fname:
        #         self.fields[i].setValue(value)
        if fname in self.field:
            self.fields[self.field[fname]].setValue(value)
    def getField(self,fname):
        if fname in self.field:
            return self.fields[self.field[fname]].getValue()
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
        # mbh = MailBoxHeader()
        # #mbh.mUrgent = "Y" if self.cUrgent.isChecked() else "N"
        # handling = self.getField("Handling")
        # #mbh.mFrom = self.cFrom.text()
        # #mbh.mTo = self.cTo.text()
        # #mbh.mBbs = self.cBBS.text()
        # #mbh.mLocalId = ""
        # mbh.mSubject = self.getField("MsgNo") + "_" + handling[0] + "_" + self.formid + self.getField("Subject") 
        # mbh.mDateSent = MailBoxHeader.normalizedDate()
        # #mbh.mDateReceived = "" # in ISO-8601 format
        # mbh.mSize = len(message)
        handling = self.getField("Handling")
        if not handling: handling = "?"
        subject = self.getField("MessageNumber") + "_" + handling[0] + "_" + self.formid + "_" + self.getField("Subject") 
        self.signalNewOutgoingMessage.emit(subject,message,handling[0] == 'I')
        self.close()

        

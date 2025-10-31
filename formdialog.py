import sys
from PyQt6 import QtWidgets
from PyQt6 import QtCore
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QMainWindow, QLineEdit, QWidget, QPlainTextEdit, QCheckBox, QRadioButton
from PyQt6.QtGui import QPixmap, QPalette, QColor, QFont
from PyQt6.uic import load_ui
from persistentdata import PersistentData
from mailfolder import MailBoxHeader


class FormItem():
    def __init__(self,parent,f):
        self.parent = parent
        self.widget = QWidget()
        self.label = f[0]
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

class FormDialog(QMainWindow):
    signalNewOutgoingMessage = pyqtSignal(MailBoxHeader,str)
    def __init__(self,pd,form,parent=None):
        super(FormDialog,self).__init__(parent)
        self.pd = pd
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
        self.fields = []
        try:
            with open(form+".desc","rb") as file:
                # the first 3 lines are part of the outgoing mail
                self.l1 = file.readline()
                self.l2 = file.readline()
                self.l3 = file.readline()
                while l := file.readline().decode():
                        f = l.split(",")
                        # typical line: 12.,Message,mstr,52,105,807,677
                        # fields:       0   1       2    3  4   5   6
                        if len(f) >= 7:
                            if f[2] == "str":
                                 self.fields.append(FormItemString(self.cForm,f))
                            elif f[2] == "mstr":
                                 self.fields.append(FormItemMultiString(self.cForm,f))
                            else:
                                 pass
                        else:
                           pass
        except FileNotFoundError:
            pass 
        self.cSend.clicked.connect(self.onSend)
    def onSend(self):
        print(self.l1)
        print(self.l2)
        print(self.l3)
        for f in self.fields:
            v = f.getValue()
            if v:
                print(f"{f.label}: [{v}]")


        

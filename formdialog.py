import datetime
import re
import sys

from PyQt6.QtCore import Qt, pyqtSignal, QObject, QRect, QPoint
from PyQt6.QtWidgets import QMainWindow, QLineEdit, QWidget, QPlainTextEdit, QCheckBox, QRadioButton, QButtonGroup, QComboBox, QFrame
from PyQt6.QtGui import QPixmap, QPalette, QColor, QFont, QPainter
from PyQt6.uic import load_ui

from globalsignals import global_signals
from persistentdata import PersistentData

class FormItem(QObject):
    def __init__(self,parent,f,dw=0,dh=0):
        super().__init__(parent)
        self.parent = parent
        self.widget = QWidget(parent)
        self.label = f[0]
        self.fieldname = f[1]
        self.valid = None
        self.validator = ""
        self.dependson = ""
        if len(f[3]) and f[3] != "Y":
            self.dependson = f[3]
        self.subjectlinesource = "Subject"
        self.group = -1 # gets set if part of a group
        if len(f[3]) and f[5] != "0":
        #if f[5] != "0": # this shows all of boxes that have been defined
            self.valid = QFrame(parent)
            # expand the coordinates a litle
            e = 4
            x0,y0,x1,y1 = FormItem.get_coordinates(f[5:9],dw,dh)
            x0 -= e
            y0 -= e
            x1 += e
            y1 += e
            self.valid.setGeometry(x0,y0,x1-x0+1,y1-y0+1)
            self.valid.setStyleSheet("QFrame { border: 6px solid #C02020;}")
            self.valid.setFrameStyle(QFrame.Shape.Box|QFrame.Shadow.Plain)
            self.valid.hide()
            self.validator = f[4] # possibly a custom validator

    def get_value(self): pass

    @staticmethod
    def get_coordinates(f:list,dw=0,dh=0):
        x0 = int(f[0])
        y0 = int(f[1])
        if f[2][0] == "+":
            x1 = x0 + int(f[2])
        else:
            x1 = int(f[2])
            if not x1:
                x1 = x0 + dw
        if f[3][0] == "+":
            y1 = y0 + int(f[3])
        else:
            y1 = int(f[3])
            if not y1:
                y1 = y0 + dh
        return (x0,y0,x1,y1)

class FormItemString(FormItem):
    signalValidityCheck = pyqtSignal(FormItem)
    def __init__(self,parent,f):
        dw = 0 # default sizees
        dh = 26
        super().__init__(parent,f,dw,dh)
        self.widget = QLineEdit("",parent) # or f[1]
        x0,y0,x1,y1 = FormItem.get_coordinates(f[5:9],dw,dh)
        self.widget.setGeometry(x0,y0,x1-x0+1,y1-y0+1)
        font = QFont()
        #font =  self.cMailList.item(i,0).font()
        font.setBold(True)
        self.widget.setFont(font)
        palette = self.widget.palette()
        palette.setColor(QPalette.ColorRole.Text,QColor("blue"))
        self.widget.setPalette(palette)
        self.widget.textChanged.connect(lambda: self.signalValidityCheck.emit(self))
    def get_value(self):
        return self.widget.text()
    def setValue(self,value):
        return self.widget.setText(value)

class FormItemMultiString(FormItem):
    signalValidityCheck = pyqtSignal(FormItem)
    def __init__(self,parent,f):
        super().__init__(parent,f)
        self.widget = QPlainTextEdit(parent)
        x0,y0,x1,y1 = FormItem.get_coordinates(f[5:9])
        self.widget.setGeometry(x0,y0,x1-x0+1,y1-y0+1)
        self.widget.setPlainText("") # or f[1]
        font = QFont()
        font.setBold(True)
        self.widget.setFont(font)
        palette = self.widget.palette()
        palette.setColor(QPalette.ColorRole.Text,QColor("blue"))
        self.widget.setPalette(palette)
        self.widget.textChanged.connect(lambda: self.signalValidityCheck.emit(self))
    def get_value(self):
        return self.widget.toPlainText().replace("]","`]").replace("\n","\\n")
    def setValue(self,value):
        return self.widget.setPlainText(value.replace("`]","]").replace("\\n","\n"))

class FormItemRadioButtons(FormItem): # always multiple buttons
    signalValidityCheck = pyqtSignal(FormItem)
    def __init__(self,parent,f):
        dw = 64 # default size
        dh = 14
        super().__init__(parent,f,dw,dh)
        nb = (len(f)-9)//5
        self.widget = QButtonGroup(parent)
        self.values = []
        for i in range (nb):
            j = i*5+9
            tmpwidget = QRadioButton("                ",parent)
            x0,y0,x1,y1 = FormItem.get_coordinates(f[j+1:j+5],dw,dh)
            tmpwidget.setGeometry(x0,y0,x1-x0+1,y1-y0+1)
            self.widget.addButton(tmpwidget,i)
            palette = tmpwidget.palette()
            palette.setColor(QPalette.ColorRole.Text,QColor("blue"))
            tmpwidget.setPalette(palette)
            self.values.append(f[j])
        self.widget.idClicked.connect(lambda: self.signalValidityCheck.emit(self))
    def get_value(self):
        index = self.widget.checkedId()
        if index < 0: return ""
        return self.values[index]
    def setValue(self,value):
        for i, v in enumerate(self.values):
            if v == value:
                self.widget.button(i).setChecked(True)

class FormItemCheckBox(FormItem):
    signalValidityCheck = pyqtSignal(FormItem)
    def __init__(self,parent,f):
        dw = 64 # default size
        dh = 14
        super().__init__(parent,f,dw,dh)
        self.widget = QCheckBox("                ",parent) # or f[1]
        x0,y0,x1,y1 = FormItem.get_coordinates(f[5:9],dw,dh)
        self.widget.setGeometry(x0,y0,x1-x0+1,y1-y0+1)
        palette = self.widget.palette()
        palette.setColor(QPalette.ColorRole.Text,QColor("blue"))
        self.widget.setPalette(palette)
        self.widget.clicked.connect(lambda: self.signalValidityCheck.emit(self))
    def get_value(self):
        return "checked" if self.widget.isChecked() else ""
    def setValue(self,value):
        return self.widget.setChecked(value)

class FormItemDropDown(FormItem):
    signalValidityCheck = pyqtSignal(FormItem)
    def __init__(self,parent,f):
        dw = 0 # default size
        dh = 26
        super().__init__(parent,f)
        self.widget = QComboBox(parent) # or f[1]
        x0,y0,x1,y1 = FormItem.get_coordinates(f[5:9],dw,dh)
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
    def get_value(self):
        return self.widget.currentText()
    def setValue(self,value):
        return self.widget.setCurrentText(value)

class FormItemRequiredGroup(FormItem):
    signalValidityCheck = pyqtSignal(FormItem)
    def __init__(self,parent,f):
        super().__init__(parent,f)
        nc = (len(f)-9)
        self.children = []
        for i in range (nc):
            self.children.append(f[i+9])
        pass
    def get_value(self,dialog):
        for c in self.children:
            v = dialog.get_value_by_field_id(c)
            if v:
                return True
        return False
    def setValue(self,value):
        pass


class FormDialog(QMainWindow):
    def __init__(self,pd,form,formid,parent=None):
        super().__init__(parent)
        self.pd = pd
        self.form = form # the name of the desc and png files
        self.formid = formid # a short item used in the subject line
        self.to_addr = "" # this get used when redoing a form
        load_ui.loadUi("formdialog.ui",self)
        self.pages = []
        self.headers = []
        self.footers = []
        self.fields = [] # a list of FormItem objects
        self.fieldid = {}  # a dictionary that maps the field id to the index
        self.fieldname = {}  # a dictionary that maps the field name to the index
        #self.group = {}  # a dictionary that maps the field id to a container group, if there is one (rare)
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
                    elif l == "[Pages]":
                        section = 3
                        continue
                    elif l == "[Fields]":
                        section = 4
                        continue
                    elif l == "[Dependencies]": # this never happened
                        section = 5
                        continue
                    if section == 1:
                        self.headers.append(l)
                    elif section == 2:
                        self.footers.append(l)
                    elif section == 3:
                        # format is filename[startline:endline], with the brackets stuff optional
                        b = l.find("[")
                        if b > 0:
                            m = re.match(r"([^[]+)\[(\d*):(\d*)\]",l)
                            if m:
                                l0 = int(m.group(2))
                                l1 = int(m.group(3))
                                nl = (l1-l0)+1
                                self.pages.append((m.group(1),l0,nl)) # specific lines
                        else:
                            self.pages.append((l,0,1100)) # all lines
                    elif section == 4:
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
                            elif f[2] == "rg":
                                self.fields.append(FormItemRequiredGroup(self.cForm,f))
                            if len(self.fields) > index: #something was added, add to dictionaries
                                if f[0]:
                                    self.fieldid[f[0]] = index
                                if f[1]:
                                    self.fieldname[f[1]] = index
                                self.fields[index].signalValidityCheck.connect(self.updateSingle)

                    elif section == 5:
                        pass
        except FileNotFoundError:
            pass

        # if there were no pages specified, use default
        if not self.pages:
            self.pages.append((self.form+".png",0,1100))
        self.make_composite_picture()

        # set up any groups
        for index, f in enumerate(self.fields):
            if isinstance(f,FormItemRequiredGroup):
                for c in f.children:
                    p = self.get_item_by_field_id(c)
                    if p:
                        p.group = index
        subject = self.pd.make_standard_subject()
        self.set_value_by_field_name("MessageNumber",subject)
        #self.setFieldByName("Handling","PRIORITY") #test
        # special handing for this non-conforming form
        if self.form == "CheckInCheckOut":
            self.set_value_by_field_name("UserCall",self.pd.getActiveUserCallSign())
            self.set_value_by_field_name("UserName",self.pd.getUserCallSign("Name"))
            self.set_value_by_field_name("TacticalCall",self.pd.getActiveTacticalCallSign())
            self.set_value_by_field_name("TacticalName",self.pd.getTacticalCallSign("Name"))
            self.set_value_by_field_name("UseTacticalCall",self.pd.getProfileBool("UseTacticalCallSign"))
        else:
            d = datetime.datetime.now()
            self.set_value_by_field_name("Date","{:%m/%d/%Y}".format(d))
            self.set_value_by_field_name("Time","{:%H:%M}".format(d))
            self.set_value_by_field_name("OpDate","{:%m/%d/%Y}".format(d)) # these will get overwritten
            self.set_value_by_field_name("OpTime","{:%H:%M}".format(d))
            self.set_value_by_field_name("OpCall",self.pd.getActiveUserCallSign())
            self.set_value_by_field_name("OpName",self.pd.getUserCallSign("Name"))
            self.set_value_by_field_name("Method","Other")
            self.set_value_by_field_name("Other","Packet")
           


        self.cSend.clicked.connect(self.onSend)
        self.updateAll()

    def resizeEvent(self,event):
        self.scrollArea.resize(event.size().width()-24,event.size().height()-56)
        return super().resizeEvent(event)
    
    def make_composite_picture(self):
        h = 0
        # pages is a tuple (filename,startline,numlines)
        for page in self.pages:
            h += page[2]
        pm = QPixmap(850,h) # all pages *should* be 850x1100
        painter = QPainter(pm)
        h = 0
        for page in self.pages:
            pm2 = QPixmap(page[0])
            painter.drawPixmap(QPoint(0,h),pm2,QRect(0,page[1],850,page[2]))
            h += page[2]
        painter.end()
        h = pm.height()
        w = pm.width()
        self.cForm.setPixmap(pm)
        self.scrollArea.setWidget(self.cForm)

    def screen_to_page(y): # returns 0 for first page, 1 for second page, etc
        p = 0
        sumofpages = 0
        for page in pages:
            sumofpages += page[2]
        if y < 0 or y >= sumofpages:
            return (-1,0)
        for page in pages:
            if y < page[2]:
                return (p,y+page[1])
            p += 1
            y -= page[2]
        assert(False)
        return (p,y+page[1])

    def page_to_screen(pageindex,line) -> int: # returns -1 if not on any page
        line_offset = 0
        if 0 <= pageindex < len(pages):
            for p,page in enumerate(pages):
                if p == pageindex:
                    if line < page[1]:
                        return -1
                    line -= page[1]
                    if line >= page[2]:
                        return -1
                    return line + line_offset
                line_offset += page[2]
                #line -= page[2]
        else:
            return -1

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
        # simple test, must be 7 or 10 digits, 0, 1, or 2 hyphens or spaces but no other characters
        nd = 0
        ns = 0
        for c in s:
            if c.isdigit():
                nd += 1
            elif c == "-" or c == " ":
                ns += 1;
            else:
                return False
        return True if  nd == 7 or nd == 10 and ns <= 2 else False

    @staticmethod
    def NumValid(s):
        if not s or s.startswith("0"): return False
        return s.isdigit()

    @staticmethod
    def ZipValid(s):
        return s and len(s) == 5 and s.isdigit()

    # if any item gets changed, we get here
    def updateSingle(self,f:FormItem):
        if (f.valid):
            # the next block of code decides if the data is valid
            # if it is, the frame will be hidden,
            # otherwise it will be shown, indicating that a valid entry is required
            # v changes types as it goes through the code but True/non-zero/non-empty string all mean "Valid"
            if isinstance(f,FormItemRequiredGroup):
                # these need additional help
                v = f.get_value(self)
            else:
                v = f.get_value().lstrip().rstrip()
            if f.validator and hasattr(self,f.validator):
                func = getattr(self,f.validator)
                if callable(func):
                    v = func(v)  # v is now a bool but that is all we need
            if not v and f.dependson:
                tmp = self.get_item_by_field_id(f.dependson)
                if (tmp):
                    tmpv = tmp.get_value()
                    if tmpv == "No":
                        tmpv = ""
                    v = not tmpv# add other non-values
            if v:
                f.valid.hide()
            else:
                f.valid.show()
        if f.group >= 0:
            self.updateSingle(self.fields[f.group])
        # even though this item is not required there might be something that depends on it
        for field in self.fields:
            if field.dependson == f.label:
                self.updateSingle(field)
        

    def updateAll(self):
        for f in self.fields:
            self.updateSingle(f)

    # this gets called when reading an existing form
    def prepopulate(self,h,m):
        self.to_addr = h.to_addr
        # we need to process the message, including multiline items
        lines = m.splitlines()
        value = ""
        for line in lines:
            if value: # we are in the middle of a multi-line item
                value += line
                if value[-1] != ']':
                    continue
                self.set_value_by_field_id(id,value[1:-1])
                value = ""
                continue
            id,_,r = line.partition(":")
            value = r.lstrip()
            if not value or value[0] != '[':
                continue
            if value[-1] == ']': 
                self.set_value_by_field_id(id,value[1:-1])
                value = ""

    def get_item_by_field_id(self,fname) -> FormItem:
        if fname in self.fieldid:
            return self.fields[self.fieldid[fname]]
        return None

    def get_item_by_field_name(self,fname) -> FormItem:
        if fname in self.fieldid:
            return self.fields[self.fieldname[fname]]
        return None

    def set_value_by_field_id(self,fname,value):
        if fname in self.fieldid:
            self.fields[self.fieldid[fname]].setValue(value)
    def get_value_by_field_id(self,fname):
        if fname in self.fieldid:
            return self.fields[self.fieldid[fname]].get_value()
        return ""
    def set_value_by_field_name(self,fname,value):
        if fname in self.fieldname:
            self.fields[self.fieldname[fname]].setValue(value)
    def get_value_by_field_name(self,fname):
        if fname in self.fieldname:
            return self.fields[self.fieldname[fname]].get_value()
        return ""
        
    def onSend(self):
        # checkincheckout is comepletely different than any other
        if self.form == "CheckInCheckOut":
            handling = "R"
            line1 = self.get_value_by_field_name("Type") + " "
            line2 = ""
            usetactical = True if self.get_value_by_field_name("UseTacticalCall") else False
            if usetactical:
                line1 += self.get_value_by_field_name("TacticalCall") + ",  " + self.get_value_by_field_name("TacticalName")
                line2 = self.get_value_by_field_name("UserCall") + " , " + self.get_value_by_field_name("UserName")
                message = line1 + "\n" + line2 + "\n"
            else:
                line1 += self.get_value_by_field_name("UserCall") + " , " + self.get_value_by_field_name("UserName")
                message = line1 + "\n"

            subject = self.get_value_by_field_name("MessageNumber") + "_" + handling[0] + "_" + line1
        else:
            message = ""
            for h in self.headers:
                message += h + "\n"
            for f in self.fields:
                if not isinstance(f,FormItemRequiredGroup):
                    v = f.get_value()
                    if v:
                        message += f"{f.label}: [{v}]\n"
            for f in self.footers:
                message += f + "\n"
            handling = self.get_value_by_field_name("Handling")
            if not handling: handling = "?"
            subject = self.get_value_by_field_name("MessageNumber") + "_" + handling[0] + "_" + self.formid + "_" + self.get_value_by_field_name(self.subjectlinesource) 
        global_signals.signal_new_outgoing_form_message.emit(subject,message,handling[0] == 'I',self.to_addr)
        self.close()

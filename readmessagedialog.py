import sys
from PyQt6 import QtWidgets
from PyQt6.QtCore import QDateTime, pyqtSignal
from PyQt6.QtWidgets import QMainWindow
from PyQt6.uic import load_ui
from persistentdata import PersistentData
from sql_mailbox import MailBoxHeader

class ReadMessageDialog(QMainWindow):
    def __init__(self,pd,parent=None):
        super().__init__(parent)
        self.pd = pd
        load_ui.loadUi("readmessagedialog.ui",self)

    def prepopulate(self,h,m):
        self.c_bbs.setText(h.bbs)
        self.c_from.setText(h.from_addr)
        self.c_to.setText(h.to_addr)
        self.c_subject.setText(h.subject)
        self.c_received.setText(MailBoxHeader.to_outpost_date(h.date_received))
        self.c_sent.setText(MailBoxHeader.to_outpost_date(h.date_sent))
        self.c_local_id.setText(h.local_id)
        self.c_message_body.setPlainText(m)

    def resizeEvent(self,event):
        self.c_message_body.resize(event.size().width()-20,event.size().height()-120)
        # these are a binch of attempts to fix up the scrollbars after a size change, none of them worked
        # self.c_message_body.document().adjustSize()
        # self.c_message_body.viewport().update()
        # self.c_message_body.updateGeometry()
        return super().resizeEvent(event)
    

from PyQt6.QtCore import QObject, pyqtSignal
from mailbox import MailBoxHeader

class GlobalSignals(QObject):
    signal_new_incoming_message = pyqtSignal(MailBoxHeader,str)
    signal_new_outgoing_text_message = pyqtSignal(MailBoxHeader,str)
    signal_new_outgoing_form_message = pyqtSignal(str,str,bool)
    signal_message_sent = pyqtSignal(int) # moves from OutTray to Sent
    signal_status_bar_message = pyqtSignal(str)
    signal_connected = pyqtSignal()
    signal_timeout = pyqtSignal()
    signal_disconnected = pyqtSignal()

global_signals = GlobalSignals()


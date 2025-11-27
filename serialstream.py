# pylint:  disable="line-too-long,missing-function-docstring,multiple-statements,no-name-in-module"

from PyQt6.QtCore import QObject, pyqtSignal, QTimer

# this class reads fom a serial stream looking for "line" ends, which can be any string
# it also looks for asynchronous notifications, like "*** Connected"

class SerialStream(QObject):
    signalLineRead = pyqtSignal(str)
    signalConnected = pyqtSignal()
    signalTimeout = pyqtSignal()
    signalDisconnected = pyqtSignal()
    def __init__(self,serial_port):
        super().__init__()
        self._read_from_file = False
        if not self._read_from_file:
            self.serial_port = serial_port
        self._sdata = bytearray()
        self.bytes_already_searched = 0
        self.line_end = b"cmd:"
        self.include_line_end_in_reply = True
        self._async_connected = b"*** CONNECTED"
        self._async_disconnected = b"*** DISCONNECTED\r\n"
        self._async_error = b"*** retry count exceeded\r\n"
        if self._read_from_file:
            self._log_file = open("s.log","rb")
            self._timer = QTimer(self)
            self._timer.timeout.connect(self.on_timer)
            self._timer.start(4)
        else:
            self.serial_port.readyRead.connect(self.on_serial_port_ready)
            self._log_file = open("serial.log","ab")
            if self._log_file:
                self._log_file.write(b"\r\n--------\r\n")
    def reset(self):
        self.serial_port.close()
        self.serial_port.readyRead.disconnect()
        self._sdata.clear()
    def write(self,s):
        if not (s and s[0] != '\r'):
            pass
        assert(s and s[0] != '\r') # no blank lines
        if not self._read_from_file:
            self.serial_port.write(s.encode("windows-1252"))
            if True:
                if self._log_file:
                    tmp = s
                    #tmp = tmp.replace('\r',"<cr>")
                    #tmp = tmp.replace('\n',"<lf>")
                    #tmp = "{"+tmp+"}"
                    tmp = tmp.replace("\r","\r\n")
                    tmp = tmp.replace("\x03","^c")
                    self._log_file.write(b"\x1b[31m"+tmp.encode("windows-1252")+b"\x1b[0m")
                    self._log_file.flush()
    def on_timer(self): # only used when reading from file
        sdata = self._log_file.read(1)
        self._sdata += sdata
        return self.find_lines()
    def on_serial_port_ready(self): # normal path, uses serial port
        sdata = bytearray(self.serial_port.readAll())
        if self._log_file:
            self._log_file.write(sdata)
            self._log_file.flush()
        self._sdata += sdata
        return self.find_lines()
    def find_lines(self):
        done = False
        while not done:
            if self._async_connected:
                start = max(self.bytes_already_searched-len(self._async_connected)+1,0)
                if (p := self._sdata.find(self._async_connected,start)) >= 0:
                    self.signalConnected.emit()
                    # extract
                    del self._sdata[p:p+len(self._async_connected)]
                    self.bytes_already_searched = min(p,self.bytes_already_searched)
            if self._async_disconnected:
                start = max(self.bytes_already_searched-len(self._async_disconnected)+1,0)
                if (p := self._sdata.find(self._async_disconnected,start)) >= 0:
                    self.signalDisconnected.emit()
                    # extract
                    del self._sdata[p:p+len(self._async_disconnected)]
                    self.bytes_already_searched = min(p,self.bytes_already_searched)
            if self._async_error:
                start = max(self.bytes_already_searched-len(self._async_error)+1,0)
                if (p := self._sdata.find(self._async_error,start)) >= 0:
                    self.signalTimeout.emit()
                    # extract
                    del self._sdata[p:p+len(self._async_error)]
                    self.bytes_already_searched = min(p,self.bytes_already_searched)
            assert(self.line_end)
            start = max(self.bytes_already_searched-len(self.line_end)+1,0)
            if (p := self._sdata.find(self.line_end,start)) >= 0:
                if self.include_line_end_in_reply:
                    self.signalLineRead.emit(self._sdata[0:p+len(self.line_end)].decode("windows-1252"))
                else:
                    self.signalLineRead.emit(self._sdata[0:p].decode("windows-1252"))
                # extract
                del self._sdata[0:p+len(self.line_end)]
                self.bytes_already_searched = 0
            else:
                self.bytes_already_searched = len(self._sdata)
                done = True
        # start = 0
        # end = 0
        # elen = len(self.line_end)
        # i = 0
        # while i < len(self._sdata):
        #     bytesleft = len(self._sdata)-i
        #     if bytesleft >= elen and self._sdata [i:i+elen] == self.line_end:
        #         end = i+elen
        #         if self.include_line_end_in_reply:
        #             self.signalLineRead.emit(self._sdata[start:end].decode("windows-1252"))
        #         else:
        #             self.signalLineRead.emit(self._sdata[start:end-elen].decode("windows-1252"))
        #         start = end
        #         i = start
        #     elif self._async_connected  and bytesleft >= len(self._async_connected) and self._sdata [i:i+len(self._async_connected)] == self._async_connected:
        #         end = i+len(self._async_connected)
        #         self.signalConnected.emit()
        #         start = end
        #         i = start
        #         break # leave any other bytes in the buffer to be process by (possibly) new reader
        #     elif self._async_disconnected and bytesleft >= len(self._async_disconnected) and self._sdata [i:i+len(self._async_disconnected)] == self._async_disconnected:
        #         end = i+len(self._async_disconnected)
        #         self.signalDisconnected.emit()
        #         start = end
        #         break # leave any other bytes in the buffer to be process by (possibly) new reader
        #     elif self._async_error and bytesleft >= len(self._async_error) and self._sdata [i:i+len(self._async_error)] == self._async_error:
        #         end = i+len(self._async_error)
        #         self.signalTimeout.emit()
        #         start = end
        #         i = start
        #         break # leave any other bytes in the buffer to be process by (possibly) new reader
        #     else:
        #         i += 1
        # # we got to the end, remove any bytes that have been processed
        # if start:
        #     if start >= len(self._sdata):
        #         self._sdata.clear()
        #     else:
        #         del self._sdata[0:start] #self.sdata = self.sdata[start:]

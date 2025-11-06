from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtSerialPort import QSerialPort

# this class reads fom a serial stream looking for "line" ends, which can be any string
# it also looks for asynchtonous notification, like "*** Connected"

class SerialStream(QObject):
    signalLineRead = pyqtSignal(str)
    signalConnected = pyqtSignal()
    signalTimeout = pyqtSignal()
    signalDisconnected = pyqtSignal()
    def __init__(self,serialport):
        super(SerialStream,self).__init__()
        self.readfromfile = False
        if not self.readfromfile:
            self.serialPort = serialport
        self.sdata = bytearray()
        self.lineEnd = b"cmd:"
        self.asyncConnected = b"*** CONNECTED"
        self.asyncDisonnected = b"*** DISCONNECTED"
        self.asyncError = b"" #b"*** retry count exceeded"
        if self.readfromfile:
            self.logFile = open("s.log","rb")
            self.timer = QTimer(self)
            self.timer.timeout.connect(self.onTimer)
            self.timer.start(4)
        else:
            self.serialPort.readyRead.connect(self.onSerialPortReady)
            self.logFile = open("serial.log","ab")
            if self.logFile:
                 self.logFile.write(b"\r\n--------\r\n")
    def done(self):
        self.serialport.close()
        self.serialport.readyRead.disconnect()
    def write(self,s):
        if not self.readfromfile:
            self.serialPort.write(s.encode())
            if True:
                if self.logFile: 
                    tmp = s
                    #tmp = tmp.replace('\r',"<cr>")
                    #tmp = tmp.replace('\n',"<lf>")
                    #tmp = "{"+tmp+"}"
                    tmp = tmp.replace("\r","\r\n")
                    self.logFile.write(b"\x1b[31m"+tmp.encode()+b"\x1b[0m")
                    self.logFile.flush()
    def onTimer(self): # only used when reading from file
        sdata = self.logFile.read(1)
        self.sdata += sdata
        return self.findLines()
    def onSerialPortReady(self): # normal path, uses serial port
        sdata = bytearray(self.serialPort.readAll())
        if self.logFile: 
             self.logFile.write(sdata)
             self.logFile.flush()
        self.sdata += sdata
        return self.findLines()
    def findLines(self):
        start = 0
        end = 0
        elen = len(self.lineEnd)
        i = 0
        while i < len(self.sdata):
            bytesleft = len(self.sdata)-i
            if bytesleft >= elen and self.sdata [i:i+elen] == self.lineEnd:
                    end = i+elen
                    self.signalLineRead.emit(self.sdata[start:end].decode())
                    start = end
                    i = start
            elif self.asyncConnected  and bytesleft >= len(self.asyncConnected) and self.sdata [i:i+len(self.asyncConnected)] == self.asyncConnected:
                    end = i+len(self.asyncConnected)
                    self.signalConnected.emit()
                    start = end
                    i = start
                    break # leave any other bytes in the buffer to be process by (possibly) new reader
            elif self.asyncDisonnected and bytesleft >= len(self.asyncDisonnected) and self.sdata [i:i+len(self.asyncDisonnected)] == self.asyncDisonnected:
                    end = i+len(self.asyncDisonnected)
                    self.signalDisconnected.emit()
                    start = end
                    break # leave any other bytes in the buffer to be process by (possibly) new reader
            elif self.asyncError and bytesleft >= len(self.asyncError) and self.sdata [i:i+len(self.asyncError)] == self.asyncError:
                    end = i+len(self.asyncError)
                    self.signalTimeout.emit()
                    start = end
                    i = start
                    break # leave any other bytes in the buffer to be process by (possibly) new reader
            else:
                 i += 1
        # we got to the end, remove any bytes that have been processed
        if start:
             if start >= len(self.sdata):
                   self.sdata.clear()
             else: 
                del self.data[0:start] #self.sdata = self.sdata[start:]

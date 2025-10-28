from PyQt6.QtCore import QObject, pyqtSignal
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
        self.serialPort = serialport
        self.serialPort.readyRead.connect(self.onSerialPortReady)
        self.sdata = ""
        self.lineEnd = "cmd:"
        self.asyncConnected = "*** CONNECTED"
        self.asyncDisonnected = "*** DISCONNECTED"
        self.asyncError = "" #"*** retry count exceeded"
        self.logFile = open("serial.log","wt")
    def done(self):
        self.serialport.close()
        self.serialport.readyRead.disconnect()
    def write(self,s):
        self.serialPort.write(s.encode())
    def onSerialPortReady(self):
        sdata = bytearray(self.serialPort.readAll()).decode()
        if self.logFile : 
             self.logFile.write(sdata)
             self.logFile.flush()
        self.sdata += sdata
        self.sdata = self.sdata.replace("\r\n","\n")
        self.sdata = self.sdata.replace("\n","\r") # make all devices look the same
        start = 0
        end = 0
        elen = len(self.lineEnd)
        for i in range(len(self.sdata)):
            bytesleft = len(self.sdata)-i
            if bytesleft >= elen and self.sdata [i:i+elen] ==  self.lineEnd:
                    end = i+elen
                    self.signalLineRead.emit(self.sdata[start:end])
                    start = end
            elif self.asyncConnected  and bytesleft >= len(self.asyncConnected) and self.sdata [i:i+len(self.asyncConnected)] == self.asyncConnected:
                    end = i+elen
                    self.signalConnected.emit()
                    start = end
                    break # leave any other bytes in the buffer to be process by (possibly) new reader
            elif self.asyncDisonnected and bytesleft >= len(self.asyncDisonnected) and self.sdata [i:i+len(self.asyncDisonnected)] == self.asyncDisonnected:
                    end = i+elen
                    self.signalDisconnected.emit()
                    start = end
                    break # leave any other bytes in the buffer to be process by (possibly) new reader
            elif self.asyncError and bytesleft >= len(self.asyncError) and self.sdata [i:i+len(self.asyncError)] == self.asyncError:
                    end = i+elen
                    self.signalTimeout.emit()
                    start = end
                    break # leave any other bytes in the buffer to be process by (possibly) new reader
        # we got to the end, remove any bytes that have been processed
        if start:
             if start >= len(self.sdata):
                   self.sdata = ""
             else: 
                self.sdata = self.sdata[start]


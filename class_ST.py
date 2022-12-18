
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import *

class SignalTracker(QWidget):
    '''
    Only incharged of signaling information when changes are present.
    signals for Enableing/disabling objects in GUI
    Or values to track positions,states etc..
    Signals then can be connected to GUI events.
    '''
    data_change=QtCore.pyqtSignal(dict)        
    log_update=QtCore.pyqtSignal(str)
    
    def __init__(self, *args, **kwargs):        
        super(SignalTracker, self).__init__(*args, **kwargs)    
        self.__name__="ST"
    
    def Log_Update(self,text):
        self.log_update.emit(text)

    def Signal_Data(self,datadict):
        self.data_change.emit(datadict)

    
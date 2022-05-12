import sys
import numpy as np
import os
import logging
from matplotlib.backends.backend_qtagg import (NavigationToolbar2QT as NavigationToolbar)
from PyQt5.QtCore import QTimer
from multiprocessing.shared_memory import SharedMemory

##Include clases from other files
from UI import Ui_MainWindow, QtWidgets
import socket_process as sp
from Canvas import MyFigureCanvas
from float_converter import NumpyFloatToFixConverter



    
class Window(QtWidgets.QMainWindow):
    def __init__(self,parent=None):
        # Set up debug log
        logging.basicConfig(filename='GUIlog.log',
                            level=logging.DEBUG,
                            format='%(asctime)s %(message)s',
                            datefmt='%m/%d/%Y %I:%M:%S %p')
        logging.debug('Logfile initialised')
        
        # setup ui
        QtWidgets.QWidget.__init__(self,parent=None)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        
        # connect button press function
        self.ui.buttonSend.clicked.connect(self.ButtonPressSend)
        self.ui.buttonMeasurement.clicked.connect(self.ButtonPressMeasure)
        self.ui.Fixed_Frequency.released.connect(self.RadioButtonMode)
        self.ui.Frequency_Sweep.released.connect(self.RadioButtonMode)
        self.ui.Linear_Feedback.released.connect(self.RadioButtonMode)
        self.ui.Parametric_Feedback.released.connect(self.RadioButtonMode)
        
        # Create data processing thread
        self.data = sp.dataThread()
        self.data.start_Process()
        
        # insert matplotlib graph
        self.layout = QtWidgets.QVBoxLayout(self.ui.MplWidget)
        self.canvas = MyFigureCanvas()
        self.layout.addWidget(self.canvas)
        self.layout.addWidget(NavigationToolbar(self.canvas,self.ui.MplWidget))
        
        # Calibration data
        self.FPGA_fclk = 125000000
        self.FPGA_phase_width = 30
        
        # init variables
        self.measurement = 0
        self.FPGA_config = {"trigger": 0,
                            "mode": 0,
                            "CIC_divider":int(np.floor(self.FPGA_fclk / 100000)),#int(self.ui.inputData1.text()))),
                            "fixed_freq":5,
                            "start_freq":0,
                            "stop_freq":0,
                            "a_const":1.0,
                            "interval":1,
                            "b_const":1}
        
        # init float to fix conversion
        self.FloatToFix = NumpyFloatToFixConverter(signed=True, n_bits=32, n_frac=16)
        
        #init monitor timer
        self.timer = QTimer()
        self.timer.timeout.connect(lambda: self.monitor())

    def closeEvent(self, event):
        # Close shared memory
        try:
            self.shared_mem.close()
            self.shared_mem.unlink()
        except:
            pass
        # Close data processing thread
        self.data.close()
        # stop monitoring
        try:
            self.timer.stop()
        except:
            pass
        # close logging
        logging.shutdown()   
        
    def monitor(self):
        if (self.data.process_isRun):
            try:
                data_ready, memory_name = self.data.data_to_GUI_Queue.get(block=False)
                logging.debug ("{}, {}".format(data_ready, memory_name))
                
                if memory_name:
                    logging.debug(memory_name)
                    self.shared_mem = SharedMemory(name=memory_name, size=self.num_bytes, create=False)
                    # Send trigger and number of bytes to server
                    packet = [1, self.FPGA_config, False, [False,self.num_bytes]]
                    try:
                        self.data.GUI_to_data_Queue.put(packet, block=False)
                        logging.debug("packet sent to socket process")
    
                    except:
                        logging.debug("Didn't send config to data process")
                        pass
                
                elif data_ready:
                    self.MeasureFinished()
            except:
                pass
        
    def MeasureFinished(self):
        self.measurement = 0
        self.ui.buttonMeasurement.setText("Start Measurement") # change button text
        # Stop data recording monitoring
        self.timer.stop()        
        #create array with view of shared mem
        logging.debug("data_ready recognised")
        temp = np.ndarray((self.num_samples), dtype=np.dtype([('in', np.int16), ('out', np.int16)]), buffer=self.shared_mem.buf)
        #copy into permanent array
        recording = np.copy(temp)
        logging.debug("recording copied")
        # Delete view of shared memory (important, otherwise memory still exists)
        del temp
        
        # Update Canvas
        self.scale=[float(self.ui.inputScal0.text()),float(self.ui.inputScal1.text()),float(self.ui.inputScal2.text()),float(self.ui.inputScal3.text())]
        self.offset=[float(self.ui.inputOffset0.text()),float(self.ui.inputOffset1.text()),float(self.ui.inputOffset2.text()),float(self.ui.inputOffset3.text())]
        self.canvas.update_canvas([recording['in'],recording['out']],self.scale,self.offset)
        
        # Store to *.csv
        if self.ui.checkBoxStore.isChecked():
            #Set up data directory
            datadir="./Data/"
            if (os.path.isdir(datadir) != True):
                os.mkdir(datadir)
            label = self.ui.inputFileName.text()
            i = 0
            while os.path.exists(datadir + '{}{}.csv'.format(label, i)):
                i += 1
            np.savetxt(datadir + '{}{}.csv'.format(label, i), 
                        [recording['in'], recording['out']], 
                        delimiter=",",
                        header="Sample rate: {}".format(125000000 / self.FPGA_config["CIC_divider"]))
        
        # Close shared memory
        self.shared_mem.close()
        self.shared_mem.unlink()
        
        
## Define button functions
    def ButtonPressSend(self):
        """Update FPGA config struct with variables from GUI """
        try:   
            self.FPGA_config["fixed_freq"] = int(self.ui.inputData1.text())
            self.FPGA_config["start_freq"] = int(self.ui.inputData1.text())
            self.FPGA_config["stop_freq"] = int(self.ui.inputData2.text())
            self.FPGA_config["CIC_Divider"] = int(np.floor(125000000 / int(self.ui.inputData4.text())))
            #Convert multiplication constant to fixed point
            a_fixed = self.FloatToFix(float(self.ui.inputData1.text()))
            self.FPGA_config["a_const"] = a_fixed
            self.FPGA_config["b_const"] = int(self.ui.inputData2.text())
            
            #Process frequency sweep information to get interval
            start_phase = self.FPGA_config["start_freq"]*(2**(self.FPGA_phase_width))/self.FPGA_fclk
            stop_phase = self.FPGA_config["stop_freq"]*(2**(self.FPGA_phase_width))/self.FPGA_fclk
            phase_span = np.abs(stop_phase - start_phase)
            
            #test for 0 phase span -> infinite interval if in different mode
            if phase_span:
                self.FPGA_config["interval"] = int(int(self.ui.inputData3.text())/int(self.ui.inputData4.text()) * self.FPGA_fclk / phase_span)
            else:
                self.FPGA_config["interval"] = 1
        except:
            logging.debug("invalid config data")
            
        # Send config data to server
        packet = [0, self.FPGA_config, True, [False,0]]
        try:
            self.data.GUI_to_data_Queue.put(packet, block=False)
            logging.debug("packet sent to socket process")

        except:
            logging.debug("Didn't send config to data process")
            pass
        
    def ButtonPressMeasure(self):
        if self.measurement==0: 
            self.measurement = 1
            self.ui.buttonMeasurement.setText("Stop Measurement") # change button text
            #Send config before measure
            self.ButtonPressSend()
            
            self.num_samples = int(self.ui.inputData3.text())
            self.num_bytes = self.num_samples * 4
            # Send record request to server
            packet = [0, self.FPGA_config, False, [True, self.num_bytes]]
            logging.debug("{} samples requested".format(self.num_samples))
            try:
                self.data.GUI_to_data_Queue.put(packet, block=False)
                logging.debug("packet sent to socket process")
                #Switch button mode
                self.measurement = 1
                self.ui.buttonMeasurement.setText("Stop Measurement") # change button text
                # Start data recording monitoring
                self.timer.start(250)
                
            except:
                logging.debug("Didn't send config to data process")
                pass
        else:
            self.measurement = 0
            self.ui.buttonMeasurement.setText("Start Measurement") # change button text
            # Stop data recording monitoring
            self.timer.stop()
            # Close shared memory
            self.shared_mem.close()
            self.shared_mem.unlink()
            
        
    def RadioButtonMode(self):
        if self.ui.Fixed_Frequency.isChecked():
            logging.debug('toggel to Fixed_Frequency')
            self.FPGA_config["mode"] = 0
            self.ui.labelData1.setText("Frequency Out [Hz]") # change button text
            self.ui.labelData2.setText("Data2") # change button text
        if self.ui.Frequency_Sweep.isChecked():
            logging.debug('toggel to Frequency_Sweep')
            self.FPGA_config["mode"] = 1
            self.ui.labelData1.setText("Frequency Start [Hz]") # change button text
            self.ui.labelData2.setText("Frequency Stop [Hz]") # change button text
        if self.ui.Linear_Feedback.isChecked():
            logging.debug('toggel to Linear_Feedback')
            self.FPGA_config["mode"] = 2
            self.ui.labelData1.setText("a Constant") # change button text
            self.ui.labelData2.setText("b Constant") # change button text
        if self.ui.Parametric_Feedback.isChecked():
            logging.debug('toggel to Parametric_Feedback')
            self.FPGA_config["mode"] = 3
            self.ui.labelData1.setText("Data1") # change button text
            self.ui.labelData2.setText("Data2") # change button text 

## Main Loop

if __name__ == "__main__":
    #initialize variable
    
    #Open QT Window and import as ui
    app=QtWidgets.QApplication(sys.argv)
    self=Window()
    self.showMaximized() #setGeometry(300, 300, 800, 600) #X co-ordinate, Y co-ordinate, Width, Height
    self.show()
    
    #crate client
    #serverClient=Client()
    
    
    
    
    
    













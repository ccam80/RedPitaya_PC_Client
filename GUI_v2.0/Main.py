import sys
import numpy as np
import os
import logging
from matplotlib.backends.backend_qt5agg import (NavigationToolbar2QT as NavigationToolbar)
from PyQt5.QtCore import QTimer
from multiprocessing.shared_memory import SharedMemory

from traceback import format_exc

##Include clases from other files
from UI import Ui_MainWindow, QtWidgets
import socket_process as sp
from Canvas import MyFigureCanvas
from float_converter import NumpyFloatToFixConverter
float_to_fix = NumpyFloatToFixConverter(True, 16, 16)
float_to_fix(1)

    
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
        self.ui.A_x_plus_b.released.connect(self.RadioButtonMode)
        self.ui.white_noise.released.connect(self.RadioButtonMode)
        self.ui.polynomial.released.connect(self.RadioButtonMode)
        self.ui.CBC.released.connect(self.RadioButtonMode)

        
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
                            "param_a":5,
                            "param_b":0,
                            "param_c":0,
                            "param_d":0,
                            "param_e":0,
                            "param_f":0,
                            "param_g":0,
                            "param_h":0}
        
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
                        np.transpose([recording['in'], recording['out']]), 
                        delimiter=";", fmt='%d',
                        header="Sample rate: {}".format(125000000 / self.FPGA_config["CIC_divider"]))
        
        # Close shared memory
        self.shared_mem.close()
        self.shared_mem.unlink()
        
        
## Define button functions
    def ButtonPressSend(self):
        """Update FPGA config struct with variables from GUI """
        try:   
            self.FPGA_config["CIC_divider"] = int(np.floor(125000000 / int(self.ui.inputData10.text())))
            
            # Mode dependent parameter calculation
            
            if self.ui.Fixed_Frequency.isChecked():
                if float(self.ui.inputData1.text()) <= 1000 and int(self.ui.inputData1.text()) > 0:
                    self.FPGA_config["param_a"] = int(float(self.ui.inputData1.text())/ 125.0e6 * (1<<30) + 0.5) #calculate fixed phase
                else:
                    logging.debug("Value out of Range")
                    self.FPGA_config["param_a"] = 42
                if abs(float(self.ui.inputData2.text())) <= 1000:
                    self.FPGA_config["param_b"] = int(float(self.ui.inputData2.text())*8.192)
                else:
                    logging.debug("Value out of Range")
                    self.FPGA_config["param_b"] = 0
                if (abs(float(self.ui.inputData3.text())) + abs(float(self.ui.inputData2.text()))) <= 1000:
                    #limit DC offset if combined DC + AC stimulation will exceed 1V.
                    self.FPGA_config["param_c"] = int(float(self.ui.inputData3.text())*8.192*32768)
                else:
                    logging.debug("Value out of Range")
                    self.FPGA_config["param_c"] = 0 
                    
                self.FPGA_config["param_d"] = 0
                self.FPGA_config["param_e"] = 0
                self.FPGA_config["param_f"] = 0
                self.FPGA_config["param_g"] = 0
                self.FPGA_config["param_h"] = 0
                logging.debug("Offset: {}".format(self.FPGA_config["param_b"]))

                
            if self.ui.Frequency_Sweep.isChecked():
                if int(self.ui.inputData1.text()) <= 1000000 and int(self.ui.inputData1.text()) > 0 and int(self.ui.inputData2.text()) <= 1000000 and int(self.ui.inputData2.text()) > 0:
                    start_phase = float(self.ui.inputData1.text())/ 125.0e6 * (1<<30) + 0.5 #calculate start phase
                    stop_phase = float(self.ui.inputData2.text())/ 125.0e6 * (1<<30) + 0.5 #calculate stop phase
                    phase_span = stop_phase - start_phase
                    self.FPGA_config["param_a"] = int(start_phase)
                    self.FPGA_config["param_b"] = int(int(self.ui.inputData9.text())/int(self.ui.inputData10.text())*125.0e6 / phase_span)
                else:
                    logging.debug("Value out of Range")
                    self.FPGA_config["param_a"] = 42
                    self.FPGA_config["param_b"] = 0
                if float(self.ui.inputData3.text()) <= 1000 and float(self.ui.inputData3.text()) > 0:
                    self.FPGA_config["param_c"] = int(float(self.ui.inputData3.text())*8.192)
                else:
                    logging.debug("Value out of Range")
                    self.FPGA_config["param_c"] = 0
                if (abs(float(self.ui.inputData4.text())) + abs(float(self.ui.inputData3.text()))) <= 1000:
                    #limit DC offset if combined DC + AC stimulation will exceed 1V.
                    self.FPGA_config["param_d"] = int(float(self.ui.inputData4.text())*8.192*32768)
                else:
                    logging.debug("Value out of Range")
                    self.FPGA_config["param_d"] = 0              
                self.FPGA_config["param_e"] = 0
                self.FPGA_config["param_f"] = 0
                self.FPGA_config["param_g"] = 0
                self.FPGA_config["param_h"] = 0
                    
            if self.ui.Linear_Feedback.isChecked():
                if float(self.ui.inputData1.text()) <= 10000 and float(self.ui.inputData1.text()) > 0: 
                    self.FPGA_config["param_a"] = int(float(self.ui.inputData1.text())*8.192)
                # elif float(self.ui.inputData1.text()) >= -10000 and float(self.ui.inputData1.text()) < 0:  
                    # self.FPGA_config["param_a"] = int(float(self.ui.inputData1.text()+(2^17)/8192))
                else:
                    logging.debug("Value out of Range")
                    self.FPGA_config["param_a"] = 0
                if float(self.ui.inputData2.text()) <= 5000 and float(self.ui.inputData2.text()) > 0: 
                    self.FPGA_config["param_b"] = int(float(self.ui.inputData2.text())*8.192)
                else:
                    logging.debug("Value out of Range")
                    self.FPGA_config["param_b"] = 0
                if float(self.ui.inputData3.text()) <= 5000 and float(self.ui.inputData3.text()) > 0: 
                    self.FPGA_config["param_c"] = int(float(self.ui.inputData3.text()))
                else:
                    logging.debug("Value out of Range")
                    self.FPGA_config["param_c"] = 0
                if float(self.ui.inputData4.text()) <= 1000000 and float(self.ui.inputData4.text()) > 0: 
                    self.FPGA_config["param_d"] = int(self.ui.inputData4.text())
                    #[63:10] 2048|0
                    #[63:9] 1024|0
                    #[63:8] 512|0
                else:
                    logging.debug("Value out of Range")
                    self.FPGA_config["param_d"] = 0
                if float(self.ui.inputData5.text()) <= 10000 and float(self.ui.inputData5.text()) >= -10000: 
                        self.FPGA_config["param_e"] = int(self.ui.inputData5.text())
                        
                else:
                        logging.debug("Value out of Range")
                        self.FPGA_config["param_e"] = 0
                if int(self.ui.inputData6.text()) <= 1000000 and int(self.ui.inputData6.text()) > 0:
                    self.FPGA_config["param_f"] = int(float(self.ui.inputData6.text())/ 125.0e6 * (1<<30) + 0.5) #calculate fixed phase
                else:
                    logging.debug("Value out of Range")
                    self.FPGA_config["param_f"] = 43
                    
                self.FPGA_config["param_g"] = 0
                self.FPGA_config["param_h"] = 0
                
            if self.ui.Parametric_Feedback.isChecked():
                if float(self.ui.inputData1.text()) <= 10000 and float(self.ui.inputData1.text()) > 0: 
                    self.FPGA_config["param_a"] = int(float(self.ui.inputData1.text())*8.192)
                # elif float(self.ui.inputData1.text()) >= -10000 and float(self.ui.inputData1.text()) < 0:  
                    # self.FPGA_config["param_a"] = int(float(self.ui.inputData1.text()+(2^17)/8192))
                else:
                    logging.debug("Value out of Range")
                    self.FPGA_config["param_a"] = 0
                if float(self.ui.inputData2.text()) <= 5000 and float(self.ui.inputData2.text()) > 0: 
                    self.FPGA_config["param_b"] = int(float(self.ui.inputData2.text())*8.192)
                else:
                    logging.debug("Value out of Range")
                    self.FPGA_config["param_b"] = 0
                if float(self.ui.inputData3.text()) <= 5000 and float(self.ui.inputData3.text()) > 0: 
                    self.FPGA_config["param_c"] = int(float(self.ui.inputData3.text()))
                else:
                    logging.debug("Value out of Range")
                    self.FPGA_config["param_c"] = 0
                if float(self.ui.inputData4.text()) <= 1000000 and float(self.ui.inputData4.text()) > 0: 
                    self.FPGA_config["param_d"] = int(self.ui.inputData4.text())
                    #[63:10] 2048|0
                    #[63:9] 1024|0
                    #[63:8] 512|0
                else:
                    logging.debug("Value out of Range")
                    self.FPGA_config["param_d"] = 0
                if float(self.ui.inputData5.text()) <= 10000 and float(self.ui.inputData5.text()) >= -10000: 
                        self.FPGA_config["param_e"] = int(self.ui.inputData5.text())
                        
                else:
                        logging.debug("Value out of Range")
                        self.FPGA_config["param_e"] = 0
                        
                self.FPGA_config["param_f"] = 0                
                self.FPGA_config["param_g"] = 0
                self.FPGA_config["param_h"] = 0
                
                
            if self.ui.A_x_plus_b.isChecked():
    
                                   
                if float(self.ui.inputData1.text()) <= 20 and float(self.ui.inputData1.text()) > -20:
                    self.FPGA_config["param_b"] = self.FloatToFix(float(self.ui.inputData1.text()))

                else:
                    logging.debug("Value out of Range")
                    self.FPGA_config["param_b"] = 0
                    
                if (self.ui.inputData2.text() != "0"): 
                    # Calculate interval from start/stop values
                    astart = self.FloatToFix(float(self.ui.inputData1.text()))
                    astop = self.FloatToFix(float(self.ui.inputData2.text()))
                    logging.debug("Sweep: A start = {}, A stop = {}".format(astart,astop))
                    if (astop != 0):
                        aspan = astop - astart
                        ainterval = int(self.ui.inputData9.text())/int(self.ui.inputData10.text())*125.0e6 / aspan
                        logging.debug("A Interval: {}".format(ainterval))
                        self.FPGA_config["param_d"] = int(ainterval)
                    else:
                        self.FPGA_config["param_d"] = 0
                else:
                    logging.debug("No A sweep chosen")
                    self.FPGA_config["param_d"] = 0
                if float(self.ui.inputData3.text()) <= 5000 and float(self.ui.inputData3.text()) > -5000: 
                    self.FPGA_config["param_c"] = int(float(self.ui.inputData3.text())*8.192*32768)
                else:
                    logging.debug("Value out of Range")
                    self.FPGA_config["param_c"] = 0
                    
                if (self.ui.inputData4.text() != "0"):
                    # Calculate interval from start/stop values
                    bstart = int(float(self.ui.inputData3.text())*8.192 * 32768)
                    bstop = int(float(self.ui.inputData4.text())*8.192 * 32768)
                    if (bstop != 0):
                        bspan = bstop - bstart
                        binterval = int(self.ui.inputData9.text())/int(self.ui.inputData10.text())*125.0e6 / bspan
                        self.FPGA_config["param_e"] = int(binterval)
                    else:
                        self.FPGA_config["param_e"] = 0

                else:
                    logging.debug("No B sweep chosen")
                    self.FPGA_config["param_e"] = 0
                
                logging.debug("Offset start: {}, Offset interval: {}".format(self.FPGA_config["param_c"],self.FPGA_config["param_e"]))
                self.FPGA_config["param_f"] = 0
                self.FPGA_config["param_g"] = 0
                self.FPGA_config["param_h"] = 0
                
                
            if self.ui.white_noise.isChecked():
                if float(self.ui.inputData1.text()) <= 10000 and float(self.ui.inputData1.text()) > 0: 
                    self.FPGA_config["param_c"] = int(float(self.ui.inputData1.text())*8.192)
                else:
                    logging.debug("Value out of Range")
                    self.FPGA_config["param_c"] = 0
                    
                if (self.ui.inputData2.text() != "0"): 
                    self.FPGA_config["param_d"] = int(float(self.ui.inputData3.text())*8.192*32768)
                else:
                    logging.debug("Value out of Range")
                    self.FPGA_config["param_d"] = 0
                
                self.FPGA_config["param_a"] = 0
                self.FPGA_config["param_b"] = 0
                self.FPGA_config["param_c"] = 0
                self.FPGA_config["param_d"] = 0
                self.FPGA_config["param_e"] = 0
                self.FPGA_config["param_f"] = 0
                self.FPGA_config["param_g"] = 0
                self.FPGA_config["param_h"] = 0
                    
            if self.ui.polynomial.isChecked():
                if float(self.ui.inputData1.text()) <= 10000 and float(self.ui.inputData1.text()) > 0: 
                    self.FPGA_config["param_c"] = int(float(self.ui.inputData1.text())*8.192)
                else:
                    logging.debug("Value out of Range")
                    self.FPGA_config["param_c"] = 0
                    
                if (self.ui.inputData2.text() != "0"): 
                    self.FPGA_config["param_d"] = int(float(self.ui.inputData3.text())*8.192)
                else:
                    logging.debug("Value out of Range")
                    self.FPGA_config["param_d"] = 0
                
                self.FPGA_config["param_a"] = 0
                self.FPGA_config["param_b"] = 0
                self.FPGA_config["param_e"] = 0
                self.FPGA_config["param_f"] = 0
                self.FPGA_config["param_g"] = 0
                self.FPGA_config["param_h"] = 0
                
            if self.ui.CBC.isChecked():
                if float(self.ui.inputData1.text()) <= 10000 and float(self.ui.inputData1.text()) > 0: 
                    self.FPGA_config["param_c"] = int(float(self.ui.inputData1.text())*8.192)
                else:
                    logging.debug("Value out of Range")
                    self.FPGA_config["param_c"] = 0
                    
                if (self.ui.inputData2.text() != "0"): 
                    self.FPGA_config["param_d"] = int(float(self.ui.inputData3.text())*8.192)
                else:
                    logging.debug("Value out of Range")
                    self.FPGA_config["param_d"] = 0
                
                self.FPGA_config["param_a"] = 0
                self.FPGA_config["param_b"] = 0
                self.FPGA_config["param_e"] = 0
                self.FPGA_config["param_f"] = 0
                self.FPGA_config["param_g"] = 0
                self.FPGA_config["param_h"] = 0
                    
            
# =============================================================================
#             
#             #Process frequency sweep information to get interval
#             start_phase = self.FPGA_config["param_a"]*(2**(self.FPGA_phase_width))/self.FPGA_fclk
#             stop_phase = self.FPGA_config["param_b"]*(2**(self.FPGA_phase_width))/self.FPGA_fclk
#             phase_span = np.abs(stop_phase - start_phase)
#             
#             #test for 0 phase span -> infinite interval if in different mode
#             if phase_span:
#                 self.FPGA_config["interval"] = int(int(self.ui.inputData9.text())/int(self.ui.inputData10.text()) * self.FPGA_fclk / phase_span)
#             else:
#                 self.FPGA_config["interval"] = 1
# =============================================================================
            
        except Exception as e:
            logging.debug(e)
            logging.debug(format_exc())
            logging.debug("invalid config data")
            logging.debug("Param B: {}".format(self.FPGA_config["param_b"]))

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
            
            self.num_samples = int(self.ui.inputData9.text())
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
            self.ui.inputData1.setText("5")
            self.ui.labelData2.setText("Amplitude Out [mV]") # change button text
            self.ui.inputData2.setText("100")
            self.ui.labelData3.setText("Offset Out [mV]") # change button text
            self.ui.inputData3.setText("0")
            self.ui.labelData4.setText("Param4") # change button text
            self.ui.labelData5.setText("Param5") # change button text
            self.ui.labelData6.setText("Param6") # change button text
            self.ui.labelData7.setText("Param7") # change button text
            self.ui.labelData8.setText("Param8") # change button text
        if self.ui.Frequency_Sweep.isChecked():
            logging.debug('toggel to Frequency_Sweep')
            self.FPGA_config["mode"] = 1
            self.ui.labelData1.setText("Frequency Start [Hz]") # change button text
            self.ui.inputData1.setText("5")
            self.ui.labelData2.setText("Frequency Stop [Hz]") # change button text
            self.ui.inputData2.setText("100")
            self.ui.labelData3.setText("Amplitude Out [mV]") # change button text
            self.ui.inputData3.setText("100")
            self.ui.labelData4.setText("DC Offset [mV]") # change button text
            self.ui.inputData4.setText("0")
            self.ui.labelData5.setText("Param5") # change button text
            self.ui.labelData6.setText("Param6") # change button text
            self.ui.labelData7.setText("Param7") # change button text
            self.ui.labelData8.setText("Param8") # change button text
        if self.ui.Linear_Feedback.isChecked():
            logging.debug('toggel to Linear_Feedback')
            self.FPGA_config["mode"] = 2
            self.ui.labelData1.setText("Offset Out [mV]") # change button text
            self.ui.labelData2.setText("Param2") # change button text
            self.ui.labelData3.setText("Feedback gain IN1[V]*IN2[V]/2^10") # change button text
            self.ui.labelData4.setText("Gain IN1[V]^2/2^10") # change button text
            self.ui.labelData5.setText("Gain IN1[V]^3/2^10") # change button text
            self.ui.labelData6.setText("Param6") # change button text
            self.ui.labelData7.setText("Param7") # change button text
            self.ui.labelData8.setText("Param8") # change button text
        if self.ui.Parametric_Feedback.isChecked():
            logging.debug('toggel to Parametric_Feedback')
            self.FPGA_config["mode"] = 3
            self.ui.labelData1.setText("Offset Out [mV]") # change button text
            self.ui.labelData2.setText("Param2") # change button text
            self.ui.labelData3.setText("Feedback gain IN1[V]*DDS/2^10") # change button text
            self.ui.labelData4.setText("Gain IN1[V]^2/2^10") # change button text
            self.ui.labelData5.setText("Gain IN1[V]^3/2^10") # change button text
            self.ui.labelData6.setText("Frequency Out [Hz]") # change button text
            self.ui.labelData7.setText("Param7") # change button text
            self.ui.labelData8.setText("Param8") # change button text
        if self.ui.A_x_plus_b.isChecked():
            logging.debug('toggel to A_x_plus_b')
            self.FPGA_config["mode"] = 4
            self.ui.labelData1.setText("A start") # change button text
            self.ui.inputData1.setText("1")
            self.ui.labelData2.setText("A stop (0 for no sweep)") # change button text
            self.ui.inputData2.setText("0")
            self.ui.labelData3.setText("B [mV]") # change button text
            self.ui.inputData3.setText("100")
            self.ui.labelData4.setText("B stop (0 for no sweep) [mV]") # change button text
            self.ui.inputData4.setText("0")
            self.ui.labelData5.setText("Param5") # change button text
            self.ui.labelData6.setText("Param6") # change button text
            self.ui.labelData7.setText("Param7") # change button text
            self.ui.labelData8.setText("Param8") # change button text
        if self.ui.white_noise.isChecked():
            logging.debug('toggel to Frequency_Sweep')
            self.FPGA_config["mode"] = 5
            self.ui.labelData1.setText("Amplitude") # change button text
            self.ui.inputData1.setText("0")
            self.ui.labelData2.setText("DC Offset [mV]") # change button text
            self.ui.inputData2.setText("0")
            self.ui.labelData3.setText("Param3") # change button text
            self.ui.inputData3.setText("0")
            self.ui.labelData4.setText("Param4") # change button text
            self.ui.inputData4.setText("0")
            self.ui.labelData5.setText("Param5") # change button text
            self.ui.labelData6.setText("Param6") # change button text
            self.ui.labelData7.setText("Param7") # change button text
            self.ui.labelData8.setText("Param8") # change button text
        if self.ui.polynomial.isChecked():
            logging.debug('toggel to polynomial')
            self.FPGA_config["mode"] = 6
            self.ui.labelData1.setText("X^0 coefficient") # change button text
            self.ui.inputData1.setText("0")
            self.ui.labelData2.setText("X^1 coefficient") # change button text
            self.ui.inputData2.setText("0")
            self.ui.labelData3.setText("X^2 coefficient") # change button text
            self.ui.inputData3.setText("0")
            self.ui.labelData4.setText("X^3 coefficient") # change button text
            self.ui.inputData4.setText("0")
            self.ui.labelData5.setText("X^4 coefficient") # change button text
            self.ui.labelData6.setText("Param6") # change button text
            self.ui.labelData7.setText("Param7") # change button text
            self.ui.labelData8.setText("Param8") # change button text
        if self.ui.CBC.isChecked():
            logging.debug('toggel to CBC')
            self.FPGA_config["mode"] = 7
            self.ui.labelData1.setText("None") # change button text
            self.ui.inputData1.setText("0")
            self.ui.labelData2.setText("of") # change button text
            self.ui.inputData2.setText("0")
            self.ui.labelData3.setText("these") # change button text
            self.ui.inputData3.setText("0")
            self.ui.labelData4.setText("do") # change button text
            self.ui.inputData4.setText("0")
            self.ui.labelData5.setText("anything") # change button text
            self.ui.labelData6.setText("Param6") # change button text
            self.ui.labelData7.setText("Param7") # change button text
            self.ui.labelData8.setText("Param8") # change button text
            

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
    
    
    
    
    
    













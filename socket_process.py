from multiprocessing import Process, Queue
from multiprocessing.shared_memory import SharedMemory
import traceback
from time import sleep
import numpy as np
import socket
import struct 
import logging


class dataThread:
    def __init__(self,
                 port=1001,
                 ip="192.168.1.3",
                 ):


               # Pipe to send final data to main process
        self.GUI_to_data_Queue = Queue()
        self.data_to_GUI_Queue = Queue()
        self.process = None
        self.process_isRun = False
        self.isRecord = False
        self.bytes_to_receive = 0
        self.trigger = False
        self.config_change = False
        self.record_request = False
        
        self.config = {"CIC_divider":1250,
                        "ch1_freq":2,
                        "a_const":1.0,
                        "ch1_ampl":32000,
                        "b_const":1}
            
        self.port = port
        self.ip = ip
        
        self.s = None
        self.reopen_serial = False

    def send_settings_to_FPGA(self):
       format_ = "HIiHh"
       logging.debug(format_)
       logging.debug(self.config)
       config_send = struct.pack(format_,                
                                 self.config["CIC_divider"],
                                 self.config["ch1_freq"],
                                 self.config["a_const"],
                                 self.config["ch1_ampl"],
                                 self.config["b_const"])
       logging.debug(self.config)
       self.s.send(config_send)
       self.s.close()
       sleep(0.001)
       self.reopen_serial = True
       logging.debug("FPGA settings sent")
       

    def start_Process(self):
        if self.process == None:
            self.process_isRun = True
            self.process = Process(target=self.backgroundThread)
            self.process.start()
            

    def fetch_instructions(self):
        """ Get and save trigger, config, config_changed flag and record requests
        """
        try:
            self.trigger, self.config, self.config_change, [self.record_request, self.bytes_to_receive] = self.GUI_to_data_Queue.get(block=False)
            logging.debug("message received")
            logging.debug(self.config)
            return True
        except Exception as e:
            # logging.debug(str(e))
            return False
        
        
    def inform_GUI(self, event):
        """ Required info: Tell GUI if new shared memory is allocated or if data
        is ready for a copy. """
        
        if event == "allocated":
            self.data_to_GUI_Queue.put([0, self.shared_memory_name], block=False)
            
        elif event == "data_ready":
            self.data_to_GUI_Queue.put([1, 0], block=False)
        
    def backgroundThread(self):    # retrieve data
        """Opens socket, then spins around like this:
            1. Check for info from GUI
            2. If info received, check flags
            3. If config changed, tell FPGA and wait for reset (open loop)
            4. If record requested, allocate memory and tell GUI the memory's name.
                Wait for GUI to set up it's side of memory and send a trigget back
            5. If triggered, set recording mode active
            6. If recording mode, slice up buffer and fill with streamed data
            7. Once recording done, tell GUI that data is ready and close shared mem
            2. Check for info from
            """
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        self.s.connect((self.ip, self.port))
        logging.basicConfig(filename='socketlog.log',
                            level=logging.DEBUG,
                            format='%(asctime)s %(message)s',
                            datefmt='%m/%d/%Y %I:%M:%S %p')
        logging.debug('Logfile initialised')
        logging.debug("socket connected")
        
        while(True):
            
            if self.reopen_serial:
                self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
                self.s.connect((self.ip, self.port))
                self.reopen_serial=False

            if self.fetch_instructions():
                                   
                if self.config_change:
                    self.send_settings_to_FPGA()
                    self.config_change = 0
                    sleep(0.1)
                    
                elif self.record_request:
                    logging.debug("request received")
                    self.shared_mem = SharedMemory(size=self.bytes_to_receive, create=True)
                    self.shared_memory_name = self.shared_mem.name
                    logging.debug(self.shared_memory_name)
                    self.inform_GUI("allocated")                    
                    self.record_request = False
                    logging.debug("inform GUI executed")
                
                elif self.trigger:
                    self.isRecord = True
                    logging.debug("trigger received")
                    logging.debug("{} to receive".format(self.bytes_to_receive))
                    self.trigger = False
                
                else:
                    sleep(0.1)
                    
            if self.isRecord:
                logging.debug("isRecord triggered")
                view = memoryview(self.shared_mem.buf)
                logging.debug("memory view created")
                logging.debug("{} to receive".format(self.bytes_to_receive))
                
                while self.bytes_to_receive:
                    logging.debug("start receive")
                    nbytes = self.s.recv_into(view, self.bytes_to_receive)
                    view = view[nbytes:]
                    self.bytes_to_receive -= nbytes
                    logging.debug(self.bytes_to_receive)
                
                del view
                self.isRecord = False
                print("send data ready")
                self.inform_GUI("data_ready")
                self.shared_mem.close()
                del self.shared_mem
                logging.debug("memory closed")
                
                self.s.close()
                self.reopen_serial = True


    def clear_dataThread(self):

       pass


    def close(self):
        self.isrun = False
        logging.debug("Close called")
        logging.debug("{} s".format(self.s))
        if self.process_isRun:
            self.process.terminate()
            self.process_isRun = False
        if self.s != None:
            self.s.close()
            logging.debug("socket closed")
        # df = pd.DataFrame(self.csvData)
        # df.to_csv('/home/rikisenia/Desktop/data.csv')

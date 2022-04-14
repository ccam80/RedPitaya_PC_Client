from multiprocessing import Process, Queue
from multiprocessing.shared_memory import SharedMemory
import traceback
from time import sleep
import numpy as np
import socket
import struct 
import logging
# import fabric


class dataThread:
    def __init__(self,
                 port=1001,
                 ip="192.168.1.3",
                 ):


        # Queues to pass data to and from main thread/GUI
        self.GUI_to_data_Queue = Queue()
        self.data_to_GUI_Queue = Queue()
        
        #State toggles and counters
        self.process = None
        self.process_isRun = False
        self.isRecord = False
        self.bytes_to_receive = 0
        self.trigger = False
        self.config_change = False
        self.record_request = False
        
        #FPGA config struct
        self.config = { "trigger": 0,
                        "state": 0,
                        "CIC_divider":1250,
                        "fixed_freq":2,
                        "start_freq":0,
                        "stop_freq":0,
                        "a_const":0,
                        "interval":1,
                        "b_const":1}
        
        #Socket config
        self.port = port
        self.ip = ip
        self.s = None
        self.reopen_socket_flag = False
        
        
    def send_settings_to_FPGA(self):
        """Package FPGA_config attribute and send to server"""
        
        # Get config and package into c-readable struct 
        format_ = "BBHIIIIIh"
     
        config_send = struct.pack(format_,
                                  self.config["trigger"],
                                  self.config["state"],
                                  self.config["CIC_divider"],
                                  self.config["fixed_freq"],
                                  self.config["start_freq"],
                                  self.config["stop_freq"],
                                  self.config["a_const"],
                                  self.config["interval"],
                                  self.config["b_const"])
        
        logging.debug(self.config)
        
        #Send config packet, check for missed bytes
        if (self.s.send(config_send) != len(config_send)):
            logging.debug("Sent config does not match config array size!")
        
        # Close and reopen socket
        self.s.close()
        sleep(0.001)
        self.reopen_socket_flag = True
        logging.debug("FPGA settings sent")
       

    def start_Process(self):
        """Begin thread, toggle run state"""
        
        if self.process == None:
            self.process_isRun = True
            self.process = Process(target=self.backgroundThread)
            self.process.start()
            

    def fetch_instructions(self):
        """ Get and save instructions from GUI thread:
            
            config: New config struct for FPGA
            config_change: Config struct changed, request to send (could easily optimise out)
            record request: First request from GUI, initiates shared memory setup and handshake
            trigger: Shared memory set up, ready to receive & send to GUI.

        """
        
        try:
            self.trigger, self.config, self.config_change, [self.record_request, self.bytes_to_receive] = self.GUI_to_data_Queue.get(block=False)
            logging.debug("message received")
            return True
        except Exception as e:
            # logging.debug(str(e))
            return False
        
        
    def inform_GUI(self, event):
        """ Send message back to GUI thread, either:
            Allocated: Tell GUI new shared memory is allocated 
            data_ready: Shared memory filled with requested data. """
        
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
                Wait for GUI to set up it's side of memory and send a trigger back
            5. If triggered, set recording mode active
            6. If recording mode, slice up buffer and fill with streamed data
            7. Once recording done, tell GUI that data is ready and close shared mem
            """
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        self.s.connect((self.ip, self.port))
        
        #Set up socketlog.log debug log
        logging.basicConfig(filename='socketlog.log',
                            level=logging.DEBUG,
                            format='%(asctime)s %(message)s',
                            datefmt='%m/%d/%Y %I:%M:%S %p')
        
        logging.debug('Logfile initialised')
        logging.debug("socket connected")
        
        while(True):
            
            if self.reopen_socket_flag:
                self.reopen_socket()

            # Check for instructions and dispatch accordingly
            if self.fetch_instructions():
            
                if self.config_change:
                    self.send_settings_to_FPGA()
                    self.config_change = 0
                    sleep(0.1)
                    
                elif self.record_request:
                    logging.debug("request received")
                    
                    #Set up shared memory block
                    self.shared_mem = SharedMemory(size=self.bytes_to_receive, create=True)
                    self.shared_memory_name = self.shared_mem.name
                    logging.debug(self.shared_memory_name)
                    
                    #Tell GUI the memory is allocated
                    self.inform_GUI("allocated")                    
                    self.record_request = False
                    logging.debug("inform GUI executed")
                
                elif self.trigger:
                    
                    #Trigger FPGA, start recording
                    self.isRecord = True
                    self.config['trigger'] = 1
                    self.send_settings_to_FPGA()
                    self.reopen_socket()
                
                    logging.debug("trigger received")
                    logging.debug("{} to receive".format(self.bytes_to_receive))
                    self.trigger = False
                    # self.send_settings_to_FPGA()

                
                else:
                    sleep(0.1)
                    
            #Once recording toggled, get data in loop until 0 bytes to receive
            if self.isRecord:
                
                logging.debug("isRecord triggered")
                self.reopen_socket()
                
                #Create view of shared memory buffer
                view = memoryview(self.shared_mem.buf)
                logging.debug("memory view created")
                logging.debug("{} to receive".format(self.bytes_to_receive))
                
                logging.debug("Awaiting trigger confirmation from server on MCU")
                
                # wait for trigger confirmation from server - process may get stuck in 
                # this loop if trigger acknowledgement is lost
                while(int.from_bytes(self.s.recv(4), "little", signed=True) != 1):
                    pass
                
                while (self.bytes_to_receive):
                    logging.debug("start receive")
                    
                    #Load info into array in nbyte chunks
                    nbytes = self.s.recv_into(view, self.bytes_to_receive)
                    view = view[nbytes:]
                    self.bytes_to_receive -= nbytes
                    logging.debug(self.bytes_to_receive)
                
                # Clean up shared memory and inform GUI thread
                del view
                self.isRecord = False
                print("send data ready")
                self.inform_GUI("data_ready")
                self.shared_mem.close()
                del self.shared_mem
                logging.debug("memory closed")
                
                # Kick socket
                self.s.close()
                self.reopen_socket()
                
                # Turn off FPGA trigger (could bring before memory cleanup if 
                # trigger end timing becomes critical)
                self.config['trigger'] = 0
                self.send_settings_to_FPGA()
                logging.debug("Trigger off sent")
                
                # Kick socket
                self.s.close()
                self.reopen_socket()

 
    def reopen_socket(self):
        """Open same socket again. Used for regular reset"""
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        self.s.connect((self.ip, self.port))
        self.reopen_socket_flag=False

    def close(self):
        """End process and close socket when GUI is closed"""
        
        self.isrun = False
        logging.debug("Close called")
        logging.debug("{} s".format(self.s))
        
        if self.process_isRun:
            self.process.terminate()
            self.process_isRun = False
            
        if self.s != None:
            self.s.close()
            logging.debug("socket closed")


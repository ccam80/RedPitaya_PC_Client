# -*- coding: utf-8 -*-
"""
RP_communications.py

data transfer into and out of the RedPitaya from the PC.

@author: cca78
"""
from multiprocessing import Process, Queue
from multiprocessing.shared_memory import SharedMemory
from time import sleep
import numpy as np
import socket
import struct
import logging
import select
import sys
import traceback
from FPGA_config import FPGA_config, config_keys

class StreamToLogger(object):
    """
    Redirect process output to a logger, as otherwise it's output is lost.

    Taken from https://stackoverflow.com/questions/19425736/how-to-redirect-stdout-and-stderr-to-logger-in-python.

    init arguments:
        logger: logger object to redirect to
        level: logger level to set (e.g. logging.DEBUG)

    returns:
        None
    """
    def __init__(self, logger, level):
       self.logger = logger
       self.level = level
       self.linebuf = ''

    def write(self, buf):
       for line in buf.rstrip().splitlines():
          self.logger.log(self.level, line.rstrip())

    def flush(self):
        pass


class RP_communications(object):
    """
    RP_communications class. Contains a process to be run in a separate thread
    to handle high-bandwidth data transfer over a TCP socket, and all required
    inter-process communication objects and methods to make that work. """


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
        self.bytes_to_receive = 0
        self.trigger = False
        self.config_change = False
        self.record_request = False

        #FPGA config dict
        self.config = FPGA_config()

        #Socket config
        self.port = port
        self.ip = ip
        self.socket = None

     # ************************ Process admin ****************************** #

    def start_process(self):
        """Begin thread, toggle run state"""

        if self.process == None:
            self.process_isRun = True
            self.process = Process(target=self.backgroundThread)
            self.process.start()
            
    

     # **************** Local Inter-process Comms with GUI****************** #

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
            logging.debug(f"""trigger: {self.trigger},
                          config: {self.config},
                          config_change: {self.config_change},
                          [rec request: {self.record_request}, btr: {self.bytes_to_receive}]""")
            return True
        except Exception as e:
            # logging.debug(traceback.format_exc())
            return False

    


        
     # ************************ TCP Comms with RP MCU  ********************* #

    





    

    

    

    

    # ********************** MAIN LOOP ************************************* #


    def backgroundThread(self):    # retrieve data
        """ Process to run in thread in the background. Saves a copy of class
        state when started, works ot of this, which is invisible to the GUI.
        This state is lost upon thread.join.
            """

        # Set up socketlog.log debug log
        logging.basicConfig(filename='socketlog.log',
                            level=logging.DEBUG,
                            format='%(asctime)s %(message)s',
                            datefmt='%m/%d/%Y %I:%M:%S %p')

        logging.debug('Logfile initialised')
        log = logging.getLogger('socket')
        sys.stdout = StreamToLogger(log, logging.DEBUG)
        sys.stderr = StreamToLogger(log, logging.DEBUG)

        while(True):
            # Check for instructions and dispatch accordingly
            if self.fetch_instructions():

                if self.config_change:
                    self.send_settings_to_FPGA()
                    self.config_change = 0

                elif self.record_request:
                    logging.debug("request received")
                    self.initiate_record()
                    self.record_request = False

                elif self.trigger:
                    # Trigger FPGA, start recording
                    self.trigger = 1
                    self.send_settings_to_FPGA()
                    logging.debug("{} to receive".format(self.bytes_to_receive))

                    self.record()

                    self.trigger = 0
                    self.send_settings_to_FPGA()
                    logging.debug("Trigger off sent")

                else:
                    sleep(0.1)


    def close(self):
        """End process and close socket when GUI is closed"""

        self.isrun = False
        logging.debug("Close called")
        logging.debug("{} s".format(self.socket))

        if self.process_isRun:
            self.process.terminate()
            self.process_isRun = False

        if self.socket is not None:
            self.socket.close()
            logging.debug("socket closed")
    
    
    # ***************************************************
    # Seigan Development - Repurposed
    # Functions unchanged, but used differently
    # ***************************************************   
    
    
    # Socket ********************************************
    def open_socket(self):
        """Open generic client socket."""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        try:
            self.socket.connect((self.ip, self.port))
        except Exception as e:
            logging.debug(e)
            
            
    def close_socket(self):
        """Close socket and wait for a 100ms. """
        # Close socket
        self.socket.close()
        sleep(0.1)
    
    def purge_socket(self):
        """Purge receive buffer if server is streaming naiively and likely to
        overshoot. Ensure you have all the data you need first. Should only be
        required after record"""

        readers = [1]
        self.socket.setblocking(False)
        sockets = [self.socket]

        while readers != []:
            readers, writers, err = select.select(sockets,
                                                  sockets,
                                                  sockets,
                                                  2)
            try:
                purged = self.socket.recv(16384)
                logging.debug("{} bytes received in purge, header = {} {} {} {}".format(len(purged), purged[0], purged[1], purged[3], purged[4]))
            except Exception as e:
                logging.debug("Purge recv error: {}".format(e))
                break
            
    
    def initiate_transfer(self, type='config'):
        """ Send request info to MCU, await acknowledgement. Sends 4-byte 0 to initiate
        config packet send, expect ack value of 2. Sends "bytes to receive" value otherwise,
        expects ack value of bytes_to_receive. """
        if type == 'config':
            payload = np.uint32(0)
            ack_value = 2
        if type == 'recording':
            payload = np.uint32(self.bytes_to_receive)
            ack_value = np.uint32(self.bytes_to_receive)

        self.socket.sendall(payload)
        if (self.wait_for_ack(ack_value) == 1):
            return 1
        else:
            return -1
    
    def wait_for_ack(self, ack_value=1):
        """ Wait for an acknowledge byte from server. If no byte or incorrect
        value received, log error and return -1. Returns 1 on successful ack. """

        ack = int.from_bytes(self.socket.recv(4), "little", signed=False)
        logging.debug("Ack value received: {}, expected {}".format(ack, ack_value))

        if ack == ack_value:
            return 1
        else:
            logging.debug("Bad acknowledge")
            return -1
     
    def push_data(self, event):
        """ Send message back to GUI thread, either:
            Allocated: Tell GUI new shared memory is allocated
            data_ready: Shared memory filled with requested data. """

        if event == "allocated":
            self.data_to_GUI_Queue.put([0, self.shared_memory_name], block=False)
            logging.debug(self.shared_memory_name + "sent to GUI")

        elif event == "data_ready":
            self.data_to_GUI_Queue.put([1, 0], block=False)
        
    # Update_FPGA_settings ********************************************
    def send_settings_to_FPGA(self):
        """Package FPGA_config attribute and send to server"""

        # Get config and package into c-readable struct
        format_ = "BBBBiiiiiiiiiiiiii"
        
        # Trigger folded into FPGA struct here, as it's modified in the RP_comms module
        # and the system byte is otherwise modified in RedPitaya/mem_mapping.
        # This is probably only here because I (CC) have gotten the heirarchy confused.
        self.config['system'] = int(self.config['system'] | (self.trigger << 2))
        
        values_to_pack = [self.config[key] for key in config_keys]

        config_send = struct.pack(format_, *values_to_pack)

        self.open_socket()
        if (self.initiate_transfer("config") < 1):
            logging.debug("Socket type (config) not acknowledged by server")
        else:
            try:
                self.socket.sendall(config_send)
            except Exception as e:
                logging.debug("config send error")
                logging.debug(e)

        self.close_socket()
        logging.debug("FPGA settings sent")
        
        
    

    
    # prepare_record ********************************************
    def initiate_record(self):
        self.shared_mem = SharedMemory(size=self.bytes_to_receive, create=True)
        self.shared_memory_name = self.shared_mem.name

        #Tell GUI the memory is allocated
        self.push_data("allocated")
        logging.debug("inform GUI executed")
        
        
        
    # trigger_record ********************************************
    def record(self):
        self.open_socket()
        if (self.initiate_transfer("recording") < 1):
            logging.debug("Socket type (record) not acknowledged by server")

        #Create view of shared memory buffer
        view = memoryview(self.shared_mem.buf)
        logging.debug("memory view created")
        logging.debug("{} to receive".format(self.bytes_to_receive))

        # wait for trigger confirmation from server - process may get stuck in
        # this loop if trigger acknowledgement is lost
        if (self.wait_for_ack() != 1):
            logging.debug("Record acknowledge not received")
            return

        logging.debug("start receive")

        while (self.bytes_to_receive):
            #Load info into array in nbyte chunks
            nbytes = self.socket.recv_into(view, self.bytes_to_receive)
            view = view[nbytes:]
            self.bytes_to_receive -= nbytes
            logging.debug(self.bytes_to_receive)

        self.purge_socket()
        self.close_socket()

        del view
        self.push_data("data_ready")
        self.shared_mem.close()
        del self.shared_mem
    
    
    # ***************************************************
    # Seigan Development - Tested and working
    # Miracles happen here
    # ***************************************************
    
    
    # ***************************************************
    # Seigan Development - Untested
    # Wild wild west of bad code goes here
    # ***************************************************
    def fetch_packet(self, packet):
        # TODO: Check description is consistent
        # TODO: CHeck whether packets are even required in this new structure (I think not)
        """ 
        This function is a re-write of the old 'fetch_instructions' functions.
        
        Receives a packet depending on a certain process. 
        The packet is a list with the contents (in order):
                1) trigger: (bool)
                    Recording trigger
                2) config: (struct)
                    New config struct for FPGA
                3) config_change: (bool)
                    Whether 'config' has changed or not
                4) [memory_allocation, memory_size_in_bytes]: list(bool, bytes?)
                    A list of two elements, consisting of whether a memory allocation exists, and the size of the memory allocation.
                    
        
        TODO: These examples were taken from the old code. To check whether they are actually consistent. 
        Ex. 1:
            packet = [0, self.system.comms.config, True, [False, 0]]
                -> The system configuration has changed.
            
        Ex. 2:
            packet = [0, self.system.comms.config, False, [True, self.num_bytes]]
                -> Sending a record request.
        
        Ex. 3:
            packet =  [1, self.system.comms.config, False, [False, self.num_bytes]]
                -> Send trigger and number of bytes to server
        """

        try:
            self.trigger, self.config, self.config_change, [self.record_request, self.bytes_to_receive] = packet
            logging.debug("message received")
            logging.debug(f"""trigger: {self.trigger},
                          config: {self.config},
                          config_change: {self.config_change},
                          [rec request: {self.record_request}, btr: {self.bytes_to_receive}]""")
            return True
        except Exception:
            # TODO - is this how to use logging.debug? 
            logging.debug("message not received")
            return False
    
    def initiate_record2(self):
        self.shared_mem = SharedMemory(size=self.bytes_to_receive, create=True)
        self.shared_memory_name = self.shared_mem.name

        #Tell GUI the memory is allocated
        #self.push_data("allocated")
        #logging.debug("inform GUI executed")
        return self.shared_mem.name
    
    def record2(self):
        self.open_socket()
        if (self.initiate_transfer("recording") < 1):
            logging.debug("Socket type (record) not acknowledged by server")

        #Create view of shared memory buffer
        view = memoryview(self.shared_mem.buf)
        logging.debug("memory view created")
        logging.debug("{} to receive".format(self.bytes_to_receive))

        # wait for trigger confirmation from server - process may get stuck in
        # this loop if trigger acknowledgement is lost
        if (self.wait_for_ack() != 1):
            logging.debug("Record acknowledge not received")
            return

        logging.debug("start receive")

        while (self.bytes_to_receive):
            #Load info into array in nbyte chunks
            nbytes = self.socket.recv_into(view, self.bytes_to_receive)
            view = view[nbytes:]
            self.bytes_to_receive -= nbytes
            logging.debug(self.bytes_to_receive)

        self.purge_socket()
        self.close_socket()

        del view
        # self.push_data("data_ready")
        self.shared_mem.close()
        del self.shared_mem
        
        return 1
    
    def recording_process(self):
        """
        Do recording stuff

        Returns
        -------
        None.

        """
        # Set up socketlog.log debug log
        logging.basicConfig(filename='socketlog.log',
                            level=logging.DEBUG,
                            format='%(asctime)s %(message)s',
                            datefmt='%m/%d/%Y %I:%M:%S %p')

        logging.debug('Logfile initialised')
        log = logging.getLogger('socket')
        sys.stdout = StreamToLogger(log, logging.DEBUG)
        sys.stderr = StreamToLogger(log, logging.DEBUG)
        
        self.rec_process.start()
        self.rec_process.stop()
        
        
        
    



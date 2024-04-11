# -*- coding: utf-8 -*-
"""
RP_communications.py

data transfer into and out of the RedPitaya from the PC.

@author: cca78
"""
from multiprocessing import Process
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

        

        #State toggles and counters
        self.process = None
        self.bytes_to_receive = 0
        self.trigger = False

        #FPGA config dict
        self.config = FPGA_config()

        #Socket config
        self.port = port
        self.ip = ip
        self.socket = None
    
        
    # =========================================================================
    # Communications with the RP
    # =========================================================================
    def send_settings_to_FPGA(self):
        """
        Called by RP.update_FPGA_settings()
        Opens the socket and sends updates to the server by. Changes of settings
        made by the config dictionaries in RP.FPGA_config, RP.channel, and RP.CBC.
        
        Returns
        -------
        None.

        """
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
        
        
    def recording_process(self, shared_memory_name):
        """
        Called by RP.start_record()
        Opens a new parallel thread (process) to enable sampling measurments 
        from the RedPitaya hardware into a shared memory space.
                
        Parameters
        ----------
        shared_memory_name : TYPE 
            Reference to shared memory address(?)
            TODO2: add datatype (its a string?)

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
        
        self.rec_process = Process(target=self.record, args=(shared_memory_name,))   
        self.rec_process.start()
        self.rec_process.join()       
        self.rec_process.close()  
        
    def record(self, shared_memory_name):
        """
        Called by RP.start_record()
        This function is called as a Process item. Measurements from hardware 
        are taken and into a shared memory space. 
                
        Parameters
        ----------
        shared_memory_name : TYPE 
            Reference to shared memory address(?)
            TODO2: add datatype (its a string?)

        Returns
        -------
        None.
        
        """
        
        self.open_socket()
        if (self.initiate_transfer("recording") < 1):
            logging.debug("Socket type (record) not acknowledged by server")

        #Create view of shared memory buffer
        self.shared_mem = SharedMemory(name=self.shared_memory_name, size=self.bytes_to_receive, create=False)
        
        
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
        self.shared_mem.close()
        del self.shared_mem
    
    # =========================================================================
    # Complimentary functions for communications with the server.
    # =========================================================================
    def initiate_transfer(self, type='config'):
        """
        Called by RP.comms.record() and RP.comms.send_settings_to_FPGA()
        Send request info to MCU, await acknowledgement. Sends 4-byte 0 to 
        initiate config packet send, expect ack value of 2. Sends 
        "bytes to receive" value otherwise, expects ack value of bytes_to_receive.

        Parameters
        ----------
        type : string, optional
            Describes which function it is used for. The default is 'config'.

        Returns
        -------
        int
            Recieved acknowlegdement value from the socket.

        """
        
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
        """
        Called by RP.comms.record()
        Wait for an acknowledge byte from server. If no byte or incorrect
        value received, log error and return -1. Returns 1 on successful ack. 
        
        Parameters
        ----------
        ack_value : int, optional
            Expected acknowledgement value. The default is 1.

        Returns
        -------
        int
            Recieved acknowlegdement value from the socket.

        """
        
        

        ack = int.from_bytes(self.socket.recv(4), "little", signed=False)
        logging.debug("Ack value received: {}, expected {}".format(ack, ack_value))

        if ack == ack_value:
            return 1
        else:
            logging.debug("Bad acknowledge")
            return -1
    
    # =========================================================================
    # Socket-related functions
    # =========================================================================
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
        self.socket = None
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
            

        
   
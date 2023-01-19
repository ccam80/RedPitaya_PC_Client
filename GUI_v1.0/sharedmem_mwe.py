# -*- coding: utf-8 -*-
"""
Created on Thu Jul 22 12:20:49 2021

@author: acoustics
"""

from multiprocessing import Process, Queue
from multiprocessing.shared_memory import SharedMemory
import matplotlib.pyplot as plt
import traceback
from time import sleep
import numpy as np
import socket
import struct 

config = {"CIC_divider":1250,
          "ch1_freq":2,
          "ch2_freq":2,
          "ch1_ampl":32000,
          "ch2_ampl":32000}

# read_list, write_list, xlist = select.select([s], [s], [s], 60)
GUI_to_data_Queue = Queue()
data_to_GUI_Queue = Queue()

num_samples = 100000

def backgroundThread(q1, q2, num_samples):    # retrieve data
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
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
    s.connect((ip, port))
    bytes_to_receive=num_samples * 2
     
    shared_mem = SharedMemory(size=bytes_to_receive, create=True)
    shared_memory_name = shared_mem.name
               
    q2.put(shared_memory_name, block=True, timeout=1)
    awaiting_send = True
    while awaiting_send:
        try:
            go = q1.get(block=False)
            if go == 1:
                awaiting_send = False
        except:
            pass
            
    view = memoryview(shared_mem.buf)
    while bytes_to_receive:
        # print("start receive")
        nbytes = s.recv_into(view, bytes_to_receive)
        view = view[nbytes:]
        bytes_to_receive -= nbytes
            
    del view
    shared_mem.close()
    q2.put(1)
        
port=1001
ip="192.168.1.3"
   


# Pipe to send final data to main process






if __name__ == '__main__':
    __spec__ = None
    process = Process(target=backgroundThread, args=(GUI_to_data_Queue,data_to_GUI_Queue, num_samples, ))
    process.start()

    awaiting_read = True
    recording = np.zeros(0, dtype=np.int16)
    

    while awaiting_read:
        try:
            go = data_to_GUI_Queue.get(block=False)
            print(go)
            if type(go) == str:
                print(go)
                shared_mem_main = SharedMemory(name=go, size=num_samples * 2, create=False)
                GUI_to_data_Queue.put(1)
            elif go == 1:
                print(go)
                awaiting_read = 0
                temp = np.ndarray((num_samples), dtype=np.int16, buffer=shared_mem_main.buf)
                #copy into kept array
                #TODO: look at holding onto shared mem until next recording for speed
                recording = np.copy(temp)
                print("received data")
        except:
            pass
        
    plt.plot(recording)
    shared_mem_main.close()
    shared_mem_main.unlink()
    del temp
    
    
    # process.terminate()
    
    
    # process = Process(target=backgroundThread, args=(GUI_to_data_Queue,data_to_GUI_Queue, num_samples, ))
    # process.start()

    awaiting_read = True
    recording = np.zeros(0, dtype=np.int16)
    

    while awaiting_read:
        try:
            go = data_to_GUI_Queue.get(block=False)
            print(go)
            if type(go) == str:
                print(go)
                shared_mem_main = SharedMemory(name=go, size=num_samples * 2, create=False)
                GUI_to_data_Queue.put(1)
            elif go == 1:
                print(go)
                awaiting_read = 0
                temp = np.ndarray((num_samples), dtype=np.int16, buffer=shared_mem_main.buf)
                #copy into kept array
                #TODO: look at holding onto shared mem until next recording for speed
                recording = np.copy(temp)
                print("received data")
        except:
            pass
        
    plt.plot(recording)
    shared_mem_main.close()
    shared_mem_main.unlink()
    del temp
    
    
    process.terminate()
    print('Disconnected...')
        # df = pd.DataFrame(self.csvData)
        # df.to_csv('/home/rikisenia/Desktop/data.csv')

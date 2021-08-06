# -*- coding: utf-8 -*-
"""
Spyder Editor

This is a temporary script file.
"""

import socket
import numpy as np
import matplotlib.pyplot as plt
import struct
import select
from time import sleep

config = {"CIC_divider":1250,
          "f_out":2,
          "f_out_2":2,
          "mult0":32000,
          "mult1":32000}


buff_depth = 256 * 1024

buffer = bytearray(buff_depth)




print("connected")

config_change = False 

format_ = "HIIHH"
config_send = struct.pack(format_,                
                          config["CIC_divider"],
                          config["f_out"],
                          config["f_out_2"],
                          config["mult0"],
                          config["mult1"])


        
      
    # print("packet saved")

s.send(config_send)
# sleep(0.5)
# s.connect((ip, port))
read_list, write_list, xlist = select.select([s], [s], [s], 60)

                                                 
# if s in write_list:
#     s.send(config)





plt.figure()
plt.plot(tdata)

s.close()
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
s.connect((ip, port))

view = memoryview(buffer)
toread = buff_depth
while toread:
    # print("start receive")
    nbytes = s.recv_into(view, toread)
    view = view[nbytes:]
    toread -= nbytes
    
plt.figure()
plt.plot(tdata)

s.close()
# -*- coding: utf-8 -*-
"""
Created on Thu Aug  3 10:11:24 2023

@author: cca78

system.py

Under-the-hood functions which take user inputs from RedPitaya.py and modify the
system_config dictionary values accordingly
"""
from system_config import system_config
from FPGA_config import FPGA_config

class system:
# _datatypes = {"continuous_output": bool,
#             "ip_address": str,
#             "sampling_rate": str,
#             "recording_duration": float
#             }
    

    def __init__(self):
        self.config = system_config()
        self.FPGA = FPGA_config()
    def set_continuous_output(self, cont_output):
        if cont_output:
            self.config["continuous_output"] = True
        else:
            self.config["continuous_output"] = False
            
    def set_sampling_rate(self, rate):
        if rate == "fast":
            self.config["sampling_rate"] = "fast"
        elif rate == "slow":
            self.config["sampling_rate"] = "slow"
        else:
            raise ValueError("'rate' must be either 'fast' or 'slow'")
    
    # TODO4: is recording duration different from the ones set in Channel and CBC? 
    
    # TODO5: setting IP address requires some protection and/or checking that the value set is correct. 
    def set_IP_address(self, ip_address):
        self.config["ip_address"] = ip_address
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
from RP_communications import RP_communications
from re import match
import traceback

_default_init = {"continuous_output": False,
            "ip_address": "192.168.1.3",
            "sampling_rate": "fast",
            "duration": 1.1
            }



class system:
    def __init__(self, default_values=_default_init):

                
        self.config = system_config(default_values = default_values)
        if self.config.ip_address:
            self.comms = RP_communications(ip=self.config.ip_address)
        else:
            self.comms = RP_communications(ip=self._default_init['ip_address'])

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

    def start_comms(self):
        try:
            self.comms.start_process()
            return True 
        except Exception:
            print(traceback.format_exc())
            return False
        
    def set_IP_address(self, ip_address):
        self.config["ip_address"] = ip_address

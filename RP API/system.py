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
import logging

_default_init = {"continuous_output": False,
            "ip_address": "192.168.1.3",
            "sampling_rate": "slow",
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
        
        
        
    # ***************************************************
    # Seigan Development - Untested
    # Wild wild west of bad code goes here
    # ***************************************************
    def send_settings_to_FPGA(self):
        self.comms.send_settings_to_FPGA()
        
    def prepare_record(self):
        return self.comms.initiate_record2()
        
    def trigger_record(self):
        # TODO: Is it required to send settings to FPGA before & after? Probably was explained but need a reminder again.
        
        
        # self.trigger = 1
        #self.comms.send_settings_to_FPGA()     # TODO: Uncomment when using with physical hardware
        logging.debug("{} to receive".format(self.comms.bytes_to_receive))  # TODO: bytes_to_recieve is a packet item. Need to check whether this will cause a hissy fit or not

        self.comms.recording_process()

        # self.trigger = 0
        #self.comms.send_settings_to_FPGA()     # TODO: Uncomment when using with physical hardware
        logging.debug("Trigger off sent")
        

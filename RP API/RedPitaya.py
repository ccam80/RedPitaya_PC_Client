# -*- coding: utf-8 -*-
"""
Created on Thu Jul 20 16:50:13 2023

@author: cca78
"""
from channel_config import channel_config
from CBC_config import CBC_config
from system_config import system_config

default_CH1_example = {"mode": "fixed_frequency",
                       "frequency_start": 100,
                       "frequency_stop": 0,
                       "frequency_sweep": False,
                       "fixed_amplitude": 100,
                       "fixed_offset": 100,
                       "A_start": 0,
                       "A_stop": 0,
                       "A_sweep": False,
                       "B_start": 0,
                       "B_stop": 0,
                       "B_sweep": False,
                       "fixed_x_coeff": 0,
                       "fixed_x2_coeff": 0,
                       "fixed_x3_coeff": 0,
                       "artificial_nonlinearity_gain1": 0,
                       "input_channel": 1}


system_settings_start = {'continuous_output': 0,
                         'ip_address': "192.168.1.3",
                         'sampling_rate': 'slow'}

class RedPitaya():
    """ RedPitaya class opens connection with redpitaya and instantiates config.
    API methods take user requests and modify config dictionaries, before
    calling functions from memory_mapping.py which convert to FPGA memory space
    and send them to the FPGA."""

    def __init__(self):

        self.CH1 = channel_config(default_CH1_example)
        self.CH2 = channel_config()
        self.CBC = CBC_config()

        # Chris to insert connection to network stuff here

    def set_frequency(self, channel, frequency):
        """Assume a fixed frequency if someone is calling "set_frequency" with
        only one frequency argument. If argument is a tuple or list of 2,
        set start and stop frequencies, and turn sweep on. """

        # Sanitise channel input
        if channel not in [1, 2, "CBC"]:
            raise ValueError("Invalid 'channel' value. It must be 1, 2, or 'CBC'.")

        if isinstance(frequency, (float, int)):
            if channel == 1:
                self.CH1.frequency_start = frequency
                self.CH2.frequency_sweep = False
            elif channel == 2:
                self.CH2.frequency_start = frequency
                self.CH2.frequency_sweep = False
            elif channel == 'CBC':
                self.CH2.frequency_start = frequency
                self.CH2.frequency_sweep = False



        elif isinstance(frequency, (list, tuple)):
            if len(frequency) > 2:
                print("Warning: 'frequency' list or tuple should contain at most two elements. Extra elements will be ignored.")
            if channel == 1:
                self.CH1.frequency_start = frequency[0]
                self.CH1.frequency_stop = frequency[1]
                self.CH1.frequency_sweep = True
            elif channel == 2:
                self.CH2.frequency_start = frequency[0]
                self.CH2.frequency_stop = frequency[1]
                self.CH2.frequency_sweep = True
            elif channel == 'CBC':
                self.CBC.f_start = frequency[0]
                self.CBC.f_stop = frequency[1]
                self.CBC.f_sweep = True


        else:
            raise TypeError("'frequency' must be a single float or a list/tuple of two floats.")

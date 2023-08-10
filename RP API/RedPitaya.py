# -*- coding: utf-8 -*-
"""
Created on Thu Jul 20 16:50:13 2023

@author: cca78
"""
from channel import channel
from CBC import CBC
from system import system

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

sweep_CHx = ["frequency",
              "A",
             "B",
             ]

sweep_CBC = ["r_hat",
              "f",
              "A",
             "B",
             "C",
             "D"]

class RedPitaya():
    """ RedPitaya class opens connection with redpitaya and instantiates config.
    API methods take user requests and modify config dictionaries, before
    calling functions from memory_mapping.py which convert to FPGA memory space
    and send them to the FPGA."""

    def __init__(self):

        # self.CH1 = channel(default_CH1_example)
        self.CH1 = channel()
        self.CH2 = channel()
        self.CBC = CBC()
        self.system = system()
        # TODo: Chris to insert connection to network stuff here
        
        
    def reset_config(self, channel):
        if channel == "CBC":
            self.CBC = CBC()
        elif channel == "CH1":
            self.CH1 = channel()
        elif channel == "CH2":
            self.CH2 = channel()
        elif channel == "system":
            self.system = system()
            
            
    def print_config(self, channel):
        if channel == "CH1":
            self.CH1.print_config()
        elif channel == "CH2":
            self.CH2.print_config()
        elif channel == "CBC":
            self.CBC.print_config()
        elif channel == "Both":
            print ("{:<20} {:<20} {:<20} ".format("Key", "Channel 1", "Channel 2"))
            for key in self.CH1.config.keys():
                print ("{:<20} {:<20} {:<20} ".format(key, str(self.CH1.config[key]), str(self.CH2.config[key])))
            print()
        else:
            raise ValueError("'channel' must be be either 'CH1', 'CH2' or 'Both', or 'CBC'.")
        
    
    # I believe this function is somewhat redundant, as there is a "set_freq" 
    # function that will allow the user to se 
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

    
    def choose_input_channel(self, channel, input_channel):
        if channel not in ["CH1", "CH2", "CBC", "Both"]:
            raise ValueError("Invalid 'channel' value. It must be 'CH1', 'CH2', or 'Both'.")
        if channel == "CBC":
            raise ValueError("Input channel cannot be set for CBC. It must be 'CH1', 'CH2', or 'Both'.")
        
        if channel == "Both":
            self.set_param("CH1", "input_channel", input_channel)
            self.set_param("CH2", "input_channel", input_channel)
        elif channel == "CH1":
            self.set_param("CH1", "input_channel", input_channel)
        elif channel == "CH2":
            self.set_param("CH2", "input_channel", input_channel)
        
        
        
    
    def choose_mode(self, channel, mode, **kwargs):
        """
        Sets an output mode for a determined channel.
        """
        if channel not in ["CH1", "CH2", "CBC", "Both"]:
            raise ValueError("Invalid 'channel' value. It must be 'CH1', 'CH2', or 'Both'.")
        if channel == "CBC":
            raise ValueError("Output mode cannot be set for CBC. It must be 'CH1', 'CH2', or 'Both'.")

        if channel == "Both":
            self.CH1.set_mode(mode)
            self.CH2.set_mode(mode)
        elif channel == "CH1":
            self.CH1.set_mode(mode, **kwargs)
        elif channel == "CH2":
            self.CH2.set_mode(mode, **kwargs)
    
    
    def choose_input_order(self, input_channel):            
        if input_channel in [1, 2]:
            self.CBC.set_input_order(input_channel) 
        else:
            raise ValueError("'input_channel' must be either 1 or 2.")
    
    
    def choose_polynomial_target(self, target):        
        if target in ["displacement", "velocity"]:
            self.CBC.set_polynomial_target(target)
        else:
            raise ValueError("'target' must be either 'displacement' or 'velocity'.")
        
        

    def choose_external_input_type(self, target):
        """
        Determines whether the external input is given as a displacement or
        velocity signal. This function should be used to protect against
        setting both to "True" at any given time.
        """        
        if target in ['displacement', 'velocity']:
            self.CBC.set_external(target)
        else:
            raise ValueError("'target' must be either 'displacement' or 'velocity'.")

    
    def choose_output(self, output_mode, CHx_mode=None):
        """
        Determines whether the output channels are configured as "CBC" or as
        "Channels". Different operating modes will use different parameter
        structures. Turning on an output type will disable the other.

        If using the channel outputs, an optional mode can be given.

        Usage:
            RP.set_output("CBC")
                -> Sets the outputs to "CBC"

            RP.set_output("CHx")
                -> Sets the outputs to "Channels"

            RP.set_output("CHx", "linear")
                -> Sets the outputs to "Channels", using the linear feedback mode.
        """
        
        if output_mode == "CHx":
            if isinstance(CHx_mode, str):
                CH1_mode = CHx_mode
                CH2_mode = CHx_mode
            elif isinstance(CHx_mode, (list, tuple)):
                if len(CHx_mode) < 2:
                    CH1_mode = CHx_mode[0]
                    CH2_mode = CHx_mode[0]
                else:
                    CH1_mode = CHx_mode[0]
                    CH2_mode = CHx_mode[1]
                if len(CHx_mode) > 2:
                    print("Warning: Only first two '*CHx_mode' arguments are considered. Additional arguments will be ignored.")
            
            self.CH1.set_mode(CH1_mode)
            self.CH2.set_mode(CH2_mode)
            self.CBC.config["CBC_enabled"] = False
        elif output_mode == "CH1":
            self.CH1.set_mode(CHx_mode)
            self.CBC.config["CBC_enabled"] = False
        elif output_mode == "CH2":
            self.CH2.set_mode(CHx_mode)
            self.CBC.config["CBC_enabled"] = False
        elif output_mode == "CBC":
            if CHx_mode:
                print("Warning: 'CHx_mode' arguments are not used in CBC mode, and will be ignored.")
            self.CH1.set_mode('off')
            self.CH2.set_mode('off')
            self.CBC.config["CBC_enabled"] = True
        else:
            raise ValueError("'output_mode' must be either 'CH1', 'CH2', 'Both' or 'CBC'.")
            
            
            
            
            
            
            
            
            
    def set_param(self, channel, param, value):
        if channel == "CH1":
            self.CH1.set_param(param, value)
        elif channel == "CH2":
            self.CH2.set_param(param, value)
        elif channel == "CBC":
            self.CBC.set_param(param, value)
        else:
            raise ValueError("'channel' must be be either 'CH1', 'CH2' or 'CBC'.")
            
   
    def params_from_dict(self, channel, dicts):
        """
        Takes a dictionary of {key: value} corresponding to parameter values for
        a given channel, and sets them in the relevant %%%_config dictionaries. 
        The intended usage of this function is to take parameter values from the GUI .
        """
        # TODO: @Chris - Would we need a function that takes GUI elements and 
        # saves them within a dictionary for this function? 
        # Additionally, for two output channels the function would need to know
        # to update both CH1 and CH2.
        
        if not dicts:
            raise ValueError("'dicts' is empty, meaning no parameters have been set.")
        
        
        if channel in ["CH1", "CH2", "CBC"]:
            for key, value in dicts.items():                
                self.set_param(channel, key, value)
        else:
            raise KeyError("'channel' must be either 'CH1', 'CH2' or 'CBC'.")
            
            
            
    def set_a(self, channel, value):
        self.set_param(channel, "a", value)
        
    def set_b(self, channel, value):
        self.set_param(channel, "b", value)
        
    def set_c(self, channel, value):
        self.set_param(channel, "c", value)
        
    def set_d(self, channel, value):
        self.set_param(channel, "d", value)
        
    def set_p3(self, channel, value):
        self.set_param(channel, "p3", value)
        
    def set_p2(self, channel, value):
        self.set_param(channel, "p2", value)
        
    def set_p1(self, channel, value):
        self.set_param(channel, "p1", value)
        
    def set_p0(self, channel, value):
        self.set_param(channel, "p0", value)
        
    def set_freq(self, channel, value):
        self.set_param(channel, "frequency", value)
    
            
        
    def set_duration(self, channel, value):
        self.set_param(channel, "duration", value)
        
    def set_gains(self, channel, gains):
        if channel == "CBC":
            if isinstance(gains, (list, tuple)) and len(gains) > 1: 
                self.CBC.set_param('kp', gains[0])
                self.CBC.set_param('kd', gains[1])
            if isinstance(gains, (list, tuple)) and len(gains) == 1:
                self.CBC.set_param('kp', gains[0])
                self.CBC.set_param('kd', 0)
                print("Warning - only one value found in 'gains'. Value for kd has been ignored.")
            elif isinstance(gains, (float, int)):   
                self.CBC.set_param('kp', gains)
                self.CBC.set_param('kd', 0)
                print("Warning - only one value found in 'gains'. Value for kd has been ignored.")
        else:
            raise ValueError("'channel' must be be 'CBC'.")
    
    def set_rhat(self, channel, values):
        if channel == "CBC":
            self.set_param(channel, "r_hat", values)
        else:
            raise ValueError("'channel' must be be 'CBC'.")
            
    
            
    
            
    
        
            
            
        
            
            
        
    
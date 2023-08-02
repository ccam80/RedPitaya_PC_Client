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

        self.CH1 = channel(default_CH1_example)
        self.CH2 = channel()
        self.CBC = CBC()
        self.system = system()

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

    ### set_mode - made redundant through channel_config functions.
    # def set_mode(self, channel, mode, params=None):
    #     """
    #     Sets an output mode for a determined channel.
    #     """
    #     if channel not in [1, 2, "CBC", "Both"]:
    #         raise ValueError("Invalid 'channel' value. It must be 1, 2, or 'Both'.")
    #     if channel == "CBC":
    #         raise ValueError("Output mode cannot be set for CBC. It must be 1, 2, or 'Both'.")

    #     if channel == "Both":
    #         self.CH1.mode = mode
    #         self.CH2.mode = mode
    #     elif channel == 1:
    #         self.CH1.mode = mode
    #     elif channel == 2:
    #         self.CH2.mode = mode

    ### set_sweep - made redundant through shared_config functions.
    # def set_sweep(self, channel, param, sweep_range):
    #     # TODO: "f" and "frequency" used for CBC and channel respectively.
    #     # Should be unified into just "f" for simplicity.


    #     if channel not in [1, 2, "CBC", "Both"]:
    #         raise ValueError("Invalid 'channel' value. It must be 1, 2, or 'Both'.")
    #     elif channel in [1, 2, "Both"] and param not in sweep_CHx:
    #         raise ValueError("Invalid 'param' value. It must be 'A', 'B', or 'frequency'")
    #     elif channel == "CBC" and param not in sweep_CBC:
    #         raise ValueError("Invalid 'param' value. It must be 'A', 'B', 'C', 'D', 'frequency', or 'r_hat.")
    #     else:
    #         p_start = param + "_start"
    #         p_stop = param + "_stop"
    #         p_sweep = param + "_sweep"


    #     if isinstance(sweep_range, (float, int)):
    #         print("Warning: Only one value found within 'sweep_range'. Parameter to be held constant and sweep turned off.")
    #         start = sweep_range
    #         stop = 0
    #         sweep = False

    #     if isinstance(sweep_range, (list, tuple)):
    #         if len(sweep_range) > 2:
    #             print("Warning: 'sweep_range' list or tuple should contain at most two elements. Extra elements will be ignored.")
    #             sweep_range = sweep_range[0:2]
    #         if len(sweep_range) == 1 or len(set(sweep_range)) == 1:
    #             print("Warning: Only one unique value found within 'sweep_range'. Parameter to be held constant and sweep turned off.")
    #             start = sweep_range[0]
    #             stop = 0
    #             sweep = False
    #         else:
    #             start = sweep_range[0]
    #             stop = sweep_range[1]
    #             sweep = True


    #     if channel == "Both":
    #         self.CH1[p_start] = start
    #         self.CH1[p_stop] = stop
    #         self.CH1[p_sweep] = sweep
    #         self.CH2[p_start] = start
    #         self.CH2[p_stop] = stop
    #         self.CH2[p_sweep] = sweep
    #     elif channel == 1:
    #         self.CH1[p_start] = start
    #         self.CH1[p_stop] = stop
    #         self.CH1[p_sweep] = sweep
    #     elif channel == 2:
    #         self.CH2[p_start] = start
    #         self.CH2[p_stop] = stop
    #         self.CH2[p_sweep] = sweep
    #     elif channel == "CBC":
    #         self.CBC[p_start] = start
    #         self.CBC[p_stop] = stop
    #         self.CBC[p_sweep] = sweep


    def choose_external_input_type(self, target):
        """
        Determines whether the external input is given as a displacement or
        velocity signal. This function should be used to protect against
        setting both to "True" at any given time.
        """
        if target in ["displacement", "disp"]:
            self.CBC["velocity_external"] = False
            self.CBC["displacement_external"] = True
        elif target in ["velocity", "vel"]:
            self.CBC["velocity_external"] = True
            self.CBC["displacement_external"] = False
        else:
            raise ValueError("'target' must be either 'displacement' or 'velocity'.")



    def set_output(self, output_mode, *CHx_mode):
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
            if len(CHx_mode) > 0:
                if len(CHx_mode) == 1:
                    CH1_mode = CHx_mode[0]
                    CH2_mode = CHx_mode[0]
                elif len(CHx_mode) == 2:
                    CH1_mode = CHx_mode[0]
                    CH2_mode = CHx_mode[1]
                elif len(CHx_mode) > 2:
                    print("Warning: Only first two '*CHx_mode' arguments are considered. Additional arguments will be ignored.")
                    CH1_mode = CHx_mode[0]
                    CH2_mode = CHx_mode[1]
                self.CH1["mode"] = CH1_mode
                self.CH2["mode"] = CH2_mode
            self.CBC["CBC_enabled"] = False
        elif output_mode =="CBC":
            if len(CHx_mode) > 0:
                print("Warning: '*CHx_mode' arguments are not used in CBC mode, and will be ignored.")
            self.CH1["mode"] = "off"
            self.CH2["mode"] = "off"
            self.CBC["CBC_enabled"] = True
        else:
            raise ValueError("'output_mode' must be either 'CHx' or 'CBC'.")

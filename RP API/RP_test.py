# -*- coding: utf-8 -*-
"""
Created on Thu Jul 20 21:55:49 2023

@author: cca78

############ Example of a typical experimental run-through ############
# RP = RedPitaya()                                              # Intiialise RP object
# ...                                                           # Set measurement controls (Sampling rate, sampling period, etc)
# RP.set_output("CHx")                                          # Choose channels (turn off CBC)
# RP.CH1.set_mode("linear")                                     # Set the output mode(s)
# RP.CH1.set_params_linear(A=1, B=[2, 5], input_channel=1):     # Set the parameters for corresponding output(s)
# for a in range(10):
#     RP.CH1.set_params_linear(A=a)                             # Set the parameters for corresponding output(s)
#     ...                                                       # Send configuration to FPGA
#     ...                                                       # Conduct/save experiments
#     ...                                                       # Post-analysis (if required)
############ End of example ############

############ Example of a typical experimental run-through ############
# RP = RedPitaya()                                              # Intiialise RP object
# ...                                                           # Set measurement controls (Sampling rate, sampling period, etc)
# RP.set_output("CBC")                                          # Choose channels (turn off CBC)
# RP.CBC.set_params_CBC(A=5, B=[4,10])                          # Set the parameters for corresponding output(s)
# for val in range(10):
#     RP.CBC.set_params_linear(rhat=val)                        # Set the parameters for corresponding output(s)
#     ...                                                       # Send configuration to FPGA
#     ...                                                       # Conduct/save experiments
#     ...                                                       # Post-analysis (if required)
############ End of example ############
"""

from RedPitaya import RedPitaya
from mem_mapping import update_FPGA_channel
from channel_config import _channel_modes
import numpy as np
import traceback
import matplotlib.pyplot as plt
import logging

logging.getLogger("matplotlib").setLevel(logging.WARNING)




default_CH1_example = {"mode": 'frequency_sweep',
                       "input_channel": 1,
                       "frequency_start": 1,
                       "frequency_stop": 100,
                       "frequency_sweep": True,
                       "linear_amplitude_start": 1000,
                       "linear_amplitude_stop": 0,
                       "linear_amplitude_sweep": False,
                       "offset_start": 0,
                       "offset_stop": 0,
                       "offset_sweep": False,
                       "cubic_amplitude_start": 0,
                       "cubic_amplitude_stop": 0,
                       "cubic_amplitude_sweep": False,
                       "quadratic_amplitude_start": 0,
                       "quadratic_amplitude_stop": 0,
                       "quadratic_amplitude_sweep": False,
                       "duration": 1.0
                       }

default_CH2_example = {"mode": 'linear_feedback',
                       "input_channel": 1,
                       "frequency_start": 0,           # in Hz
                       "frequency_stop": 0,             # in Hz
                       "frequency_sweep": False,
                       "linear_amplitude_start": 10,
                       "linear_amplitude_stop": 0,
                       "linear_amplitude_sweep": False,
                       "offset_start": 500,        # mV
                       "offset_stop": 0,        # mV
                       "offset_sweep": False,
                       "cubic_amplitude_start": 0,  
                       "cubic_amplitude_stop": 0,
                       "cubic_amplitude_sweep": False,
                       "quadratic_amplitude_start": 0,
                       "quadratic_amplitude_stop": 0,
                       "quadratic_amplitude_sweep": False,
                       "duration": 1.0
                       }

default_CBC_example = {"CBC_enabled": False,
                       "input_order": 1 , # The channel which displacement goes into
                       "polynomial_target": 'displacement',
                       "proportional_gain": 0,
                       "derivative_gain": 0,
                       "reference_amplitude_start": 0,          # Value in [0, 1] depicicting the proportion of the reference amplitude
                       "reference_amplitude_stop": 0,
                       "reference_amplitude_sweep": False,
                       "frequency_start": 0,
                       "frequency_stop": 0,
                       "frequency_sweep": False,
                       "linear_amplitude_start": -10,          # Representing mV/units
                       "linear_amplitude_stop": 0,
                       "linear_amplitude_sweep": False,
                       "quadratic_amplitude_start": 0,
                       "quadratic_amplitude_stop": 0,
                       "quadratic_amplitude_sweep": False,
                       "cubic_amplitude_start": 0,
                       "cubic_amplitude_stop": 0,
                       "cubic_amplitude_sweep": False,
                       "offset_start": 900,                     # Value in [-1000, 1000], representing mV output offset
                       "offset_stop": 0,
                       "offset_sweep": True,
                       "duration": 0.5}

# default_config =    {"CBC_enabled": True,
#                        "input_order": 1,
#                        "velocity_external": True,
#                        "displacement_external": False,
#                        "polynomial_target": 'displacement',
#                        "proportional_gain": 1.1,
#                        "derivative_gain": 1.2,
#                        "reference_amplitude_start": 100,
#                        "reference_amplitude_stop": 200,
#                        "reference_amplitude_sweep": True,
#                        "frequency_start": 100,
#                        "frequency_stop": 10000,
#                        "frequency_sweep": True,
#                        "linear_amplitude_start": 0,
#                        "linear_amplitude_stop": 1,
#                        "linear_amplitude_sweep": True,
#                        "quadratic_amplitude_start": 0,
#                        "quadratic_amplitude_stop": 1,
#                        "quadratic_amplitude_sweep": True,
#                        "cubic_amplitude_start": 0,
#                        "cubic_amplitude_stop": 1,
#                        "cubic_amplitude_sweep": True,
#                        "offset_start": 0,
#                        "offset_stop": 1,
#                        "offset_sweep": False,
#                        "duration": 0.4}

default_system = {"continuous_output": False,
                  "ip_address": "192.168.1.3",
                  "sampling_rate": "slow",
                  "duration": 1.0}

RP = RedPitaya(CH1_init=default_CH1_example,
               CH2_init=default_CH2_example,
               CBC_init=default_CBC_example,
               system_init=default_system)

if __name__ == '__main__':
    
    # f0=1, f1 = 10, T=4secs -> weird
    
    # RP.start()
    
    # RP.choose_output("CBC")
    # RP.choose_CBC_input_order("displacement", "none")
    RP.set_duration(3)
    # RP.print_config("CBC")
    
    RP.update_FPGA_settings()
    # RP.start_record(savename="Bug8_2")
    RP.start_record()         # Run this if you don't care about renaming filename
    # RP.close_recording()
    
    RP.PlotRecording()

    
    
    
# RP.reset_config('CH1')
# RP.reset_config("CH2")
# RP.reset_config("CBC")


# # Example: Linear Feedback
# out_channel = "CH1"
# RP.choose_output(out_channel, "linear_feedback")
# RP.choose_channel_input(out_channel, 1)
# RP.set_linear_amplitude(out_channel, [100, 200])
# RP.set_offset(out_channel, 1)
# RP.print_config('Both')

# # Example: cubic feedback
# out_channel = "CH2"
# RP.choose_output(out_channel, "cubic")
# RP.choose_channel_input(out_channel, 2)
# RP.set_cubic_amplitude(out_channel, 50)
# RP.set_quadratic_amplitude(out_channel, 50)
# RP.print_config('Both')



# for mode in _channel_modes:
#     RP.set_mode(1, mode)
#     update_FPGA_channel(1, RP.CH1.config, RP.system.FPGA)
#     update_FPGA_channel(2, RP.CH2.config, RP.system.FPGA)
#     print(mode)
#     for key, item in RP.system.FPGA.items():
#         print(f'{key}: {item}')
#     print("")

#     update_FPGA_channel('CBC', RP.CBC.config, RP.system.FPGA)
#     RP.print_config("CBC")

#     for key, item in RP.system.FPGA.items():
#         print(f'{key}: {item}')
#     print("")

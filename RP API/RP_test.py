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

default_CH1_example = {"mode": 'fixed_frequency',
                       "input_channel": 1,
                       "frequency_start": 100,
                       "frequency_stop": 1000,
                       "frequency_sweep": True,
                       "linear_amplitude_start": 0,
                       "linear_amplitude_stop": 1,
                       "linear_amplitude_sweep": True,
                       "offset_start": 100,
                       "offset_stop": 200,
                       "offset_sweep": True,
                       "cubic_amplitude_start": 0,
                       "cubic_amplitude_stop": 0,
                       "cubic_amplitude_sweep": False,
                       "quadratic_amplitude_start": 0,
                       "quadratic_amplitude_stop": 0,
                       "quadratic_amplitude_sweep": False,
                       "duration": 1.1
                       }

RP = RedPitaya(CH1_init=default_CH1_example)


# RP.set_frequency('CBC', 1000)
# RP.set_frequency(1, [1000,200000])
# RP.CH1.frequency_sweep

# RP.CBC.polynomial_target = "displacement"
# # RP.CBC.polynomial_target = "blargh"
# RP.CH1.mode = "linear_feedback"

# RP.CH1.set_params_cubic()
# RP.choose_output("CHx")

RP.set_mode("CH1", 'linear_feedback')
RP.CH1.set_params_noise(linear_amplitude=[5, -100], offset=[1,100])
RP.print_config("Both")




RP.print_config("CBC")
for mode in _channel_modes:
    RP.set_mode(1, mode)
    update_FPGA_channel(1, RP.CH1.config, RP.system.FPGA)
    print(mode)
    for key, item in RP.system.FPGA.items():
        print(f'{key}: {item}')
    print("")

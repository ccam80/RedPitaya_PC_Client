# -*- coding: utf-8 -*-
"""
Created on Thu Jul 20 21:55:49 2023

@author: cca78
"""

from RedPitaya import RedPitaya

RP = RedPitaya()

RP.set_frequency('CBC', 1000)
RP.set_frequency(1, [1000,200000])
RP.CH1.frequency_sweep

RP.CBC.polynomial_target = "displacement"
# RP.CBC.polynomial_target = "blargh"
RP.CH1.mode = "linear_feedback"




### Typical go-through of a sweep
# Set measurement controls (Sampling rate, sampling period, etc)
# Choose channels (turn off CBC)                                    RP.set_output(output_type, optional: mode)
# Set the input channels                                            RP.CH1.set_input_channel(input_num)
# Set the output mode(s)                                            RP.CH1.set_mode(mode_type, optional: parameters)
# Set the parameters for corresponding output(s)                    RP.CH1.set_params(parameter_name, value)

# Send config to FPGA
# Conduct experiment/save measurements
# Update parameters, repeat


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
# RP.CH1.mode = "blarg"

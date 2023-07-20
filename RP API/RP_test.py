# -*- coding: utf-8 -*-
"""
Created on Thu Jul 20 21:55:49 2023

@author: cca78
"""

from RedPitaya import RedPitaya

RP = RedPitaya()

RP.set_frequency(1, [100,1000])

RP.CH1.frequency_sweep

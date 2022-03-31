# -*- coding: utf-8 -*-
"""
Created on Thu Nov  4 11:44:21 2021

@author: acoustics
"""

import numpy as np
import matplotlib.pyplot as plt

plt.close('all')

freq = np.linspace(0,30000,num=30000)
phase = (freq * 2**30) / 125000000

plt.figure()
plt.plot(phase)


freqspan = 100
duration = 10

span = freqspan * 2**30 / 125000000
clocks = 125000000 * duration

interval = clocks/span

maxval = 2**30



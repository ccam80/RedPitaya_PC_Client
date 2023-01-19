# -*- coding: utf-8 -*-
"""
Created on Thu Mar 17 12:12:08 2022

@author: acoustics
"""

import matplotlib.pyplot as plt
import numpy as np

plt.close('all')
data = np.genfromtxt("./Data/Filename5.csv", delimiter=",", skip_header=1)

plt.plot(data[1].byteswap())
input_unmathed = data[0] * GUI_w.adc_scale + GUI_w.adc_0
plt.plot(input_unmathed)
plt.plot(np.int16(data[1]).byteswap())



diff = np.diff(data)
in_diff = diff[np.abs(diff) > 10]
in_indices = np.argwhere(np.abs(diff) > 10)
bigdiff

data[indices-1:indices+1]

addition = data[1] + input_unmathed
subtraction = data[1] - input_unmathed
mean = (data[1] + input_unmathed) / 2

plt.plot(addition)
plt.plot(subtraction)
plt.plot(mean)

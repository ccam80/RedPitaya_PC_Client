# -*- coding: utf-8 -*-
"""
Created on Thu Mar 17 12:12:08 2022

@author: acoustics
"""

import matplotlib.pyplot as plt
import numpy as np

data = np.genfromtxt("./Data/1mhz0.csv", delimiter=",", skip_header=1)

plt.plot(data[1])
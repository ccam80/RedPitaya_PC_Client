# -*- coding: utf-8 -*-
"""
Created on Thu May 11 16:06:12 2023

@author: acoustics
"""


import numpy as np
import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches

#%% Import

datapath = "./Data/"


fs = 488281

square = np.genfromtxt(datapath + "squared0.csv",
                       delimiter=";",
                       encoding='UTF-8')
cube = np.genfromtxt(datapath + "cubed0.csv",
                       delimiter=";",
                       encoding='UTF-8')
linear = np.genfromtxt(datapath + "linear0.csv",
                       delimiter=";",
                       encoding='UTF-8')

time = np.linspace(0, 1, num=len(square)) 

#%% Break up & interpret




square_in = square[:,0] / 1000
square_out = square[:,1] / 1000

cube_in = cube[:,0] / 1000
cube_out = cube[:,1] / 1000

linear_in = linear[:,0] / 1000
linear_out = linear[:,1] / 1000

plt.close('all')

fig, ax = plt.subplots(2,3, sharex='col', layout='constrained')
ax = ax.ravel()

ax[0].plot(time, linear_in, color="#0072BD")
ax[0].set_title("V_out = V_in")
ax[3].plot(time, linear_out, color="#0072BD")
ax[3].set_xlabel("Time (s)")
ax[0].set_ylabel("V_in (V)")
ax[3].set_ylabel("V_out (V)")

ax[1].plot(time, square_in, color="#0072BD")
ax[1].set_title("V_out = V_in^2")
ax[4].plot(time, square_out, color="#0072BD")
ax[4].set_xlabel("Time (s)")

ax[2].plot(time, cube_in, color="#0072BD")
ax[2].set_title("V_out = V_in^3")
ax[5].plot(time, cube_out, color="#0072BD")
ax[5].set_xlabel("Time (s)")



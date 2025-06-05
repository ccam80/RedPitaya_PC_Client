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
import time

logging.getLogger("matplotlib").setLevel(logging.WARNING)




default_CH1_example = {"mode": 'artificial_nonlinearity_parametric',
                       "input_channel": 2,
                       "frequency_start": 5,           # in Hz
                       "frequency_stop": 0,             # in Hz
                       "frequency_sweep": False,
                       "linear_amplitude_start": 1.0,
                       "linear_amplitude_stop": 0,
                       "linear_amplitude_sweep": False,
                       "offset_start": -0,        # mV
                       "offset_stop": 0,        # mV
                       "offset_sweep": False,
                       "cubic_amplitude_start": 0,  
                       "cubic_amplitude_stop": 0,
                       "cubic_amplitude_sweep": False,
                       "quadratic_amplitude_start": 0,
                       "quadratic_amplitude_stop": 0,
                       "quadratic_amplitude_sweep": False,
                       "duration": 5.0
                       }

default_CH2_example = {"mode": 'artificial_nonlinearity',
                       "input_channel": 1,
                       "frequency_start": 500e3,           # in Hz
                       "frequency_stop": 0,             # in Hz
                       "frequency_sweep": False,
                       "linear_amplitude_start": 1.0,
                       "linear_amplitude_stop": 0,
                       "linear_amplitude_sweep": False,
                       "offset_start": -0,        # mV
                       "offset_stop": 0,        # mV
                       "offset_sweep": False,
                       "cubic_amplitude_start": 0,  
                       "cubic_amplitude_stop": 0,
                       "cubic_amplitude_sweep": False,
                       "quadratic_amplitude_start": 0,
                       "quadratic_amplitude_stop": 0,
                       "quadratic_amplitude_sweep": False,
                       "duration": 5.0
                       }

default_CBC_example = {"CBC_enabled": False,
                        "input_order": 1 , # The channel which displacement goes into
                        "polynomial_target": 'displacement',
                        "proportional_gain": 1,
                        "derivative_gain": 0,
                        "reference_amplitude_start": 0,          # Value in [0, 1] depicicting the proportion of the reference amplitude
                        "reference_amplitude_stop": 0,              # General rule of thumb: Kp=1 for a<5, Kp=(0.4a-1) for a>=5
                        "reference_amplitude_sweep": False,
                        "frequency_start": 94e3,
                        "frequency_stop": 101e3,
                        "frequency_sweep": False,
                        "linear_amplitude_start": 5,          # Representing mV/units
                        "linear_amplitude_stop": 10,
                        "linear_amplitude_sweep": False,
                        "quadratic_amplitude_start": 0,
                        "quadratic_amplitude_stop": 0,
                        "quadratic_amplitude_sweep": False,
                        "cubic_amplitude_start": 0,
                        "cubic_amplitude_stop": 0,
                        "cubic_amplitude_sweep": False,
                        "offset_start": 500,                     # Value in [-1000, 1000], representing mV output offset
                        "offset_stop": 0,
                        "offset_sweep": False,
                        "duration": 1.0}





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

default_system = {"continuous_output": True,
                  "ip_address": "192.168.1.3",
                  "sampling_rate": "fast",
                  "duration": 0.1}

RP = RedPitaya(CH1_init=default_CH1_example,
               CH2_init=default_CH2_example,
               CBC_init=default_CBC_example,
               system_init=default_system)

if __name__ == '__main__':
    # # This is the default 'setup' for running an experiment. 
    RP.set_duration(1)
    # RP.choose_channel_mode("CH2", "fixed_frequency")
    # RP.set_param("CH2", "linear_amplitude", 0.5)
    # RP.set_param("CH2", "offset", 100)
    # RP.set_param("CH2", "frequency", 100e3)
    # RP.update_FPGA_settings()
    # RP.start_record(savename="daniel_test_250411_")
    # RP.PlotRecording()
    
    # RP.set_gains('CBC', 0)
    # RP.set_param("CBC", "reference_amplitude", 0)
    # RP.set_param("CBC", "frequency", 98.2e3)
    # RP.set_param("CBC", 'linear_amplitude', [0,10])
    # RP.set_param("CBC", 'offset', 500)
    RP.update_FPGA_settings()
    #RP.start_record(savename="daniel_ARC_7.15")
    RP.start_record()         # Run this if you don't care about renaming filename    
    RP.PlotRecording()
    
    # RP.set_duration(1)
    # RP.choose_channel_mode("CH1", 'off')
    
    # # ==== SETTING PARAMS
    # RP.set_param("CBC", "linear_amplitude", 0)
    # RP.set_param("CBC", "offset", 300)
    # RP.set_gains("CBC", [0, 1])
    # strengths = [0.005,0.01,0.025,0.05,0.075,0.1,0.125,0.15,0.175,0.2,0.25]
    # for i in range(len(strengths)):
        
    #     RP.set_param("CBC", "frequency", [95e3,98.2e3])
    #     RP.set_param("CBC", "reference_amplitude", strengths[i])
    #     # RP.update_FPGA_settings()
    #     # RP.start_record(savename = "backbone_b300_a_sweep")
    #     # RP.PlotRecording()
    #     # RP.print_config("CBC")
        
    #     # =========== sweeps ========
        
    #     # RP.set_param("CBC", "reference_amplitude", [0,1])
    #     # RP.set_gains("CBC", [0, 1])
    #     RP.update_FPGA_settings()
    #     name = "frequency_sweep_khat"+str(strengths[i])+"_b300_a0.0"
    #     RP.start_record(savename=name)
    #     RP.PlotRecording()

    # RP.set_param("CBC", "reference_amplitude", [0.2,0])
    # RP.update_FPGA_settings()
    # RP.start_record(savename="24_08_21_quasisweep_OM=96.30_a=6_down")
    
    # RP.set_gains('CBC', [1.5,0])
    # RP.set_param("CBC", "reference_amplitude", [0,0.3])
    # RP.update_FPGA_settings()
    # RP.start_record(savename="24_08_21_quasisweep_OM=96.30_a=6_CBC")
    
    # RP.set_duration(0.1)
    # RP.set_param("CBC", "CBC_enabled", False)
    # RP.update_FPGA_settings()
    # RP.start_record()
    
    
    ## Routine to set CL->OL->CL to show effect of control
    # Rigol8 - CL-0.058, OL-0.05
    # Rigol9 - CL-0.056, OL-0.05
    # Rigol10 - CL-0.054, OL-0.05
    
    # RP.set_duration(0.1)
    # RP.set_gains('CBC', [1.5,0])
    # RP.set_param("CBC", "reference_amplitude", 0.056)
    # RP.set_param("CBC", "frequency", 96.3e3)
    # RP.set_param("CBC", 'linear_amplitude', 6)
    # RP.set_param("CBC", 'offset', 500)
    # RP.update_FPGA_settings()
    # RP.start_record()
        
    # RP.set_gains('CBC', [0,1])
    # RP.set_param("CBC", "reference_amplitude", 0.05)
    # RP.set_param("CBC", "frequency", 96.3e3)
    # RP.set_param("CBC", 'linear_amplitude', 6)
    # RP.set_param("CBC", 'offset', 500)
    # RP.update_FPGA_settings()
    # RP.start_record()
    
    # RP.set_gains('CBC', [1.5,0])
    # RP.set_param("CBC", "reference_amplitude", 0.056)
    # RP.update_FPGA_settings()
    # RP.start_record()
    
    # RP.set_param("CBC", "CBC_enabled", False)
    # RP.update_FPGA_settings()
    # RP.start_record()
    
    
    
    # RP.set_param("CBC", "reference_amplitude", [0.2,0])
    # RP.update_FPGA_settings()
    # RP.start_record(savename="24_08_19_quasisweep_OM=96.50_a=6_down")
    
    # RP.set_param("CBC", "reference_amplitude", [0,0.4])
    # RP.set_gains('CBC', 1.5)
    # RP.update_FPGA_settings()
    # RP.start_record(savename="24_08_19_quasisweep_OM=96.50_a=6_CBC")
    # RP.PlotRecording()
    
    # RP.set_duration(1)
    # filename = time.strftime("%Y-%m-%d ", time.localtime())
    # for ii in range(10):
    #     print(ii)
    #     RP.update_FPGA_settings()
    #     RP.start_record(savename=filename+"warmup_")
    
    
    
    
    
    # RP.set_duration(20)
    # RP.set_duration(3)
    # filename = time.strftime("%Y-%m-%d %H_%M", time.localtime())
    # for ii in range(10):
    #     print(ii)
    #     if ii % 2:
    #         RP.set_param("CBC", "reference_amplitude", [0.01, 1])
    #         RP.update_FPGA_settings()
    #         RP.start_record(savename=filename+"up3_")
    #     else:
    #         RP.set_param("CBC", "reference_amplitude", [1, 0.01])
    #         RP.update_FPGA_settings()
    #         RP.start_record(savename=filename+"down3_")
            
        
        # RP.start_record()
    
    ## Stepped CBC 
    # RP.set_gains('CBC', 1)      # Choose Kp, leaves Kd=0.
    # RP.set_frequency('CBC', 97.8e3)
    # RP.print_config("CBC") 
    # filename = time.strftime("%Y-%m-%d %H_%M", time.localtime())
    # for rhat in np.concatenate((np.linspace(0.01, 0.09, 9), np.linspace(0.1, 0.9, 9))):
    #     print(round(rhat, 2))
    #     RP.set_param("CBC", "reference_amplitude_start", float(round(rhat, 2)))
    #     RP.update_FPGA_settings()
    #     RP.start_record(savename=filename+"_CBC_"+str(round(rhat, 2)))
    
    # Stepped Hopf 
    # RP.set_duration(1)
    # RP.set_gains('CBC', 0)
    # RP.set_param("CBC", "reference_amplitude", 0)
    # RP.set_param("CBC", "frequency", 0)
    # RP.set_param("CBC", 'linear_amplitude', [0,10])
    # RP.print_config("CBC") 
    # filename = time.strftime("%Y-%m-%d %H_%M", time.localtime())
    # b_vec = np.concatenate((np.linspace(0, 150, 4), np.linspace(200, 295, 20), np.linspace(300, 1000, 36)))
    # b_vec = np.linspace(200, 295, 20)
    # b_vec = np.sort(b_vec)
    # for b in b_vec:
    #     print(round(b, 2))
    #     RP.set_param("CBC", 'offset', int(b))
    #     RP.set_param("CBC", 'linear_amplitude', [0,10])
    #     RP.update_FPGA_settings()        
    #     RP.start_record(savename=filename+"_HopfSweepsUp_"+str(int(b)).zfill(4))
    #     RP.set_param("CBC", 'linear_amplitude', [10,0])
    #     RP.update_FPGA_settings()        
    #     RP.start_record(savename=filename+"_HopfSweepsDn_"+str(int(b)).zfill(4))
    
    
    # Swept CBC (linear amplitude) for different frequencies
    # RP.set_duration(1)
    # RP.set_gains('CBC', 2)      # Choose Kp, leaves Kd=0.
    # RP.print_config("CBC") 
    # RP.set_param("CBC", "reference_amplitude", [0.01, 1])
    # filename = time.strftime("%Y-%m-%d %H_%M", time.localtime())
    # print("Time start: " + time.strftime("%H:%M:%S", time.localtime()))
    # # for freq in np.linspace(96e3, 98e3, 20, endpoint=False):
    # #     print(freq)
    # #     RP.set_param("CBC", "frequency", freq.tolist())
    # #     RP.update_FPGA_settings()
    # #     RP.start_record(savename=filename+"_CBC_"+ str(round(freq*1e-3, 2)))
    # # for freq in np.linspace(98.4e3, 100e3, 17):
    # #     print(freq)
    # #     RP.set_param("CBC", "frequency", freq.tolist())
    # #     RP.update_FPGA_settings()
    # #     RP.start_record(savename=filename+"_CBC_"+ str(round(freq*1e-3, 2)))
    # for freq in np.linspace(97.7e3, 98.5e3, 161):
    #     print(freq)
    #     RP.set_param("CBC", "frequency", freq.tolist())
    #     RP.update_FPGA_settings()
    #     RP.start_record(savename=filename+"_CBC_"+ str(freq))
    # print("Time end: " + time.strftime("%H:%M:%S", time.localtime()))
    
    
    # Swept vs stepped response
    # RP.set_duration(5)
    # RP.set_gains('CBC', 1)      # Choose Kp, leaves Kd=0.
    # RP.set_param("CBC", "reference_amplitude", [0.01, 1])
    # RP.set_param("CBC", "frequency", 98.13e3)
    # RP.print_config("CBC") 
    # RP.update_FPGA_settings()
    # RP.start_record(savename="swept_CBC")
    
    # RP.set_duration(1)
    # for rhat in np.linspace(0.01, 0.4, 40):
    #     RP.set_param("CBC", "reference_amplitude", rhat.tolist())
    #     RP.print_config("CBC") 
    #     RP.update_FPGA_settings()
    #     RP.start_record(savename="stepped_CBC_"+str(round(rhat, 2)))
    
    
    # Over a range of coupling offset at constant freq
    # filename = time.strftime("%Y-%m-%d %H_%M", time.localtime())
    # RP.set_param("CBC", "proportional_gain", 2)    
    # RP.set_duration(1)
    # for f in np.linspace(96e3, 97e3, 21):
    #     RP.set_param("CBC", "frequency", int(f))            
    #     RP.print_config("CBC") 
    #     RP.update_FPGA_settings()
    #     RP.start_record(savename=filename+"_CBC_OM=" + str(int(f)) + "_a=6_b=500")
    
    # Over a range of coupling strength at constant freq
    # filename = time.strftime("%Y-%m-%d %H_%M", time.localtime())
    # RP.set_duration(1)
    # for b in np.linspace(100, 900, 17):
    #     RP.set_param("CBC", "offset", int(b.tolist()))
    #     RP.print_config("CBC") 
    #     RP.update_FPGA_settings()
    #     RP.start_record(savename=filename+"_CBC_a=10_b="+ str(int(b)))
        
    
    
    # # Ensure different gains produce same outcomes
    # filename = time.strftime("%Y-%m-%d %H_%M", time.localtime())
    # RP.set_duration(1)
    # for Kp in np.linspace(1, 4, 7):
    #     RP.set_param("CBC", "proportional_gain", Kp.tolist())
    #     RP.print_config("CBC") 
    #     RP.update_FPGA_settings()
    #     RP.start_record(savename="gain_test_"+ str(round(Kp, 1)))
    
    
    
    #==========================================================================
    # # Mass sweep testing 
    
    # # Freq Sweeps
    # OM = np.linspace(98e3, 98.3e3, 31).reshape(-1,1)
    # a = np.array([6,6,6,8,10])
    # b = np.array([900, 700, 500, 500, 500])
    # "B" Sweeps
    # OM = np.linspace(100, 900, 17).reshape(-1,1)
    # b = np.array([98.2e3, 98.2e3, 98.2e3, 98.15e3, 98.1e3])
    # a = np.array([10, 8, 6, 6, 6])
    
    # # "A" Sweeps
    # OM = np.linspace(0, 12, 31).reshape(-1,1)
    # a = np.array([98.2e3, 98.2e3, 98.2e3, 98.15e3, 98.1e3])
    # b = np.array([900, 700, 500, 500, 500])
    
    # for ii in range(len(a)):
    #     x = np.hstack([a[ii]+0*OM, b[ii]+0*OM, OM])
    #     if ii==0:
    #         exp_combo = x
    #     else:
    #         exp_combo = np.vstack([exp_combo, x])
    #     OM = np.flip(OM)    
    # filename = time.strftime("%Y-%m-%d %H-%M", time.localtime())
    # RP.set_duration(1)
    # RP.set_param("CBC", "proportional_gain", 3)
    # RP.print_config("CBC") 
    # for row in exp_combo:
    #     print(row)
    #     f = round(row[0], 0)
    #     b = round(row[1], 0)
    #     a = round(row[2], 1)
        
    #     RP.set_param("CBC", "frequency", f.tolist())
    #     RP.set_param("CBC", "linear_amplitude", a.tolist())
    #     RP.set_param("CBC", "offset", int(b))        
    #     RP.update_FPGA_settings()
    #     savename = filename + "_CBC_OM={f}_a={a}_b={b}".format(f=f, a=a, b=b)
    #     RP.start_record(savename=savename)
    #==========================================================================
    
    
    
    
    
    
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

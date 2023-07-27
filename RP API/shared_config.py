# -*- coding: utf-8 -*-
"""
Created on Wed Jul 26 14:26:35 2023

@author: sha211

This file contains generic function handles that are shared between the 
channel_config and CBC_config classes. Utilising this separate file will allow 
for more efficient usage of various methods, similar in functionality for both 
classes. 
"""

def myFunc(x):
    return 2*x + 1

# def set_sweep(self, channel, param, sweep_range):
#     # TODO: "f" and "frequency" used for CBC and channel respectively. 
#     # Should be unified into just "f" for simplicity.
    
    
#     if channel not in [1, 2, "CBC", "Both"]:
#         raise ValueError("Invalid 'channel' value. It must be 1, 2, or 'Both'.")
#     elif channel in [1, 2, "Both"] and param not in sweep_CHx:
#         raise ValueError("Invalid 'param' value. It must be 'A', 'B', or 'frequency'")
#     elif channel == "CBC" and param not in sweep_CBC:
#         raise ValueError("Invalid 'param' value. It must be 'A', 'B', 'C', 'D', 'frequency', or 'r_hat.")
#     else:
#         p_start = param + "_start"
#         p_stop = param + "_stop"
#         p_sweep = param + "_sweep"
      
    
#     if isinstance(sweep_range, (float, int)):
#         print("Warning: Only one value found within 'sweep_range'. Parameter to be held constant and sweep turned off.")
#         start = sweep_range
#         stop = 0
#         sweep = False
        
#     if isinstance(sweep_range, (list, tuple)):
#         if len(sweep_range) > 2:
#             print("Warning: 'sweep_range' list or tuple should contain at most two elements. Extra elements will be ignored.")
#             sweep_range = sweep_range[0:2]
#         if len(sweep_range) == 1 or len(set(sweep_range)) == 1:
#             print("Warning: Only one unique value found within 'sweep_range'. Parameter to be held constant and sweep turned off.")
#             start = sweep_range[0]
#             stop = 0
#             sweep = False
#         else:
#             start = sweep_range[0]
#             stop = sweep_range[1]
#             sweep = True
                    

#     if channel == "Both":
#         self.CH1[p_start] = start
#         self.CH1[p_stop] = stop
#         self.CH1[p_sweep] = sweep
#         self.CH2[p_start] = start
#         self.CH2[p_stop] = stop
#         self.CH2[p_sweep] = sweep
#     elif channel == 1:
#         self.CH1[p_start] = start
#         self.CH1[p_stop] = stop
#         self.CH1[p_sweep] = sweep
#     elif channel == 2:
#         self.CH2[p_start] = start
#         self.CH2[p_stop] = stop
#         self.CH2[p_sweep] = sweep
#     elif channel == "CBC":
#         self.CBC[p_start] = start
#         self.CBC[p_stop] = stop
#         self.CBC[p_sweep] = sweep



def set_value_or_sweep(self, param, sweep_range, sweepable_params):
    if param not in sweepable_params:
        raise ValueError("Invalid 'param' value. Please check that the parameter selected is valid for the output type.")
    
    if isinstance(sweep_range, (list, tuple)):
        if len(sweep_range) > 2:
            # Restricts the parameter length to just two elements.
            print("Warning: 'sweep_range' list or tuple should contain at most two elements. Extra elements will be ignored.")
            sweep_range = sweep_range[0:2]
        if len(sweep_range) == 1 or len(set(sweep_range)) == 1:
            # Checks whether there is only one element, or one unique (i.e. repeated) element.
            print("Warning: Only one unique value found within 'sweep_range'. Parameter to be held constant and sweep turned off.")
            start = sweep_range[0]
            stop = 0
            sweep = False
        else:
            start = sweep_range[0]
            stop = sweep_range[1]
            sweep = True
    elif isinstance(sweep_range, (float, int)):
        start = sweep_range
        stop = 0
        sweep = False
    
    self[param + "_start"] = start
    self[param + "_stop"] = stop
    self[param + "_sweep"] = sweep
    
    
    
    
    
    
    
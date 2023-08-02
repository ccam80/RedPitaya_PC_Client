# -*- coding: utf-8 -*-
"""
Created on Wed Jul 26 14:26:35 2023

@author: sha211

This file contains generic function handles that are shared between the
channel_config and CBC_config classes. Utilising this separate file will allow
for more efficient usage of various methods, similar in functionality for both
classes.
"""


def fixed_or_sweep(self, param, sweep_range, sweepable_params):
    """
    This is a function shared by the CBC_config.py and channel_config.py modules.

    If a certain parameter type has options for sweeps (i.e. frequency), this
    function will
    1) Determine whether one, two, or more inputs are given
    2) Sets logic to set the intital, final, and sweep values based off of input(s)

    The "param" argument should be given as the name of the variable to be
    changed. In the case of a sweepable parameter, you should use the parameter \
    name without the "_start", etc.


    Usage:
        RP.CH1.set_params_linear(A=1)
            This will set the "A" pameter to be a constant of 1
            -> A_start = 1
            -> A_stop = 0
            -> A_sweep = False
        RP.CH1.set_params_linear(A=[1, 100])
            This will set the "A" pameter to be swept from 1 to 100
            -> A_start = 1
            -> A_stop = 100
            -> A_sweep = True
        RP.CH1.set_params_linear(A=[1, 1])
            Repeated entries are also assumed to be constant.
            -> A_start = 1
            -> A_stop = 0
            -> A_sweep = False
        RP.CH1.set_params_linear(A=[1, 100, 200])
            Entries past two elements are ignored.
            If the third (onward) entries are unique, these are still ignored.
            -> A_start = 1
            -> A_stop = 100
            -> A_sweep = True
    """
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

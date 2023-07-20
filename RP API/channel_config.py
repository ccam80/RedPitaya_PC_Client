# -*- coding: utf-8 -*-
"""
Created on Thu Jul 20 16:54:25 2023
@author: cca78

Channel config class.
Dictionary which stores desired physical parameters for each RP channel.

Class overrides __getattr__ and __setattr__ methods so that each key can be
called as an attribute, for convenience in API calls.

Overrides __setitem__ to not allow any non-specified keys to be added.

"""

channel_keys = ["mode",
                "frequency_start",
                "frequency_stop",
                "frequency_sweep",
                "fixed_amplitude",
                "fixed_offset",
                "A_start",
                "A_stop",
                "A_sweep",
                "B_start",
                "B_stop",
                "B_sweep",
                "fixed_x_coeff",
                "fixed_x2_coeff",
                "fixed_x3_coeff",
                "artificial_nonlinearity_gain1",
                "input_channel"]


class channel_config(dict):

    def __init__(self, default_values=None):
        super().__init__({key: None for key in channel_keys})
        if default_values:
            for key, value in default_values.items():
                if key in channel_keys:
                    self[key] = value
                else:
                    print(f"Warning: The key '{key}' is not included in CBC settings and has been discarded.")


    def __getattr__(self, item):
        if item in self:
            return self[item]
        else:
            raise AttributeError(f"'Channel Config' object has no attribute '{item}'")

    def __setattr__(self, key, value):
        self[key] = value

    def __setitem__(self, key, value):
        if key in channel_keys:
            super().__setitem__(key, value)
        else:
            raise KeyError(f"'Channel Config' object does not support adding new keys")

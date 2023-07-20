# -*- coding: utf-8 -*-
"""
Created on Thu Jul 20 16:54:25 2023
@author: cca78

CBC config class.
Dictionary which stores desired physical parameters for combined CBC settings.

Class overrides __getattr__ and __setattr__ methods so that each key can be
called as an attribute, for convenience in API calls.

Overrides __setitem__ to not allow any non-specified keys to be added.

"""

CBC_keys = ["input_order",
                "velocity_external",
                "displacement_external",
                "polynomial_target",
                "r_hat_start",
                "r_hat_stop",
                "r_hat_sweep",
                "f_start",
                "f_stop",
                "f_sweep",
                "A_start",
                "A_stop",
                "A_sweep",
                "B_start",
                "B_stop",
                "B_sweep",
                "C_start",
                "C_stop",
                "C_sweep",
                "D_start",
                "D_stop",
                "D_sweep",]


class CBC_config(dict):

    def __init__(self, default_values=None):
        super().__init__({key: None for key in CBC_keys})
        if default_values:
            for key, value in default_values.items():
                if key in CBC_keys:
                    self[key] = value
                else:
                    print(f"Warning: The key '{key}' is not included in CBC settings and has been discarded.")


    def __getattr__(self, item):
        if item in self:
            return self[item]
        else:
            raise AttributeError(f"'CBC Config' object has no attribute '{item}'")

    def __setattr__(self, key, value):
        self[key] = value

    def __setitem__(self, key, value):
        if key in CBC_keys:
            super().__setitem__(key, value)
        else:
            raise KeyError(f"'CBC Config' object does not support adding new keys")

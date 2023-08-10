# -*- coding: utf-8 -*-
"""
Created on Thu Aug  3 11:52:43 2023

@author: cca78

FPGA_config.py contains a custom dict along the lines of channel_config which
represents the config memory block on the FPGA. Parameters in this dict are
abstract, arbitrarily scaled, and occupy varying places the memory, so don't
look in this one for answers unless you know what the FPGA is doing. Individual
bits are or'ed into bytes for the first three entries.

No type or limit checking here, as humans should keep their grubby little
fingers out of this portion of the code - already sanitised inputs from config
dicts allowed only.

"""

config_keys = ["system",
               "CH1_settings",
               "CH2_settings",
               "CBC_settings",
               "Parameter_A",
               "Parameter_B",
               "Parameter_C",
               "Parameter_D",
               "Parameter_E",
               "Parameter_F",
               "Parameter_G",
               "Parameter_H",
               "Parameter_I",
               "Parameter_J",
               "Parameter_K",
               "Parameter_L",
               "Parameter_M",
               "Parameter_N",
               ]


class FPGA_config(dict):

    def __init__(self, default_values=None):
        super().__init__({key: 0 for key in config_keys})
        if default_values:
            for key, value in default_values.items():
                if key in config_keys:
                    self[key] = value
                else:
                    print(f"Warning: The key '{key}' is not included in CBC settings and has been discarded.")


    def __getattr__(self, item):
        if item in self:
            return self[item]
        else:
            raise AttributeError(f"'FPGA Config' object has no attribute '{item}'")

    def __setattr__(self, key, value):
        self[key] = value

    def __setitem__(self, key, value):
        """Check that key is part of the allowed list, then perform type and
        value checks before setting any items. """

        if key in config_keys:
            super().__setitem__(key, value)

        else:
            raise KeyError(f"'FPGA Config' object does not support adding new keys")

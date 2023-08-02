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
from shared_config import *

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

channel_sweepable = ["frequency",
                      "A",
                     "B"]

channel_modes = ["fixed_frequency",
                 "frequency_sweep",
                 "artificial_nonlinearity",
                 "artificial_nonlinearity_parametric",
                 "cubic",
                 "linear_feedback",
                 "white_noise",
                 "off"]

datatypes = {"mode": str,
            "frequency_start": float,
            "frequency_stop": float,
            "frequency_sweep": bool,
            "fixed_amplitude": float,
            "fixed_offset": int,
            "A_start": float,
            "A_stop": float,
            "A_sweep": bool,
            "B_start": int,
            "B_stop": int,
            "B_sweep": bool,
            "fixed_x_coeff": float,
            "fixed_x2_coeff": float,
            "fixed_x3_coeff": float,
            "artificial_nonlinearity_gain1": float,
            "input_channel": int
            }



limits = {"mode": channel_modes,
          "frequency_start": [0,2000000],
          "frequency_stop": [0,2000000],
          "frequency_sweep": [0,1],
          "fixed_amplitude": [-1000,1000],
          "fixed_offset": [-1000,1000],
          "A_start": [-1000,1000],
          "A_stop":  [-1000,1000],
          "A_sweep": [0,1],
          "B_start": [-1000,1000],
          "B_stop": [-1000,1000],
          "B_sweep": [0,1],
          "fixed_x_coeff": [-1000,1000],
          "fixed_x2_coeff": [-1000,1000],
          "fixed_x3_coeff": [-1000,1000],
          "artificial_nonlinearity_gain1":  [-1000,1000],
          "input_channel": [1,2]}


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
        """Check that key is part of the allowed list, then perform type and
        value checks before setting any items. """

        if key in channel_keys:

            if type(value) == datatypes[key]:
                if self.is_within_limits(value, limits[key]):
                    super().__setitem__(key, value)
                else:
                    raise ValueError(f"{value} is outside of limits for {key}, which are {limits[key]}")

            elif datatypes[key] == float and type(value) == int:
                if self.is_within_limits(value, limits[key]):
                    super().__setitem__(key, float(value))
                else:
                    raise ValueError(f"{value} is outside of limits for {key}, which are {limits[key]}")

            else:
                raise TypeError(f"Parameter entered is of type '{type(value)}' whereas {key} expects a parameter of type {datatypes[key]}")
        else:
            raise KeyError(f"'Channel Config' object does not support adding new keys")

    def is_within_limits(self, value, limits):
        """
        Determines whether the given input value(s) are within the limits specified
        """
        if type(limits[0]) == str:
            return value in limits

        else:
            if len(limits) != 2:
                raise ValueError("Limits list must contain exactly two items.")

            lower_limit, upper_limit = sorted(limits)

            return lower_limit <= value <= upper_limit

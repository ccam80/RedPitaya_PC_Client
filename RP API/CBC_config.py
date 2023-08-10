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
from _utils import *

_CBC_keys = ["CBC_enabled",
             "input_order",
             "velocity_external",
             "displacement_external",
             "polynomial_target",
             "kp",
             "kd",
             "r_hat_start",
             "r_hat_stop",
             "r_hat_sweep",
             "frequency_start",
             "frequency_stop",
             "frequency_sweep",
             "a_start",
             "a_stop",
             "a_sweep",
             "b_start",
             "b_stop",
             "b_sweep",
             "c_start",
             "c_stop",
             "c_sweep",
             "d_start",
             "d_stop",
             "d_sweep",
             "duration"  # Duration included in multiple places for ease of
                         # mapping in the dict translation module.
             ]

_datatypes = {"CBC_enabled": bool,
              "input_order": int,
              "velocity_external": bool,
              "displacement_external": bool,
              "polynomial_target": str,
              "kp": float,
              "kd": float,
              "r_hat_start": float,
              "r_hat_stop": float,
              "r_hat_sweep": bool,
              "f_start": float,
              "f_stop": float,
              "f_sweep": bool,
              "a_start": float,
              "a_stop": float,
              "a_sweep": bool,
              "b_start": float,
              "b_stop": float,
              "b_sweep": bool,
              "c_start": float,
              "c_stop": float,
              "c_sweep": bool,
              "d_start": float,
              "d_stop": float,
              "d_sweep": bool,
              "duration": float}

_limits = {"CBC_enabled": [0, 1],
           "input_order": [1, 2],
           "velocity_external": [0, 1],
           "displacement_external": [0, 1],
           "polynomial_target": ["displacement", "velocity"],
           "kp": [-1024, 1024],
           "kd": [-1024, 1024],
           "r_hat_start": [-1000, 1000],
           "r_hat_stop": [-1000, 1000],
           "r_hat_sweep": [0, 1],
           "f_start": [0, 2000000],
           "f_stop": [0, 2000000],
           "f_sweep": [0, 1],
           "a_start": [-1000, 1000],
           "a_stop": [-1000, 1000],
           "a_sweep": [0, 1],
           "b_start": [-1000, 1000],
           "b_stop": [-1000, 1000],
           "b_sweep": [0, 1],
           "c_start": [-1000, 1000],
           "c_stop": [-1000, 1000],
           "c_sweep": [0, 1],
           "d_start": [-1000, 1000],
           "d_stop": [1000, -1000],
           "d_sweep": [0, 1],
           "duration": [0, 60]}



class CBC_config(dict):

    def __init__(self, default_values=None):
        super().__init__({key: 0 for key in _CBC_keys})
        if default_values:
            for key, value in default_values.items():
                if key in _CBC_keys:
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
        """Check that key is part of the allowed list, then perform type and
        value checks before setting any items. """

        if key in _CBC_keys:

            if type(value) == _datatypes[key]:
                if self.is_within_limits(value, _limits[key]):
                    super().__setitem__(key, value)
                else:
                    raise ValueError(f"{value} is outside of _limits for {key}, which are {_limits[key]}")

            elif _datatypes[key] == float and type(value) == int:
                if self.is_within_limits(value, _limits[key]):
                    super().__setitem__(key, float(value))
                else:
                    raise ValueError(f"{value} is outside of _limits for {key}, which are {_limits[key]}")

            else:
                raise TypeError(f"Parameter entered is of type '{type(value)}' whereas {key} expects a parameter of type {_datatypes[key]}")
        else:
            raise KeyError(f"'Channel Config' object does not support adding new keys. Key '{key}' rejected")

    def is_within_limits(self, value, _limits):
        if type(_limits[0]) == str:
            return value in _limits

        else:
            if len(_limits) != 2:
                raise ValueError("_limits list must contain exactly two items.")
            lower_limit, upper_limit = sorted(_limits)
            return lower_limit <= value <= upper_limit

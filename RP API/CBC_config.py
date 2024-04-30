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
             "proportional_gain",
             "derivative_gain",
             "reference_amplitude_start",
             "reference_amplitude_stop",
             "reference_amplitude_sweep",
             "frequency_start",
             "frequency_stop",
             "frequency_sweep",
             "cubic_amplitude_start",
             "cubic_amplitude_stop",
             "cubic_amplitude_sweep",
             "quadratic_amplitude_start",
             "quadratic_amplitude_stop",
             "quadratic_amplitude_sweep",
             "linear_amplitude_start",
             "linear_amplitude_stop",
             "linear_amplitude_sweep",
             "offset_start",
             "offset_stop",
             "offset_sweep",
             "duration"  # Duration included in multiple places for ease of
                         # mapping in the dict translation module.
             ]

_datatypes = {"CBC_enabled": bool,
              "input_order": int,
              "velocity_external": bool,
              "displacement_external": bool,
              "polynomial_target": str,
              "proportional_gain": float,
              "derivative_gain": float,
              "reference_amplitude_start": float,
              "reference_amplitude_stop": float,
              "reference_amplitude_sweep": bool,
              "frequency_start": float,
              "frequency_stop": float,
              "frequency_sweep": bool,
              "cubic_amplitude_start": float,
              "cubic_amplitude_stop": float,
              "cubic_amplitude_sweep": bool,
              "quadratic_amplitude_start": float,
              "quadratic_amplitude_stop": float,
              "quadratic_amplitude_sweep": bool,
              "linear_amplitude_start": float,
              "linear_amplitude_stop": float,
              "linear_amplitude_sweep": bool,
              "offset_start": int,
              "offset_stop": int,
              "offset_sweep": bool,
              "duration": float}

_limits = {"CBC_enabled": [0, 1],
           "input_order": [0, 2],
           "velocity_external": [0, 1],
           "displacement_external": [0, 1],
           "polynomial_target": ["displacement", "velocity"],
           "proportional_gain": [-1024, 1024],
           "derivative_gain": [-32767, 32767], # Chris has changed this for testing, if it's still above 1000 then I forgot to change it back
           "reference_amplitude_start": [-1000, 1000],
           "reference_amplitude_stop": [-1000, 1000],
           "reference_amplitude_sweep": [0, 1],
           "frequency_start": [0, 2000000],
           "frequency_stop": [0, 2000000],
           "frequency_sweep": [0, 1],
           "cubic_amplitude_start": [-1000, 1000],
           "cubic_amplitude_stop": [-1000, 1000],
           "cubic_amplitude_sweep": [0, 1],
           "quadratic_amplitude_start": [-1000, 1000],
           "quadratic_amplitude_stop": [-1000, 1000],
           "quadratic_amplitude_sweep": [0, 1],
           "linear_amplitude_start": [-1000, 1000],
           "linear_amplitude_stop": [-1000, 1000],
           "linear_amplitude_sweep": [0, 1],
           "offset_start": [-1000, 1000],
           "offset_stop": [1000, -1000],
           "offset_sweep": [0, 1],
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

    def is_within_limits(self, value, limits):
        if type(limits[0]) == str:
            return value in limits

        else:
            if len(limits) != 2:
                raise ValueError("_limits list must contain exactly two items.")
            lower_limit, upper_limit = sorted(limits)
            return lower_limit <= value <= upper_limit

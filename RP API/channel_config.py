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

_channel_keys = ["mode",
                 "input_channel",
                 "frequency_start",
                 "frequency_stop",
                 "frequency_sweep",
                 "a_start",
                 "a_stop",
                 "a_sweep",
                 "b_start",
                 "b_stop",
                 "b_sweep",
                 "A",
                 "B",
                 "C",
                 "D",
                 "duration"  # Duration included in multiple places for ease of
                             # mapping in the dict translation module.
                 ]

_channel_modes = ["fixed_frequency",
                  "frequency_sweep",
                  "artificial_nonlinearity",
                  "artificial_nonlinearity_parametric",
                  "cubic",
                  "linear_feedback",
                  "white_noise",
                  "off"]


_datatypes = {"mode": str,
              "input_channel": int,
              "frequency_start": float,
              "frequency_stop": float,
              "frequency_sweep": bool,
              "a_start": float,
              "a_stop": float,
              "a_sweep": bool,
              "b_start": int,
              "b_stop": int,
              "b_sweep": bool,
              "A": float,
              "B": float,
              "C": float,
              "D": int,
              "duration": float
              }

_limits = {"mode": _channel_modes,
           "input_channel": [1, 2],
           "frequency_start": [0, 2000000],
           "frequency_stop": [0, 2000000],
           "frequency_sweep": [0, 1],
           "a_start": [-1000, 1000],
           "a_stop":  [-1000, 1000],
           "a_sweep": [0, 1],
           "b_start": [-1000, 1000],
           "b_stop": [-1000, 1000],
           "b_sweep": [0, 1],
           "A": [-1000, 1000],
           "B": [-1000, 1000],
           "C": [-1000, 1000],
           "D": [-1000, 1000],
           "duration": [0, 60]
           }


class channel_config(dict):

    def __init__(self, default_values=None):
        super().__init__({key: None for key in _channel_keys})
        if default_values:
            for key, value in default_values.items():
                if key in _channel_keys:
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

        if key in _channel_keys:

            if type(value) == _datatypes[key]:
                if self.is_within_limits(value, _limits[key]):
                    super().__setitem__(key, value)
                else:
                    raise ValueError(f"{value} is outside of limits for {key}, which are {_limits[key]}")

            elif _datatypes[key] == float and type(value) == int:
                if self.is_within_limits(value, _limits[key]):
                    super().__setitem__(key, float(value))
                else:
                    raise ValueError(f"{value} is outside of limits for {key}, which are {_limits[key]}")

            else:
                raise TypeError(f"Parameter entered is of type '{type(value)}' whereas {key} expects a parameter of type {_datatypes[key]}")
        else:
            raise KeyError("'Channel Config' object does not support adding new keys")

    def is_within_limits(self, value, limits):
        """
        Determines whether the given input value(s) are within the limits specified
        """
        if type(_limits[0]) == str:
            return value in limits

        else:
            if len(_limits) != 2:
                raise ValueError("Limits list must contain exactly two items.")

            lower_limit, upper_limit = sorted(_limits)

            return lower_limit <= value <= upper_limit

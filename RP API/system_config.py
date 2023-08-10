# -*- coding: utf-8 -*-
"""
Created on Thu Jul 20 16:54:25 2023
@author: cca78

System config class.
Dictionary which stores desired physical parameters for each RP channel.

Class overrides __getattr__ and __setattr__ methods so that each key can be
called as an attribute, for convenience in API calls.

Overrides __setitem__ to not allow any non-specified keys to be added.

"""

_system_keys = ["continuous_output",
               "ip_address",
               "sampling_rate",
               "recording_duration"
               ]

# TODO: To double-check
# cont_output -> is or isnt
# ip -> a string of 12:345:678
# sample -> "fast" or "slow"
_datatypes = {"continuous_output": bool,
            "ip_address": str,
            "sampling_rate": str,
            "recording_duration": float
            }

_limits = {"continuous_output": [0, 1],
          "ip_address": None,
          "sampling_rate": ["fast", "slow"],
          "recording_duration": [0,60]
          }

class system_config(dict):

    def __init__(self, default_values=None):
        super().__init__({key: 0 for key in _system_keys})
        if default_values:
            for key, value in default_values.items():
                if key in _system_keys:
                    self[key] = value
                else:
                    print(f"Warning: The key '{key}' is not included in System Config and has been discarded.")


    def __getattr__(self, item):
        if item in self:
            return self[item]
        else:
            raise AttributeError(f"'System Config' object has no attribute '{item}'")

    def __setattr__(self, key, value):
        self[key] = value

    def __setitem__(self, key, value):
        if key in _system_keys:

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
            raise KeyError(f"'System Config' object does not support adding new keys")

    def is_within_limits(self, value, _limits):
        if type(_limits[0]) == str:
            return value in _limits

        else:
            if len(_limits) != 2:
                raise ValueError("_limits list must contain exactly two items.")
            lower_limit, upper_limit = sorted(_limits)
            return lower_limit <= value <= upper_limit

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
from re import match

_system_keys = ["continuous_output",
               "ip_address",
               "sampling_rate",
               "recording_duration"
               ]

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
            raise KeyError("'System Config' object does not support adding new keys")

    def is_within_limits(self, value, limits):

        if limits is None:
            return self._check_ip_valid(value)

        elif type(limits[0]) == str:
            return value in limits

        else:
            if len(limits) != 2:
                raise ValueError("_limits list must contain exactly two items.")
            lower_limit, upper_limit = sorted(limits)
            return lower_limit <= value <= upper_limit

    def _check_ip_valid(self, ip):
        lower_bound = "0.0.0.0"
        upper_bound = "255.255.255.255"
        ip_pattern =  r'^(\d{1,3}\.){3}\d{1,3}$'

        # Split the IP address and bounds into lists of integers
        ip_parts = list(map(int, ip.split('.')))
        lower_parts = list(map(int, lower_bound.split('.')))
        upper_parts = list(map(int, upper_bound.split('.')))

        if match(ip_pattern, ip):
            for i in range(len(lower_parts)):
                if ip_parts[i] < lower_parts[i] or ip_parts[i] > upper_parts[i]:
                    raise ValueError("IP must be in range 0.0.0.0 - 255.255.255.255. The {}h number in your ip is outside of this range".format(i))
        else:
            raise ValueError("{} is not a valid IP address string".format(ip))

        return True

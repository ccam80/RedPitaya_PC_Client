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

CBC_keys = ["CBC_enabled",
            "input_order",
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
            "D_sweep"]

datatypes = {"CBC_enabled": bool,
            "input_order": int,
            "velocity_external": bool,
            "displacement_external": bool,
            "polynomial_target": str,
            "r_hat_start": float,
            "r_hat_stop": float,
            "r_hat_sweep": bool,
            "f_start": float,
            "f_stop": float,
            "f_sweep": bool,
            "A_start": float,
            "A_stop": float,
            "A_sweep": bool,
            "B_start": float,
            "B_stop": float,
            "B_sweep": bool,
            "C_start": float,
            "C_stop": float,
            "C_sweep": bool,
            "D_start": float,
            "D_stop": float,
            "D_sweep": bool}

limits = {"CBC_enabled": [0,1],
          "input_order": [1,2],
          "velocity_external": [0,1],
          "displacement_external": [0,1],
          "polynomial_target": ["displacement", "velocity"],
          "r_hat_start": [-1000,1000],
          "r_hat_stop": [-1000,1000],
          "r_hat_sweep": [0,1],
          "f_start": [0,2000000],
          "f_stop": [0,2000000],
          "f_sweep": [0,1],
          "A_start": [-1000,1000],
          "A_stop": [-1000,1000],
          "A_sweep": [0,1],
          "B_start": [-1000,1000],
          "B_stop": [-1000,1000],
          "B_sweep": [0,1],
          "C_start": [-1000,1000],
          "C_stop": [-1000,1000],
          "C_sweep": [0,1],
          "D_start": [-1000,1000],
          "D_stop": [1000,-1000],
          "D_sweep": [0,1]}



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
        """Check that key is part of the allowed list, then perform type and
        value checks before setting any items. """

        if key in CBC_keys:

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
            raise KeyError(f"'CBC Config' object does not support adding new keys")



    def is_within_limits(self, value, limits):
        if type(limits[0]) == str:
            return value in limits

        else:
            if len(limits) != 2:
                raise ValueError("Limits list must contain exactly two items.")

            lower_limit, upper_limit = sorted(limits)

            return lower_limit <= value <= upper_limit

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
from shared_config import *

CBC_keys = ["CBC_enabled",
            "input_order",
            "velocity_external",
            "displacement_external",
            "polynomial_target",
            "r_hat_start",
            "r_hat_stop",
            "r_hat_sweep",
            "frequency_start",
            "frequency_stop",
            "frequency_sweep",
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

CBC_sweepable = ["r_hat",
              "f",
              "A",
             "B",
             "C",
             "D"]

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



limits = {"CBC_enabled": [0, 1],
          "input_order": [1, 2],
          "velocity_external": [0, 1],
          "displacement_external": [0, 1],
          "polynomial_target": ["displacement", "velocity"],
          "r_hat_start": [-1000, 1000],
          "r_hat_stop": [-1000, 1000],
          "r_hat_sweep": [0, 1],
          "f_start": [0, 2000000],
          "f_stop": [0, 2000000],
          "f_sweep": [0, 1],
          "A_start": [-1000, 1000],
          "A_stop": [-1000, 1000],
          "A_sweep": [0, 1],
          "B_start": [-1000, 1000],
          "B_stop": [-1000, 1000],
          "B_sweep": [0, 1],
          "C_start": [-1000, 1000],
          "C_stop": [-1000, 1000],
          "C_sweep": [0, 1],
          "D_start": [-1000, 1000],
          "D_stop": [1000, -1000],
          "D_sweep": [0, 1]}



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
            self.choose_external_input_type(key, value)    
    
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
    
    def choose_external_input_type(self, key, value):
        """
        This function configures whether the input to the RP is of a certain type.
        In doing so, it sets its compliment to False. 
        
        
        --- Logic ---    
        (input) key = value
            -> displacement_external = ...  (output)
            -> displacement_external = ...  (output)
        
        displacement_external = False
            -> displacement_external = False
            -> velocity_external = False
            
        velocity_external = False
            -> displacement_external = False
            -> velocity_external = False
            
        displacement_external = True
            -> displacement_external = True
            -> velocity_external = False
            
        velocity_external = True
            -> displacement_external = False
            -> velocity_external = True
        """
        if key == "velocity_external" and value == True:
            self["displacement_external"] = False
            print("Warning: key '*displacement_external' set to 'False'.")
        elif key == "displacement_external" and value == True:
            self["velocity_external"] = False
            print("Warning: key '*velocity_external' set to 'False'.")
    
    def set_param(self, param_name, param_val):
        """
        Sets relevant parameter value. 
        
        If the parameter can be swept (such as frequency), a list or tuple can 
        be given to set the sweep range. As such, the sweep logic is simultaneously 
        updated.
        """
        if param_name in CBC_sweepable:
            set_value_or_sweep(self, param_name, param_val, CBC_sweepable)
        else:
            self[param_name] = param_val
            
    def set_params_CBC(self, **kwargs):
        """
        Sets the parameters for the CBC output type
        Coefficients are of the mathematical form of:
            y = Ax + B
        
        Possible key/arguments
            1) A - int, float, list, tuple
            2) B - int, float, list, tuple
            3) C - int, float, list, tuple
            4) D - int, float, list, tuple
            5) rhat - int, float, list, tuple
            6) frequency - int, float, list, tuple
            7) polynomial_target - "displacement" or "velocity"
            8) external - "displacement" or "velocity"
            9) input_order - 1, 2
    
        Empty/non-assigned arguments will be ignored/left unchanged.
        Irrelevant arguments outside of the possible keys will be ignored.
        
        
        Usage:
            RP.CBC.set_params_CBC(A=1, B=[1,4])
                -> A_start = 1
                -> A_stop = 0
                -> A_sweep = False
                -> B_start = 1
                -> B_stop = 4
                -> B_sweep = True
                -> All other parameters are ignored.
            
            RP.CBC.set_params_CBC(polynomial_target="displacement")
                -> polynomial_target = "displacement"
                -> All other parameters are ignored
            
            RP.CBC.set_params_CBC(external="displacement")
                -> displacement_external = True
                -> velocity_external = False
                -> All other parameters are ignored
        """        
        CBC_keys = {"A", "B", "C", "D", "rhat", "frequency", "polynomial_target", "external", "input_order"}
        for key, value in kwargs.items():
            if key == "external":
                if value == "displacement":
                    self.set_param("displacement_external", True)
                    CBC_keys.remove(key)
                elif value == "velocity":
                    self.set_param("velocity_external", True)
                    CBC_keys.remove(key)
                else:
                    print("Warning: value '%s' is not valid for key '%s', and will be ignored." % (value, key))
            elif key in CBC_keys:
                self.set_param(key, value)
                CBC_keys.remove(key)
            else:
                # TODO: Could throw a KeyError(?) telling that this key is not used for the linear mode
                print("Warning: key '%s' is not used in CBC, and will be ignored." % key)
        
        for key in CBC_keys:
            print("Warning: key '%s' not found. Value will remain unchanged" % key)


    
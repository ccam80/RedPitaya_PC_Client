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
    
    def set_mode(self, mode, **kwargs):
        """ 
        Sets an output mode for a determined channel. 
        
        Possible mode/**kwargs options
            1) linear feedback
                keys: A, B, input_channel
            2) cubic
                keys: fixed_x3_coeff, fixed_x2_coeff, fixed_x_coeff, fixed_offset, input_channel
                Note: A, B, C, D can be used shorthand.
            3) white_noise
                keys: fixed_amplitude, fixed_offset
            4) artificial_nonlinearity
                keys: fixed_x_coeff, fixed_x2_coeff, fixed_x3_coeff, fixed_offset
                Note: A, B, C, D can be used shorthand.
            5) artificial_nonlinearity_parametric
                keys: fixed_x_coeff, fixed_x2_coeff, fixed_x3_coeff, fixed_offset
                Note: A, B, C, D can be used shorthand.
            6) fixed_frequency
                keys: fixed_amplitude, fixed_offset, frequency
            7) frequency_sweep    
                keys: fixed_amplitude, fixed_offset, frequency    
                
        
        Usage: 
            RP.CH1.set_param("linear")
                -> mode = "linear"
                
            RP.CH1.set_param("cubic", fixed_offset=5)
                -> mode = "cubic"
                -> fixed_offset = 5
                
            RP.CH1.set_param("cubic", D=5)
                -> mode = "cubic"
                -> fixed_offset = 5
        """
        self.mode = mode
        if kwargs:
            # If there are any keyword-argument inputs, then the relevant 
            # set_param_(mode) function is called to set these parameters. 
            if mode == "linear_feedback":       
                self.set_params_linear(**kwargs)
            elif mode == "cubic":
                self.set_params_cubic(**kwargs)
            elif mode == "white_noise":
                self.set_params_noise(**kwargs)
            elif mode in ["artificial_nonlinearity", "artificial_nonlinearity_parametric"]:
                self.set_params_artificial(**kwargs)
            elif mode in ["fixed_frequency", "frequency_sweep"]:
                self.set_params_freq(**kwargs)
               
                
            
    def set_input_channel(self, input_channel):
        """
        Sets the logic for the correct input channel used for further computation. 
        
        Usage:
            RP.CH1.set_input_channel(1)
                -> input_channel = 2
        """
        self.input_channel = input_channel
        
        
        
    def set_param(self, param_name, param_val):
        """
        Sets relevant parameter value. 
        
        If the parameter can be swept (such as frequency), a list or tuple can 
        be given to set the sweep range. As such, the sweep logic is simultaneously 
        updated.
        
        Usage:
            RP.CH1.set_param("fixed_offset", 10)
                -> fixed_offset = 10
                
            RP.CH1.set_param("frequency", 10)
                -> frequency_start = 10
                -> frequency_stop = 0
                -> frequency_sweep = False
                
            RP.CH1.set_param("A", [1, 100])
                -> A_start = 1
                -> A_stop = 10
                -> A_sweep = True
        """
        if param_name in channel_sweepable:
            set_value_or_sweep(self, param_name, param_val, channel_sweepable)
        else:
            self[param_name] = param_val
        
    
    def set_params_linear(self, **kwargs):
        """
        Sets the parameters for the linear output type
        Coefficients are of the mathematical form of:
            y = Ax + B
        
        Possible key/arguments
            1) A - int, float, list, tuple
            2) B - int, float, list, tuple
            3) input_channel - int (1 or 2)
    
        Empty/non-assigned arguments will be ignored/left unchanged.
        Irrelevant arguments outside of the possible keys will be ignored.
        
        Usage:
            RP.CH1.set_params_linear(A=1)
                -> A_start = 1
                -> A_stop = 0
                -> A_sweep = False
                -> All other parameters are ignored.
                
            RP.CH1.set_params_linear(A=[1, 5])
                -> A_start = 1
                -> A_stop = 5
                -> A_sweep = True
                -> All other parameters are ignored.
            
            RP.CH1.set_params_linear(A=1, B=5)
                -> A_start = 1
                -> B_start = 5
                -> A_stop, B_stop = 0
                -> A_sweep, B_sweep = False
                -> All other parameters are ignored.
                
            RP.CH1.set_params_linear(input_channel=2)
                -> input_channel = 2
                -> All other parameters are ignored.
        """
        
        lin_keys = {"A", "B", "input_channel"}
        for key, value in kwargs.items():
            if key in lin_keys:
                self.set_param(key, value)
                lin_keys.remove(key)
            else:
                # TODO: Could throw a KeyError(?) telling that this key is not used for the linear mode
                print("Warning: key '%s' is not used in linear mode, and will be ignored." % key)
        
        for key in lin_keys:
            print("Warning: key '%s' not found. Value will remain unchanged" % key)
                

    def set_params_cubic(self, **kwargs):
        """
        Sets the parameters for the linear output type
        Coefficients are of the mathematical form of:
            y = Ax^3 + Bx^2 + Cx + D
                where: 
                    A := fixed_x3_coeff
                    B := fixed_x2_coeff
                    C := fixed_offset
                    D := fixed_offset
            
        Possible key/arguments
            1) fixed_x3_coeff, A - int, float, list, tuple
            2) fixed_x2_coeff, B - int, float, list, tuple
            3) fixed_x_coeff, C - int, float, list, tuple
            4) fixed_offset, D - int, float, list, tuple
            5) input_channel - int (1 or 2)
    
        Empty/non-assigned arguments will be ignored/left unchanged.
        Irrelevant arguments outside of the possible keys will be ignored.
        
        Usgae:
            RP.CH1.set_params_cubic(fixed_x3_coeff=1)
                -> fixed_x3_coeff = 1
                -> All other parameters are ignored.
                
            RP.CH1.set_params_cubic(fixed_x3_coeff=1, fixed_x2_coeff=4)
                -> fixed_x3_coeff = 1
                -> fixed_x2_coeff = 4
                -> All other parameters are ignored.
                
            RP.CH1.set_params_cubic(A=10, D=4)
                -> fixed_x3_coeff = 10
                -> fixed_offset = 4
                -> All other parameters are ignored.
        """
        
        cubic_keys = {"fixed_x3_coeff", "fixed_x2_coeff", "fixed_x_coeff", "fixed_offset", "input_channel"}
        for key, value in kwargs.items():                        
            if key == "A":
                self.set_param("fixed_x3_coeff", value)
                cubic_keys.remove("fixed_x3_coeff")
            elif key == "B":
                self.set_param("fixed_x2_coeff", value)
                cubic_keys.remove("fixed_x2_coeff")
            elif key == "C":
                self.set_param("fixed_x_coeff", value)
                cubic_keys.remove("fixed_x_coeff")
            elif key == "D":
                self.set_param("fixed_offset", value)
                cubic_keys.remove("fixed_offset")
            elif key in cubic_keys:
                self.set_param(key, value)
                cubic_keys.remove(key)
            else:
                # TODO: Could throw a KeyError(?) telling that this key is not used for the linear mode
                print("Warning: key '%s' is not used in cubic mode, and will be ignored." % key)           
        
        for key in cubic_keys:
            print("Warning: key '%s' not found. Value will remain unchanged" % key)
                
                
    def set_params_noise(self, **kwargs):
        """
         Sets the parameters for the white noise output type
         Coefficients are of the mathematical form of:
            Y = fixed_amplitude*Z + fixed_offset
                where:
                    Z ~ normal distribution w/ E(Z)=0, Var(Z)=?
        
        Possible key/arguments
            1) fixed_amplitude - int, float
            2) fixed_offset - int, float
    
        Empty/non-assigned arguments will be ignored/left unchanged.
        Irrelevant arguments outside of the possible keys will be ignored.
        
        Usgae:
            RP.CH1.set_params_noise(fixed_amplitude=1)
                -> fixed_amplitude = 1
                -> fixed_offset is ignored.
                
            RP.CH1.set_params_noise(fixed_amplitude=1, fixed_offset=4)
                -> fixed_amplitude = 1
                -> fixed_offset = 4
        """
        noise_keys = {"fixed_amplitude", "fixed_offset"}
            
        for key, value in kwargs.items():
            if key in noise_keys:
                self.set_param(key, value)
                noise_keys.remove(key)
            else:
                # TODO: Could throw a KeyError(?) telling that this key is not used for the linear mode
                print("Warning: key '%s' is not used in white noise mode, and will be ignored." % key)
        
        for key in noise_keys:
            print("Warning: key '%s' not found. Value will remain unchanged" % key)
                
    def set_params_freq(self, **kwargs):
        """
        Sets the parameters for the white noise output type
         Coefficients are of the mathematical form of:
            y = a sin(2*pi*f0*t) + c              or
            y = a sin(2*pi*f(t)*t) + c
                    where: 
                        f(t) = (f1-f0)*t/2/T + f0 (linear chirp)
                        a := fixed_amplitude
                        c := fixed_offset
                            
        Possible key/arguments
            1) frequency - int, float, list, tuple
                TODO: there is currently no logic between "fixed" and "swept" modes
            2) fixed_amplitude - int, float
            3) fixed_offset - int, float
    
        Empty/non-assigned arguments will be ignored/left unchanged.
        Irrelevant arguments outside of the possible keys will be ignored.
        
        Usgae:
            RP.CH1.set_params_freq(fixed_amplitude=1)
                -> fixed_amplitude = 1
                -> All other parameters are ignored.
                
            RP.CH1.set_params_freq(fixed_offset=1, frequency=4)
                -> fixed_offset = 1
                -> frequency_start = 4
                -> frequency_stop = 0
                -> frequency_sweep = False
                -> All other parameters are ignored.
                
            RP.CH1.set_params_freq(fixed_amplitude=1, frequency=[40, 400])
                -> fixed_amplitude = 1
                -> frequency_start = 40
                -> frequency_stop = 400
                -> frequency_sweep = True
                -> All other parameters are ignored.
        """
        
        freq_keys = {"fixed_amplitude", "fixed_offset", "frequency"}
        for key, value in kwargs.items():            
            if key in freq_keys:
                self.set_param(key, value)
                freq_keys.remove(key)
            else:
                # TODO: Could throw a KeyError(?) telling that this key is not used for the linear mode
                print("Warning: key '%s' is not used in frequency mode, and will be ignored." % key)
        
        for key in freq_keys:
            if key not in kwargs.keys():
                print("Warning: key '%s' not found. Value will remain unchanged" % key)
    
    
    def set_params_artificial(self, **kwargs):
        """
        Sets the parameters for the white noise output type
        Coefficients are of the mathematical form of:
            y = a*x1^3 + b*x1^2 + c*x1*x2 + d                   or
            y = a*x1^3 + b*x1^2 + c*x1*sin(2*pi*f*t) + d
                    where: 
                        a := fixed_x3_coeff
                        b := fixed_x2_coeff
                        c := fixed_offset
                        d := fixed_offset
                        f := frequency
                            
        Possible key/arguments
            1) fixed_x3_coeff - int, float
            2) fixed_x2_coeff - int, float
            3) fixed_x_coeff - int, float
            4) fixed_offset - int, float
            5) frequency - int, float 
                Frequency is only set if the mode is set to "artificial_nonlinearity_parametric"
    
        Empty/non-assigned arguments will be ignored/left unchanged.
        Irrelevant arguments outside of the possible keys will be ignored.
        
        Usgae:
            RP.CH1.set_params_artificial(fixed_x_coeff=1)
                -> fixed_x_coeff = 1
                -> All other parameters are ignored.
                
            RP.CH1.set_params_artificial(fixed_x3_coeff=1, frequency=4)
                -> fixed_x3_coeff = 1
                -> frequency_start = 4
                -> frequency_stop = 0
                -> frequency_sweep = False
                -> All other parameters are ignored.
                
            RP.CH1.set_params_artificial(fixed_x3_coeff=1, B=2)
                -> fixed_x3_coeff = 1
                -> fixed_x2_coeff = 2
                -> All other parameters are ignored.
        """
        artificial_keys = {"fixed_x_coeff", "fixed_x2_coeff", "fixed_x3_coeff", "fixed_offset", "frequency"}
        
        if self["mode"] != "artificial_nonlinearity_parametric":
            artificial_keys.remove("frequency_start")
        
        
        for key, value in kwargs.items():
            if key == "A":
                self.set_param("fixed_x3_coeff", value)
                artificial_keys.remove("fixed_x3_coeff")
            elif key == "B":
                self.set_param("fixed_x2_coeff", value)
                artificial_keys.remove("fixed_x2_coeff")
            elif key == "C":
                self.set_param("fixed_x_coeff", value)
                artificial_keys.remove("fixed_x_coeff")
            elif key == "D":
                self.set_param("fixed_offset", value)
                artificial_keys.remove("fixed_offset")
            elif key == "frequency" and self["mode"] == "artificial_nonlinearity_parametric":
                self.set_param("frequency", value)
                artificial_keys.remove("frequency")                
            elif key in artificial_keys:
                self.set_param(key, value)
                artificial_keys.remove(key)
            else:
                # TODO: Could throw a KeyError(?) telling that this key is not used for the artificial mode
                print("Warning: key '%s' is not used in artificial nonlinearity mode, and will be ignored." % key)
        
        for key in artificial_keys:
            if key not in kwargs.keys():
                print("Warning: key '%s' not found. Value will remain unchanged" % key)
                
    
    

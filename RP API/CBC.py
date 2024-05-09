# -*- coding: utf-8 -*-
"""
Created on Thu Aug  3 10:11:24 2023

@author: cca78

CBC.py

Under-the-hood functions which take user inputs from RedPitaya.py and modify the
CBC_config dictionary values accordingly
"""
from CBC_config import CBC_config
from _utils import fixed_or_sweep

CBC_sweepable = ["r_hat",
              "f",
              "a",
             "b",
             "c",
             "d"]

CBC_static = ["CBC_enabled",
             "input_order",
             "polynomial_target",
             "kp",
             "kd",
             "duration"  # Duration included in multiple places for ease of
                         # mapping in the dict translation module.
             ]

_default_values = {"CBC_enabled": 0,
           "input_order": 1,
           "polynomial_target":"displacement",
           "proportional_gain": 0,
           "derivative_gain": 0,
           "reference_amplitude_start": 0,
           "reference_amplitude_stop": 0,
           "reference_amplitude_sweep":0,
           "frequency_start": 0,
           "frequency_stop": 0,
           "frequency_sweep": 0,
           "cubic_amplitude_start": 0,
           "cubic_amplitude_stop": 0,
           "cubic_amplitude_sweep": 0,
           "quadratic_amplitude_start": 0,
           "quadratic_amplitude_stop": 0,
           "quadratic_amplitude_sweep": 0,
           "linear_amplitude_start": 0,
           "linear_amplitude_stop": 0,
           "linear_amplitude_sweep": 0,
           "offset_start": 0,
           "offset_stop": 0,
           "offset_sweep": 0,
           "duration": 0}


class CBC:

    def __init__(self, default_values=_default_values):
        self.config = CBC_config(default_values)

    def print_config(self):
        print ("{:<25} {:<25} ".format("Key", "CBC"))
        for key in self.config.keys():
            print ("{:<25} {:<25} ".format(key, str(self.config[key])))
        print()


    def set_param(self, param_name, param_val):
        """
        Sets relevant parameter value.

        If the parameter can be swept (such as frequency), a list or tuple can
        be given to set the sweep range. As such, the sweep logic is simultaneously
        updated.
        """

        param_ranges = fixed_or_sweep(param_name, param_val, "CBC")
        if len(param_ranges) == 3:
            self.config[param_name + "_start"] = param_ranges[0]
            self.config[param_name + "_stop"] = param_ranges[1]
            self.config[param_name + "_sweep"] = param_ranges[2]
        elif len(param_ranges) == 1:
            self.config[param_name] = param_ranges[0]





    def set_polynomial_target(self, target):
        """
        Set the polynomial variable used for the feedback mechanism.
        Choices are either 'displacement' or 'velocity'.

        Parameters
        ----------
        target : string
            Either 'displacement' or 'velocity'.

        Returns
        -------
        None.

        """
        if target == "displacement":
            self.config["polynomial_target"] = "displacement"
        elif target == "velocity":
            self.config["polynomial_target"] = "velocity"
        else:
            raise ValueError("'target' must be either 'displacement' or 'velocity'.")


    def set_params_CBC(self, cubic_amplitude=None, quadratic_amplitude=None, linear_amplitude=None, offset=None, reference_amplitude=None, proportional_gain=None, derivative_gain=None, frequency=None, polynomial_target=None, velocity_external=None, displacement_external=None, input_order=None):
        """
        Sets parameters within the CBC channel.
        Likely redundant/clunky to use - Use set_from_dict instead.
        """
        if cubic_amplitude:
            self.set_param("cubic_amplitude", cubic_amplitude)
        if quadratic_amplitude:
            self.set_param("quadratic_amplitude", quadratic_amplitude)
        if linear_amplitude:
            self.set_param("linear_amplitude", linear_amplitude)
        if offset:
            self.set_param("offset", offset)
        if reference_amplitude:
            self.set_param("reference_amplitude", reference_amplitude)
        if frequency:
            self.set_param("frequency", frequency)
        if proportional_gain:
            self.set_param("proportional_gain", proportional_gain)
        if derivative_gain:
            self.set_param("derivative_gain", derivative_gain)
        if polynomial_target:
            self.set_polynomial_target(polynomial_target)
        if input_order:
            self.set_input_order(input_order)


    def set_displacement_input(self, channel):
        """
        This function assigns the channel given as an argument to be the 
        "displacement" input to the CBC system. The other channel is 
        automatically assigned to be velocity (the system can not accept 
                                               multiple displacement inputs)

        Parameters
        ----------
        channel : int or string
            The channel that the displacement input is plugged into
            Can be 1, 2, "IN1", "IN2", "1", "2", "CH1", "CH2", to be
            a bit more user friendly.

        Returns
        -------
        None.

        """
        if str(channel) in ["1", "IN1", "CH1"]:
            self.config["input_order"] = 1
        elif str(channel) in ["2", "IN2", "CH2"]:
            self.config["input_order"] = 2
            
        else:
            raise ValueError("channel must be either X, CHX, or INX, where X=1 or X=2")
            
    def get_displacement_input(self):
          """
          This function returns the channel currently set as the displacement input
          to CBC. As multiple inputs to each state are impossible, the other 
          channel can be assumed to be displacement.
          
          Parameters
          ----------
          None 

          Returns
          -------
          channel (int) - 1 or 2, indicating the current displacement input.

          """
          if self.config["input_order"] == 1:
              print("Displacement input is set to IN1")
              return 1
          elif self.config["input_order"] == 2:
              print("Displacement input is set to IN2")
              return 2
            
    def set_velocity_input(self, channel):
          """
          This function assigns the channel, given as an argument, to be the 
          "velocity" input to the CBC system. The other channel is 
          automatically assigned to be displacement (the system can not accept 
                                                 multiple velocity inputs)

          Parameters
          ----------
          channel : int or string
              The channel that the displacement input is plugged into
              Can be 1, 2, "IN1", "IN2", "1", "2", "CH1", "CH2", to be
              a bit more user friendly.

          Returns
          -------
          None.

          """
          if str(channel) in ["1", "IN1", "CH1"]:
              self.config["input_order"] = 2
          elif str(channel) in ["2", "IN2", "CH2"]:
              self.config["input_order"] = 1
              
          else:
              raise ValueError("channel must be either X, CHX, or INX, where X=1 or X=2")   
    
    def get_velocity_input(self):
          """
          This function returns the channel currently set as the velocity input
          to CBC. As multiple inputs to each state are impossible, the other 
          channel can be assumed to be displacement.
          
          Parameters
          ----------
          None 

          Returns
          -------
          channel (int) - 1 or 2, indicating the current velocity input.

          """
          if self.config["input_order"] == 2:
              print("Velocity input is set to IN1")
              return 1
          elif self.config["input_order"] == 1:
              print("Velocity input is set to IN2")
              return 2
 

    def clear_param(self, parameter):
        self[parameter] = _default_values[parameter]

# -*- coding: utf-8 -*-
"""
Created on Thu Aug  3 10:11:24 2023

@author: cca78

CBC.py

Under-the-hood functions which take user inputs from RedPitaya.py and modify the
CBC_config dictionary values accordingly
"""
from CBC_config import CBC_config
from utils import fixed_or_sweep

CBC_sweepable = ["r_hat",
              "f",
              "A",
             "B",
             "C",
             "D"]

class CBC:

    def __init__(self):
        self.config = CBC_config()
        
    def print_config(self):
        for key, value in self.config.items():
            print(key,":", value)
            
    # def reset_config(self):
    #     for key in self.config.keys():            
    #         if isinstance(self.config[key], bool):
    #             self.config[key] = False
    #         elif isinstance(self.config[key], (float, int)):
    #             self.config[key] = 0
    #         elif isinstance(self.config[key], str):
    #             self.config[key] = ""
            
            
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
            start, stop, sweep = fixed_or_sweep(param_name, param_val, CBC_sweepable)
            self.config[param_name + "_start"] = start
            self.config[param_name + "_stop"] = stop
            self.config[param_name + "_sweep"] = sweep
        else:
            self.config[param_name] = param_val
            
            
            
    def set_external(self, external_input):
        if external_input == "displacement":
            self.config["displacement_external"] = True
            self.config["velocity_external"] = False            
        elif external_input == "velocity":
            self.config["displacement_external"] = False
            self.config["velocity_external"] = True
        else:
            raise ValueError("input type '%s' is invalid. Use either 'displacement' or 'velocity'")



    def set_params_CBC(self, A=None, B=None, C=None, D=None, rhat=None, kp=None, kd=None, frequency=None, polynomial_target=None, external=None, input_order=None):
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
        if A:
            self.set_param("A", A)
        if B:
            self.set_param("B", B)
        if C:
            self.set_param("C", C)
        if D:
            self.set_param("D", D)
        if rhat:
            self.set_param("rhat", rhat)
        if frequency:
            self.set_param("frequency", frequency)
        if kp:
            self.set_param("kp", kp)
        if kd:
            self.set_param("kd", kd)
        if polynomial_target:
            self.set_param("polynomial_target", polynomial_target)
        if external:
            self.set_external(external)
        if input_order:
            self.set_param("input_order", input_order)
        
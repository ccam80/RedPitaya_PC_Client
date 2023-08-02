# -*- coding: utf-8 -*-
"""
Created on Thu Aug  3 10:11:24 2023

@author: cca78

CBC.py

Under-the-hood functions which take user inputs from RedPitaya.py and modify the
CBC_config dictionary values accordingly
"""
from CBC_config import CBC_config

class CBC:

    def __init__(self):
        config = CBC_config()

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

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
             "velocity_external",
             "displacement_external",
             "polynomial_target",
             "kp",
             "kd",
             "duration"  # Duration included in multiple places for ease of
                         # mapping in the dict translation module.
             ]

_default_values = {"CBC_enabled": 0,
           "input_order": 1,
           # "velocity_external": [0, 1],
           # "displacement_external": [0, 1],
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
        if displacement_external:
            self.set_displacement_external(displacement_external)
        if velocity_external:
            self.set_velocity_external(velocity_external)
        if input_order:
            self.set_input_order(input_order)

        def set_input_order(self, input_channel):
            """
            Note: This is an old function - please use 'determine_input_order' instead.
            This function sets which input channel is displacement.

            Parameters
            ----------
            input_channel : int
                1 or 2

            Returns
            -------
            None.
            """

            if input_channel in [1, 2]:
                self.config["input_channel"] = input_channel
            else:
                raise ValueError("'input_channel' must be either 1 or 2.")


    def determine_input_order(self, IN1, IN2):
        """
        This function takes in the physical description of the signal in each
        input channel, and interprets the logic required for setting the
        relevant MUX within the FPGA.
        (See TODO1 for logic, and put in description here)

        Parameters
        ----------
        IN1 : string
            'displacement' or 'velocity'.
        IN2 : string
            'displacement' or 'velocity'.

        Returns
        -------
        None.

        """
        # TODO1 - check whether the logic here makes sense. Added an additional option of "0" where both inputs are not set at all.
        #   If IN1=Disp, IN2=Vel  -> input_order=1?
        #   If IN1=Vel,  IN2=Disp -> input_order=2?
        # On top of this logic, if an input is set to "none", then whichever option the other input is, it conforms to that.
        # Of course, it means that if there is no input set, then that state must be either differentiated/integrated to be re-constructed down the line.

        # velocity_external     = 0 -> to use the differentiater?
        # displacement_external = 0 -> to use the integrator?

        # Case 0 - Neither input is plugged in
        if IN1 == "none"            and IN2 == "none":
            self.config["input_order"] = 0

        # Case 1 - Only one of the inputs are given
        elif IN1 == "none"          and IN2 == "displacement":
            self.config["input_order"] = 2
            self.config["displacement_external"] = True
            self.config["velocity_external"] = False
        elif IN1 == "none"          and IN2 == "velocity":
            self.config["input_order"] = 1
            self.config["displacement_external"] = False
            self.config["velocity_external"] = True
        elif IN1 == "displacement"  and IN2 == "none":
            self.config["input_order"] = 1
            self.config["displacement_external"] = True
            self.config["velocity_external"] = False
        elif IN1 == "velocity"      and IN2 == "none":
            self.config["input_order"] = 2
            self.config["displacement_external"] = False
            self.config["velocity_external"] = True

        # Case 2 - both inputs are uniquely given
        elif IN1 == "displacement"  and IN2 == "velocity":
            self.config["input_order"] = 1
        elif IN1 == "velocity"      and IN2 == "displacement":
            self.config["input_order"] = 2

        # Case 3 - both inputs are repeated of the same (this basically shouldn't happen)
        elif IN1 == "displacement"  and IN2 == "displacement":
            raise ValueError("Both inputs are set to 'displacement'. For computation, only one of these channels will be used in CBC mode.")
        elif IN1 == "velocity"      and IN2 == "velocity":
            raise ValueError("Both inputs are set to 'velocity'. For computation, only one of these channels will be used in CBC mode.")
        else:
            raise ValueError("'IN1' and 'IN2' must be either 'displacement', 'velocity', or 'none'")


    def set_external(self, external_input, logic):
        """
        A general function which determines whether a particular input should use
        the original signal, or an integrated/differentiated variant of itself.

        Parameters
        ----------
        external_input : string
            'displacement' or 'velocity'
        logic : bool
            True  - To use the original, external signal.
            False - To differentiate/integrate the signal.

        Returns
        -------
        None.

        """
        # TODO1: To check whether logic is the correct way around.
        if not isinstance(logic, bool):
            raise TypeError("'logic' should be of boolean type; either True or False")

        if external_input == "displacement":
            self.set_displacement_external(logic)
        elif external_input == "velocity":
            self.set_velocity_external(logic)
        else:
            raise ValueError("input type '%s' is invalid. Use either 'displacement' or 'velocity'")


    def set_displacement_external(self, logic):
        """
        Determines whether to use the direct displacement measure, or an integrated veocity measure.
            True  = Direct/external
            False = Integrated
        """
        # TODO1: To check whether logic is the correct way around.
        if isinstance(logic, bool):
            self.config["displacement_external"] = logic
        else:
            raise TypeError("'logic' should be of type 'bool'")


    def set_velocity_external(self, logic):
        """
        Determines whether to use the direct velocity measure, or a differentiated displacement measure.
            True  = Direct/external
            False = Differentiated
        """
        # TODO1: To check whether logic is the correct way around.
        if isinstance(logic, bool):
            self.config["velocity_external"] = logic
        else:
            raise TypeError("'logic' should be of type 'bool'")

     def clear_param(self, parameter):
         self[parameter] = _default_values[parameter]

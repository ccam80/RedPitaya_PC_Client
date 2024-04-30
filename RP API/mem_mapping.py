# -*- coding: utf-8 -*-
"""
Created on Thu Aug  3 11:52:43 2023

@author: cca78

mem_mapping.py contains the per-mode mappings from the physical mode settings
(frequency, amplitude, etc) to the FPGA's memory representation. This requires
both a mapping of each physical parameter to a different place in memory
per mode, but also some conversion, for example from a start-stop-sweep triplet
to a start-interval pair for swept values, and from frequency to phase increment.

This is a translation from human to hardware, so the output is not intended to
be particularly human-readable, however the mapping should be readable.
"""

from float_converter import NumpyFloatToFixConverter
from functools import partial


# Map mode names to their number representation on fabric
_channel_modes = {"fixed_frequency": 0,
                  "frequency_sweep": 1,
                  "artificial_nonlinearity": 2,
                  "artificial_nonlinearity_parametric": 3,
                  "cubic": 6,
                  "linear_feedback": 4,
                  "white_noise": 5,
                  "off": 7}

# Map selected input channel onto binary toggle on fabric
_channel_inputs = {1:1,
                   2:0}

# Map CBC channel selection onto binary toggle on fabric
_CBC_input_orders = {1:1,
                    2:0}

# Map "polynomial target" onto binary toggle on fabric
_polynomial_targets = {'displacement': 0,
                     'velocity': 1}

_continuous_modes = {True: 1,
                     False: 0}

_fast_modes = {'fast': 1,
               'slow': 0}

_millivolts_to_counts = 8192/1000
_FPGA_clk_freq = 125000000

# Start float to Q16.16 format converter
_float_to_fix = NumpyFloatToFixConverter(True, 32, 16)


def range_to_interval(start, stop, duration):
    """Convert a sweep from a sensible format of  start:stop into the less
    sensible format of start and interval. Only works on values already
    transferred to the right form of binary

    The interval is how many clock ticks to wait before increasing the number
    by a binary LSB, which will change values depending on which parameter
    we're talking about.

    Arguments:
        start(int): start of range
        stop(int): final of range
        duration(int or float): Duration of sweep in seconds

    Returns:
        interval (int): closest integer (floor rounded) to the number of clock
        cycles required between LSB increments.

    e.g.

    range_to_interval(1.0, 100, 0.5)
    >> 631313

    """
    
    # rate = 488281
    try:
        span = stop - start
        return int(duration * _FPGA_clk_freq / span)
        # return int(span/(duration * 125.0e6))

    except ValueError:
        raise TypeError(f"'range_to_interval' expects three float or int arguments, you have passed it a {type(start)}, {type(stop)}, {type(duration)} instead.")


def freq_to_phase(frequency):
    """Convert frequency to a phase increment for the FPGA's DDS compiler.
    Frequency can be a float or an integer. Return value is an int, ready
    for storage. Don't expect number to make sense to you if you are not
    an FPGA, and even if you are, don't expect it to make sense unless you're
    an FPGA with a DDS compiler running at 125MHz with a 30 bit phase width.

    Arguments:
        frequency(int or float): desired frequency

    Returns:
        increment (int): increment - DDS compiler will advance by:
            increment / 2^30 of a full phase

    e.g.

    freq_to_phase(100000.0)
    >> 858993

    Equation in https://docs.xilinx.com/v/u/en-US/pg141-dds-compiler
    """

    # sanitise input and calculate increment, raise error if it's the wrong type
    try:
        return int(float(frequency) / _FPGA_clk_freq * (1 << 30) + 0.5)
    except ValueError:
        raise TypeError(f"'freq_to_phase' expects a float or int argument, you have passed it a {type(frequency)} instead.")


def interval_if_sweep(start, stop, sweep, duration, conversion=None):
    """Return an "interval" value given config dict values. A bit of a busy
    function, potentially doing too many things. Converts values if given a
    conversion function, checks if "sweep" is true - if true, calculate and
    return interval using appropriate function, otherwise return 0.

    Arguments:
        start (int or float): starting value from config dict
        stop (int or float): starting value from config dict
        sweep (bool): sweep toggle from config dict
        conversion (callable): scaling or conversion function

    Returns:
        interval value or 0

    e.g.

    get_interval_if_sweep(0,100,True, 1.0, conversion=freq_to_phase)
    >>  10737418

    get_interval_if_sweep(0,100,False, 1.0, conversion=freq_to_phase)
    >>  0

    get_interval_if_sweep(0,100,True, 1.0, conversion=None)
    >>  10737418
    """

    if callable(conversion):
        start = conversion(start)
        stop = conversion(stop)

    if sweep:
        return range_to_interval(start, stop, duration)
    else:
        return 0


def channel_settings_to_byte(mode, input_select):
    """Take channel settings dictionary and manipulate the boolean options
    into an integer value corresponding to their position in memory, outlined
    in Onboard/interfaces.md.

    Arguments:
        mode (string): Channel operating mode
        input_select (int): input channel for output in question

    Returns:
        config_byte (int): an integer value corresponding to the bit pattern
            of the boolean toggles according to Onboard/interfaces.md

    e.g.

    channel_settings_to_byte("linear_feedback", 2)
    >> 15
    """
    try:
        input_channel = _channel_inputs[input_select]
        return (int(_channel_modes[mode] << 1) | input_channel)
    except:
        raise TypeError(f"The CH1 settings arguments (mode, input_select) are not valid!")


def channel_settings_for_CBC(ignored):
    """Sets channel mode to 'off' (mode 7), which internally enables CBC on the RP

    Arguments:
        ignored: ignored, but required for compatibility with mapping function
    Returns:
        config_byte (int): an integer value corresponding to an 'off' mode and
        input_channel of 1 (input_channel is unused in CBC)

    e.g.

    channel_settings_for_CBC(42)
    >> 14
    """
    return(int(_channel_modes['off'] << 1))
    

def CBC_settings_to_byte(input_order,
                         velocity_external,
                         displacement_external,
                         polynomial_target):
    """Take CBC settings dictionary and manipulate the boolean options
    into an integer value corresponding to their position in memory, outlined
    in Onboard/interfaces.md. velocity_external and displacement_internal's
    logical clash is covered in higher-level logic - don't call both True.'

    Arguments:
        input_order (string): Choose which input is displacement
        velocity_external (bool): velocity external or internal
        displacement_external (bool): displacement external or internal
        polynomial_target (string): is the cubic acting on displacement or vel?

    Returns:
        config_byte (int): an integer value corresponding to the bit pattern
            of the boolean toggles according to Onboard/interfaces.md

    e.g.

    CBC_settings_to_byte(1, True, False, 'displacement')
    >> 3
    """
    try:
        input_order = _CBC_input_orders[input_order]
        velocity = int(velocity_external) << 1
        displacement = int(displacement_external) << 2
        poly = _polynomial_targets[polynomial_target] <<3
        return (input_order | velocity | displacement | poly)
    except:
        raise TypeError(f"The CBC settings arguments (mode, input_select) are not valid!")

def scale_and_convert(scale, value, conversion=None):
    """Multiplies value by a constant, then converts to an int for storage.

    Arguments:
        value (float or int): physical parameter value
        scale (float or int): multiplier (originally hard coded)

    Returns:
        result (int): integer result of multiplication

    e.g.
    scale_and_convert(1, 2.5)
    >> 2
    """
    if callable(conversion):
        result = conversion(value * scale)
    elif conversion == None:
        result = int(float(value)*float(scale))
    else:
        raise TypeError("You have given a non-callable conversion function handle")
        return 0

    return result



# Function to apply mappings based on the mode with bitwise combination. Work required
def update_FPGA_channel(channel, settings_dict, FPGA):
    """Converts settings dictionaries into FPGA config values ready for sending
    to the c server. Calling this without zeroing the other mode (CBC/channel)
    will result in undefined behaviour, so do not call this function directly.
    Used by update_FPGA().

    Arguments:
        channel (int or string): 1, 2, or 'CBC'. This setting picks a mapping.
        settings_dict (channel_config or FPGA_config)
    """

    if channel == 1:
        mapping = _CH1_mappings[settings_dict['mode']]
    elif channel == 2:
        mapping = _CH2_mappings[settings_dict['mode']]
    elif channel == 'CBC':
        mapping = _CBC_mappings

    for param, arguments in mapping.items():
        if isinstance(arguments, (int, float)):
            FPGA[param] = arguments
        elif isinstance(arguments, (tuple, list)):
            if callable(arguments[0]):
                #in arguments tuple, use any strings as dict keys, and pass
                #numeric inputs through untouched.
                arguments_list = [settings_dict[arg] if isinstance(arg, str) else arg for arg in arguments[1]]

                FPGA[param] = arguments[0](*arguments_list)

def update_FPGA_config(system_dict, FPGA):
    """Converts system settings dict into FPGA config values ready for sending
    to the c server. Used by update_FPGA().

    Take system settings dictionary and trigger and manipulate the boolean options
    into an integer value corresponding to their position in memory, outlined
    in Onboard/interfaces.md.

    Arguments:
        system_dict (system_config): Custom dictionary of system config parameters
        trigger (int): 1 for trigger, 0 for no trigger -separated as this is set
                        by RP.comms module. Potential target for refactoring.
    Returns:
        None
    e.g.

    FPGA_config_to_byte(config, trigger, FPGA)
    >>
    """
    fast_mode = int(_fast_modes[system_dict.sampling_rate]) << 4
    continuous_mode = int(_continuous_modes[system_dict.continuous_output]) << 3
    # _trigger = int(trigger) << 2 // trigger removed as it is set in the comms module, I will need to handle it there. Delete this comment if still here June 2024.
    settings_byte = int(fast_mode | continuous_mode)
    FPGA['system'] = settings_byte
    

"""Mapping dictionaries. One dictionary per mode. Each dictionary is keyed by
the FPGA-memory parameter, with an entry that is either a number, a string, or
a tuple of a function handle and a tuple or list of arguments.

If a number, set parameter to this value (usually 0). If a string, set parameter
to config[string]. If a tuple, call the first argument with config[second] as
its arguments"""
_CH1_mappings = {
    "fixed_frequency": {
        "CH1_settings": (channel_settings_to_byte, ("mode",
                                                    "input_channel")),
        "Parameter_A": (freq_to_phase, ("frequency_start",)),
        "Parameter_B": (scale_and_convert, (_millivolts_to_counts, "linear_amplitude_start",)),
        "Parameter_C": (scale_and_convert, (_millivolts_to_counts, "offset_start")),
        "Parameter_D": 0,
        "Parameter_E": 0,
        "Parameter_F": 0,
    },

    "frequency_sweep": {
        "CH1_settings": (channel_settings_to_byte, ("mode",
                                                    "input_channel")),
        "Parameter_A": (freq_to_phase, ("frequency_start", )),
        "Parameter_B": (interval_if_sweep, ("frequency_start",
                                             "frequency_stop",
                                             "frequency_sweep",
                                             "duration",
                                             freq_to_phase)),
        "Parameter_C": (scale_and_convert, (_millivolts_to_counts, "linear_amplitude_start")),
        "Parameter_D": (scale_and_convert, (_millivolts_to_counts, "offset_start")),
        "Parameter_E": 0,
        "Parameter_F": 0,
    },

    "artificial_nonlinearity": {
        "CH1_settings": (channel_settings_to_byte, ("mode",
                                                    "input_channel")),
        "Parameter_A": (scale_and_convert, (_millivolts_to_counts, "offset_start")),
        "Parameter_B": 0,
        "Parameter_C": (scale_and_convert, (1, 'linear_amplitude_start')),
        "Parameter_D": (scale_and_convert, (1, 'quadratic_amplitude_start')),
        "Parameter_E": (scale_and_convert, (1, 'cubic_amplitude_start')),
        "Parameter_F": 0,
    },

    "artificial_nonlinearity_parametric": {
        "CH1_settings": (channel_settings_to_byte, ("mode",
                                                    "input_channel")),
        "Parameter_A": (scale_and_convert, (_millivolts_to_counts, "offset_start")),
        "Parameter_B": 0,
        "Parameter_C": (scale_and_convert, (1, 'linear_amplitude_start')),
        "Parameter_D": (scale_and_convert, (1, 'quadratic_amplitude_start')),
        "Parameter_E": (scale_and_convert, (1, 'cubic_amplitude_start')),
        "Parameter_F": (freq_to_phase, ('frequency_start', )),
    },

    "cubic": {
        "CH1_settings": (channel_settings_to_byte, ("mode",
                                                    "input_channel")),
        "Parameter_A": (scale_and_convert, (1/512,
                                            'linear_amplitude_start',
                                            _float_to_fix)),
        "Parameter_B": (scale_and_convert, (1/(64*0.98631), # 0.987 is a measured calibration constant
                                            'quadratic_amplitude_start',
                                            _float_to_fix)),
        "Parameter_C": (scale_and_convert, (1/(64*0.96659), # 0.967 is a measured calibration constant
                                            'cubic_amplitude_start',
                                            _float_to_fix)),
        "Parameter_D": 0,
        "Parameter_E": (scale_and_convert, (_millivolts_to_counts, 'offset_start')),
        "Parameter_F": 0,
    },

    "linear_feedback": {
        "CH1_settings": (channel_settings_to_byte, ("mode",
                                                    "input_channel")),
        "Parameter_A": (_float_to_fix, ("linear_amplitude_start",)),
        "Parameter_B": (_float_to_fix, ("linear_amplitude_start",)),
        "Parameter_C": (scale_and_convert, (_millivolts_to_counts, "offset_start")),
        "Parameter_D": (interval_if_sweep, ("linear_amplitude_start",
                                            "linear_amplitude_stop",
                                            "linear_amplitude_sweep",
                                            "duration",
                                            _float_to_fix)),
        "Parameter_E": (interval_if_sweep, ("offset_start",
                                            "offset_stop",
                                            "offset_sweep",
                                            "duration",
                                            partial(scale_and_convert, _millivolts_to_counts))),
        "Parameter_F": 0,
    },

    "white_noise": {
        "CH1_settings": (channel_settings_to_byte, ("mode",
                                                    "input_channel")),
        "Parameter_A": 0,
        "Parameter_B": 0,
        "Parameter_C": (scale_and_convert, (_millivolts_to_counts, "linear_amplitude_start")),
        "Parameter_D": (scale_and_convert, (_millivolts_to_counts, 'offset_start')),
        "Parameter_E": 0,
        "Parameter_F": 0,
    },

    "off": {
        "CH1_settings": (channel_settings_to_byte, ("mode",
                                                    "input_channel")),
        "Parameter_A": 0,
        "Parameter_B": 0,
        "Parameter_C": 0,
        "Parameter_D": 0,
        "Parameter_E": 0,
        "Parameter_F": 0,
    },
}

_CH2_mappings = {
    "fixed_frequency": {
        "CH2_settings": (channel_settings_to_byte, ("mode",
                                                    "input_channel")),
        "Parameter_G": (freq_to_phase, ("frequency_start",)),
        "Parameter_H": (scale_and_convert, (_millivolts_to_counts, "linear_amplitude_start",)),
        "Parameter_I": (scale_and_convert, (_millivolts_to_counts, "offset_start")),
        "Parameter_J": 0,
        "Parameter_K": 0,
        "Parameter_L": 0,
    },

    "frequency_sweep": {
        "CH2_settings": (channel_settings_to_byte, ("mode",
                                                    "input_channel")),
        "Parameter_G": (freq_to_phase, ("frequency_start", )),
        "Parameter_H": (interval_if_sweep, ("frequency_start",
                                             "frequency_stop",
                                             "frequency_sweep",
                                             "duration",
                                             freq_to_phase)),
        "Parameter_I": (scale_and_convert, (_millivolts_to_counts, "linear_amplitude_start")),
        "Parameter_J": (scale_and_convert, (_millivolts_to_counts, "offset_start")),
        "Parameter_K": 0,
        "Parameter_L": 0,
    },

    "artificial_nonlinearity": {
        "CH2_settings": (channel_settings_to_byte, ("mode",
                                                    "input_channel")),
        "Parameter_G": (scale_and_convert, (_millivolts_to_counts, "offset_start")),
        "Parameter_H": 0,
        "Parameter_I": (scale_and_convert, (1, 'linear_amplitude_start')),
        "Parameter_J": (scale_and_convert, (1, 'quadratic_amplitude_start')),
        "Parameter_K": (scale_and_convert, (1, 'cubic_amplitude_start')),
        "Parameter_L": 0,
    },

    "artificial_nonlinearity_parametric": {
        "CH2_settings": (channel_settings_to_byte, ("mode",
                                                    "input_channel")),
        "Parameter_G": (scale_and_convert, (_millivolts_to_counts, "offset_start")),
        "Parameter_H": 0,
        "Parameter_I": (scale_and_convert, (1, 'linear_amplitude_start')),
        "Parameter_J": (scale_and_convert, (1, 'quadratic_amplitude_start')),
        "Parameter_K": (scale_and_convert, (1, 'cubic_amplitude_start')),
        "Parameter_L": (freq_to_phase, ('frequency_start', )),
    },

    "cubic": {
        "CH2_settings": (channel_settings_to_byte, ("mode",
                                                    "input_channel")),
        "Parameter_G": (scale_and_convert, (1/512,
                                            'linear_amplitude_start',
                                            _float_to_fix)),
        "Parameter_H": (scale_and_convert, (1/(64*0.98631), # 0.987 is a measured calibration constant
                                            'quadratic_amplitude_start',
                                            _float_to_fix)),
        "Parameter_I": (scale_and_convert, (1/(64*0.96659), # 0.967 is a measured calibration constant
                                            'cubic_amplitude_start',
                                            _float_to_fix)),
        "Parameter_J": 0,
        "Parameter_K": (scale_and_convert, (_millivolts_to_counts, 'offset_start')),
        "Parameter_L": 0,
    },

    "linear_feedback": {
        "CH2_settings": (channel_settings_to_byte, ("mode",
                                                    "input_channel")),
        "Parameter_G": (_float_to_fix, ("linear_amplitude_start",)),
        "Parameter_H": (_float_to_fix, ("linear_amplitude_start",)),
        "Parameter_I": (scale_and_convert, (_millivolts_to_counts, "offset_start")),
        "Parameter_J": (interval_if_sweep, ("linear_amplitude_start",
                                            "linear_amplitude_stop",
                                            "linear_amplitude_sweep",
                                            "duration",
                                            _float_to_fix)),
        "Parameter_K": (interval_if_sweep, ("offset_start",
                                            "offset_stop",
                                            "offset_sweep",
                                            "duration",
                                            partial(scale_and_convert, _millivolts_to_counts))),
        "Parameter_L": 0,
    },

    "white_noise": {
        "CH2_settings": (channel_settings_to_byte, ("mode",
                                                    "input_channel")),
        "Parameter_G": 0,
        "Parameter_H": 0,
        "Parameter_I": (scale_and_convert, (_millivolts_to_counts, "linear_amplitude_start")),
        "Parameter_J": (scale_and_convert, (_millivolts_to_counts, 'offset_start')),
        "Parameter_K": 0,
        "Parameter_L": 0,
    },

    "off": {
        "CH2_settings": (channel_settings_to_byte, ("mode",
                                                    "input_channel")),
        "Parameter_G": 0,
        "Parameter_H": 0,
        "Parameter_I": 0,
        "Parameter_J": 0,
        "Parameter_K": 0,
        "Parameter_L": 0,
    },
}

_CBC_mappings = {
    "CH1_settings": (channel_settings_for_CBC, (0,)), # CBC is toggled by the 4-bits which represent CH1's mode. 
                          # Turning channels 'off' should turn CBC on (by design, this 
                          # makes sense to me), but I could be persuaded otherwise.
                          # therefore, to tur CBC on, ew need to turn channels off in
                          # this mapping. This doesn't make sense, open to an alternative
                          # strategy.
    "CH2_settings": (channel_settings_for_CBC, (0,)),
    "CBC_settings": (CBC_settings_to_byte, ("input_order",
                                            "velocity_external",
                                            "displacement_external",
                                            "polynomial_target")),
    
    
    "Parameter_A": (_float_to_fix, ('reference_amplitude_start',)),
    
    # Copy-paste setting from CH frequency_sweep mode. Didn't work
    # "Parameter_A": (scale_and_convert, (_millivolts_to_counts, "reference_amplitude_start")),
    
    
    "Parameter_B": (interval_if_sweep, ("reference_amplitude_start",
                                        "reference_amplitude_stop",
                                        "reference_amplitude_sweep",
                                        "duration",
                                        _float_to_fix)), #this may need to be multiplied up from 1000 max to ADC_max
    
    
    "Parameter_C": (freq_to_phase, ("frequency_start", )),
    "Parameter_D": (interval_if_sweep, ("frequency_start",
                                          "frequency_stop",
                                          "frequency_sweep",
                                          "duration",
                                          freq_to_phase)),
    
    
    "Parameter_E": (_float_to_fix, ("proportional_gain",)),
    "Parameter_F": (_float_to_fix, ("derivative_gain",)),
    "Parameter_G": (scale_and_convert, (1/(64*0.96659), # 0.967 is a measured calibration constant
                                        'cubic_amplitude_start',
                                        _float_to_fix)),
    "Parameter_H": (interval_if_sweep, ("cubic_amplitude_start",
                                        "cubic_amplitude_stop",
                                        "cubic_amplitude_sweep",
                                        "duration",
                                        partial(scale_and_convert,
                                                1/(64*0.96659),
                                                conversion=_float_to_fix))),
    "Parameter_I":(scale_and_convert, (1/(64*0.98631), # 0.987 is a measured calibration constant
                                        'quadratic_amplitude_start',
                                        _float_to_fix)),
    "Parameter_J": (interval_if_sweep, ("quadratic_amplitude_start",
                                        "quadratic_amplitude_stop",
                                        "quadratic_amplitude_sweep",
                                        "duration",
                                        partial(scale_and_convert,
                                                1/(64*0.98631),
                                                 conversion=_float_to_fix))),
    "Parameter_K": (scale_and_convert, (1/512, 
                                        'linear_amplitude_start',
                                        _float_to_fix)),
    "Parameter_L": (interval_if_sweep, ("linear_amplitude_start",
                                        "linear_amplitude_stop",
                                        "linear_amplitude_sweep",
                                        "duration",
                                        partial(scale_and_convert,
                                                1/512,
                                                conversion=_float_to_fix))),
    
    # Copy-paste settings from CH linear_feedback mode. Didn't work.
    # "Parameter_K": (_float_to_fix, ("linear_amplitude_start",)),
    # "Parameter_L": (interval_if_sweep, ("linear_amplitude_start",
    #                                     "linear_amplitude_stop",
    #                                     "linear_amplitude_sweep",
    #                                     "duration",
    #                                     _float_to_fix)),
    
    
    "Parameter_M": (scale_and_convert, (_millivolts_to_counts, 'offset_start')),
    "Parameter_N": (interval_if_sweep, ("offset_start",
                                        "offset_stop",
                                        "offset_sweep",
                                        "duration",
                                        partial(scale_and_convert,
                                                _millivolts_to_counts)))
    
}

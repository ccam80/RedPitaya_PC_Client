# -*- coding: utf-8 -*-
"""
Created on Thu Aug  3 11:52:43 2023

@author: cca78

mem_mapping.py contains the per-mode mappings from the physical mode settings
(frequency, amplitude, etc) to the FPGA's memory representation. This requires
both a mapping of each physical mparameter to a different place in memory
per mode, but also some conversion, for example from a start-stop-sweep triplet
to a start-interval pair for swept values, and from frequency to phase increment.

This is a translation from human to hardware, so the output is not intended to
be particularly human-readable, however the mapping should be readable.
"""

from numpy import multiply

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


_CH1_mode_mappings = {
    "fixed_frequency": {
        "CH1_settings": (channel_settings_to_byte, ("mode",
                                                    "input_select")),
        "Paramater_A": (frequency_to_phase, ("frequency_start")),
        "Paramater_B": (interval_if_sweep, ("frequency_start",
                                             "frequency_stop",
                                             "frequency_sweep",
                                             "duration")),
        "Paramater_C": (scale_and_convert, ("A", 8.192)),
        "Paramater_D": (scale_and_Convert, ("B", 8.192*32768)),
        "Paramater_E": 0,
        "Paramater_F": 0,
    },

    "frequency_sweep": {
        "CH1_settings": (channel_settings_to_byte, ("mode",
                                                    "input_select")),
        "Paramater_A": (frequency_to_phase, ("frequency_start")),
        "Paramater_B": (interval_if_sweep, ("frequency_start",
                                             "frequency_stop",
                                             "frequency_sweep",
                                             "duration")),
        "Paramater_C": (scale_and_convert, ("A", 8.192)),
        "Paramater_D": (scale_and_Convert, ("B", 8.192*32768)),
        "Paramater_E": 0,
        "Paramater_F": 0,
    },
    "artificial_nonlinearity": {
       "CH1_settings": ("CH1", "ampl"),
       "Paramater_A": ("CH2", "freq"),
       "Paramater_B": ("CBC", "kp"),
       "Paramater_C": ("CBC", "kd"),
       "Paramater_D": ("CH2", "ampl"),
       "Paramater_E": ("CH2", "freq"),
       "Paramater_F": ("CH1", "ampl"),
    },
    "artificial_nonlinearity_parametric": {
       "CH1_settings": ("CH1", "ampl"),
       "Paramater_A": ("CH2", "freq"),
       "Paramater_B": ("CBC", "kp"),
       "Paramater_C": ("CBC", "kd"),
       "Paramater_D": ("CH2", "ampl"),
       "Paramater_E": ("CH2", "freq"),
       "Paramater_F": ("CH1", "ampl"),
    },
    "cubic": {
        "CH1_settings": ("CH1", "ampl"),
        "Paramater_A": ("CH2", "freq"),
        "Paramater_B": ("CBC", "kp"),
        "Paramater_C": ("CBC", "kd"),
        "Paramater_D": ("CH2", "ampl"),
        "Paramater_E": ("CH2", "freq"),
        "Paramater_F": ("CH1", "ampl"),
    },
    "linear_feedback": {
        "CH1_settings": ("CH1", "ampl"),
        "Paramater_A": ("CH2", "freq"),
        "Paramater_B": ("CBC", "kp"),
        "Paramater_C": ("CBC", "kd"),
        "Paramater_D": ("CH2", "ampl"),
        "Paramater_E": ("CH2", "freq"),
        "Paramater_F": ("CH1", "ampl"),
    },
    "white_noise": {
        "CH1_settings": ("CH1", "ampl"),
        "Paramater_A": ("CH2", "freq"),
        "Paramater_B": ("CBC", "kp"),
        "Paramater_C": ("CBC", "kd"),
        "Paramater_D": ("CH2", "ampl"),
        "Paramater_E": ("CH2", "freq"),
        "Paramater_F": ("CH1", "ampl"),
    },
    "off": {
        "CH1_settings": ("CH1", "ampl"),
        "Paramater_A": ("CH2", "freq"),
        "Paramater_B": ("CBC", "kp"),
        "Paramater_C": ("CBC", "kd"),
        "Paramater_D": ("CH2", "ampl"),
        "Paramater_E": ("CH2", "freq"),
        "Paramater_F": ("CH1", "ampl"),
    }
}

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
    try:
        span = stop - start
        return int(duration * 125.0e6 / span)

    except ValueError:
        raise TypeError(f"'range_to_interval' expects two float or int arguments, you have passed it a {type(start)} and {type(stop)} instead.")


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
        return int(float(frequency) / 125.0e6 * (1 << 30) + 0.5)
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
        channel_dict (channel_config): Custom dictionary of config parameters

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

def scale_and_convert(value, scale):
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

    return int(float(value)*float(scale))



# Function to apply mappings based on the mode with bitwise combination. Work required
def apply_mode_mapping(mode, memory, channel_settings):
    mappings = mode_mappings.get(mode)
    if mappings:
        for mem_param, (config_key, manipulation_func, *params) in mappings.items():
            if callable(config_key):  # Check if the mapping involves a function
                config_values = [channel_settings[param][param_key] for param_key in params]
                value = config_key(*config_values, *params)
            else:
                value = channel_settings[config_key][param_key]
            if isinstance(value, int):  # Ensure the value is an integer (if it's a bitwise combination)
                memory[mem_param] = value

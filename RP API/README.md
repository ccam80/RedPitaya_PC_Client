# Red Pitaya API

Containing in these files are various files which contain API functions for the RedPitaya development. 
The Python commands are to be used as an interface between user and the RP's FPGA logic. 
The following sub-headings contain documentation and information of each of the functions found, and a description/usage example for each.

Below is a typical runthrough of an experiment, using the API functions:
```python
########### Example of a typical channel experimental run-through ############
# In this example, the output is set to linear feedback. The parameter "B" is swept from 2->5, with constant "A". The "A" parameter is varied within the range of 0->10 over multiple experiments.
RP = RedPitaya()                                              # Initialise RP object
...                                                           # Set measurement controls (Sampling rate, sampling period, etc)
RP.set_output("CHx")                                          # Choose channels (turn off CBC)
RP.CH1.set_mode("linear")                                     # Set the output mode(s)
RP.CH1.set_params_linear(A=1, B=[2, 5], input_channel=1):     # Set the parameters for corresponding output(s)
for a in range(10):
    RP.CH1.set_params_linear(A=a)                             # Set the parameters for corresponding output(s)
    ...                                                       # Send configuration to FPGA 
    ...                                                       # Conduct/save experiments
    ...                                                       # Post-analysis (if required)
########### End of example ############

########### Example of a typical CBC experimental run-through ############
# In this example, the output is set to CBC. The parameter "A" is kept constant, whilst "B" is swept from 4->10. The constant "rhat" parameter is varied within the range of 0->10 over multiple experiments.
RP = RedPitaya()                                              # Initialise RP object
...                                                           # Set measurement controls (Sampling rate, sampling period, etc)
RP.set_output("CBC")                                          # Choose channels (turn off CBC)
RP.CBC.set_params_CBC(A=5, B=[4,10])                          # Set the parameters for corresponding output(s)
for val in range(10):
    RP.CBC.set_params_linear(rhat=val)                        # Set the parameters for corresponding output(s)
    ...                                                       # Send configuration to FPGA 
    ...                                                       # Conduct/save experiments
    ...                                                       # Post-analysis (if required)
########### End of example ############
```

## RedPitaya.py

```python
import foobar

# returns 'words'
foobar.pluralize('word')

# returns 'geese'
foobar.pluralize('goose')

# returns 'phenomenon'
foobar.singularize('phenomena')
```

## system_config.py


## channel_config.py

## CBC_config.py

## shared_config.py

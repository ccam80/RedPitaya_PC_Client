# -*- coding: utf-8 -*-
"""
Created on Thu Jul 20 16:50:13 2023

@author: cca78
"""
from channel import channel
from CBC import CBC
from system import system
from mem_mapping import update_FPGA_channel, update_FPGA_config
import numpy as np
from time import sleep
import os
import traceback
import logging
from multiprocessing.shared_memory import SharedMemory
from time import gmtime, strftime

#Todo: create config.txt file to save and load offset, scale parameters, modifiable with a button push (maybe?)
#Todo: recording progress bar/readout

class RedPitaya():
    """ RedPitaya class opens connection with redpitaya and instantiates config.
    API methods take user requests and modify config dictionaries, before
    calling functions from memory_mapping.py which convert to FPGA memory space
    and send them to the FPGA.
    """

    def __init__(self,
                 CH1_init=None,
                 CH2_init=None,
                 CBC_init=None,
                 system_init=None
                 ):

        self.CH1 = channel(CH1_init)
        self.CH2 = channel(CH2_init)
        self.CBC = CBC(CBC_init)
        self.system = system(system_init)
        
        self.measurement=0
        self.num_samples = 0


        logging.basicConfig(filename='APIlog.log',
                            level=logging.DEBUG,
                            format='%(asctime)s.%(msecs)03d %(message)s',
                            datefmt='%m/%d/%Y %I:%M:%S')
        logging.debug('Logfile initialised')
                
        
    def start(self):
        """
        Starts the communications Process() between the (?) Python API and FPGA.
        system.start_comms() 
            -> system.RP_communications.start_process()
            -> system.RP_communications.process = Process()
            
        TODO: Check if this description is correct
        TODO: This function is named extremely arbitrarily (start, start_comms, 
                stary_process). Any way to simply/unify them?
        """
        try:
            self.system.start_comms()
            return True
        
        except Exception:
            logging.debug(traceback.format_exc())
            return False
        
    def reset_config(self, channel_name, CH_init=None):
        """
        This function will restore/reset the configuration given by the user.
        An optional 'CH_init' dictoinary can be passed (similarly to creating
        the RP object) to set to a default set of parameters.


        Parameters
        ----------
        channel : "CBC", "CH1", "CH2", "system", 1, 2
            The specified channel which is being reset.

        CH_init : dict, optional
            An initialisation dictionary. Sets the RP channel object
            configuration dictionary. The default is None.


        Returns
        -------
        None.


        Usage
        ----------
        Ex.1
        RP.reset_config("CH1")
            -> Resets channel 1 to a blank state.

        Ex. 2
        CH1_init = {"mode": 'fixed_frequency', "input_channel": 1, ...}
        RP.reset_config("CH1", CH1_init)
            -> Resets channel 1 to the entries given in CH1_init

        """
        if channel_name == "CBC":
            self.CBC = CBC(CH_init)
        elif channel_name in ["CH1", 1]:
            self.CH1 = channel(CH_init)
        elif channel_name in ["CH2", 2]:
            self.CH2 = channel(CH_init)
        elif channel_name == "system":
            self.system = system()
        else:
            raise ValueError("'channel' must be be either 'CH1', 'CH2', or 'CBC'.")


    def print_config(self, channel):
        """
        This function prints out a formatted string of key:value entries within
        the config dictionary of the specified channel.

        Parameters
        ----------
        channel : "CBC", "CH1", "CH2", "Both", 1, 2
            The specified channel which is being reset.
            "Both" refers to printing "CH1" and "CH2".

        Returns
        -------
        None.

        Usage
        ----------
        Ex.1
        RP.print_config("CH1")
            -> Prints a table of RP.CH1.config with coloumns of key/value.

        Ex.2
        RP.print_config("Both")
            -> Prints a table of configs with coloumns of key/CH1 value/CH2 value.
        """

        if channel in ["CH1", 1]:
            self.CH1.print_config()
        elif channel in ["CH2", 2]:
            self.CH2.print_config()
        elif channel == "CBC":
            self.CBC.print_config()
        elif channel == "Both":
            logging.debug ("{:<25} {:<20} {:<20} ".format("Key", "Channel 1", "Channel 2"))
            for key in self.CH1.config.keys():
                logging.debug ("{:<25} {:<20} {:<20} ".format(key, str(self.CH1.config[key]), str(self.CH2.config[key])))
        else:
            raise ValueError("'channel' must be be either 'CH1', 'CH2' or 'Both', or 'CBC'.")


    def choose_channel_input(self, channel, input_channel):
        """
        This function sets which input channel is used for mathematical computation.
        This is used in certain channel modes (linear_feedback, cubic).

        Parameters
        ----------
        channel : "CH1", "CH2", "Both", 1, 2
            The specified channel which is being set.
        input_channel : 1, 2
            Specifies the physical input used.

        Returns
        -------
        None.


        Usage
        ----------
        Ex.1
        RP.choose_input_channel("CH1", 1)
            -> Sets Channel 1's input channel to 1.

        Ex.2
        RP.choose_input_channel("Both", 2)
            -> Sets both Channel 1 and Channel 2's input channel to 2.
        """

        if channel not in ["CH1", "CH2", "CBC", "Both"]:
            raise ValueError("Invalid 'channel' value. It must be 'CH1', 'CH2', or 'Both'.")
        if channel == "CBC":
            raise ValueError("Input channel cannot be set for CBC. It must be 'CH1', 'CH2', or 'Both'.")
        if input_channel not in [1, 2]:
            raise ValueError("'input_channel' must be 1 or 2")


        if channel == "Both":
           self.CH1.set_input_channel(input_channel)
           self.CH2.set_input_channel(input_channel)
        elif channel in ["CH1", 1]:
            self.CH1.set_input_channel(input_channel)
        elif channel in ["CH2", 2]:
            self.CH2.set_input_channel(input_channel)




    def choose_channel_mode(self, channel, mode, **kwargs):
        """
        Sets an output mode for a determined channel.

        Parameters
        ----------
        channel : "CH1", "CH2", "Both", 1, 2
            The specified channel which is being set.
        mode : "linear_feedback", "cubic", "white_noise", "fixed_frequency", "frequency_sweep", "artificial_nonlinearity", "artificial_nonlinearity_parametric", "off"
            Specifies the mode used.
        **kwargs: kay=value pairs of optional arguments to set specific parameters within the mode specified.

        Returns
        -------
        None.

        """
        if channel not in ["CH1", "CH2", "CBC", "Both"]:
            raise ValueError("Invalid 'channel' value. It must be 'CH1', 'CH2', or 'Both'.")
        if channel == "CBC":
            raise ValueError("Output mode cannot be set for CBC. It must be 'CH1', 'CH2', or 'Both'.")

        if channel == "Both":
            self.CH1.set_mode(mode, **kwargs)
            self.CH2.set_mode(mode, **kwargs)
        elif channel in ["CH1", 1]:
            self.CH1.set_mode(mode, **kwargs)
        elif channel in ["CH2", 2]:
            self.CH2.set_mode(mode, **kwargs)



    def choose_CBC_polynomial_target(self, target):
        if target in ["displacement", "velocity"]:
            self.CBC.set_polynomial_target(target)
        else:
            raise ValueError("'target' must be either 'displacement' or 'velocity'.")

    # def choose_external_input_type(self, target, logic):
    #     """
    #     Determines whether the external input is given as a displacement or
    #     velocity signal. This function should be used to protect against
    #     setting both to "True" at any given time.
    #     """
    #     if target in ["displacement", "disp"]:
    #         self.CBC.set_external("displacement", logic)
    #     elif target in ["velocity", "vel"]:
    #         self.CBC.set_external("velocity", logic)
    #     else:
    #         raise ValueError("'target' must be either 'displacement' or 'velocity'.")

    def choose_CBC_displacement_input(self, target):
        if target == "external":
            self.CBC.set_displacement_external(True)
        elif target == "integrate":
            self.CBC.set_displacement_external(False)
        else:
            raise ValueError("'target' must be either 'external' or 'integrate'")

    def choose_CBC_velocity_input(self, target):
        if target == "external":
            self.CBC.set_velocity_external(True)
        elif target == "differentiate":
            self.CBC.set_velocity_external(False)
        else:
            raise ValueError("'target' must be either 'external' or 'differentiate'")

    def choose_output(self, channel, CHx_mode=None):
        """
        Determines whether the output channels are configured as "CBC" or as
        "Channels". Different operating modes will use different parameter
        structures. Turning on an output type will disable the other.

        If using the channel outputs, an optional mode can be given.

        Parameters
        ----------
        channel : 'CH1', 'CH2', 'Both' or 'CBC', 1, 2
            The specified channel which is being set.
        CHx_mode : string, optional
            Used when 'channel' is specified as not 'CBC'. The mode which the
            channel(s) are set to.

        Returns
        -------
        None.


        Usage
        ----------
        Ex.1
        RP.choose_output("CBC")
            -> RP.CBC turned on
            -> RP.CH1, RP.CH2 set to "off"

        Ex.2
        RP.choose_output("CH1", "linear_feedback")
            -> RP.CBC turned off
            -> RP.CH2 set to "off"
            -> RP.CH1 set to "linear_feedback"

        Ex.3
        RP.choose_output("Both", "linear_feedback")
            -> RP.CBC turned off
            -> RP.CH1, CH2 set to "linear_feedback"

        Ex.4
        RP.choose_output("Both", ["cubic", "white_noise"])
            -> RP.CBC turned off
            -> RP.CH1 set to "cubic"
            -> RP.CH1 set to "white_noise"
        """



        if isinstance(CHx_mode, str):
                CH1_mode = CHx_mode
                CH2_mode = CHx_mode
        elif isinstance(CHx_mode, (list, tuple)):
            if len(CHx_mode) < 2:
                CH1_mode = CHx_mode[0]
                CH2_mode = CHx_mode[0]
            else:
                CH1_mode = CHx_mode[0]
                CH2_mode = CHx_mode[1]
            if len(CHx_mode) > 2:
                logging.debug("Warning: Only first two '*CHx_mode' arguments are considered. Additional arguments will be ignored.")
        else:
            CH1_mode = "off"
            CH2_mode = "off"

        if channel == "Both":
            self.CH1.set_mode(CH1_mode)
            self.CH2.set_mode(CH2_mode)
            self.CBC.config["CBC_enabled"] = False
        elif channel in ["CH1", 1]:
            self.CH1.set_mode(CH1_mode)
            self.CH2.set_mode("off")
            self.CBC.config["CBC_enabled"] = False
        elif channel in ["CH2", 2]:
            self.CH2.set_mode(CH1_mode)
            self.CH1.set_mode("off")
            self.CBC.config["CBC_enabled"] = False
        elif channel == "CBC":
            if CHx_mode:
                logging.debug("Warning: 'CHx_mode' arguments are not used in CBC mode, and will be ignored.")
            self.CH1.set_mode('off')
            self.CH2.set_mode('off')
            self.CBC.config["CBC_enabled"] = True
        else:
            raise ValueError("'channel' must be either 'CH1', 'CH2', 'Both' or 'CBC'.")



    def choose_CBC_input_order(self, IN1="none", IN2="none"):
        self.CBC.determine_input_order(IN1, IN2)




    def set_param(self, channel, parameter_name, value):
        """
        A general-purpose parameter setting function. Called by various
        parameter-specific functions.

        Parameters
        ----------
        channel : 'CH1', 'CH2', 'Both' or 'CBC', 1, 2
            The specified channel which is being set.
        parameter_name : string
            String specifying the parameter to be changed. Must be within the
            allowed list of keys of the specific channel.
        value : int, float, string, list, tuple
            Value for the updated parameter.

        Returns
        -------
        None.

        """
        if channel == "Both":
            self.CH1.set_param(parameter_name, value)
            self.CH2.set_param(parameter_name, value)
        elif channel in ["CH1", 1]:
            self.CH1.set_param(parameter_name, value)
        elif channel in ["CH2", 2]:
            self.CH2.set_param(parameter_name, value)
        elif channel == "CBC":
            self.CBC.set_param(parameter_name, value)
        else:
            raise ValueError("'channel' must be be either 'CH1', 'CH2' 'Both', or 'CBC'.")


    def params_from_dict(self, channel, dicts):
        """
        Takes a dictionary of {key: value} corresponding to parameter values for
        a given channel, and sets them in the relevant %%%_config dictionaries.
        The intended usage of this function is to take parameter values from the GUI .
        """

        if not dicts:
            raise ValueError("'dicts' is empty, meaning no parameters have been set.")


        if channel in ["CH1", "CH2", "CBC", 1, 2]:
            for key, value in dicts.items():
                self.set_param(channel, key, value)
        else:
            raise KeyError("'channel' must be either 'CH1', 'CH2' or 'CBC'.")



    def set_linear_amplitude(self, channel, value):
        self.set_param(channel, "linear_amplitude", value)

    def set_quadratic_amplitude(self, channel, value):
        self.set_param(channel, "quadratic_amplitude", value)

    def set_cubic_amplitude(self, channel, value):
        self.set_param(channel, "cubic_amplitude", value)

    def set_offset(self, channel, value):
        self.set_param(channel, "offset", value)

    def set_freq(self, channel, value):
        self.set_param(channel, "frequency", value)

    def set_frequency(self, channel, value):
        self.set_param(channel, "frequency", value)


    def set_gains(self, channel, gains):
        if channel == "CBC":
            if isinstance(gains, (list, tuple)) and len(gains) > 1:
                self.CBC.set_param('proportional_gain', gains[0])
                self.CBC.set_param('derivative_gain', gains[1])
            if isinstance(gains, (list, tuple)) and len(gains) == 1:
                self.CBC.set_param('proportional_gain', gains[0])
                self.CBC.set_param('derivative_gain', 0)
                logging.debug("Warning - only one value found in 'gains'. Value for derivative_gain has been ignored.")
            elif isinstance(gains, (float, int)):
                self.CBC.set_param('proportional_gain', gains)
                self.CBC.set_param('derivative_gain', 0)
                logging.debug("Warning - only one value found in 'gains'. Value for derivative_gain has been ignored.")
        else:
            raise ValueError("'channel' must be be 'CBC'.")

    def set_reference_amplitude(self, channel, values):
        if channel == "CBC":
            self.set_param(channel, "reference_amplitude", values)
        else:
            raise ValueError("'channel' must be be 'CBC'.")

    def set_duration(self, duration):
        # TODO: there may be another setting for duration in 'config'. To check what to use.
        self.set_param("CH1", "duration", duration)
        self.set_param("CH2", "duration", duration)
        self.set_param("CBC", "duration", duration)
    
    
    def start_recording(self):
       if self.measurement==0: 
           self.measurement = 1
           #TODO: Un-hard-code sample rates
           
           # TODO: Does self.system.config refer to FPGA_config? 
           if self.system.config.sampling_rate == "slow":
               self.num_samples = (int(self.system.config.duration *
                                   488281))
           elif self.system.config.sampling_rate == "fast":
               self.num_samples = (int(self.system.config.duration *
                                   5000000))
               
           self.num_bytes = self.num_samples * 8
           # Send record request to server
           packet = [0, self.system.comms.config, False, [True, self.num_bytes]]
           logging.debug("{} samples requested".format(self.num_samples))
           try:
               self.system.comms.GUI_to_data_Queue.put(packet, block=False)
               logging.debug("packet sent to socket process")
               #Switch button mode
               self.measurement = 1
               while (self.measurement):
                   self.monitor()
                   sleep(0.1)
               
           except Exception:
               logging.debug("Didn't send config to data process")
               logging.debug(traceback.format_exc())
               pass
       else:
           self.measurement = 0
           # Stop data recording monitoring
           self.timer.stop()
           # Close shared memory
           self.shared_mem.close()
           self.shared_mem.unlink()
           
    def monitor(self):
        if (self.system.comms.process_isRun):
            try:
                # TODO - remove Queue and change to 'normal' process
                data_ready, memory_name = self.system.comms.data_to_GUI_Queue.get(block=False)
                logging.debug ("{}, {}".format(data_ready, memory_name))
                
                if memory_name:
                    logging.debug(memory_name)
                    self.shared_mem = SharedMemory(name=memory_name, size=self.num_bytes, create=False)
                    # Send trigger and number of bytes to server
                    packet = [1, self.system.comms.config, False, [False,self.num_bytes]]
                    try:
                        # TODO - remove Queue and change to 'normal' process
                        self.system.comms.GUI_to_data_Queue.put(packet, block=False)
                        logging.debug("packet sent to socket process")
    
                    except Exception:
                        logging.debug("Didn't send config to data process")
                        logging.debug(traceback.format_exc())
                        pass
                
                elif data_ready:
                    self.MeasureFinished()
            except:
                pass
                
    def MeasureFinished(self):
        self.measurement = 0
    
        #create array with view of shared mem
        logging.debug("data_ready recognised")
        temp = np.ndarray((self.num_samples), dtype=np.dtype([('in1', np.int16), ('in2', np.int16), ('out1', np.int16), ('out2', np.int16)]), buffer=self.shared_mem.buf)
        #copy into permanent array
        recording = np.copy(temp)
        logging.debug("recording copied")
        # Delete view of shared memory (important, otherwise memory still exists)
        del temp
        
        
        # Store to *.csv
        #Set up data directory
        datadir="./Data/"
        if (os.path.isdir(datadir) != True):
            os.mkdir(datadir)
        label = strftime("%Y-%m-%d %H_%M_%S", gmtime())
        i = 0
        while os.path.exists(datadir + '{}{}.csv'.format(label, i)):
            i += 1
        np.savetxt(datadir + '{}{}.csv'.format(label, i), 
                   np.transpose([recording['in1'], recording['in2'], recording['out1'], recording['out2']]), 
                   delimiter=";", fmt='%d',
                   header="Sample rate: {}\n In1; In2; Out1; Out2".format(self.system.config.sampling_rate))
        
        # Close shared memory
        self.shared_mem.close()
        self.shared_mem.unlink()
        self.recording = recording
        


    def update_FPGA(self):
        if self.CBC.config.CBC_enabled:
            update_FPGA_channel('CBC', self.CBC.config, self.system.comms.config)
        else:
            update_FPGA_channel(1, self.CH1.config, self.system.comms.config)
            update_FPGA_channel(2, self.CH2.config, self.system.comms.config)
            
        update_FPGA_config(self.system.config, self.system.comms.config)
        
        #           [no trigger,    config dictionary,          config HAS changed, [no recording,  zero bytes]]
        packet =    [0,             self.system.comms.config,   True,               [False,         0]]
        
        try:
            # TODO - remove Queue and change to 'normal' process
            self.system.comms.GUI_to_data_Queue.put(packet, block=False)
            logging.debug("packet sent to socket process")

        except Exception:
            logging.debug("Didn't send config to data process")
            logging.debug(traceback.format_exc())
            pass
        
        
    # ***************************************************
    # Seigan Development - Untested
    # Wild wild west of bad code goes here
    # ***************************************************
    def update_FPGA_settings(self):
        """
        TODO: add description + examples

        Returns
        -------
        None.

        """
        # TODO: Check what our notation/convetion for layering was, as this might void it. 
        # Might not be possible to reference 'parallel' layers anyway, so this will have to do
        if self.CBC.config.CBC_enabled:
            update_FPGA_channel('CBC', self.CBC.config, self.system.comms.config)
        else:
            update_FPGA_channel(1, self.CH1.config, self.system.comms.config)
            update_FPGA_channel(2, self.CH2.config, self.system.comms.config)
            
        update_FPGA_config(self.system.config, self.system.comms.config)
        
        try:
            # This is the only change compared to 'update_FPGA'. Essentially removes the Queue item
            self.system.send_settings_to_FPGA()
            logging.debug("FPGA settings successfully updated.")
        except Exception:
            logging.debug("An exception occured. FPGA settings could not be updated.")
            logging.debug(traceback.format_exc())       # TODO: not sure what this line does. 
            pass
    

    def prepare_record(self):
        """
        TODO: add descriptions + examples
        TODO: check name is appropriate.

        Returns
        -------
        None.

        """
        logging.debug("Recording request recieved")       # TODO: likely redundant
        return self.system.prepare_record()
    
    
    def start_record(self):
        if self.measurement==0: 
           self.measurement = 1
           #TODO: Un-hard-code sample rates
           
           # TODO: Does self.system.config refer to FPGA_config? 
           if self.system.config.sampling_rate == "slow":
               self.num_samples = (int(self.system.config.duration *
                                   488281))
           elif self.system.config.sampling_rate == "fast":
               self.num_samples = (int(self.system.config.duration *
                                   5000000))
               
           self.num_bytes = self.num_samples * 8
           self.system.comms.bytes_to_receive = self.num_bytes        # TODO - needed as the packet no longer exists. Think of a better implementation
           
           
           # Send record request to server
           # packet = [0, self.system.comms.config, False, [True, self.num_bytes]]
           
           logging.debug("{} samples requested".format(self.num_samples))
           try:
               # self.system.comms.GUI_to_data_Queue.put(packet, block=False)
               self.shared_memory_name = self.prepare_record()
               self.shared_mem = SharedMemory(name=self.shared_memory_name, size=self.num_bytes, create=False)
               
               logging.debug("packet sent to socket process")
               #Switch button mode
               self.measurement = 1
               while (self.measurement):
                   self.monitor_recording()
                   sleep(0.1)
               
           except Exception:
               logging.debug("Didn't send config to data process")
               logging.debug(traceback.format_exc())
               pass
        else:
           self.measurement = 0
           # Stop data recording monitoring
           self.timer.stop()
           # Close shared memory
           self.shared_mem.close()
           self.shared_mem.unlink()
   
    def monitor_recording(self):
        # if (self.system.comms.process_isRun):
        #     try:
        #         # TODO - remove Queue and change to 'normal' process
        #         data_ready, memory_name = self.system.comms.data_to_GUI_Queue.get(block=False)
        #         logging.debug ("{}, {}".format(data_ready, memory_name))
                
        #         if memory_name:
        #             logging.debug(memory_name)
        #             self.shared_mem = SharedMemory(name=memory_name, size=self.num_bytes, create=False)
        #             # Send trigger and number of bytes to server
        #             packet = [1, self.system.comms.config, False, [False,self.num_bytes]]
        #             try:
        #                 # TODO - remove Queue and change to 'normal' process
        #                 self.system.comms.GUI_to_data_Queue.put(packet, block=False)
        #                 logging.debug("packet sent to socket process")
    
        #             except Exception:
        #                 logging.debug("Didn't send config to data process")
        #                 logging.debug(traceback.format_exc())
        #                 pass
                
        #         elif data_ready:
        #             self.MeasureFinished()
        #     except:
        #         pass
         if (self.system.comms.process_isRun):
             try:
                 if self.shared_memory_name and not self.data_ready:
                     try:
                         self.system.trigger_record()
                     except:
                         logging.debug("Didn't send config to data process")
                         logging.debug(traceback.format_exc())
                     self.MeasureFinished()
                     del self.shared_memory_name
             except:
                 pass
                 
             
          
    
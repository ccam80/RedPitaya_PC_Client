import sys
import os
import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk

import matplotlib.animation as animation
from matplotlib.figure import Figure as mplf_figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import socket_process as sp
from multiprocessing.shared_memory import SharedMemory
from functools import partial

import numpy as np
from GS_timing import micros

from datetime import datetime
import pstats
from functools import wraps

import csv

import logging


np.set_printoptions(threshold=sys.maxsize)

class NumpyFloatToFixConverter(object):
    """*** IMPORTED FROM RIG LIBRARY, RIG NOT AVAILABLE THROUGH CONDA CHANNELS***
    A callable which converts Numpy arrays of floats to fixed point arrays.
    General usage is to create a new converter and then call this on arrays of
    values.  The `dtype` of the returned array is determined from the
    parameters passed.  For example::
        >>> f = NumpyFloatToFixConverter(signed=True, n_bits=8, n_frac=4)
    Will convert floating point values to 8-bit signed representations with 4
    fractional bits.  Consequently the returned `dtype` will be `int8`::
        >>> import numpy as np
        >>> vals = np.array([0.0, 0.25, 0.5, -0.5, -0.25])
        >>> f(vals)
        array([ 0,  4,  8, -8, -4], dtype=int8)
    The conversion is saturating::
        >>> f(np.array([15.0, 16.0, -16.0, -17.0]))
        array([ 127,  127, -128, -128], dtype=int8)
    The byte representation can be expected to match that for using
    `float_to_fix`::
        >>> d = f(np.array([-16.0]))
        >>> import struct
        >>> g = float_to_fix(True, 8, 4)
        >>> val = g(-16.0)
        >>> struct.pack('B', val) == bytes(d.data)
        True
    An exception is raised if the number of bits specified cannot be
    represented using a whole `dtype`::
        >>> NumpyFloatToFixConverter(True, 12, 0)
        Traceback (most recent call last):
        ValueError: n_bits: 12: Must be 8, 16, 32 or 64.
    """
    dtypes = {
        (False, 8): np.uint8,
        (True, 8): np.int8,
        (False, 16): np.uint16,
        (True, 16): np.int16, 
        (False, 32): np.uint32,
        (True, 32): np.int32,
        (False, 64): np.uint64,
        (True, 64): np.int64,
    }

    def __init__(self, signed, n_bits, n_frac):
        """Create a new converter from floats into ints.
        Parameters
        ----------
        signed : bool
            Indicates that the converted values are to be signed or otherwise.
        n_bits : int
            The number of bits each value will use overall (must be 8, 16, 32,
            or 64).
        n_frac : int
            The number of fractional bits.
        """
        # Check the number of bits is sane
        if n_bits not in [8, 16, 32, 64]:
            raise ValueError(
                "n_bits: {}: Must be 8, 16, 32 or 64.".format(n_bits))

        # Determine the maximum and minimum values after conversion
        if signed:
            self.max_value = 2**(n_bits - 1) - 1
            self.min_value = -self.max_value - 1
        else:
            self.max_value = 2**n_bits - 1
            self.min_value = 0

        # Store the settings
        self.bytes_per_element = n_bits / 8
        self.dtype = self.dtypes[(signed, n_bits)]
        self.n_frac = n_frac

    def __call__(self, values):
        """Convert the given NumPy array of values into fixed point format."""
        # Scale and cast to appropriate int types
        vals = values * 2.0 ** self.n_frac

        # Saturate the values
        vals = np.clip(vals, self.min_value, self.max_value)

        # **NOTE** for some reason just casting resulted in shape
        # being zeroed on some indeterminate selection of OSes,
        # architectures, Python and Numpy versions"
        return np.array(vals, copy=True, dtype=self.dtype)

class GUI:
    """FPGA Cantilever controller GUI. PAsses parameters back and forth from user
    to C server and receives raw data from server.
        """

    def __init__(self,
                 sampling_rate = 100000,
                 datadir="./Data/"
                 ):

        # Argument Assignments
        self.sampling_rate = sampling_rate
        self.datadir = datadir
    
        # Misc counters        
        self.num_samples = 0
        self.num_bytes = 0
        
        # Calibration data
        self.FPGA_fclk = 125000000
        self.FPGA_phase_width = 30
        self.adc_0 = 85
        self.adc_v_plus = 0.751
        self.adc_v_plus_read = 4739
        self.adc_v_neg = -0.722
        self.adc_v_neg_read = -4409
        self.adc_scale = (self.adc_v_plus_read - self.adc_v_neg_read) / (self.adc_v_plus - self.adc_v_neg)
        
        #Set up data directory
        if (os.path.isdir(datadir) != True):
            os.mkdir(datadir)

        # Create data processing thread
        self.data = sp.dataThread()
        
        # State toggles
        self.running = True
        
        # Vector allocation
        self.input_temp = np.zeros(0, dtype=np.uint16)
        self.output_temp = np.zeros(0, dtype=np.uint16)
        self.input_recording = np.zeros(0, dtype=np.int16) 
        self.output_recording = np.zeros(0, dtype=np.int16)

        # Plotting guide lines
        self.max_time_vec = np.linspace(0, 7.2e6, 10)
        
        # Data formats
        self.dt = np.dtype([('in', np.uint16), ('out', np.uint16)])
        self.q16_16 = NumpyFloatToFixConverter(signed=True, n_bits=32, n_frac=16)
     
        # Create data processing thread
        self.data = sp.dataThread()
        self.data.start_Process()
    
        # FPGA config
        self.FPGA_config = {"trigger": 0,
                            "state": 0,
                            "CIC_divider":int(np.floor(125000000 /sampling_rate)),
                            "fixed_freq":5,
                            "start_freq":0,
                            "stop_freq":0,
                            "a_const":1.0,
                            "interval":1,
                            "b_const":1}
        
        # Overwrite matplotlib's logging so it doesn't fill up our debug log
        mpl_logger = logging.getLogger('matplotlib')
        mpl_logger.setLevel(logging.WARNING)
        
        # Set up debug log
        logging.basicConfig(filename='GUIlog.log',
                            level=logging.DEBUG,
                            format='%(asctime)s %(message)s',
                            datefmt='%m/%d/%Y %I:%M:%S %p')
        logging.debug('Logfile initialised')
        
        # -----------------------------------
        # Plots
        # -----------------------------------
        
        # Parents
        self.liveplot_fig = mplf_figure()
        self.liveplot_axs = self.liveplot_fig.subplots(
            2, 1)
        self.liveplot_ax = self.liveplot_axs.ravel()

        # artists
        self.artist0, = self.liveplot_ax[0].plot([], [], 'b', markersize=1)
        self.artist1, = self.liveplot_ax[1].plot([], [], 'b', markersize=1)
       
        logging.debug('MPLFs created')
        
        
        # ----------------------------------
        # GUI Config
        # ----------------------------------
        self.graph_w = tk.Tk()

        self.graph_w.wm_title("RedPitaya Cantilever Controller")
        self.graph_w.wm_geometry('1024x920')
        self.graph_w.wm_state('zoomed')
        self.master_f = tk.Frame(self.graph_w)
        self.master_f.grid(row=0, column=0, sticky='nsew')

        self.graph_w.columnconfigure(0, weight=1)
        self.graph_w.rowconfigure(0, weight=1)

       # Fonts
        self.buttonFont = tk.font.Font(family='Helvetica', size=16)
        self.headingFont = tkfont.Font(
            family='Helvetica', size=22, weight=tk.font.BOLD)
        logging.debug('Window Created')
       # **************** Master Grid Layout *************************

        self.control_f = tk.Frame(self.master_f, bd=2, relief='solid')
        self.prog_frame = tk.Frame(self.master_f, bd=2, relief='solid')
        self.canvas = FigureCanvasTkAgg(
            self.liveplot_fig, master=self.master_f)

        self.canvas.get_tk_widget().grid(
            row=0, column=0, sticky='nsew', rowspan=4, columnspan=3)
        self.control_f.grid(row=0, column=3, rowspan=5, sticky='nsew')
        self.prog_frame.grid(row=4, column=0, columnspan=3, sticky='nsew')

        self.set_cell_weights_to_1(self.master_f)
        # self.graph_w.bind("<Configure>", self.resize_prog_bar)
        self.canvas.draw()

        
      
        # **************************** Control Frame *********************
        
        # Button Variables
        self.start_freq_var = tk.IntVar()
        self.stop_freq_var = tk.IntVar()
        self.fixed_freq_var = tk.IntVar()
        self.label_var = tk.StringVar()
        self.sampling_freq_var = tk.IntVar()
        self.duration_var = tk.DoubleVar()
        self.a_var = tk.StringVar()
        self.b_var = tk.IntVar()
        self.sigmode_var = tk.StringVar()

        
        self.labels = [self.start_freq_var,
                        self.stop_freq_var,
                        self.fixed_freq_var,
                        self.label_var,
                        self.sampling_freq_var,
                        self.duration_var,
                        self.a_var,
                        self.b_var]
        self.label = ''
        self.label_var.set("Filename")
        
        self.init_control_frame_fixed()

    def set_cell_weights_to_1(self, widget):
        """ Set weight of all cells in tkinter grid to 1 so that they stretch """
        for col_num in range(widget.grid_size()[0]):
            widget.columnconfigure(col_num, weight=1)
        for row_num in range(widget.grid_size()[1]):
            widget.rowconfigure(row_num, weight=1)
            
            
   # **************************** Plotting Functions  *********************

    def init_plots(self):
        """Initiate all lines, save references to attributes to keep them for
        the animation functions & to allow blitting (not used in this GUI currently)

        Configure axes while we're at it to avoid overloading the animation
        functions
        """

        self.artist0.set_data([], [])
      
        self.liveplot_ax[0].set_ylabel("ADC Counts")
        self.liveplot_ax[0].set_xlabel("Sample Count")
       
        self.liveplot_ax[0].grid(b=True, which='both')

        self.liveplot_ax[1].set_ylabel("DAC Counts")
        self.liveplot_ax[1].set_xlabel("Sample Count")
       
        self.liveplot_ax[1].grid(b=True, which='both')
        self.liveplot_fig.tight_layout()

        return self.artist0, 

    def update_plots(self):
        """ Update lines & axis limits on each call. """
        # logging.debug("animate_plots")
        
        self.artist0.set_data(range(len(self.input_recording)), self.input_recording)
        
        self.liveplot_ax[0].set_xlim((0,len(self.input_recording)))
        self.liveplot_ax[0].set_ylim((np.min(self.input_recording), np.max(self.input_recording)))
        
        self.artist1.set_data(range(len(self.output_recording)), self.output_recording)
        
        self.liveplot_ax[1].set_xlim((0,len(self.output_recording)))
        self.liveplot_ax[1].set_ylim((np.min(self.output_recording), np.max(self.output_recording)))
        
        self.canvas.draw()
   
    # **************************** GUI Button Callbacks  *********************

    def start_recording(self):
        """Calculate bytes to receive, send request to data thread"""
        self.num_samples = int(self.duration_var.get() * self.sampling_freq_var.get())
        self.num_bytes = self.num_samples * 4
        self.active_f.configure(bg='green')
        self.start_b.configure(state=tk.DISABLED)
        self.send_config_to_data("record_request")
        logging.debug("start_recording_ends")
        # self.save_data()
        
    def kick(self):
        """ Close and reopen data thread in case of hang """
        self.data.close()
        self.data = sp.dataThread()
        self.stop_trial()
        self.data.start_Process()

    def stop_trial(self):
        """ Turns red light green """
        self.active_f.configure(bg='red')
        self.start_b.configure(state=tk.NORMAL)
        
    def set_sig_mode(self):
        """ Pick current stimulation mode, load appropriate GUI screen and update
        FPGA config """
        
        mode = self.sigmode_var.get()
        if (mode == "fixed"):
            self.control_f.destroy()
            self.control_f = tk.Frame(self.master_f, bd=2, relief='solid')
            self.control_f.grid(row=0, column=3, rowspan=5, sticky='nsew')
            self.init_control_frame_fixed()
            self.FPGA_config["state"] = 0
        elif (mode == "sweep"):
            self.control_f.destroy()
            self.control_f = tk.Frame(self.master_f, bd=2, relief='solid')
            self.control_f.grid(row=0, column=3, rowspan=5, sticky='nsew')
            self.init_control_frame_sweep()
            self.FPGA_config["state"] = 1
        elif (mode == "lin"):
            self.control_f.destroy()
            self.control_f = tk.Frame(self.master_f, bd=2, relief='solid')
            self.control_f.grid(row=0, column=3, rowspan=5, sticky='nsew')
            self.init_control_frame_lin()
            self.FPGA_config["state"] = 2
        elif (mode == "fancy"):
            self.control_f.destroy()
            self.control_f = tk.Frame(self.master_f, bd=2, relief='solid')
            self.control_f.grid(row=0, column=3, rowspan=5, sticky='nsew')
            self.init_control_frame_fancy()
            self.FPGA_config["state"] = 3
            
    
    # Close graphing window

    def close_graph(self):
        """Does what it says on the tin."""
        self.data.close()
        self.stop_trial()
        self.graph_w.destroy()
        self.running = False
        return "break"

    def save(self):
        """Save csv of current data """

        label = self.label_var.get()
        i = 0
        while os.path.exists(self.datadir + '{}{}.csv'.format(label, i)):
            i += 1
        np.savetxt(self.datadir + '{}{}.csv'.format(label, i), 
                   [self.input_recording, self.output_recording], 
                   delimiter=",",
                   header="Sample rate: {}".format(125000000 / self.FPGA_config["CIC_divider"]))

    

    # ************************* Inter-process comms  *********************
    
    def update_config(self):
        """Update FPGA config struct with variables from GUI """
            
        self.FPGA_config["fixed_freq"] = self.fixed_freq_var.get()
        self.FPGA_config["start_freq"] = self.start_freq_var.get()
        self.FPGA_config["stop_freq"] = self.stop_freq_var.get()
        self.FPGA_config["CIC_Divider"] = int(np.floor(125000000 / 
                                              self.sampling_freq_var.get()))
        #Convert multiplication constant to fixed point
        a_val = np.float32(self.a_var.get())
        a_fixed = self.q16_16(a_val)
        self.FPGA_config["a_const"] = a_fixed
        
        self.FPGA_config["b_const"] = self.b_var.get()
        
        #Process frequency sweep information to get interval
        start_phase = self.FPGA_config["start_freq"]*(2**(self.FPGA_phase_width))/self.FPGA_fclk
        stop_phase = self.FPGA_config["stop_freq"]*(2**(self.FPGA_phase_width))/self.FPGA_fclk
        phase_span = np.abs(stop_phase - start_phase)
        
        #test for 0 phase span -> infinite interval if in different mode
        if phase_span:
            self.FPGA_config["interval"] = int(self.duration_var.get() * self.FPGA_fclk / phase_span)
        else:
            self.FPGA_config["interval"] = 1
            
        self.send_config_to_data("config_change")

        
    def send_config_to_data(self, event):
        """ Send config information to socket process.
        
        GUI splits up packet as:
                self.trigger, - start recording
                self.FPGA_config,  - config struct
                self.FPGA_config_change, - flag to indicate change of config
                [self.record_request, self.bytes_to_receive] - initial request for a recording
                """
                
        if event == "config_change":
            packet = [0, self.FPGA_config, True, [False,0]]
        
        elif event == "trigger":
            packet = [1, self.FPGA_config, False, [False,self.num_bytes]]
            
        elif event == "record_request":
            packet = [0, self.FPGA_config, False, [True, self.num_bytes]]
            logging.debug("{} samples requested".format(self.num_samples))
        

        try:
            self.data.GUI_to_data_Queue.put(packet, block=False)
            logging.debug("packet sent to socket process")

        except Exception as e:
            logging.debug("Didn't send config to data process")
            # logging.debug(e)
                      
    def receive_info_from_data(self):
        """ Get recorded data from socket process"""
        
        #Binary mask to only get 14 bits
        mask = (1 << 14) - 1
        
        try:
            # Get shared memory info from socket process
            data_ready, memory_name = self.data.data_to_GUI_Queue.get(block=False)
            logging.debug ("{}, {}".format(data_ready, memory_name))
            
            #If shared memory received, set up this end of it then send trigger
            if memory_name:
                logging.debug(memory_name)
                self.shared_mem = SharedMemory(name=memory_name, size=self.num_bytes, create=False)
                self.send_config_to_data("trigger")
                return True
            
            #Once socket indicates data is ready, get and process recorded binary data
            elif data_ready:
                
                #create array with view of shared mem
                logging.debug("data_ready recognised")
                temp = np.ndarray((self.num_samples), dtype=self.dt, buffer=self.shared_mem.buf)
                
                 #copy into permanent array
                recording = np.copy(temp)
                logging.debug("recording copied")
                
                # This triple-shift operation may not be required, can optimise out if required.
                self.input_temp_unshifted = np.uint16(np.bitwise_and(recording['in'], np.uint16(mask)))
                self.output_temp_unshifted = np.uint16(np.bitwise_and(recording['out'], np.uint16(mask)))
                
                self.input_temp = np.uint16(np.left_shift(recording['in'], np.uint16(2)))
                self.output_temp = np.uint16(np.left_shift(recording['out'], np.uint16(2)))
                
                self.input_recording = (np.int16(np.right_shift(self.input_temp, np.uint16(2))).byteswap() - self.adc_0) / self.adc1_scale
                self.output_recording = np.int16(np.right_shift(self.output_temp, np.int16(2))).byteswap()
                
                logging.debug("recordings broken up")
                
                # Delete view of shared memory (important, otherwise memory still exists)
                del temp
                logging.debug("received data")

                #Close memory, stop trial, update plots...                
                self.shared_mem.close()
                self.shared_mem.unlink()
                self.stop_trial()
                self.update_plots()
                return True
            
            else:
                return False

        except Exception as e:
            return e
      
        
  # **************************** GUI LAYOUTS ******************************* #
  # One function for each control scheme. Not pretty!
  
    def init_control_frame_fixed(self):
        """Fixed frequency stimulation interface"""
        
        # SAME VARIABLES CREATED FOR ALL FRAMES
        # Button Variables - instantiate
        used_vars = [self.fixed_freq_var,
                     self.label_var,
                     self.duration_var,
                     self.sampling_freq_var]
        
        unused_vars = [self.start_freq_var,
                        self.stop_freq_var,
                        self.a_var,
                        self.b_var]
        
        # Button Variables - initialize
        for var in unused_vars:
            var.set(0)
        self.duration_var.set(1.0)
        self.sigmode_var.set("fixed")
        self.fixed_freq_var.set(self.FPGA_config["fixed_freq"])
        self.sampling_freq_var.set(125000000 / self.FPGA_config["CIC_divider"])
        
        #Set FPGA options for stimulation mode
        self.FPGA_config["state"] = 0
        
        # Create Widgets
        self.control_l = tk.Label(
            self.control_f, text="Recording Controls", font=self.headingFont)
        self.fixed_freq_e = tk.Entry(
            self.control_f, textvariable=self.fixed_freq_var, justify='center', font=self.buttonFont)
        self.fixed_freq_l = tk.Label(
            self.control_f, text="Frequency Out:", justify='right', font=self.buttonFont)
        self.sampling_freq_e = tk.Entry(
            self.control_f, textvariable=self.sampling_freq_var, justify='center', font=self.buttonFont)
        self.sampling_freq_l = tk.Label(
            self.control_f, text="Sampling Frequency:", justify='right', font=self.buttonFont)
        self.duration_e = tk.Entry(
            self.control_f, textvariable=self.duration_var, justify='center', font=self.buttonFont)
        self.duration_l = tk.Label(
            self.control_f, text="Recording Duration:", justify='right', font=self.buttonFont)       
        self.send_changes_b =  tk.Button(self.control_f, text="Send Changes to FPGA",
                                         command=self.update_config, font=self.buttonFont, highlightthickness=5, borderwidth=5)
        self.start_b = tk.Button(self.control_f, text='Start', command=self.start_recording,
                                 font=self.buttonFont, highlightthickness=5, borderwidth=5)
        self.active_f = tk.Frame(self.control_f, width=50, height=50, bg='red')
        self.label_e = tk.Entry(
            self.control_f, textvariable=self.label_var, justify='center', font=self.buttonFont)
        self.label_l = tk.Label(
            self.control_f, text="File Label:", justify='right', font=self.buttonFont)
        self.save_b = tk.Button(self.control_f, text="Save CSV", command=self.save, font=self.buttonFont, highlightthickness=5, borderwidth=5)
        self.kick_b = tk.Button(self.control_f, text="Kick",
                                         command=self.kick, font=self.buttonFont, highlightthickness=5, borderwidth=5)
        self.graph_close_b = tk.Button(self.control_f, text="Close", command=self.close_graph,
                                       fg='red', font=self.buttonFont, highlightthickness=5, borderwidth=5)
        self.fixed_mode_l = tk.Label(self.control_f, text="Fixed Frequency", justify="right", font=self.buttonFont)
        self.sweep_mode_l = tk.Label(self.control_f, text="Frequency Sweep", justify="right", font=self.buttonFont)
        self.fixed_mode_b = tk.Radiobutton(self.control_f, variable=self.sigmode_var, value="fixed", command=self.set_sig_mode)
        self.sweep_mode_b = tk.Radiobutton(self.control_f, variable=self.sigmode_var, value="sweep", command=self.set_sig_mode)
        self.lin_mode_l = tk.Label(self.control_f, text="Linear Feedback", justify="right", font=self.buttonFont)
        self.fancy_mode_l = tk.Label(self.control_f, text="Fancy Feedback", justify="right", font=self.buttonFont)
        self.lin_mode_b = tk.Radiobutton(self.control_f, variable=self.sigmode_var, value="lin", command=self.set_sig_mode)
        self.fancy_mode_b = tk.Radiobutton(self.control_f, variable=self.sigmode_var, value="fancy", command=self.set_sig_mode)
        
        # Set grid layout
        self.control_l.grid(row=0, column=0, columnspan=2, sticky='nsew')
        self.fixed_freq_e.grid(row=1, column=1, sticky='nsew')
        self.fixed_freq_l.grid(row=1, column=0, sticky='nsew')
        self.sampling_freq_e.grid(row=2, column=1, sticky='nsew')
        self.sampling_freq_l.grid(row=2, column=0, sticky='nsew')
        self.duration_e.grid(row=3, column=1, sticky='nsew')
        self.duration_l.grid(row=3, column=0, sticky='nsew')
        self.label_e.grid(row=4, column=1, sticky='nsew')
        self.label_l.grid(row=4, column=0, sticky='nsew')
        self.fixed_mode_l.grid(row=5, column=0, sticky='nsew')
        self.fixed_mode_b.grid(row=5, column=1, sticky='nsew')
        self.sweep_mode_l.grid(row=6, column=0, sticky='nsew')
        self.sweep_mode_b.grid(row=6, column=1, sticky='nsew')
        self.lin_mode_l.grid(row=7, column=0, sticky='nsew')
        self.lin_mode_b.grid(row=7, column=1, sticky='nsew')
        self.fancy_mode_l.grid(row=8, column=0, sticky='nsew')
        self.fancy_mode_b.grid(row=8, column=1, sticky='nsew')
        self.save_b.grid(row=9, column=0, sticky='nsew')
        self.kick_b.grid(row=9, column=1, sticky='nsew')
        self.send_changes_b.grid(row=10, column=0, sticky='nsew')
        self.start_b.grid(row=10, column=1, sticky='nsew')
        self.graph_close_b.grid(row=11, column=1, sticky='nsew')
        self.active_f.grid(row=11, column=0, sticky='nsew')
        
        self.set_cell_weights_to_1(self.control_f)
    
    def init_control_frame_sweep(self):
        """Frequency sweep stimulation interface"""
        
        # SAME VARIABLES CREATED FOR ALL FRAMES
        # Button Variables - instantiate
        used_vars = [self.start_freq_var,
                     self.stop_freq_var,
                     self.label_var,
                     self.duration_var,
                     self.sampling_freq_var]
        
        unused_vars = [self.fixed_freq_var,
                       self.a_var,
                       self.b_var]
        
        # Button Variables - initialize
        for var in unused_vars:
            var.set(0)
        self.sigmode_var.set("sweep")
        self.start_freq_var.set(self.FPGA_config["start_freq"])
        self.start_freq_var.set(self.FPGA_config["stop_freq"])
        self.duration_var.set(1.0)
        self.sampling_freq_var.set(125000000 / self.FPGA_config["CIC_divider"])
        
        #Set FPGA options for stimulation mode
        self.FPGA_config["state"] = 1
        
        # Create Widgets
        self.control_l = tk.Label(
            self.control_f, text="Recording Controls", font=self.headingFont)
        self.start_freq_e = tk.Entry(
            self.control_f, textvariable=self.start_freq_var, justify='center', font=self.buttonFont)
        self.start_freq_l = tk.Label(
            self.control_f, text="Start Frequency:", justify='right', font=self.buttonFont)
        self.stop_freq_e = tk.Entry(
            self.control_f, textvariable=self.stop_freq_var, justify='center', font=self.buttonFont)
        self.stop_freq_l = tk.Label(
            self.control_f, text="Stop Frequency:", justify='right', font=self.buttonFont)
        self.sampling_freq_e = tk.Entry(
            self.control_f, textvariable=self.sampling_freq_var, justify='center', font=self.buttonFont)
        self.sampling_freq_l = tk.Label(
            self.control_f, text="Sampling Frequency:", justify='right', font=self.buttonFont)
        self.duration_e = tk.Entry(
            self.control_f, textvariable=self.duration_var, justify='center', font=self.buttonFont)
        self.duration_l = tk.Label(
            self.control_f, text="Sweep Duration:", justify='right', font=self.buttonFont)
        self.send_changes_b =  tk.Button(self.control_f, text="Send Changes to FPGA",
                                         command=self.update_config, font=self.buttonFont, highlightthickness=5, borderwidth=5)
        self.start_b = tk.Button(self.control_f, text='Start', command=self.start_recording,
                                 font=self.buttonFont, highlightthickness=5, borderwidth=5)
        self.active_f = tk.Frame(self.control_f, width=50, height=50, bg='red')
        self.label_e = tk.Entry(
            self.control_f, textvariable=self.label_var, justify='center', font=self.buttonFont)
        self.label_l = tk.Label(
            self.control_f, text="File Label:", justify='right', font=self.buttonFont)
        self.save_b = tk.Button(self.control_f, text="Save CSV", command=self.save, font=self.buttonFont, highlightthickness=5, borderwidth=5)
        self.kick_b = tk.Button(self.control_f, text="Kick",
                                         command=self.kick, font=self.buttonFont, highlightthickness=5, borderwidth=5)
        self.graph_close_b = tk.Button(self.control_f, text="Close", command=self.close_graph,
                                       fg='red', font=self.buttonFont, highlightthickness=5, borderwidth=5)
        self.fixed_mode_l = tk.Label(self.control_f, text="Fixed Frequency", justify="right", font=self.buttonFont)
        self.sweep_mode_l = tk.Label(self.control_f, text="Frequency Sweep", justify="right", font=self.buttonFont)
        self.fixed_mode_b = tk.Radiobutton(self.control_f, variable=self.sigmode_var, value="fixed", command=self.set_sig_mode)
        self.sweep_mode_b = tk.Radiobutton(self.control_f, variable=self.sigmode_var, value="sweep", command=self.set_sig_mode)
        self.lin_mode_l = tk.Label(self.control_f, text="Linear Feedback", justify="right", font=self.buttonFont)
        self.fancy_mode_l = tk.Label(self.control_f, text="Fancy Feedback", justify="right", font=self.buttonFont)
        self.lin_mode_b = tk.Radiobutton(self.control_f, variable=self.sigmode_var, value="lin", command=self.set_sig_mode)
        self.fancy_mode_b = tk.Radiobutton(self.control_f, variable=self.sigmode_var, value="fancy", command=self.set_sig_mode)
        
        
        # Set grid layout
        self.control_l.grid(row=0, column=0, columnspan=2, sticky='nsew')
        self.start_freq_e.grid(row=1, column=1, sticky='nsew')
        self.start_freq_l.grid(row=1, column=0, sticky='nsew')
        self.stop_freq_e.grid(row=2, column=1, sticky='nsew')
        self.stop_freq_l.grid(row=2, column=0, sticky='nsew')
        self.sampling_freq_e.grid(row=3, column=1, sticky='nsew')
        self.sampling_freq_l.grid(row=3, column=0, sticky='nsew')
        self.duration_e.grid(row=4, column=1, sticky='nsew')
        self.duration_l.grid(row=4, column=0, sticky='nsew')
        self.label_e.grid(row=5, column=1, sticky='nsew')
        self.label_l.grid(row=5, column=0, sticky='nsew')
        self.fixed_mode_l.grid(row=6, column=0, sticky='nsew')
        self.fixed_mode_b.grid(row=6, column=1, sticky='nsew')
        self.sweep_mode_l.grid(row=7, column=0, sticky='nsew')
        self.sweep_mode_b.grid(row=7, column=1, sticky='nsew')
        self.lin_mode_l.grid(row=8, column=0, sticky='nsew')
        self.lin_mode_b.grid(row=8, column=1, sticky='nsew')
        self.fancy_mode_l.grid(row=9, column=0, sticky='nsew')
        self.fancy_mode_b.grid(row=9, column=1, sticky='nsew')
        self.save_b.grid(row=10, column=0, sticky='nsew')
        self.kick_b.grid(row=10, column=1, sticky='nsew')
        self.send_changes_b.grid(row=11, column=0, sticky='nsew')
        self.start_b.grid(row=11, column=1, sticky='nsew')
        self.graph_close_b.grid(row=12, column=1, sticky='nsew')
        self.active_f.grid(row=12, column=0, sticky='nsew')
        
        self.set_cell_weights_to_1(self.control_f)
        
    def init_control_frame_lin(self):
        """Linear (Ax + b) feedback control interface"""
        
        # Button Variables
        used_vars = [self.a_var,
                     self.b_var,
                     self.label_var,
                     self.duration_var,
                     self.sampling_freq_var]
        
        unused_vars = [self.fixed_freq_var,
                       self.start_freq_var,
                       self.stop_freq_var]
        
        # Button Variables - initialize
        for var in unused_vars:
            var.set(0)
        self.sigmode_var.set("lin")
        self.duration_var.set(1.0)
        self.sampling_freq_var.set(125000000 / self.FPGA_config["CIC_divider"])
        self.a_var.set(self.FPGA_config["a_const"])
        self.b_var.set(self.FPGA_config["b_const"])
    
        #Set FPGA options for stimulation mode
        self.FPGA_config["state"] = 2

    
        # Create Widgets    
        self.control_l = tk.Label(
            self.control_f, text="Recording Controls", font=self.headingFont)
        self.a_e = tk.Entry(
            self.control_f, textvariable=self.a_var, justify='center', font=self.buttonFont)
        self.a_l = tk.Label(
            self.control_f, text="a constant:", justify='right', font=self.buttonFont)
        self.b_e = tk.Entry(
            self.control_f, textvariable=self.b_var, justify='center', font=self.buttonFont)
        self.b_l = tk.Label(
            self.control_f, text="b constant:", justify='right', font=self.buttonFont)
        self.sampling_freq_e = tk.Entry(
            self.control_f, textvariable=self.sampling_freq_var, justify='center', font=self.buttonFont)
        self.sampling_freq_l = tk.Label(
            self.control_f, text="Sampling Frequency:", justify='right', font=self.buttonFont)
        self.duration_e = tk.Entry(
            self.control_f, textvariable=self.duration_var, justify='center', font=self.buttonFont)
        self.duration_l = tk.Label(
            self.control_f, text="Recording Duration:", justify='right', font=self.buttonFont)
        self.send_changes_b =  tk.Button(self.control_f, text="Send Changes to FPGA",
                                         command=self.update_config, font=self.buttonFont, highlightthickness=5, borderwidth=5)
        self.start_b = tk.Button(self.control_f, text='Start', command=self.start_recording,
                                 font=self.buttonFont, highlightthickness=5, borderwidth=5)
        self.active_f = tk.Frame(self.control_f, width=50, height=50, bg='red')
        self.label_e = tk.Entry(
            self.control_f, textvariable=self.label_var, justify='center', font=self.buttonFont)
        self.label_l = tk.Label(
            self.control_f, text="File Label:", justify='right', font=self.buttonFont)
        self.save_b = tk.Button(self.control_f, text="Save CSV", command=self.save, font=self.buttonFont, highlightthickness=5, borderwidth=5)
        self.kick_b = tk.Button(self.control_f, text="Kick",
                                         command=self.kick, font=self.buttonFont, highlightthickness=5, borderwidth=5)
        self.graph_close_b = tk.Button(self.control_f, text="Close", command=self.close_graph,
                                       fg='red', font=self.buttonFont, highlightthickness=5, borderwidth=5)
        self.fixed_mode_l = tk.Label(self.control_f, text="Fixed Frequency", justify="right", font=self.buttonFont)
        self.sweep_mode_l = tk.Label(self.control_f, text="Frequency Sweep", justify="right", font=self.buttonFont)
        self.fixed_mode_b = tk.Radiobutton(self.control_f, variable=self.sigmode_var, value="fixed", command=self.set_sig_mode)
        self.sweep_mode_b = tk.Radiobutton(self.control_f, variable=self.sigmode_var, value="sweep", command=self.set_sig_mode)
        self.lin_mode_l = tk.Label(self.control_f, text="Linear Feedback", justify="right", font=self.buttonFont)
        self.fancy_mode_l = tk.Label(self.control_f, text="Fancy Feedback", justify="right", font=self.buttonFont)
        self.lin_mode_b = tk.Radiobutton(self.control_f, variable=self.sigmode_var, value="lin", command=self.set_sig_mode)
        self.fancy_mode_b = tk.Radiobutton(self.control_f, variable=self.sigmode_var, value="fancy", command=self.set_sig_mode)
        
        # Set grid layout
        self.control_l.grid(row=0, column=0, columnspan=2, sticky='nsew')
        self.a_e.grid(row=1, column=1, sticky='nsew')
        self.a_l.grid(row=1, column=0, sticky='nsew')
        self.b_e.grid(row=2, column=1, sticky='nsew')
        self.b_l.grid(row=2, column=0, sticky='nsew')
        self.sampling_freq_e.grid(row=3, column=1, sticky='nsew')
        self.sampling_freq_l.grid(row=3, column=0, sticky='nsew')
        self.duration_e.grid(row=4, column=1, sticky='nsew')
        self.duration_l.grid(row=4, column=0, sticky='nsew')
        self.label_e.grid(row=5, column=1, sticky='nsew')
        self.label_l.grid(row=5, column=0, sticky='nsew')
        self.fixed_mode_l.grid(row=6, column=0, sticky='nsew')
        self.fixed_mode_b.grid(row=6, column=1, sticky='nsew')
        self.sweep_mode_l.grid(row=7, column=0, sticky='nsew')
        self.sweep_mode_b.grid(row=7, column=1, sticky='nsew')
        self.lin_mode_l.grid(row=8, column=0, sticky='nsew')
        self.lin_mode_b.grid(row=8, column=1, sticky='nsew')
        self.fancy_mode_l.grid(row=9, column=0, sticky='nsew')
        self.fancy_mode_b.grid(row=9, column=1, sticky='nsew')
   
        self.save_b.grid(row=10, column=0, sticky='nsew')
        self.kick_b.grid(row=10, column=1, sticky='nsew')
        self.send_changes_b.grid(row=11, column=0, sticky='nsew')
        self.start_b.grid(row=11, column=1, sticky='nsew')
        self.graph_close_b.grid(row=12, column=1, sticky='nsew')
        self.active_f.grid(row=12, column=0, sticky='nsew')
        
        self.set_cell_weights_to_1(self.control_f)
    
    def init_control_frame_fancy(self):
        """ "Fancy feedback" Placeholder screen, just a clone of linear feedback
        for now."""
        # Button Variables
        used_vars = [self.a_var,
                     self.b_var,
                     self.label_var,
                     self.duration_var,
                     self.sampling_freq_var]
        
        unused_vars = [self.fixed_freq_var,
                       self.start_freq_var,
                       self.stop_freq_var]
        
        # Button Variables - initialize
        for var in unused_vars:
            var.set(0)
        self.sigmode_var.set("lin")
        self.duration_var.set(1.0)
        self.sampling_freq_var.set(125000000 / self.FPGA_config["CIC_divider"])
        self.a_var.set(self.FPGA_config["a_const"])
        self.b_var.set(self.FPGA_config["b_const"])
    
        #Set FPGA options for stimulation mode
        self.FPGA_config["state"] = 3

    
        # Create Widgets    
        self.control_l = tk.Label(
            self.control_f, text="Recording Controls", font=self.headingFont)
        self.a_e = tk.Entry(
            self.control_f, textvariable=self.a_var, justify='center', font=self.buttonFont)
        self.a_l = tk.Label(
            self.control_f, text="a constant:", justify='right', font=self.buttonFont)
        self.b_e = tk.Entry(
            self.control_f, textvariable=self.b_var, justify='center', font=self.buttonFont)
        self.b_l = tk.Label(
            self.control_f, text="b constant:", justify='right', font=self.buttonFont)
        self.sampling_freq_e = tk.Entry(
            self.control_f, textvariable=self.sampling_freq_var, justify='center', font=self.buttonFont)
        self.sampling_freq_l = tk.Label(
            self.control_f, text="Sampling Frequency:", justify='right', font=self.buttonFont)
        self.duration_e = tk.Entry(
            self.control_f, textvariable=self.duration_var, justify='center', font=self.buttonFont)
        self.duration_l = tk.Label(
            self.control_f, text="Recording Duration:", justify='right', font=self.buttonFont)
        self.send_changes_b =  tk.Button(self.control_f, text="Send Changes to FPGA",
                                         command=self.update_config, font=self.buttonFont, highlightthickness=5, borderwidth=5)
        self.start_b = tk.Button(self.control_f, text='Start', command=self.start_recording,
                                 font=self.buttonFont, highlightthickness=5, borderwidth=5)
        self.active_f = tk.Frame(self.control_f, width=50, height=50, bg='red')
        self.label_e = tk.Entry(
            self.control_f, textvariable=self.label_var, justify='center', font=self.buttonFont)
        self.label_l = tk.Label(
            self.control_f, text="File Label:", justify='right', font=self.buttonFont)
        self.save_b = tk.Button(self.control_f, text="Save CSV", command=self.save, font=self.buttonFont, highlightthickness=5, borderwidth=5)
        self.kick_b = tk.Button(self.control_f, text="Kick",
                                         command=self.kick, font=self.buttonFont, highlightthickness=5, borderwidth=5)
        self.graph_close_b = tk.Button(self.control_f, text="Close", command=self.close_graph,
                                       fg='red', font=self.buttonFont, highlightthickness=5, borderwidth=5)
        self.fixed_mode_l = tk.Label(self.control_f, text="Fixed Frequency", justify="right", font=self.buttonFont)
        self.sweep_mode_l = tk.Label(self.control_f, text="Frequency Sweep", justify="right", font=self.buttonFont)
        self.fixed_mode_b = tk.Radiobutton(self.control_f, variable=self.sigmode_var, value="fixed", command=self.set_sig_mode)
        self.sweep_mode_b = tk.Radiobutton(self.control_f, variable=self.sigmode_var, value="sweep", command=self.set_sig_mode)
        self.lin_mode_l = tk.Label(self.control_f, text="Linear Feedback", justify="right", font=self.buttonFont)
        self.fancy_mode_l = tk.Label(self.control_f, text="Fancy Feedback", justify="right", font=self.buttonFont)
        self.lin_mode_b = tk.Radiobutton(self.control_f, variable=self.sigmode_var, value="lin", command=self.set_sig_mode)
        self.fancy_mode_b = tk.Radiobutton(self.control_f, variable=self.sigmode_var, value="fancy", command=self.set_sig_mode)
        
        # Set grid layout
        self.control_l.grid(row=0, column=0, columnspan=2, sticky='nsew')
        self.a_e.grid(row=1, column=1, sticky='nsew')
        self.a_l.grid(row=1, column=0, sticky='nsew')
        self.b_e.grid(row=2, column=1, sticky='nsew')
        self.b_l.grid(row=2, column=0, sticky='nsew')
        self.sampling_freq_e.grid(row=3, column=1, sticky='nsew')
        self.sampling_freq_l.grid(row=3, column=0, sticky='nsew')
        self.duration_e.grid(row=4, column=1, sticky='nsew')
        self.duration_l.grid(row=4, column=0, sticky='nsew')
        self.label_e.grid(row=5, column=1, sticky='nsew')
        self.label_l.grid(row=5, column=0, sticky='nsew')
        self.fixed_mode_l.grid(row=6, column=0, sticky='nsew')
        self.fixed_mode_b.grid(row=6, column=1, sticky='nsew')
        self.sweep_mode_l.grid(row=7, column=0, sticky='nsew')
        self.sweep_mode_b.grid(row=7, column=1, sticky='nsew')
        self.lin_mode_l.grid(row=8, column=0, sticky='nsew')
        self.lin_mode_b.grid(row=8, column=1, sticky='nsew')
        self.fancy_mode_l.grid(row=9, column=0, sticky='nsew')
        self.fancy_mode_b.grid(row=9, column=1, sticky='nsew')
   
        self.save_b.grid(row=10, column=0, sticky='nsew')
        self.kick_b.grid(row=10, column=1, sticky='nsew')
        self.send_changes_b.grid(row=11, column=0, sticky='nsew')
        self.start_b.grid(row=11, column=1, sticky='nsew')
        self.graph_close_b.grid(row=12, column=1, sticky='nsew')
        self.active_f.grid(row=12, column=0, sticky='nsew')
        
        self.set_cell_weights_to_1(self.control_f)
    

    def main(self):
        """Reasonably hacky time-slice scheduler to time GUI updates and data
        requests """
        
        dataMicros = micros()
        GUIMicros = micros()
        
        while(self.running):
         
            currentMicros = micros()
            
            if ((currentMicros - dataMicros) > 250000):
                dataMicros = currentMicros
                
                if (self.data.process_isRun):
                    self.receive_info_from_data()
                    
            if ((currentMicros - GUIMicros) > 250000):
                GUIMicros = currentMicros
                
                try:
                    self.graph_w.update()
            
                except tk._tkinter.TclError as e:
                    logging.debug(e)
                    break
            
        return 0
    


if __name__ == '__main__':

    __spec__ = None
    GUI_w = GUI()
    GUI_w.main()


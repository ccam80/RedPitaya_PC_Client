import sys
import os
import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk

import matplotlib.animation as animation
from matplotlib.figure import Figure as mplf_figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import socket_process as sp
from collections import deque
from multiprocessing.shared_memory import SharedMemory
from functools import partial

import numpy as np
import cProfile
from GS_timing import micros

from datetime import datetime
import pstats
import time
from functools import wraps
from gitStorage import Sync, check_ping

import csv
from time import sleep

import logging


np.set_printoptions(threshold=sys.maxsize)


class dump_event:
    def __init__(self,
                 tag="",
                 start_index=0,
                 active=True):

        self.tag = tag
        self.start_index = start_index
        self.last_save = start_index
        self.active = active





# class CodeProfiling:
#     def __init__(self):
#         now = datetime.now()
#         self.daily_created_directory = "./Profiling/" +\
#             str(now.year) + "-" + str(now.month) + "-" + str(now.day)
#         print(self.daily_created_directory)

#         if not check_directory_exists(self.daily_created_directory):
#             self.make_dir(self.daily_created_directory)

#         self.runtime_directory = self.daily_created_directory + "/" + \
#             str(now.hour) + "_" + str(now.minute) + "_" + str(now.second)
#         print(self.runtime_directory)

#         self.make_dir(self.runtime_directory)

#     def save_to_file(self, data):
#         with open("{}/profile.txt".format(self.runtime_directory), 'a') as text_file:
#             text_file.write("Additional information:\n\n")
#             text_file.write(data)

#     def make_dir(self, directory):
#         os.mkdir(directory)

#     def get_time(self):
#         pass

#     def generate_profile(self, function_to_run):
#         cProfile.run(function_to_run,
#                      "{}/code.profile".format(self.runtime_directory))
#         with open("{}/profile.txt".format(self.runtime_directory), 'w') as stream:
#             stats = pstats.Stats(
#                 "{}/code.profile".format(self.runtime_directory), stream=stream)
#             # stats.strip_dirs()
#             stats.sort_stats("cumtime").print_stats(1000)


def check_directory_exists(directory):
    if os.path.isdir(directory):
        return True
    else:
        print("directory not found, making a new one")
        return False


def time_this(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        r = func(*args, **kwargs)
        end = time.perf_counter()
        print('{}.{} : {}'.format(func.__module__, func.__name__, end - start))
        return r
    return wrapper


class GUI:
    """
        """

    def __init__(self,
                 sampling_rate = 100000,
                 datadir="./Data/",
                 animation_delay=500
                 ):

        # Argument Assignments

        self.sampling_rate = sampling_rate
        self.animation_delay = animation_delay
        self.datadir = datadir

        self.num_samples = 0
        
        if (os.path.isdir(datadir) != True):
            os.mkdir(datadir)

        # Create data processing thread
        self.data = sp.dataThread()
        # State toggles
        self.running = True
        self.new_data = False
        self.input_recording = np.zeros(0, dtype=np.int16) 
        self.output_recording = np.zeros(0, dtype=np.int16)
        # Plotting guide lines
        self.max_time_vec = np.linspace(0, 7.2e6, 10)

        # Initialise Git storage
        self.git_storage = Sync()
        
        # Initialise data thread
        self.data.start_Process()
    
        self.FPGA_config = {"CIC_divider":int(np.floor(125000000 /sampling_rate)),
                            "ch1_freq":5,
                            "a_const":1.0,
                            "ch1_ampl":32000,
                            "b_const":1}
        # self.send_config_to_data("config_change")
        mpl_logger = logging.getLogger('matplotlib')
        mpl_logger.setLevel(logging.WARNING)
        
        logging.basicConfig(filename='GUIlog.log',
                            level=logging.DEBUG,
                            format='%(asctime)s %(message)s',
                            datefmt='%m/%d/%Y %I:%M:%S %p')
        logging.debug('Logfile initialised')
        
        # Parents
        self.liveplot_fig = mplf_figure()
        self.liveplot_axs = self.liveplot_fig.subplots(
            2, 1)
        self.liveplot_ax = self.liveplot_axs.ravel()

        # artists
        self.artist0, = self.liveplot_ax[0].plot([], [], 'b', markersize=1)
        self.artist1, = self.liveplot_ax[1].plot([], [], 'b', markersize=1)
       

    
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
        buttonFont = tk.font.Font(family='Helvetica', size=16)
        headingFont = tkfont.Font(
            family='Helvetica', size=22, weight=tk.font.BOLD)

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
        self.patient_id = ''
        self.patient_id_var = tk.StringVar()
        self.patient_id_var.set("Enter ID to enable 'Start'")
        self.f_out_var = tk.IntVar()
        self.f_out_var.set(self.FPGA_config["ch1_freq"])
        self.ampl_var = tk.IntVar()
        self.ampl_var.set(self.FPGA_config["ch1_ampl"])
        self.sampling_freq_var = tk.IntVar()
        self.sampling_freq_var.set(125000000 / self.FPGA_config["CIC_divider"])
        self.duration_var = tk.IntVar()
        self.duration_var.set(1)
        self.a_var = tk.StringVar()
        self.b_var = tk.IntVar()
        self.a_var.set(self.FPGA_config["a_const"])
        self.b_var.set(self.FPGA_config["b_const"])
        # self.progress_var = tk.IntVar()
        # self.progress_var.set(self.git_storage.progress)

        self.control_l = tk.Label(
            self.control_f, text="Recording Controls", font=headingFont)
        self.f_out_e = tk.Entry(
            self.control_f, textvariable=self.f_out_var, justify='center', font=buttonFont)
        self.f_out_l = tk.Label(
            self.control_f, text="Frequency Out:", justify='right', font=buttonFont)
        self.ampl_e = tk.Entry(
            self.control_f, textvariable=self.ampl_var, justify='center', font=buttonFont)
        self.ampl_l = tk.Label(
            self.control_f, text="Amplitude Out:", justify='right', font=buttonFont)
        self.sampling_freq_e = tk.Entry(
            self.control_f, textvariable=self.sampling_freq_var, justify='center', font=buttonFont)
        self.sampling_freq_l = tk.Label(
            self.control_f, text="Sampling Frequency:", justify='right', font=buttonFont)
        self.duration_e = tk.Entry(
            self.control_f, textvariable=self.duration_var, justify='center', font=buttonFont)
        self.duration_l = tk.Label(
            self.control_f, text="Recording Duration:", justify='right', font=buttonFont)
        self.a_e = tk.Entry(
            self.control_f, textvariable=self.a_var, justify='center', font=buttonFont)
        self.a_l = tk.Label(
            self.control_f, text="a constant:", justify='right', font=buttonFont)
        self.b_e = tk.Entry(
            self.control_f, textvariable=self.b_var, justify='center', font=buttonFont)
        self.b_l = tk.Label(
            self.control_f, text="b constant:", justify='right', font=buttonFont)
        
        self.send_changes_b =  tk.Button(self.control_f, text="Send Changes to FPGA",
                                         command=self.update_config, font=buttonFont, highlightthickness=5, borderwidth=5)
        self.start_b = tk.Button(self.control_f, text='Start', command=self.start_recording,
                                 font=buttonFont, highlightthickness=5, borderwidth=5)
        self.active_f = tk.Frame(self.control_f, width=50, height=50, bg='red')
        
        self.graph_close_b = tk.Button(self.control_f, text="Close", command=self.close_graph,
                                       fg='red', font=buttonFont, highlightthickness=5, borderwidth=5)
     
        self.control_l.grid(row=0, column=0, columnspan=2, sticky='nsew')
        self.f_out_e.grid(row=1, column=1, sticky='nsew')
        self.f_out_l.grid(row=1, column=0, sticky='nsew')
        self.ampl_e.grid(row=2, column=1, sticky='nsew')
        self.ampl_l.grid(row=2, column=0, sticky='nsew')
        self.sampling_freq_e.grid(row=3, column=1, sticky='nsew')
        self.sampling_freq_l.grid(row=3, column=0, sticky='nsew')
        self.duration_e.grid(row=4, column=1, sticky='nsew')
        self.duration_l.grid(row=4, column=0, sticky='nsew')
        self.a_e.grid(row=5, column=1, sticky='nsew')
        self.a_l.grid(row=5, column=0, sticky='nsew')
        self.b_e.grid(row=6, column=1, sticky='nsew')
        self.b_l.grid(row=6, column=0, sticky='nsew')
        self.send_changes_b.grid(row=7, column=0, sticky='nsew')
        self.start_b.grid(row=7, column=1, sticky='nsew')
        self.graph_close_b.grid(row=8, column=1, sticky='nsew')
        self.active_f.grid(row=8, column=0, sticky='nsew')
        self.set_cell_weights_to_1(self.control_f)

        # animations
        self.ani = animation.FuncAnimation(self.liveplot_fig,
                                           self.animate_plots,
                                           init_func=self.init_plots,
                                           interval=self.animation_delay,
                                           blit=False)

        

   # **************************** GUI Callbacks  *********************

    def set_cell_weights_to_1(self, widget):
        """ Set weight of all cells in tkinter grid to 1 so that they stretch """
        for col_num in range(widget.grid_size()[0]):
            widget.columnconfigure(col_num, weight=1)
        for row_num in range(widget.grid_size()[1]):
            widget.rowconfigure(row_num, weight=1)

    def init_plots(self):
        """Initiate all lines, save references to attributes to keep them for
        the animation functions & to allow blitting

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

    # @profile
    def animate_plots(self, frames):
        """ Update lines & x_axis on each animation. If your time scale is constant,
        get rid of x-axis update and turn blitting on for a performance boost"""
        # logging.debug("animate_plots")
        if self.new_data:
            self.artist0.set_data(range(len(self.input_recording)), self.input_recording)
            self.liveplot_ax[0].set_xlim((0,len(self.input_recording)))
            self.liveplot_ax[0].set_ylim((np.min(self.input_recording), np.max(self.input_recording)))
            
            self.artist1.set_data(range(len(self.output_recording)), self.output_recording)
            self.liveplot_ax[1].set_xlim((0,len(self.output_recording)))
            self.liveplot_ax[1].set_ylim((np.min(self.output_recording), np.max(self.output_recording)))
            self.new_data = False
        return self.artist0, self.artist1, 

   
    # **************************** GUI Button Callbacks  *********************

    def start_recording(self):
        """Reset all data once configures, get a fresh set of vectors to save"""
        # if (self.trial_active == False):
        #     self.trial_active = True
        #     self.clear_and_reset()
        self.num_samples = self.duration_var.get() * 2 * self.sampling_freq_var.get()
        self.active_f.configure(bg='green')
        self.start_b.configure(state=tk.DISABLED)
        self.send_config_to_data("record_request")
        logging.debug("start_recording_ends")
        # self.save_data()

    def stop_trial(self):
        """ Turns red light green and saves the current trial"""
        # if (self.trial_active == True):
        #     self.trial_active = False
        self.active_f.configure(bg='red')
        self.start_b.configure(state=tk.NORMAL)
        self.debug_flag = True
        
        #     self.save_data()
        #     self.save_raw_data()
            # self.save_to_cloud()

    # Close graphing window

    def close_graph(self):
        """Does what it says on the tin."""
        self.data.close()
        self.stop_trial()
        self.graph_w.destroy()
        self.running = False
        return "break"

  

    

    # ************************* Inter-process comms  *********************
    
    def update_config(self):
        self.FPGA_config["ch1_freq"] = self.f_out_var.get()
        self.FPGA_config["ch1_ampl"] = self.ampl_var.get()
        self.FPGA_config["CIC Divider"] = int(np.floor(125000000 / 
                                              self.sampling_freq_var.get()))
        a_val = self.a_var.get()
        a_split = a_val.split(".")
        
        if len(a_split) == 1:
            integer = np.int16(a_split)
            mantissa = 0
            a_good = True
        elif len(a_split) == 2:
            integer = np.int16(a_split[0])
            mantissa = np.int16(a_split[1])
            a_good = True
        else:
            self.a_var.set("Bad number!")
            a_good=False
        
        if a_good:
            self.FPGA_config["a_const"] = (integer << 16 | mantissa)
        self.FPGA_config["b_const"] = self.b_var.get()
        self.send_config_to_data("config_change")
        
    def send_config_to_data(self, event):
        """ GUI splits up packet as:
                self.trigger,
                self.FPGA_config, 
                self.FPGA_config_change, 
                [self.record_request, self.bytes_to_receive]
                """
                
        if event == "config_change":
            packet = [0, self.FPGA_config, True, [False,0]]
        
        elif event == "trigger":
            packet = [1, self.FPGA_config, False, [False,self.num_samples * 2]]
            
        elif event == "record_request":
            packet = [0, self.FPGA_config, False, [True, self.num_samples * 2]]
            logging.debug("{} samples requested".format(self.num_samples))
        
        try:
            self.data.GUI_to_data_Queue.put(packet, block=False)
            logging.debug("packet sent to socket process")
            self.packet_sent = True
        except Exception as e:
            logging.debug("Didn't send config to data process")
            # logging.debug(e)
            
    def receive_info_from_data(self):

        try:
            data_ready, memory_name = self.data.data_to_GUI_Queue.get(block=False)
            logging.debug ("{}, {}".format(data_ready, memory_name))
            if memory_name:
                logging.debug(memory_name)
                self.shared_mem = SharedMemory(name=memory_name, size=self.num_samples * 2, create=False)
                self.send_config_to_data("trigger")
                return True
            
            elif data_ready:
                #create array with view of shared mem
                temp = np.ndarray((self.num_samples), dtype=np.int16, buffer=self.shared_mem.buf)
                 #copy into kept array
                recording = np.copy(temp)
                self.input_recording = recording[1::2]
                self.output_recording = recording[0::2]
                del temp
                logging.debug("received data")
                self.active_f.configure(bg='red')
                self.shared_mem.close()
                self.shared_mem.unlink()
                self.stop_trial()
                self.new_data = True

                return True
            else:
                return False

        except Exception as e:
            return e
       

    def main(self):
        
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
    trialwin = GUI()
    trialwin.main()
    # codeProfile = CodeProfiling()
    # codeProfile.generate_profile("trialwin.main()")
    # codeProfile.save_to_file("Patient data goes here")
    # logging.debug("ending")
    # codeProfile.save_to_file("Patient data goes here")
    # logging.debug("ending")
    # codeProfile.save_to_file("Patient data goes here")
    # logging.debug("ending")

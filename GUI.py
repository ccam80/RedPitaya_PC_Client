import sys
import os
import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk

import matplotlib.animation as animation
from matplotlib.figure import Figure as mplf_figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import datathread as dt
from collections import deque

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


class popupWindow(object):
    def __init__(self, master):
        headingFont = tkfont.Font(
            family='Helvetica', size=22, weight=tk.font.BOLD)

        top = self.top = tk.Toplevel(master)
        self.top.wm_geometry('600x400+500+500')
        self.l = tk.Label(top, text="Enter reason/note", font=headingFont)
        self.l.grid(row=0, column=0, sticky='nsew')
        self.e = tk.Entry(top, font=headingFont, justify='center',
                          validate="key", vcmd=self.activate_ok)
        self.e.grid(row=1, column=0, sticky='nsew')
        self.b = tk.Button(
            top, text='Ok', command=self.cleanup, font=headingFont,
            state=tk.DISABLED)
        self.b.grid(row=2, column=0, sticky='nsew')
        self.b.bind()
        for row_num in range(top.grid_size()[1]):
            top.rowconfigure(row_num, weight=1)
        for col_num in range(top.grid_size()[0]):
            top.columnconfigure(col_num, weight=1)

    def activate_ok(self):
        self.b.configure(state=tk.NORMAL)

    def cleanup(self):
        self.value = self.e.get()
        self.top.destroy()


class CodeProfiling:
    def __init__(self):
        now = datetime.now()
        self.daily_created_directory = "./Profiling/" +\
            str(now.year) + "-" + str(now.month) + "-" + str(now.day)
        print(self.daily_created_directory)

        if not check_directory_exists(self.daily_created_directory):
            self.make_dir(self.daily_created_directory)

        self.runtime_directory = self.daily_created_directory + "/" + \
            str(now.hour) + "_" + str(now.minute) + "_" + str(now.second)
        print(self.runtime_directory)

        self.make_dir(self.runtime_directory)

    def save_to_file(self, data):
        with open("{}/profile.txt".format(self.runtime_directory), 'a') as text_file:
            text_file.write("Additional information:\n\n")
            text_file.write(data)

    def make_dir(self, directory):
        os.mkdir(directory)

    def get_time(self):
        pass

    def generate_profile(self, function_to_run):
        cProfile.run(function_to_run,
                     "{}/code.profile".format(self.runtime_directory))
        with open("{}/profile.txt".format(self.runtime_directory), 'w') as stream:
            stats = pstats.Stats(
                "{}/code.profile".format(self.runtime_directory), stream=stream)
            # stats.strip_dirs()
            stats.sort_stats("cumtime").print_stats(1000)


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


class RR_trial:
    """User Interface and data processing lumped into one ugly class. GUI setup
    dealt with in the __init__ function.

    Variables:

        port: COM port (hard coded until I crack the search function)

        baud = serial baud rate

        data_rate = sample rate in S/s

        plot_window = length in s of window to plot. Some settings may be hard
            coded to 30s, this was an old feature that I left in in case I
            wanted an adjustable window again

        animation_delay = how long to wait between plot refreshes in ms

        progress_bar_animation_delay = refresh rate of long term plot in ms

        datadir = where to save data

        filter_lag = lag for peak pdetection algo
        filtedata.R_threshold = threshold ' '
        filter_influence = influence ' '

        peak_signal_rolling_window = rolling mean window width in samples,
            passed over detected peak signal to only consider consecutive
            outliers

        start_filter_at_sample = sample at which filters get started, can't
        start them on an empty signal

        data.R_threshold = starting cutoff for smoothed peak signal that indicates
            a heart beat, adjusted by nurse

        debounce_cycles = debouncing on peak signal to ignore spurious beats

        rms_window = window length in seconds for the rms variability calc

        ECG_level_GUI = starting ECG signal size, adjusted by nurse
        EMG_level_GUI = starting EMG signal size, adjusted by nurse

        max_events = how many tag labels to save

        QRS_cycle = average QRS duration to search for a spike inside


        """

    def __init__(self,
                 data_rate=1000,
                 plot_window=30,
                 animation_delay=300,
                 progress_bar_animation_delay=300,
                 datadir="./RR_data/",
                 max_events=20,
                 dump_duration=320,  # record 5m after event
                 ECG_level_GUI=1.5,
                 EMG_level_GUI=0.5,
                 R_threshold=0.2,
                 rms_window=300):

        # Argument Assignments

        self.data_rate = data_rate
        self.plot_window = plot_window
        self.animation_delay = animation_delay
        self.progress_bar_animation_delay = progress_bar_animation_delay
        self.max_events = max_events
        self.datadir = datadir
        self.rms_window = rms_window
        self.ECG_level_GUI = ECG_level_GUI
        self.EMG_level_GUI = EMG_level_GUI
        self.peak_threshold_GUI = R_threshold

        if (os.path.isdir(datadir) != True):
            os.mkdir(datadir)

        self.graph_window = self.data_rate * self.plot_window
        self.dump_duration = dump_duration

        # Create data processing thread
        self.data = dt.dataThread(ECG_level=ECG_level_GUI,
                                  EMG_level=EMG_level_GUI,
                                  peak_burst_threshold=R_threshold)

        # Counter variables
        self.event_counter = 0
        self.event_counter_anim = 0
        self.last_saved_event = 0
        self.last_saved_spike = 0
        self.last_plotted_interval = 0

        # State toggles
        self.running = True
        self.trial_active = False

        self.EMG = deque([], maxlen=self.graph_window)
        self.time = deque([], maxlen=self.graph_window)
        self.EMG_peaks_smth = deque([], maxlen=self.graph_window)

        self.deques = [self.EMG,
                       self.time,
                       self.EMG_peaks_smth
                       ]
        # Final data vectors
        self.R_peaks = np.zeros(1)
        self.intervals = np.zeros(1)
        self.msrms = np.zeros(1)
        self.prog_time = np.zeros(1)

        self.datavecs = [self.R_peaks,
                         self.intervals,
                         self.msrms,
                         self.prog_time]

        self.timestamp_labels = []
        self.timestamps = []
        self.data_dumps = []

        self.datalists = [self.timestamp_labels,
                          self.timestamps]

        # Plotting guide lines
        self.max_time_vec = np.linspace(0, 7.2e6, 10)
        self.R_threshold_linevec = np.ones(10) * R_threshold
        self.EMG_max_line = np.ones(10) * 0.5
        self.ECG_max_line = np.ones(10) * 1.5
        self.max_hr = 0
        self.min_hr = 0
        self.max_peak = 0

        # Initialise Git storage
        self.git_storage = Sync()
        # Initialise data thread
        self.data.start_Process()
        # 30s snapshot window

        # Parents
        self.liveplot_fig = mplf_figure()
        self.liveplot_axs = self.liveplot_fig.subplots(
            3, 1, sharex=True, sharey=False)
        self.liveplot_ax = self.liveplot_axs.ravel()

        # artists
        self.artist0, = self.liveplot_ax[0].plot([], [], 'bo', markersize=1)
        self.artist1_peaks, = self.liveplot_ax[1].plot(
            [], [], 'bo', markersize=1)
        self.artist1_thresh, = self.liveplot_ax[1].plot(
            [], [], 'y', linewidth=2)
        self.artist2, = self.liveplot_ax[2].plot([], [], 'bx', markersize=3)
        self.artist3, = self.liveplot_ax[1].plot([], [], 'rx', markersize=3)
        self.artist0_EMG_pos, = self.liveplot_ax[0].plot(
            [], [], 'r', linewidth=2)
        self.artist0_EMG_neg, = self.liveplot_ax[0].plot(
            [], [], 'r', linewidth=2)
        self.artist0_ECG_pos, = self.liveplot_ax[0].plot(
            [], [], 'g', linewidth=2)
        self.artist0_ECG_neg, = self.liveplot_ax[0].plot(
            [], [], 'g', linewidth=2)

        # "Progress" Bar

        # Parents
        self.prog_bar = mplf_figure(figsize=(6, 1.5))
        self.prog_bar_ax = self.prog_bar.subplots(1, 1)

        # Artists
        self.prog_bar_lines = []
        self.prog_bar_tags = []
        self.prog_bar_artist, = self.prog_bar_ax.plot(
            [], [], 'bo', markersize=1)
        self.prog_bar_artists = [self.prog_bar_artist, ]

        for i in range(max_events):
            self.prog_bar_lines.append(
                self.prog_bar_ax.axvline(-1, color='red', animated=True))
            self.prog_bar_tags.append(
                self.prog_bar_ax.text(-1, 10, "", color='r'))
            self.prog_bar_artists.append(self.prog_bar_lines[-1])
            self.prog_bar_artists.append(self.prog_bar_tags[-1])

        # ----------------------------------
        # GUI Config
        # ----------------------------------
        self.graph_w = tk.Tk()

        self.graph_w.wm_title("Live R-R recognition")
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
        sliderFont = tkfont.Font(family='Helvetica', size=14)

       # **************** Master Grid Layout *************************

        self.control_f = tk.Frame(self.master_f, bd=2, relief='solid')
        self.sliders_f = tk.Frame(self.master_f, bd=2, relief='solid')
        self.stamps_f = tk.Frame(self.master_f, bd=2, relief='solid')
        self.progress_bar_canvas = FigureCanvasTkAgg(
            self.prog_bar, master=self.master_f)
        self.canvas = FigureCanvasTkAgg(
            self.liveplot_fig, master=self.master_f)

        self.canvas.get_tk_widget().grid(
            row=0, column=0, sticky='nsew', rowspan=4, columnspan=2)
        self.sliders_f.grid(row=0, column=2, rowspan=2, sticky='nsew')
        self.stamps_f.grid(row=2, column=2, rowspan=2, sticky='nsew')
        self.progress_bar_canvas.get_tk_widget().grid(
            row=4, column=0, sticky='nsew', columnspan=2)
        self.control_f.grid(row=4, column=2, sticky='nsew')

        self.set_cell_weights_to_1(self.master_f)
        self.graph_w.bind("<Configure>", self.resize_prog_bar)
        self.canvas.draw()
        self.progress_bar_canvas.draw()

        # ******************* Slider Frame ***********************************

        # Input Variables
        self.ECG_level_GUI_var = tk.DoubleVar()
        self.ECG_level_GUI_var.set(self.ECG_level_GUI)
        self.EMG_level_GUI_var = tk.DoubleVar()
        self.EMG_level_GUI_var.set(self.EMG_level_GUI)
        self.thresh_var = tk.DoubleVar()
        self.thresh_var.set(self.data.peak_burst_threshold)

        #Sliders, binding, labels
        self.sliders_l = tk.Label(
            self.sliders_f, text="Filter Settings", font=headingFont)

        self.ECG_level_GUI_s = tk.Scale(self.sliders_f,
                                        from_=0.5, to=2,
                                        digits=3, resolution=0.1,
                                        variable=self.ECG_level_GUI_var,
                                        orient=tk.HORIZONTAL)
        self.ECG_level_GUI_s.bind("<ButtonRelease-1>", self.set_ECG_level_GUI)
        self.ECG_level_GUI_label = tk.Label(
            self.sliders_f, text="Peak Height (GREEN)", font=sliderFont)

        self.EMG_level_GUI_s = tk.Scale(self.sliders_f,
                                        from_=0.05, to=1,
                                        digits=3, resolution=0.1,
                                        variable=self.EMG_level_GUI_var,
                                        orient=tk.HORIZONTAL)
        self.EMG_level_GUI_s.bind("<ButtonRelease-1>", self.set_EMG_level_GUI)
        self.EMG_level_GUI_label = tk.Label(
            self.sliders_f, text="Full Inhale Breath Level (RED)", font=sliderFont)

        self.thresh_s = tk.Scale(self.sliders_f,
                                 from_=0, to=0.5,
                                 digits=3,
                                 resolution=0.01,
                                 orient=tk.HORIZONTAL,
                                 variable=self.thresh_var)
        self.thresh_s.bind("<ButtonRelease-1>", self.set_threshold_level)
        self.thresh_label = tk.Label(
            self.sliders_f, text="Peak Threshold (YELLOW)", font=sliderFont)

        # Layout
        self.sliders_l.grid(row=0, column=0, sticky='nsew')
        self.EMG_level_GUI_label.grid(row=1, column=0, sticky='nsew')
        self.EMG_level_GUI_s.grid(row=2, column=0, sticky='nsew')
        self.ECG_level_GUI_label.grid(row=3, column=0, sticky='nsew')
        self.ECG_level_GUI_s.grid(row=4, column=0, sticky='nsew')
        self.thresh_label.grid(row=5, column=0, sticky='nsew')
        self.thresh_s.grid(row=6, column=0, sticky='nsew')

        self.set_cell_weights_to_1(self.sliders_f)

        # *************************** Timestamps Frame ************************

        self.timestamps_l = tk.Label(
            self.stamps_f, text="Time Stamps", font=headingFont)
        self.consult_room_b = tk.Button(self.stamps_f, text="Consult Room", command=partial(
            self.time_stamp, "CR"), font=buttonFont, highlightthickness=5, borderwidth=5)
        self.table_b = tk.Button(self.stamps_f, text="On Table", command=partial(
            self.time_stamp, "OT"), font=buttonFont, highlightthickness=5, borderwidth=5)
        self.abex_b = tk.Button(self.stamps_f, text="Abd. Exam", command=partial(
            self.time_stamp, "AE"), font=buttonFont, highlightthickness=5, borderwidth=5)
        self.initial_insertion_b = tk.Button(self.stamps_f, text="Initial Insertion", command=partial(
            self.time_stamp, "I I"), font=buttonFont, highlightthickness=5, borderwidth=5)
        self.max_insertion_b = tk.Button(self.stamps_f, text="Maximum Insertion", command=partial(
            self.time_stamp, "MI"), font=buttonFont, highlightthickness=5, borderwidth=5)
        self.scope_removed_b = tk.Button(self.stamps_f, text="Scope Removed", command=partial(
            self.time_stamp, "SR"), font=buttonFont, highlightthickness=5, borderwidth=5)
        self.vasovagal_b = tk.Button(self.stamps_f, text="Vasovagal Event", command=partial(
            self.time_stamp, "V V"), font=buttonFont, highlightthickness=5, borderwidth=5)
        self.change_position_b = tk.Button(self.stamps_f, text="Change Position", command=partial(
            self.time_stamp, "CP"), font=buttonFont, highlightthickness=5, borderwidth=5)
        self.pressure_b = tk.Button(self.stamps_f, text="Pressure Applied", command=partial(
            self.time_stamp, "PA"), font=buttonFont, highlightthickness=5, borderwidth=5)
        self.polyp_b = tk.Button(self.stamps_f, text="Polyp Removal", command=partial(
            self.time_stamp, "PR"), font=buttonFont, highlightthickness=5, borderwidth=5)
        self.biopsy_b = tk.Button(self.stamps_f, text="Biopsy", command=partial(
            self.time_stamp, "Bi"), font=buttonFont, highlightthickness=5, borderwidth=5)
        self.haem_b = tk.Button(self.stamps_f, text="Haemmorrhoid", command=partial(
            self.time_stamp, "HB"), font=buttonFont, highlightthickness=5, borderwidth=5)

        self.end_l = tk.Label(
            self.stamps_f, text="Procedure Ended:", font=buttonFont)
        self.end_prem_b = tk.Button(self.stamps_f, text="Premature", command=partial(
            self.time_stamp, "EP_P"), font=buttonFont, highlightthickness=5, borderwidth=5)
        self.end_normal_b = tk.Button(self.stamps_f, text="Normal", command=partial(
            self.time_stamp, "EP_D"), font=buttonFont, highlightthickness=5, borderwidth=5)
        self.other_b = tk.Button(self.stamps_f, text="Other", command=partial(
            self.time_stamp, "O"), font=buttonFont, highlightthickness=5, borderwidth=5)

        self.timestamps_l.grid(row=0, column=0, sticky='nsew', columnspan=2)
        self.consult_room_b.grid(row=1, column=0, sticky='nsew', rowspan=2)
        self.table_b.grid(row=1, column=1, sticky='nsew', rowspan=2)
        self.abex_b.grid(row=3, column=0, sticky='nsew', rowspan=2)
        self.initial_insertion_b.grid(
            row=3, column=1, sticky='nsew', rowspan=2)
        self.max_insertion_b.grid(row=5, column=0, sticky='nsew', rowspan=2)
        self.scope_removed_b.grid(row=5, column=1, sticky='nsew', rowspan=2)
        self.change_position_b.grid(row=8, column=0, sticky='nsew')
        self.pressure_b.grid(row=8, column=1, sticky='nsew')
        self.polyp_b.grid(row=9, column=0, sticky='nsew')
        self.biopsy_b.grid(row=9, column=1, sticky='nsew')
        self.haem_b.grid(row=10, column=0, sticky='nsew')
        self.vasovagal_b.grid(row=10, column=1, sticky='nsew')
        self.other_b.grid(row=11, column=0, sticky='nsew', columnspan=2)
        self.end_l.grid(row=12, column=0, sticky='nsew', columnspan=2)
        self.end_prem_b.grid(row=13, column=0, sticky='nsew')
        self.end_normal_b.grid(row=13, column=1, sticky='nsew')

        self.set_cell_weights_to_1(self.stamps_f)

        # **************************** Control Frame *********************

        # Button Variables
        self.patient_id = ''
        self.patient_id_var = tk.StringVar()
        self.patient_id_var.set("Enter ID to enable 'Start'")
        self.progress_var = tk.IntVar()
        self.progress_var.set(self.git_storage.progress)

        self.control_l = tk.Label(
            self.control_f, text="Recording Controls", font=headingFont)
        self.patient_id_e = tk.Entry(
            self.control_f, textvariable=self.patient_id_var, justify='center', font=buttonFont)
        self.patient_id_b = tk.Button(self.control_f, text="Set", command=self.set_patient_id,
                                      font=buttonFont, highlightthickness=5, borderwidth=5)
        self.patient_id_l = tk.Label(
            self.control_f, text="Patient ID:", justify='right', font=buttonFont)
        self.start_b = tk.Button(self.control_f, text='Start', command=self.start_trial,
                                 state=tk.DISABLED, font=buttonFont, highlightthickness=5, borderwidth=5)
        self.stop_b = tk.Button(self.control_f, text='Stop', command=self.stop_trial,
                                font=buttonFont, highlightthickness=5, borderwidth=5)
        self.active_f = tk.Frame(self.control_f, width=50, height=50, bg='red')
        self.cloud_b = tk.Button(self.control_f, text='Save to Cloud',
                                 command=self.save_to_cloud, font=buttonFont, highlightthickness=5, borderwidth=5)
        self.graph_close_b = tk.Button(self.control_f, text="Close", command=self.close_graph,
                                       fg='red', font=buttonFont, highlightthickness=5, borderwidth=5)
        self.cloud_progbar = ttk.Progressbar(
            self.control_f, length=100, mode="determinate", orient=tk.HORIZONTAL, variable=self.progress_var)

        self.patient_id_e.bind("<ButtonRelease-1>", self.select_all)
        self.control_l.grid(row=0, column=0, columnspan=3, sticky='nsew')
        self.patient_id_l.grid(row=1, column=0, sticky='nsew')
        self.patient_id_e.grid(row=1, column=1, sticky='nsew')
        self.patient_id_b.grid(row=1, column=2, sticky='nsew')
        self.start_b.grid(row=2, column=0, sticky='nsew')
        self.active_f.grid(row=2, column=1, sticky='nsew')
        self.stop_b.grid(row=2, column=2, sticky='nsew')
        self.cloud_progbar.grid(row=3, column=0, sticky='nsew')
        self.cloud_b.grid(row=3, column=1, sticky='nsew')
        self.graph_close_b.grid(row=3, column=2, sticky='nsew')

        self.set_cell_weights_to_1(self.control_f)

        # animations
        self.ani = animation.FuncAnimation(self.liveplot_fig,
                                           self.animate_plots,
                                           init_func=self.init_plots,
                                           interval=self.animation_delay,
                                           blit=False)

        self.prog_bar_animation = animation.FuncAnimation(self.prog_bar,
                                                          self.animate_progress_bar,
                                                          init_func=self.init_progress_bar,
                                                          interval=self.progress_bar_animation_delay,
                                                          blit=True)

   # **************************** GUI Callbacks  *********************

    def set_cell_weights_to_1(self, widget):
        """ Set weight of all cells in tkinter grid to 1 so that they stretch """
        for col_num in range(widget.grid_size()[0]):
            widget.columnconfigure(col_num, weight=1)
        for row_num in range(widget.grid_size()[1]):
            widget.rowconfigure(row_num, weight=1)

    def resize_prog_bar(self, event):
        """resize progress bar window to fit the grid when the window changes size"""
        height = self.graph_w.winfo_height()
        width = self.graph_w.winfo_width()
        self.prog_bar.width = int(width * 2 / 3)
        self.prog_bar.height = int(height / 5)

    def select_all(self, event):
        self.patient_id_e.select_range(0, 'end')

    def init_plots(self):
        """Initiate all lines, save references to attributes to keep them for
        the animation functions & to allow blitting

        Configure axes while we're at it to avoid overloading the animation
        functions
        """

        self.artist0.set_data([], [])
        self.artist1_peaks.set_data([], [])
        self.artist1_thresh.set_data([], [])
        self.artist2.set_data([], [])
        self.artist3.set_data([], [])
        self.artist1_thresh.set_data(
            self.max_time_vec, self.R_threshold_linevec)
        self.artist0_EMG_pos.set_data(self.max_time_vec, self.EMG_max_line)
        self.artist0_EMG_neg.set_data(self.max_time_vec, -self.EMG_max_line)
        self.artist0_ECG_pos.set_data(self.max_time_vec, self.ECG_max_line)
        self.artist0_ECG_neg.set_data(self.max_time_vec, -self.ECG_max_line)

        self.liveplot_ax[0].set_ylabel("mV")
        self.liveplot_ax[0].set_title("Live ECG")
        self.liveplot_ax[1].set_title("Recognised Peaks")
        self.liveplot_ax[2].set_ylabel("bpm")
        self.liveplot_ax[2].set_title("Instantaneous Heart Rate")

        # self.liveplot_fig.suptitle("30 Second Snapshot")

        self.liveplot_ax[0].set_ylim([-2, 2])
        self.liveplot_ax[1].set_ylim([0, 0.5])
        # self.liveplot_ax[2].set_ylim([30,150])
        # self.liveplot_ax[3].set_ylim([0,100])

        for i in range(len(self.liveplot_ax)):
            self.liveplot_ax[i].grid(b=True, which='both')

        self.liveplot_fig.tight_layout()

        return self.artist0, self.artist1_peaks, self.artist1_thresh, self.artist2, self.artist3,

    # @profile
    def animate_plots(self, frames):
        """ Update lines & x_axis on each animation. If your time scale is constant,
        get rid of x-axis update and turn blitting on for a performance boost"""

        if ((len(self.R_peaks) != len(self.intervals)) |
                (len(self.time) < 2)):
            return self.artist0, self.artist1_peaks, self.artist1_thresh, self.artist2, self.artist3,

        if (len(self.EMG) > 0):
            self.artist0.set_data(self.time, self.EMG)
            self.artist1_peaks.set_data(self.time, self.EMG_peaks_smth)
            self.artist2.set_data(self.R_peaks, np.divide(
                60, (self.intervals), out=np.zeros_like(self.intervals), where=self.intervals != 0))
            # self.artist3.set_data(self.R_peaks, self.R_peaks)

            # This dodgy bit of code is from data
            self.last_plotted_interval = np.amin(
                np.argwhere(self.R_peaks > (self.R_peaks[-1] - 30)))

            min_interval = np.amin(self.intervals[self.last_plotted_interval:],
                                   out=np.zeros_like(1, dtype=float),
                                   where=self.intervals[self.last_plotted_interval:] != 0,
                                   initial=2)

            if (min_interval != 0):
                max_hr = 60 / (min_interval)
            else:
                max_hr = 0

            if ((max_hr != self.max_hr) & (max_hr != 0)):
                self.max_hr = max_hr
                self.liveplot_ax[2].set_ylim([0, (self.max_hr * 1.4)])

            if (np.amax(self.EMG_peaks_smth) != self.max_peak):
                self.max_peak = np.amax(self.EMG_peaks_smth)
                if (self.max_peak != 0):
                    self.liveplot_ax[1].set_ylim([0, (self.max_peak * 1.5)])

        self.liveplot_ax[2].set_xlim([self.time[0], self.time[-1]])

        return self.artist0, self.artist1_peaks, self.artist1_thresh, self.artist2, self.artist3,

    def init_progress_bar(self):
        """Configure axis and artists for the progress bar and "tag" lines"""
        self.prog_bar_artist.set_data([], [])
        self.prog_bar_ax.set_ylabel("R-R variability")
        self.prog_bar_ax.set_xlabel("Time (m)")
        self.prog_bar_ax.set_xlim([0, 60])
        self.prog_bar_ax.set_ylim([10, 200])
        self.prog_bar_ax.grid(b=True, which='both')
        self.prog_bar_ax.set_title("Procedure Progress")
        self.prog_bar.tight_layout()

        return self.prog_bar_artists

    def animate_progress_bar(self, frames):
        """Update the prog bar plot, and the event tag lines if there have been
        any since the last animate."""
        self.prog_bar_artist.set_data(self.prog_time / 60, self.msrms)

        # Check for new events. If multiple events in one animation period, loop through them
        if (self.event_counter != self.event_counter_anim):
            for i in range(self.event_counter - self.event_counter_anim):
                self.prog_bar_artists[(self.event_counter - i) * 2 - 1].set_xdata(
                    [self.timestamps[-1 - i] / 60, self.timestamps[-1 - i] / 60])
                self.prog_bar_artists[(self.event_counter - i) * 2].set_position(
                    [self.timestamps[-1 - i] / 60, (20*(self.event_counter - i)) % 180 + 20])
                self.prog_bar_artists[(self.event_counter - i)
                                      * 2].set_text(self.timestamp_labels[-1 - i])
            self.event_counter_anim = self.event_counter

        return self.prog_bar_artists

    # **************************** GUI Button Callbacks  *********************

    def start_trial(self):
        """Reset all data once configures, get a fresh set of vectors to save"""
        if (self.trial_active == False):
            self.trial_active = True
            self.clear_and_reset()
            self.active_f.configure(bg='green')
            self.save_data()

    def stop_trial(self):
        """ Turns red light green and saves the current trial"""
        if (self.trial_active == True):
            self.trial_active = False
            self.active_f.configure(bg='red')
            self.save_data()
            self.save_raw_data()
            # self.save_to_cloud()

    # Close graphing window

    def close_graph(self):
        """Does what it says on the tin. Closes serial port as a bonus"""
        self.graph_w.destroy()
        self.stop_trial()
        self.data.close()
        self.running = False
        return "break"

    def set_patient_id(self):
        """Set current patient to whatever is in the text box"""
        self.patient_id = self.patient_id_var.get()
        self.start_b.configure(state=tk.NORMAL)

    def time_stamp(self, event):
        """Save an event tag"""

        # Increment event counter for plotting
        self.event_counter += 1
        self.event_counter = self.event_counter % self.max_events
        if (self.event_counter == 0):
            self.event_counter = 1

        # Save event time and label
        self.timestamp_labels.append(event)
        self.timestamps.append(self.time[-1])

        # Create dump object to store raw data
        self.data_dumps.append(dump_event(
            tag=event, start_index=self.time[-1], active=True))

        # Prompt for reason if tag "other" or "premature end procedure"
        if ((event == "O") or (event == "EP_P")):
            self.reason = popupWindow(self.graph_w)
            self.graph_w.wait_window(self.reason.top)
            self.save_other(event, self.time[-1], self.reason.value)

    def set_ECG_level_GUI(self, event):
        """Adjust ECG level by eye using slider"""
        self.ECG_level_GUI = self.ECG_level_GUI_var.get()
        self.ECG_max_line = np.ones(10) * self.ECG_level_GUI
        self.artist0_ECG_pos.set_data(self.max_time_vec, self.ECG_max_line)
        self.artist0_ECG_neg.set_data(self.max_time_vec, -self.ECG_max_line)
        self.update_child_process()

    def set_EMG_level_GUI(self, event):
        """Adjust EMG level by eye using slider"""
        self.EMG_level_GUI = self.EMG_level_GUI_var.get()
        self.EMG_max_line = np.ones(10) * self.EMG_level_GUI
        self.artist0_EMG_pos.set_data(self.max_time_vec, self.EMG_max_line)
        self.artist0_EMG_neg.set_data(self.max_time_vec, -self.EMG_max_line)
        self.update_child_process()

    def set_threshold_level(self, event):
        """Adjust peak threshold by eye using slider"""
        self.peak_threshold_GUI = self.thresh_var.get()
        self.R_threshold_linevec = np.ones(10) * self.peak_threshold_GUI
        self.artist1_thresh.set_data(
            self.max_time_vec, self.R_threshold_linevec)
        self.update_child_process()

    # ************************* File mgmgt/ Saving  *********************

    def save_data(self):
        """Save under current patient number"""
        # Set up directory + path
        directory = self.datadir + str(self.patient_id)
        if (os.path.isdir(directory) != True):
            os.mkdir(directory)

        # Save data as csv
        savestr = directory + "/beatLog.csv"

        if (os.path.isfile(savestr) != True):
            csv_headers = ['Time (ms)', 'R peak', 'Event Stamp']
            with open(savestr, 'w', newline='') as log_file:
                datawriter = csv.writer(log_file, delimiter=',')
                datawriter.writerow(csv_headers)
                log_file.close()

        else:
            with open(savestr, 'a', newline='') as log_file:
                datawriter = csv.writer(log_file, delimiter=',')
                saveslice = self.R_peaks[self.last_saved_spike:-1]

                for i in range(len(saveslice)):
                    datawriter.writerow(
                        ["{index}".format(index=saveslice[i]), "-1", "-1"])

                self.last_saved_spike = len(self.R_peaks) - 1

                new_events = self.event_counter - self.last_saved_event
                if (new_events != 0):
                    for i in range(new_events):
                        datawriter.writerow(["-1", "{stamp}".format(stamp=self.timestamps[i - new_events]),
                                            "{label}".format(label=self.timestamp_labels[i - new_events])])
                self.last_saved_event = self.event_counter
                log_file.close()

    def save_raw_data(self):
        """Save block of raw data under current patient number"""
        # Set up directory + path
        dump_EMG = np.asarray(self.EMG)
        dump_x = np.asarray(self.time)
        directory = self.datadir + str(self.patient_id)
        if (os.path.isdir(directory) != True):
            os.mkdir(directory)

        # Save data as csv
        for dump in self.data_dumps:
            if dump.active:
                savestr = directory + "/" + dump.tag + \
                    "_{:.1f}".format(dump.start_index) + ".csv"

                if (os.path.isfile(savestr) != True):
                    csv_headers = ["Time (s)", "EMG(mV)", "Tag = " + dump.tag]
                    with open(savestr, 'w', newline='') as log_file:
                        datawriter = csv.writer(log_file, delimiter=',')
                        datawriter.writerow(csv_headers)
                        log_file.close()

                else:
                    with open(savestr, 'a', newline='') as log_file:
                        datawriter = csv.writer(log_file, delimiter=',')
                        EMG_saveslice = dump_EMG[dump_x > dump.last_save]
                        time_saveslice = dump_x[dump_x > dump.last_save]

                        for i in range(len(EMG_saveslice)):
                            datawriter.writerow(["{index}".format(index=time_saveslice[i]),
                                                 "{index}".format(index=EMG_saveslice[i])])

                        dump.last_save = time_saveslice[-1]
                        log_file.close()

                        if (dump.last_save > (dump.start_index + self.dump_duration)):
                            dump.active = False

    def save_other(self, event, time, reason):
        """Save "Other" tag reason in separate spreadsheet"""

        directory = self.datadir + str(self.patient_id)
        if (os.path.isdir(directory) != True):
            os.mkdir(directory)

        # Save data as csv
        savestr = directory + "/others.csv"

        if (os.path.isfile(savestr) != True):
            csv_headers = ['Time (ms)', 'Stamp', 'Reason']
            with open(savestr, 'w', newline='') as log_file:
                datawriter = csv.writer(log_file, delimiter=',')
                datawriter.writerow(csv_headers)
                log_file.close()

        with open(savestr, 'a', newline='') as log_file:
            datawriter = csv.writer(log_file, delimiter=',')
            datawriter.writerow(
                ["{}".format(time), "{}".format(event), "{}".format(reason)])
            log_file.close()

    def save_to_cloud(self):
        # save_message = 'Saving data to the cloud. This will take a few seconds...'
        # time.sleep(2)
        if check_ping():
            # self.message_l.configure(text=save_message)
            # self.graph_w.update()
            self.graph_close_b.configure(state=tk.DISABLED)
            files, filepaths = self.get_all_files()
            # print("-----")
            # print(files)
            # print(filepaths)
            # print("-----")
            self.git_storage.commit_process(files, filepaths)
            # save_message = 'Finished saving to cloud. \n It is safe to start next recording or close application.'
        # else:
            # save_message = 'Failed to connect to server'

        # self.message_l.configure(text=save_message)

    def get_all_files(self):
        top_directory = self.datadir
        if (os.path.isdir(top_directory) != True):
            return 0
        # directory = top_directory + "\Subject_" + str(self.study_id)
        subfolders = [f.path for f in os.scandir(top_directory) if f.is_dir()]
        # print(subfolders)
        filepaths = []
        files = []
        for sub in subfolders:
            for f in os.listdir(sub):
                src = sub + "/" + f
                filepaths.append(src)
                files.append(f)
                # print(f)
        return files, filepaths

    # ************************* Inter-process comms  *********************

    def update_child_process(self):

        self.data.settingsQueue.put([self.EMG_level_GUI,
                                     self.ECG_level_GUI,
                                     self.peak_threshold_GUI],
                                    block=True,
                                    timeout=1)

    def fetch_data(self):

        try:
            packet = self.data.dataQueue.get()
            self.time.append(packet[0])
            self.EMG.append(packet[1])
            self.EMG_peaks_smth.append(packet[2])
            last_peak = packet[3]

            if (self.R_peaks[-1] != last_peak):
                self.intervals = np.append(
                    self.intervals, last_peak - self.R_peaks[-1])
                self.R_peaks = np.append(self.R_peaks, last_peak)
                self.calc_rms_variability()

            return True
        except Exception as e:
            return e
        else:
            return False

    def fetch_progress(self):
        try:
            progress = self.git_storage.progressQueue.get(block=False)
            if (progress <= 100):
                self.progress_var.set(progress)
            else:
                self.graph_close_b.configure(state=tk.NORMAL)
                self.progress_var.set(0)

            return True
        except Exception as e:
            return e
        else:
            return False


# ************************* Helpers ************************************

    def calc_rms_variability(self):
        """calculate RMSSD"""
        #  pick out intervals in last rms_window seconds
        rms_indices = np.transpose(np.nonzero(
            (self.R_peaks > (self.R_peaks[-1] - self.rms_window)) & (self.R_peaks[-1] > 1)))
        n = len(rms_indices)
        square = 0

        for i in range(n-1):
            interval_difference = (
                self.intervals[-i-1] - self.intervals[-i-2]) * 1000
            square += interval_difference**2
        if (n != 0):
            self.msrms = np.append(self.msrms, np.sqrt(square / n))
        else:
            self.msrms = np.append(self.msrms, 0)

        self.prog_time = np.append(self.prog_time, self.time[-1])

    def clear_and_reset(self):
        # Clear signal chain
        self.data.clearQueue.put(True)
        sleep(0.1)
        while(True):
            try:
                self.data.dataQueue.get(block=False)
            except:
                break

        for queue in self.deques:
            queue.clear()
        for stamp in self.datalists:
            stamp.clear()

        self.data_dumps = []

        self.R_peaks = np.zeros(1)
        self.intervals = np.zeros(1)
        self.msrms = np.zeros(1)
        self.prog_time = np.zeros(1)

        # reset counters
        self.event_counter = 0
        self.event_counter_anim = 0
        self.last_saved_event = 0
        self.last_saved_spike = 0

        # Clear progress bar artists
        for line in self.prog_bar_lines:
            line.set_xdata(-100)
        for tag in self.prog_bar_tags:
            tag.set_position([-100, -10])

    def main(self):

        dataMicros = micros()
        GUIMicros = micros()
        while(self.running):
            currentMicros = micros()

            if (currentMicros > (dataMicros + 200)):
                if (self.data.process_isRun):
                    self.fetch_data()
                    self.fetch_progress()
                dataMicros = micros()

            if (currentMicros > (GUIMicros + 100000)):
                try:
                    self.graph_w.update()

                except tk._tkinter.TclError:
                    break

                # Save data every 10s in case of mid-trial crash
                if (len(self.R_peaks) > 3):
                    if ((self.trial_active == True) & ((self.time[-1] - self.R_peaks[self.last_saved_spike]) > 10)):
                        self.save_data()
                        self.save_raw_data()

                GUIMicros = currentMicros
        return 0


if __name__ == '__main__':

    __spec__ = None
    trialwin = RR_trial()
    trialwin.main()
    # codeProfile = CodeProfiling()
    # codeProfile.generate_profile("trialwin.main()")
    # codeProfile.save_to_file("Patient data goes here")
    # print("ending")
    # codeProfile.save_to_file("Patient data goes here")
    # print("ending")
    # codeProfile.save_to_file("Patient data goes here")
    # print("ending")

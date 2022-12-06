from multiprocessing import Process, Queue
import serial
# import sys
from serial.tools import list_ports
from scipy.ndimage.filters import uniform_filter1d as rolling_mean
# from scipy.signal import find_peaks
import traceback
from time import sleep
import numpy as np


class ReadLine:
    def __init__(self, s):
        self.buf = bytearray()
        self.s = s

    def readline(self):
        i = self.buf.find(b"\n")
        if i >= 0:
            r = self.buf[:i+1]
            self.buf = self.buf[i+1:]
            return r
        while True:
            i = max(1, min(2048, self.s.in_waiting))
            data = self.s.read(i)
            i = data.find(b"\n")
            if i >= 0:
                r = self.buf + data[:i+1]
                self.buf[0:] = data[i+1:]
                return r
            else:
                self.buf.extend(data)

class real_time_peak_detection():
    """Peak detection algorithm. Takes a rolling mean & std dev, and identifies
    any points that lay outside of a set threshold * std dev range of the mean.

    Configurable parameters:

        lag: length of rolling mean window in samples. Set high for better stability on
        stationary signal, short if signal moves around a bit.

        threshold: How many std devs away from mean counts as an outlier

        influence: How much the identified outliers should affect the rolling
        mean and std dev figures. 0 - no effect, 1 - treated like a non-outlier

    """

    def __init__(self, array, lag, threshold, influence):
        self.y = list(array)
        self.length = len(self.y)
        self.lag = lag
        self.threshold = threshold
        self.influence = influence
        self.signals = [0] * len(self.y)
        self.filteredY = np.array(self.y).tolist()
        self.avgFilter = [0] * len(self.y)
        self.stdFilter = [0] * len(self.y)
        self.avgFilter[self.lag - 1] = np.mean(self.y[0:self.lag]).tolist()
        self.stdFilter[self.lag - 1] = np.std(self.y[0:self.lag]).tolist()



    #@profile
    def thresholding_algo(self, new_value):
        self.y.append(new_value)
        i = len(self.y) - 1
        self.length = len(self.y)
        if i < self.lag:
            return 0
        elif i == self.lag:
            self.signals = [0] * len(self.y)
            self.filteredY = np.array(self.y).tolist()
            self.avgFilter = [0] * len(self.y)
            self.stdFilter = [0] * len(self.y)
            self.avgFilter[self.lag - 1] = np.mean(self.y[0:self.lag]).tolist()
            self.stdFilter[self.lag - 1] = np.std(self.y[0:self.lag]).tolist()
            return 0

        self.signals += [0]
        self.filteredY += [0]
        self.avgFilter += [0]
        self.stdFilter += [0]

        if abs(self.y[i] - self.avgFilter[i - 1]) > self.threshold * self.stdFilter[i - 1]:
            if self.y[i] > self.avgFilter[i - 1]:
                self.signals[i] = 1
            else:
                self.signals[i] = -1

            self.filteredY[i] = self.influence * self.y[i] + (1 - self.influence) * self.filteredY[i - 1]
            self.avgFilter[i] = np.mean(self.filteredY[(i - self.lag):i])
            self.stdFilter[i] = np.std(self.filteredY[(i - self.lag):i])
        else:
            self.signals[i] = 0
            self.filteredY[i] = self.y[i]
            self.avgFilter[i] = np.mean(self.filteredY[(i - self.lag):i])
            self.stdFilter[i] = np.std(self.filteredY[(i - self.lag):i])

        return self.signals[i]

class dataThread:
    def __init__(self,
                 baud=115200,
                 filter_lag = 300,
                 filter_threshold = 5,
                 filter_influence = 0,
                 peak_smoothing_window_length = 100,
                 peak_burst_threshold = 0.2,
                 debounce_cycles = 3,
                 QRS_cycle_duration = 0.150,
                 gradient_smoothing_samples = 8,
                 ECG_level = 1.5,
                 EMG_level = 0.5,
                 QRS_analysis_buffer_length = 2000):


        self.process = None
        self.filters_started = False
        self.serial_isOpen = False
        self.process_isRun = False

        self.baud = baud
        self.filter_lag = filter_lag
        self.filter_threshold = filter_threshold
        self.filter_influence = filter_influence
        self.peak_smoothing_window_length = peak_smoothing_window_length
        self.debounce_cycles = debounce_cycles

        self.peak_burst_threshold = peak_burst_threshold
        self.QRS_cycle_duration = QRS_cycle_duration
        self.gradient_smoothing_samples = gradient_smoothing_samples
        self.EMG_level = EMG_level
        self.ECG_level = ECG_level
        self.QRS_analysis_buffer_length = QRS_analysis_buffer_length

        self.upper_interval_limit = 1.150
        self.lower_interval_limit = 0.500


        #State machine variables (for identifying spikes)
        self.edge = 'falling'
        self.rising_debounce_counter = 0
        self.falling_debounce_counter = 0
        self.pulse_start = 0
        self.pulse_end = 0


        # Counter variables
        # self.sample_count = 0
        self.peak_sum = 0
        self.consecutive_zeros = 0
        self.unit_off = False
        self.time_set = False
        self.clear_flag = False
        self.wrap_counter = 0

        # Pipe to send final data to main process
        self.dataQueue = Queue()
        self.settingsQueue = Queue()
        self.clearQueue = Queue()


        # Signal chain values
        self.EMG = 0                        # raw EMG sample
        self.EMG_rect = 0                   # rectified EMG sample
        self.x = 0                          # current time in s
        self.peak_detected = 0              # peak detected, 1 or 0
        self.peak_smoothing_counter = 0     # peak bits counted so far (to check that buffer is full)
        self.peaks_detected_smoothed = 0    # Moving average filtered value of previous "window_length" peak detected bits
        self.burst_center_index = 0
        self.last_R_peak = 0
        self.starting_time = 0
        self.overflowed = False


        #Kept states and buffers for filtering and peak finding - minimise the amount of vectors here!
        self.peak_smoothing_buffer = np.zeros(1)
        self.filter_warmup_buffer = np.zeros(1)
        self.QRS_analysis_buffer = np.zeros(1)


    def receive_settings(self):
        reset_flag = 0

        try:
            packet = self.settingsQueue.get(block=False)

            if (self.EMG_level != packet[0]):
                self.EMG_level = packet[0]
                reset_flag = 1

            if (self.ECG_level != packet[1]):
                self.ECG_level = packet[1]
                reset_flag = 1

            self.peak_burst_threshold = packet[2]

            if reset_flag:
                self.reset_filters()
        except:
            pass
        
        try:
            clear = self.clearQueue.get(block=False)
            if clear:
                self.clear_flag = True
                print("clear_flag set")
            else:
                pass
        except:
            pass



    def start_Process(self):
        if self.process == None:
            self.process_isRun = True
            self.process = Process(target=self.backgroundThread)
            self.process.start()


    def backgroundThread(self):    # retrieve data

        port = 0
        portinfo = list_ports.grep("Serial")
        settings_ticks = 0

        #************************ Serial Port Init ***************************
        #     Find USB to serial device, prompt user if not found.

        for found_port in portinfo:
            port = found_port.device

        try:
            ser = serial.Serial(baudrate=self.baud, timeout=1)
            ser.port = port
            try:
                ser.open()
            except:
                ser.open()
        except:
            print("No serial!")

        if (isinstance(port, str)):
            self.serial_isOpen = True

        rl = ReadLine(ser)

        sleep(0.01)  # give some buffer time for retrieving data
        while (self.process_isRun):
            
            if self.clear_flag:
                self.clear_dataThread()
                self.clear_flag = False
                while(ser.in_waiting):
                    line = rl.readline()
                
            while(ser.in_waiting):
                try:
                #Read and break up arduino output - same form as EMG
                    line = rl.readline()
                    string = line.decode()
                    split_string = string.split("\t")
                    length = string.count('\t') + 1
                    settings_ticks += 1

                    #save EMG output, clamp to 2V otherwise return 0
                    if (abs(float(split_string[length - 2])) < 2.3):
                        self.EMG = float(split_string[length-2])
                    else:
                        self.EMG = 0


                    # Check for a long list of zeros (unit off). State machine will detect unit
                    # off after 100ms of zeros, and check for a signal. When the unit boots,
                    # and returns a value, the filters clear and restart.
                    if ((self.EMG == 0) & (self.unit_off == False)):
                        self.consecutive_zeros +- 1
                        if (self.consecutive_zeros > 100):
                            self.unit_off = True
                    else:
                        self.consecutive_zeros=0

                    if ((self.unit_off == True) & (self.EMG != 0)):
                        self.unit_off == False
                        self.clear_and_reset()

                    if (len(self.QRS_analysis_buffer) < self.QRS_analysis_buffer_length):
                        self.QRS_analysis_buffer = np.append(self.QRS_analysis_buffer, self.EMG)
                    else:
                        self.QRS_analysis_buffer = np.roll(self.QRS_analysis_buffer,-1)
                        self.QRS_analysis_buffer[-1] = self.EMG

                    # self.sample_count += 1

                    #rectify EMG, perform the R-R identification and calculations
                    self.EMG_rect = abs(self.EMG)
                    # self.x = self.sample_count / 1000
                    self.x = float(split_string[length - 1]) / 1e6 - self.starting_time + (self.wrap_counter * 4294.967295) 
                    # print(float(split_string[length - 1]) / 1e6)
                    # print(self.starting_time)
                    # print(self.x)
                    
                    
                    if (((float(split_string[length - 1]) / 1e6) < self.starting_time)
                        and self.overflowed == False):
                        print("Overflow detected!")
                        print("Starting time" + str(self.starting_time))
                        self.wrap_counter += 1
                        self.overflowed = True
                    
                    if (self.overflowed == True and
                        ((float(split_string[length - 1]) / 1e6) > self.starting_time)):
                        self.overflowed = False
                    
                        # if (self.wrap_counter == 0):
                        #     self.starting_time = 4294.967295 - self.starting_time
                        #     print("Wrap count = 0")
                        #     print("New Starting time" + str(self.starting_time))
                        # else:
                        #     self.starting_time += 4293.967295
                        #     print("Wrap count = 1")
                        #     print("New Starting time" + str(self.starting_time))
                        # self.wrap_counter += 1
                    
                    if (self.time_set == False):
                        self.starting_time = self.x
                        print(self.starting_time)
                        self.time_set = True
                        self.x = 0
                        

                    self.detect_peaks()
                    self.smooth_peaks()
                    if (self.x > 0.5):
                        self.index_R_wave()

                    self.dataQueue.put([self.x,
                                        self.EMG,
                                        self.peaks_detected_smoothed,
                                        self.last_R_peak
                                        ],
                                       block=True,
                                       timeout=1)
                    if (settings_ticks >= 50):                  
                        self.receive_settings()
                        settings_ticks = 0
                    
                except:
                    traceback.print_exc()
                    # pass


    def detect_peaks(self):

        """ Run peak-detection algorithm over EMG stream
        Saves peak signal to an EMG_peaks vector """
        if (len(self.filter_warmup_buffer) < self.filter_lag):
            self.filter_warmup_buffer = np.append(self.filter_warmup_buffer, self.EMG_rect)
        elif ((len(self.filter_warmup_buffer) >= self.filter_lag) & (~self.filters_started)):
            self.filter = real_time_peak_detection(self.filter_warmup_buffer, self.filter_lag, self.filter_threshold, self.filter_influence)
            self.filters_started = True
        elif (self.filters_started):
            self.peak_detected = self.filter.thresholding_algo(self.EMG_rect)
        else:
            self.peak_detected = 0


    def smooth_peaks(self):
        """ Moving average window over peak signal to mitigate effect of noise
        saves and EMG_peaks_smth vector"""


        self.peak_sum += self.peak_detected

        if (self.peak_smoothing_counter > self.peak_smoothing_window_length):
            self.peak_sum -= self.peak_smoothing_buffer[0]
            self.peak_smoothing_buffer = np.roll(self.peak_smoothing_buffer, -1)
            self.peak_smoothing_buffer[-1] = self.peak_detected

        else:
            self.peak_smoothing_buffer = np.append(self.peak_smoothing_buffer, self.peak_detected)

        self.peaks_detected_smoothed = self.peak_sum / self.peak_smoothing_window_length
        if self.peaks_detected_smoothed > 0.95:
            self.reset_filters()
        #protect form weird start condition
        if (self.peaks_detected_smoothed > 1):
            self.peaks_detected_smoothed = 0

        self.peak_smoothing_counter += 1


    def index_R_wave(self):
        """ State machine which detects a "spike" and saves a stamp for it's
        center point to a burst_center_index vector"""
        if (self.peaks_detected_smoothed > self.peak_burst_threshold):
            self.rising_debounce_counter += 1

            if(self.edge == 'falling'):
                self.falling_debounce_counter = 0

            if (self.rising_debounce_counter == self.debounce_cycles):
                self.edge = 'rising'
                self.pulse_start = self.x


        else:
            self.falling_debounce_counter += 1

            if(self.edge == 'rising'):
                self.rising_debounce_counter = 0

            if (self.falling_debounce_counter == self.debounce_cycles):

                self.edge = 'falling'
                self.pulse_end = self.x

                # save time index of center of pulse
                self.burst_center_index = ((self.pulse_end + self.pulse_start) / 2) - (self.peak_smoothing_window_length / 2000)
                if (self.burst_center_index != 0):
                    self.resolve_R_wave()

                # if (len(self.last_R_peak) > 3):
                    # self.check_beat()


    # @profile
    def resolve_R_wave(self, mode="standard", start=0, stop=0):
        """
        """

        # Set up QRS slice depending on condition - if normal operation, then
        # slice the set QRS duration. If searching for a missed or double beat
        # then search in specially defined indices
        if (mode == "standard"):
            half_cycle = self.QRS_cycle_duration / 2
            start_time = self.burst_center_index - half_cycle
            stop_time = self.burst_center_index + half_cycle

        else:
            duration = stop - start
            half_cycle = duration / 2
            start_time = start
            stop_time = stop

        # eprint("x =")
        # eprint(self.x)
        # sys.stdout.flush()

        start_index = -int((self.x - start_time) * 1000)
        stop_index = -int((self.x - stop_time) * 1000)

        # eprint(start_index)
        # eprint(stop_index)

        QRS_slice = np.ravel(self.QRS_analysis_buffer[start_index:stop_index])

        # As long as we're not at the very start of the recording, find the
        # max and min gradients in the slice, and find the zero crossing between
        # them to indicate the R-peak's location
        if (self.x > 0.100):
            """Identify max and min gradients, signifying sides of R peak
            Find gradient zero crossing to indicate peak"""
            try:
                cycle_gradients = np.gradient(QRS_slice)
            except ValueError:
                return
            smoothing_delay = self.gradient_smoothing_samples / 2
            smoothed_gradients = rolling_mean(cycle_gradients, size=self.gradient_smoothing_samples)
            max_gradient_index = int(np.argmax(smoothed_gradients) - smoothing_delay)
            min_gradient_index = int(np.argmin(smoothed_gradients) - smoothing_delay)

            #if leads are on backwards, switch max and min
            if (max_gradient_index > min_gradient_index):
                temp = max_gradient_index
                max_gradient_index = min_gradient_index
                min_gradient_index = temp

            #Check for spurious noise peaks (these are short, therefore max - min gradients will be less than a few milliseconds)
            if ((min_gradient_index - max_gradient_index) > 2):
                try:
                    local_R_index = np.where(np.diff(np.signbit(cycle_gradients[max_gradient_index:min_gradient_index+1])))[0][0] + max_gradient_index
                except IndexError: #no zero crossing - bad news, or smoothing period is too long
                    local_R_index = 0
            else:
                local_R_index = 0


            localmax = start_time + local_R_index / 1000
            # print(localmax, flush=True)
            # Use newly calculated index - either insert, replace spurious pair,
            # or simply append
            # if (mode == "missed"):
            #     scipy_peaks = find_peaks(QRS_slice, self.ECG_level / 1.4, distance=400, width=8)[0]

            #     for peak in range(len(scipy_peaks)):
            #         self.last_R_peak = np.insert(self.last_R_peak,
            #                                  -1,
            #                                  scipy_peaks[peak] / 1000 + start_time)
            #         self.intervals = np.insert(self.intervals,
            #                                    -1,
            #                                    self.last_R_peak[-2] - self.last_R_peak[-3])

            #     self.intervals[-1] = self.last_R_peak[-1] - self.last_R_peak[-2]


            # if (mode == "double"):

            #     #Get rid of last two spurious beats, replace
            #     self.last_R_peak = np.delete(self.last_R_peak,[-1, -2])
            #     self.last_R_peak = np.append(self.last_R_peak, localmax)

            #     #remove last two intervals, replace
            #     self.intervals = np.delete(self.intervals,[-1, -2])
            #     self.intervals = np.append(self.intervals,
            #                                self.last_R_peak[-1] - self.last_R_peak[-2])

            if (mode == "standard"):
                if (local_R_index):
                   self.last_R_peak = localmax
                   # self.last_interval = np.append(self.intervals, self.last_R_peak[-1] - self.last_R_peak[-2])


            # if len(self.last_R_peak) < 5:
            #     last_R_peak_length = len(self.last_R_peak)
            #     # intervals_length = len(self.intervals)
            #     if (last_R_peak_length > intervals_length):
            #         # self.intervals = np.append(self.intervals, 0)
            #     if (intervals_length > last_R_peak_length):
            #         self.last_R_peak = np.append(self.last_R_peak, 0)

        else:
            self.last_R_peak = 0
            # self.intervals = np.append(self.intervals, self.last_R_peak[-1] - self.last_R_peak[-2])


    # @profile
    # def check_beat(self):
    #     """Check if interval has increased or decreased beyond some bounds
    #     between beats, if so, assume a beat has been missed or double counted.
    #     For a double-beat (Short interval), run gradient checker over a longer
    #     interval to pick out the actual R peak.
    #     For a missed beat, either insert a null value or scan area between beats for
    #     with gradient checker."""
    #     interval_ratio = self.intervals[-1]/self.intervals[-2]



    #     if (interval_ratio < 0.5):
    #         start_time = self.last_R_peak[-2] - self.QRS_cycle_duration
    #         stop_time = self.last_R_peak[-1] + self.QRS_cycle_duration
    #         self.resolve_R_wave("double", start_time, stop_time)


    #     elif (interval_ratio > 1.8):
    #         self.missed_type = "single"
    #         start_time = self.last_R_peak[-2] + self.QRS_cycle_duration
    #         stop_time = self.last_R_peak[-1] - self.QRS_cycle_duration
    #         self.resolve_R_wave("missed", start_time, stop_time)



    def clear_dataThread(self):

        # Clear signal chain
        self.pulse_start = 0
        self.pulse_end = 0
        self.peak_sum = 0
        self.EMG = 0                        # raw EMG sample
        self.EMG_rect = 0                   # rectified EMG sample
        self.x = 0                          # current time in s
        self.peak_detected = 0              # peak detected, 1 or 0
        self.peak_smoothing_counter = 0     # peak bits counted so far (to check that buffer is full)
        self.peaks_detected_smoothed = 0    # Moving average filtered value of previous "window_length" peak detected bits
        self.burst_center_index = 0
        self.last_R_peak = 0
        self.starting_time = 0
        self.time_set = False
        self.peak_smoothing_buffer = np.zeros(1)
        self.QRS_analysis_buffer = np.zeros(1)


    def reset_filters(self):
        """Reset peak finding algo if readings are whack"""
        ratio = self.ECG_level / self.EMG_level
        self.filter_lag = int(500 - 10*ratio)
        self.filter_threshold = int(3.5 + 0.375*ratio)
        self.filter = real_time_peak_detection([0] * self.filter_lag, self.filter_lag, self.filter_threshold, self.filter_influence)
        # print("Filters reset")

    def close(self):
        self.isrun = False
        self.process.terminate()
        ser = serial.Serial()
        portinfo = list_ports.grep("Serial")
        for found_port in portinfo:
            port = found_port.device
        ser.port = port
        try:
            ser.open()
        except:
            ser.close()

        print('Disconnected...')
        # df = pd.DataFrame(self.csvData)
        # df.to_csv('/home/rikisenia/Desktop/data.csv')

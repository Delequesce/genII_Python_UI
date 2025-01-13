from matplotlib.figure import Figure
from RingBuffer import *
import tkinter as tk
import tkinter.ttk as ttk
import numpy as np
import time, csv, serial, sys, glob
import struct
import serial.tools.list_ports
from tkinter.filedialog import askopenfilename, asksaveasfilename
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg,  
NavigationToolbar2Tk)

class GenII_Interface:

    TEMPARRAYSIZE = 60

    def __init__(self, root):

        self.root = root
        self.deviceStatus = tk.StringVar()
        self.deviceStatus.set("No Devices Connected")
        self.eqcStatus = tk.StringVar()
        self.eqcStatus.set("EQC has not been run today")
        self.calibStatus = tk.StringVar()
        self.calibStatus.set("Calibration has not been run today")
        self.frameList = []
        self.frame_ctr = -1
        self.plot1 = None
        self.SerialObj = None

        # Variables for labels and entries
        self.str_filePath = tk.StringVar()
        self.str_runT = tk.StringVar(value = "30")
        self.str_incTemp = tk.StringVar(value = "37")
        self.str_currentTemp = tk.StringVar(value= "N/A")
        self.str_heaterStatus = tk.StringVar(value="Heater Off")
        self.str_tpeak_est = []
        self.str_deltaEps_est = []
        for i in range(4):
            self.str_tpeak_est.append(tk.StringVar(value = "0 min")) 
            self.str_deltaEps_est.append(tk.StringVar(value = "0"))

        #self.str_tpeak_est_conf = tk.StringVar(value = "0%")
        #self.str_deltaEps_est_conf = tk.StringVar(value = "0%")
        self.timerVar = tk.StringVar()
        self.timerVar.set('')

        # Frames
        self.frameList.append(self.createTopWindow(root)) # Create a top window element for root instance
        self.frameList.append(self.createParamWindow(root))
        self.frameList.append(self.creatTestRunWindow(root))
        self.frameList.append(self.createResultsWindow(root))

        # Flags
        self.isHeating = 0
        self.isMeasuring = 0
        self.clickedFlag = 0
        self.dontInterrupt = False

        # Other
        self.exit_code = bytearray([0, 1, 2, 3])
        self.countData = []
        self.channelList = []
        self.channelBin = 0
        self.DataMat = []
        self.oldDataVec = [0, 0, 0, 0, 0, 0, 0, 0]
        self.output_file = None
        self.csv_writer = None
        self.tempArray = RingBuffer(self.TEMPARRAYSIZE)
        self.tempStabilityThreshold = 0.5
        
        # Initialize first frame
        self.forward()

    def createTopWindow(self, root):
        #root.minsize(root.winfo_width(), root.winfo_height())
        # Get Height of Screen
        #width = int(root.winfo_screenwidth()/4)
        #height = int(root.winfo_screenheight()*0.75)
        width = 480
        height = 272
        #x_coordinate = 2000
        #y_coordinate = 300
        #root.geometry("{}x{}+{}+{}".format(width, height, x_coordinate, y_coordinate))
        root.title("MIA Generation II Interface")
        style = ttk.Style(root)
        root.tk.call('source', 'Azure-ttk-theme/azure.tcl') # Imports TCL file for styling
        style.theme_use('azure')
        style.configure("AccentButton", foreground = 'white')

        # Frames and canvases
        fr_main = ttk.Frame(root)
        cv_statusLights = tk.Canvas(fr_main, width = 50, height = 100)
        #fr_main.pack()
        
        # Buttons
        btn_connect = ttk.Button(fr_main, text = "Connect to Device", style = "AccentButton", command = self.connectToDevice)
        btn_EQC = ttk.Button(fr_main, text = "Perform Daily EQC", style = "AccentButton", command = self.performEQC)
        btn_calib = ttk.Button(fr_main, text = "Perform Calibration", style = "AccentButton", command = self.performCalibration)
        btn_newTest = ttk.Button(fr_main, text = "Setup New Test", style = "AccentButton", command = self.forward)
        btn_connect.grid(row = 0, column = 0, pady = 5)
        btn_EQC.grid(row = 1, column = 0, pady = 5)
        btn_calib.grid(row = 2, column = 0, pady = 5)
        btn_newTest.grid(row = 3, column = 0, pady = 5)

        # Status Lights
        root.update()
        cButton_y = btn_connect.winfo_y()
        cButton_height = btn_connect.winfo_height()
        eqcButton_y = btn_EQC.winfo_y()
        cButton_height = btn_connect.winfo_height()
        offset = 20
        light_size = int(cButton_height/2); 
        light_connect = cv_statusLights.create_oval(10, cButton_y + 5, 10 + light_size, cButton_y + light_size+5)
        light_EQC = cv_statusLights.create_oval(10, eqcButton_y + offset, 10 + light_size, eqcButton_y+light_size + offset)
        cv_statusLights.grid(row = 0, column = 1, rowspan = 2)
        cv_statusLights.itemconfig(light_connect, fill="red")
        cv_statusLights.itemconfig(light_EQC, fill="red")

        # Labels
        lbl_deviceStatus = ttk.Label(fr_main, textvariable=self.deviceStatus)
        lbl_eqcStatus = ttk.Label(fr_main, textvariable = self.eqcStatus)
        lbl_calibStatus = ttk.Label(fr_main, textvariable = self.calibStatus)
        lbl_eqcTimer = ttk.Label(fr_main, textvariable=self.timerVar)
        lbl_deviceStatus.grid(row = 0, column = 2, padx = 0, pady = 5)
        lbl_eqcStatus.grid(row = 1, column = 2, padx = 0, pady = 5)
        lbl_eqcTimer.grid(row = 1, column = 3)
        lbl_calibStatus.grid(row = 2, column = 2, padx = 0, pady = 5)
        

        # Assign variables to class
        self.cv_statusLights = cv_statusLights
        self.light_connect = light_connect
        self.light_EQC = light_EQC

        return fr_main

    def createParamWindow(self, root):
        # Frames and canvases
        fr_params = ttk.Frame(root);
        fr_channels = ttk.Frame(fr_params)
        #fr_params.pack()
        fr_channels.grid(row = 2, column = 1)
        fr_filePath = ttk.Frame(fr_params)
        fr_filePath.grid(row = 3, column = 1, columnspan = 2)

        # Labels
        lbl_runTime = ttk.Label(fr_params, text = "Run Time (sec)")
        lbl_incTemp = ttk.Label(fr_params, text = "Incubation\nTemperature (C)")
        lbl_channels = ttk.Label(fr_params, text = "Active Channels")
        lbl_fpath = ttk.Label(fr_params, text= "Filepath")
        lbl_runTime.grid(row = 0, column = 0, padx = 0, pady = 5)
        lbl_incTemp.grid(row = 1, column = 0, padx = 0, pady = 5)
        lbl_channels.grid(row = 2, column = 0, padx = 0, pady = 5)
        lbl_fpath.grid(row = 3, column = 0, padx = 0, pady = 5)

        # Entry Boxes
        
        ent_runTime = ttk.Entry(fr_params, textvariable= self.str_runT, width = 5)
        ent_incTemp = ttk.Entry(fr_params, textvariable= self.str_incTemp, width = 5)
        ent_filePath = ttk.Entry(fr_filePath, textvariable= self.str_filePath, width = 30)
        ent_runTime.grid(row = 0, column = 1, padx = 0, pady = 0)
        ent_incTemp.grid(row = 1, column = 1, padx = 0, pady = 0)
        ent_filePath.grid(row = 0, column = 1, columnspan = 2, pady = 0)
        #ent_filePath.bind("<1>", self.openSaveDialog) # Will launch when entry box is left-clicked

        # Buttons
        btn_next = ttk.Button(fr_params, text = "Continue", style = "AccentButton", command = self.forward)
        btn_back = ttk.Button(fr_params, text = "Back", style = "AccentButton", command = self.previous)
        btn_fileEdit = ttk.Button(fr_filePath, text = "...", style = "AccentButton", command = self.openSaveDialog)
        btn_next.grid(row = 0, column = 2, pady = 5)
        btn_back.grid(row = 1, column = 2, pady = 5)
        btn_fileEdit.grid(row = 0, column = 0) # Should be just to the left of the filepath text box

        # Free run checkbox
        self.freeRunVar = tk.IntVar(value = 0)
        ttk.Checkbutton(fr_params, text = "Free Run",variable=self.freeRunVar, onvalue=1, offvalue=0).grid(row = 2, column = 2)


        self.channelVars = []
        for i in range(4):
            tempVar = tk.IntVar(value = 1)
            self.channelVars.append(tempVar)
            ttk.Checkbutton(fr_channels, text=f"Ch{i+1}",variable=tempVar, 
                onvalue=1, offvalue=0, command=lambda: self.root.after(200, self.channelAdjust)).grid(row = int(i/2), column = i % 2, padx = 5, pady = 1)

        return fr_params
    
    def creatTestRunWindow(self, root):
        self.fr_testWindow = ttk.Frame(root)
        self.fr_leftInfo = ttk.Frame(self.fr_testWindow)
        self.fr_vis = ttk.Frame(self.fr_testWindow)

        # Button Text Arrays
        self.heatBtnText = ["Start Heating", "Stop Heating"]
        self.measBtnText = ["Begin Measurement", "Stop Measurement"]
        self.heaterStatus = ["Heater Off", "Heating System", "Stable Temperature Achieved"]

        # Components
        self.heatBtn_text = tk.StringVar(value = self.heatBtnText[0])
        btn_startHeating = ttk.Button(self.fr_leftInfo, textvariable = self.heatBtn_text, style = "AccentButton", command = self.startHeating)
        self.btn_text = tk.StringVar(value = self.measBtnText[0])
        btn_beginMeasurement = ttk.Button(self.fr_leftInfo, textvariable = self.btn_text, style = "AccentButton", command = self.startStop)
        btn_loadData = ttk.Button(self.fr_leftInfo, text = "Load Data", style = "AccentButton", command = self.loadAndPlotData)
        btn_back  = ttk.Button(self.fr_leftInfo, text = "Back", style = "AccentButton", command = self.previous)
        btn_results = ttk.Button(self.fr_leftInfo, text = "Results", style = "AccentButton", command = self.forward)

        lbl_tempLabel = ttk.Label(self.fr_leftInfo, text="Current Temp (C):")
        lbl_heaterStatus = ttk.Label(self.fr_leftInfo, textvariable = self.str_heaterStatus)
        lbl_currentTemp = ttk.Label(self.fr_leftInfo, textvariable=self.str_currentTemp)
        
        # Layout Grid
        self.fr_leftInfo.grid(row = 0, column = 0)
        btn_startHeating.grid(row = 0, column = 0, columnspan=2, pady = 2)
        lbl_heaterStatus.grid(row = 1, column = 0, columnspan= 2, pady = 2)
        lbl_tempLabel.grid(row = 2, column = 0, pady = 2)
        lbl_currentTemp.grid(row = 2, column = 1, pady = 2)
        btn_beginMeasurement.grid(row = 3, column = 0, columnspan=2, pady=2)
        btn_loadData.grid(row=4, column = 0, columnspan=2, pady=2)
        btn_back.grid(row = 5, column = 0, columnspan=2, pady=2)
        btn_results.grid(row = 6, column = 0, columnspan=2, pady = 2)

        # Plot
        self.fig = Figure(figsize = (3, 3), dpi = 100)
        plot1 = self.fig.add_axes([0.25, 0.35, 0.7, 0.556], autoscale_on = True)
        plot1.set_xlabel("Time (s)")
        plot1.set_ylabel("Capacitance (pF)")
        self.plot1 = plot1

        # Visual Frame
        self.canvas = FigureCanvasTkAgg(self.fig, master = self.fr_vis)
        
        # Bind key press
        self.canvas.get_tk_widget().bind("<Button-1>", self.grow_shrink_canvas)
        self.canvas.get_tk_widget().pack(expand=True, fill=tk.BOTH)

        self.canvas.draw()
        self.fr_vis.grid(row = 0, column = 1, rowspan=2, columnspan=3)

        return self.fr_testWindow
    

    def createResultsWindow(self, root):
        fr_resultsWindow = ttk.Frame(root)
        fr_resultsParams = ttk.LabelFrame(fr_resultsWindow, text = "TraumaChek Output Variables")
        fr_resultsParams.grid(row=0, column=0, columnspan=3)

        lbl_chan1 = ttk.Label(fr_resultsParams, text = "Ch 1")
        lbl_chan2 = ttk.Label(fr_resultsParams, text = "Ch 2")
        lbl_chan3 = ttk.Label(fr_resultsParams, text = "Ch 3")
        lbl_chan4 = ttk.Label(fr_resultsParams, text = "Ch 4")
        lbl_tpeak = ttk.Label(fr_resultsParams, text = "Tpeak")
        lbl_deltaEps = ttk.Label(fr_resultsParams, text = u'{x}{y}max'.format(x = '\u0394', y = '\u03B5'))
        lbl_tpeak_est = []
        lbl_deltaEps_est = []
        for x in self.str_tpeak_est:
            lbl_tpeak_est.append(ttk.Label(fr_resultsParams, textvariable=x))
        
        for x in self.str_deltaEps_est:
            lbl_deltaEps_est.append(ttk.Label(fr_resultsParams, textvariable=x))

        #lbl_tpeak_est_conf = ttk.Label(fr_resultsParams, textvariable=self.str_tpeak_est_conf)
        #lbl_deltaEps_est_conf = ttk.Label(fr_resultsParams, textvariable=self.str_deltaEps_est_conf)

        lbl_chan1.grid(row = 0, column = 1, padx = 5, pady = 5)
        lbl_chan2.grid(row = 0, column = 2, padx = 5, pady = 5)
        lbl_chan3.grid(row = 0, column = 3, padx = 5, pady = 5)
        lbl_chan4.grid(row = 0, column = 4, padx = 5, pady = 5)
        lbl_tpeak.grid(row = 1, column = 0, padx = 5, pady = 5)
        lbl_deltaEps.grid(row = 2, column = 0, padx = 5, pady = 5)

        i = 1
        for x in lbl_tpeak_est:
            x.grid(row = 1, column = i, padx = 5, pady = 5)
            i+=1
        
        i = 1
        for x in lbl_deltaEps_est:
            x.grid(row = 2, column = i, padx = 5, pady = 5)
            i+=1

        #lbl_tpeak_est_conf.grid(row = 0, column = 3, padx = 5, pady = 5)
        #lbl_deltaEps_est_conf.grid(row = 1, column = 3, padx = 5, pady = 5)

        btn_back  = ttk.Button(fr_resultsWindow, text = "Back", style = "AccentButton", command = self.previous)
        btn_back.grid(row=1, column = 0, columnspan=1)

        return fr_resultsWindow


    def grow_shrink_canvas(self, event):
        #print("Canvas Clicked")
        if self.clickedFlag:
            self.fr_leftInfo.grid(row = 0, column = 0)
            #self.fig.set_figwidth(3)
            self.canvas.get_tk_widget().configure(width = 300)
            self.plot1.set_position([0.25, 0.35, 0.7, 0.556])
            self.canvas.draw()
        else:
            # Remove other elements from grid and expand canvas
            self.fr_leftInfo.grid_remove()
            #self.fr_vis.grid_remove()
            #self.fr_vis.pack_forget()
            #self.fig.set_figwidth(4)
            self.canvas.get_tk_widget().configure(width = 480)
            self.plot1.set_position([0.15, 0.35, 0.8, 0.556])
            self.canvas.draw()
            #self.fr_vis.pack()


        # Toggle Flag
        self.clickedFlag^=1
         
        return

    def forward(self):
        for fr in self.frameList:
            fr.grid_forget()
        self.frame_ctr += 1
        self.frameList[self.frame_ctr].grid(row = 0, column = 0)

    def previous(self):
        for fr in self.frameList:
            fr.grid_forget()
        self.frame_ctr -= 1
        self.frameList[self.frame_ctr].grid(row = 0, column = 0)

    def openSaveDialog(self):
        saveDataFilePath = asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")])
        self.str_filePath.set(saveDataFilePath)
        return

    def loadAndPlotData(self):
        readDataFilePath = askopenfilename(defaultextension=".csv", filetypes=[("CSV Files", "*.csv")])
        self.plotData(readDataFilePath)
        return

    def startStop(self):
        self.isMeasuring^=1
        if self.isMeasuring:
            self.beginMeasurement()
        else:
            self.btn_text.set(self.measBtnText[0])
            self.cancelMeasurement()

        return

    # Button Callback Functions
    def connectToDevice(self):

#         with open('C://Users/cdeli/Desktop/TemperatureLog.csv', 'w', newline = '') as output_file:
#             csv_writer = csv.writer(output_file, delimiter = ',', quoting = csv.QUOTE_NONNUMERIC, quotechar='|')
#             csv_writer.writerow(["Temperature"])

        ret = 0

        windows = False
        if windows:
            list = serial.tools.list_ports.comports()
            connected = []
            print("Connected COM ports:") 
            if len(list) == 1:
                genII_port = list[0].device
            for element in list:
                connected.append(element.device)
                print(str(element.device) + ": " + element.description)
            if element.manufacturer == 'SEGGER':
                genII_port = element.device
            if sys.platform.startswith('win'):
                ports = ['COM%s' % (i+1) for i in range(256)]
            elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
                ports = glob.glob('/dev/tty[A-Za-z]*')
            elif sys.platform.startswith('darwin'):
                ports = glob.glob('/dev/tty.*')
            else:
                raise EnvironmentError('Unsupported platform')
        else:
            #genII_port = "/dev/ttyS0"
            genII_port = "/dev/ttyACM0"
        
        #port = input("Enter the requested port number to connect")
        SerialObj = serial.Serial(baudrate = 115200, timeout = 5) # Port is immediately opened upon creation.         
        SerialObj.port = genII_port
        SerialObj.bytesize = 8
        SerialObj.partiy = 'N'
        SerialObj.stopbits = 1

        try:
            print("Attempting connection to %s" % str(genII_port))
            #SerialObj = serial.Serial('/dev/ttyS3') # Port is immediately opened upon creation. 
            SerialObj.open()
            print("Port Succesfully Opened")
            # Save open serial object for future communications
            self.SerialObj = SerialObj
        except Exception as e:
            self.deviceStatus.set("Failed to Access COM Port")
            print(e)
            return

        # Wakeup and Check Connection Status Command. Function is blocking until timeout
        self.cv_statusLights.itemconfig(self.light_connect, fill="yellow")
        SerialObj.reset_input_buffer()
        SerialObj.reset_output_buffer()
        if not self.deviceAck(2, 3, b'C\n'):
            print("Failed to Connect to Device")
            self.cv_statusLights.itemconfig(self.light_connect, fill="red")
            return 

        # Update UI with connection status
        self.deviceStatus.set("Device Successfully Connected")
        self.cv_statusLights.itemconfig(self.light_connect, fill="green")

        # Flush Buffers to await new temperature data 
        self.SerialObj.reset_input_buffer()
        self.SerialObj.reset_output_buffer()

        # Call periodic read
        self.SerialObj.timeout = 0 # No timeout
        self.processInputs()
    

    def performCalibration(self):
        try: 
            self.SerialObj.write(b'B\n')
        except: 
            self.calibStatus.set("Failed to Write to COM Port")
            return
        
        self.calibStatus.set("Waiting for Calibration to complete")

    def finishCalibration(self, dataVec):

        #if Zfb_real == 0:
        #   self.eqcStatus.set("Calibration Failed")
        #    return
        printString = """New Calibration Values:
              Channel 1: %s + %s j
              Channel 2: %s + %s j
              Channel 3: %s + %s j
              Channel 4: %s + %s j"""
        
        print(printString % (dataVec[0], dataVec[1], dataVec[2], dataVec[3], dataVec[4], dataVec[5], dataVec[6], dataVec[7]))
    
        self.eqcStatus.set("Calibration Successful")
        return


    def performEQC(self):
        try: 
           self.SerialObj.write(b'Q\n')
        except: 
           self.eqcStatus.set("Failed to Write to COM Port")
           return
        self.cv_statusLights.itemconfig(self.light_EQC, fill="yellow")
        self.eqcStatus.set("EQC Running:")
        print("Starting Countdown")
        self.startTimer(30)
        return
    
    def startTimer(self, time):
        if time > 1:
            # Set initial time
            self.timerVar.set(str(time))
            # Call method every second until end
            self.root.after(1000, lambda: self.startTimer(time-1))
            return
        
        print("Countdown Complete")
        self.timerVar.set('')
    
    def finishEQC(self, dataVec):
        rmsd_C = float(dataVec[0])
        rmsd_G = float(dataVec[1])
        noise_C = float(dataVec[2])
        noise_G = float(dataVec[3])

        print("EQC RMSD Errors:\n C = %0.3f\n G = %0.3f" % (rmsd_C, rmsd_G))
        print("EQC Noise:\n C = %0.3f\n G = %0.3f" % (noise_C, noise_G))
        eqcFail = False
        if rmsd_C > 5 or rmsd_G > 5:
            self.cv_statusLights.itemconfig(self.light_EQC, fill="red")
            self.eqcStatus.set("EQC Failed: Accuracy")
            eqcFail = True
        
        if noise_C > 0.5 or noise_G > 0.1:
            self.cv_statusLights.itemconfig(self.light_EQC, fill="red")
            self.eqcStatus.set("EQC Failed: Noise")
            eqcFail = True
        
        if eqcFail:
            return
        

        self.cv_statusLights.itemconfig(self.light_EQC, fill="green")
        self.eqcStatus.set("EQC Passed")
        return
    
    def startHeating(self):

        # Toggle Heater State and wait for response
        if not self.deviceAck(10, 1, b'H\n'):
            self.str_heaterStatus.set("Heater Error")
            return
        
        # Status is Idle -> Heating -> Stable
        stat = self.str_heaterStatus.get()
        if stat == self.heaterStatus[0]: #Idle, Start Heating
            self.str_heaterStatus.set(self.heaterStatus[1])
            self.heatBtn_text.set(self.heatBtnText[1])
        else: # Stop Heating
            self.str_heaterStatus.set(self.heaterStatus[0])
            self.heatBtn_text.set(self.heatBtnText[0])
            self.tempArray = RingBuffer(self.TEMPARRAYSIZE) # Re-initialize temperature array as empty Ring Buffer
        
        self.dontInterrupt = False
        return

    # Function that checks for 'K' response from MCU for a variety of reasons
    def deviceAck(self, N_Count, N_Attempt, writeData):
        self.SerialObj.timeout = 1
        self.dontInterrupt = True
        acked = False
        attemptCounter = 0
        while attemptCounter < N_Attempt:
            count = 0
            while count < N_Count:
                try: 
                    self.SerialObj.write(writeData)
                except: 
                    print("Write Error to COM Port")
                
                acked = (self.SerialObj.read(1) == b'K')
                if acked:
                    self.dontInterrupt = False
                    return 1

                count+=1

            attemptCounter+=1

        self.dontInterrupt = False
        return 0
    
    # General handler function for serial comms
    # Basically, it reads a character at a time and tries to match to controlCharacters.
    # After X reads, it pauses to let other things run.
    def processInputs(self):
        if self.dontInterrupt:
            self.io_task = self.root.after(IOSLEEPTIME, self.processInputs)
            return
        start_time = time.perf_counter()
        self.SerialObj.timeout = 0.5
        for i in range(self.SerialObj.in_waiting):
            # Read a single character from buffer
            controlChar = self.SerialObj.read(1)
            if controlChar == b'E': # Error Code
                line = self.SerialObj.readline()
                try:
                    decoded_line = line.decode(encoding='ascii')
                except Exception as e:
                    print(e);
                    self.io_task = self.root.after(ERR_IOSLEEPTIME, self.processInputs) # Schedule new read in 500 msec
                    return
                print(decoded_line[0:-1])
            elif controlChar == b'D': # Data (C and G)
                line = self.SerialObj.readline()
                try:
                    decoded_line = line.decode(encoding='ascii')
                except Exception as e:
                    print(e)
                    print(line)
                    self.io_task = self.root.after(ERR_IOSLEEPTIME, self.processInputs)
                    return
                #print(decoded_line);
                dataVec = decoded_line[0:-1].split('!')
                if len(dataVec) < 8:
                    dataVec = self.oldDataVec

                self.countData.append(len(self.countData) + 1)
                self.printAndStore(dataVec)
                self.oldDataVec = dataVec

            elif controlChar == b'C': # Calibration return values
                line = self.SerialObj.readline().decode(encoding='ascii', errors = 'ignore')
                dataVec = line[0:-1].split('!')
                self.finishCalibration(dataVec)
            elif controlChar == b'X': # Measurement finish
                self.finishTest()
            elif controlChar == b'Q':
                line = self.SerialObj.readline()
                try:
                    decoded_line = line.decode(encoding='ascii')
                except Exception as e:
                    print(e)
                    print(line)
                    self.io_task = self.root.after(ERR_IOSLEEPTIME, self.processInputs)
                    return
                #print(decoded_line);
                dataVec = decoded_line[0:-1].split('!')
                if len(dataVec) < 2:
                    print(decoded_line)
                    #print(dataVec)
                else:
                    self.finishEQC(dataVec)
            elif controlChar == b'T': # Temperature Reading
                try:
                    line = self.SerialObj.readline().decode(encoding='ascii')
                    #print(line)
                except Exception as e:
                    print(e)
                    print(line)
                    self.io_task = self.root.after(ERR_IOSLEEPTIME, self.processInputs)
                    return
                #print("Temperature: %s" % line[0:-1])
                self.str_currentTemp.set(line[0:-4]) #Increase number to reduce how many decimals are printed
                
                # Create moving average to see when temperature becomes stable (if last X measurements were within Y degrees of each other)
                if self.isHeating and len(self.tempArray.data) == self.TEMPARRAYSIZE:
                    self.tempArray.add(float(line[0:-4]))
                    if np.std(self.tempArray.data) < self.tempStabilityThreshold:
                        self.str_heaterStatus.set(self.heaterStatus[2])

            elif controlChar == b'F': # Free Data. F character tells UI to expect 512 data points 
                try:
                    self.SerialObj.timeout = 2
                    line = self.SerialObj.readline()
                    decoded_line = line.decode(encoding='utf-8')
                    dataVec = decoded_line[0:-1].split('!')
                    if not self.output_file.closed:
                        self.processFreeData(dataVec)
                except Exception as e:
                    print(e)
                    self.io_task = self.root.after(ERR_IOSLEEPTIME, self.processInputs) # Schedule new read in 500 msec
            else:
                continue

            break
        # If one of the characters was matched, break loop and move on.
        #elapsedTime = time.perf_counter() - start_time
        #print(f"Time Elapsed: {elapsedTime}")
        self.io_task = self.root.after(IOSLEEPTIME, self.processInputs) # Schedule new read in 500 msec

    # Command board to begin taking measurements and sending data    
    def beginMeasurement(self):
        invalid = 0
        self.filePath = self.str_filePath.get()
        freeRun = self.freeRunVar.get()
        self.plotRange = np.array([0, 200])

        # Cancel Any previously ongoing test on MCU End
        try: 
            self.SerialObj.timeout = 1
            self.SerialObj.write(b'X\n')
        except: 
            print("Test Cancel Failure")
        
        # Clear output file and write header
        if self.filePath:
            with open(self.filePath, 'w', newline = '') as output_file:
                csv_writer = csv.writer(output_file, delimiter = ',', quoting = csv.QUOTE_NONNUMERIC, quotechar='|')
                if freeRun:
                    csv_writer.writerow(['Ve', 'Vr'])
                else:
                    csv_writer.writerow(['Time', 'C1', 'C2', 'C3','C4','G1','G2','G3', 'G4', 'Temp'])
            # Reopen file in append mode to continuously write data
            self.output_file = open(self.filePath, 'a', newline = '')
            self.csv_writer = csv.writer(self.output_file, delimiter = ',', quoting=csv.QUOTE_NONNUMERIC)

        if freeRun:
            try: 
                self.SerialObj.timeout = 1
                self.SerialObj.write(b'F\n') # Free run
                print("Starting Free Run")
            except: 
                self.eqcStatus.set("Failed to Start test to COM Port")
            return

        # Send command to device to start measurement. Cancel reads during this process
        #tk.after_cancel(self.io_task)
        runT = self.str_runT.get()
        intrunT = int(runT)
        N_bytes_1 = len(runT)
        collectionInterval = '1'
        N_bytes_2 = len(collectionInterval)
        incTemp = self.str_incTemp.get()
        N_bytes_3 = len(incTemp)

        valTime = [1, 9999]
        valCol = [1, np.min([intrunT, 9])]
        valTemp = [25, 50]


        if intrunT > valTime[1] or intrunT < valTime[0]:
            print("Invalid Run Time. Valid Range is 1 - 9999 sec")
            invalid = 1
        
        if int(collectionInterval) > valCol[1] or int(collectionInterval) < valCol[0]:
            print("Invalid Collection Interval, must be less than Run Time and between 0 and 9")
            invalid = 1

        if int(incTemp) > valTemp[1] or int(incTemp) < valTemp[0]:
            print("Invalid Incubation Temperature. Valid range is 25 - 50 C")
            invalid = 1

        if invalid:
            # Adjust Button State and abort Test
            # To Do...
            self.btn_text.set("Begin Measurement")
            return

        # Adjust run time byte length for transmission
        for i in range(4-N_bytes_1):
            runT = "0" + runT
        self.dontInterrupt = True
        sendData = bytearray('S' + runT + collectionInterval +  incTemp + '\n', 'ascii')
        
        # Write new test params to device
        if not self.deviceAck(10, 5, sendData):
            print("Failed to Write new test parameters")
            self.cancelMeasurement()
            return 

        # Command new test
        self.dontInterrupt = False
        self.SerialObj.write(b'N\n')
        
        self.btn_text.set(self.measBtnText[1])

        # Reinitialize data vectors
        self.DataMat = np.empty((intrunT, 9))
        self.DataMat[:] = np.nan

        self.countData = []
        # Initialize plot
        self.plot1.cla()
        for i in range(4):
            self.plot1.plot([], [], 'o-', label = f"Ch {i+1}", markersize=4)

        self.lines = self.plot1.get_lines()
        self.plot1.set_xlabel("Time (s)")
        self.plot1.set_ylabel("Capacitance (pF)")
        self.plot1.legend(loc='upper left', prop={'size':6})
        self.plot1.set_xlim(-1, 30)

        i = 0
        self.channelBin = 0
        for var in self.channelVars:
            if var.get() == 1:
                self.channelList.append(i)
                self.channelBin = self.channelBin + (1 << i)
            i+=1

        # After function exits, input processing thread will continue to run and handle incoming data
        #self.io_task = tk.after(100, self.processInputs) # Schedule new read in 500 msec
        return
    

    #def storeTemps(self, line):
    #    with open('C://Users/cdeli/Desktop/TemperatureLog.csv', 'a', newline = '') as output_file:
    #        csv_writer = csv.writer(output_file, delimiter = ',', quoting = csv.QUOTE_NONNUMERIC, quotechar='|')
    #        csv_writer.writerow([float(line)])

    def printAndStore(self, dataVec):

        # Get current count
        i = self.countData[-1]

        # Process Data Vector
        CVec = []
        GVec = []

        try:
            for C, G in zip(dataVec[0::2], dataVec[1::2]):
                CVec.append(float(C[:-1]))
                GVec.append(float(G[:-1]))

        except Exception as e:
            print(e)
            for C, G in zip(self.oldDataVec[0::2], self.oldDataVec[1::2]):
                CVec.append(float(C[:-1]))
                GVec.append(float(G[:-1]))
            return

        for chan in self.channelList:
            self.DataMat[i-1, chan] = CVec[chan]
            self.DataMat[i-1, chan+4] = GVec[chan]
            l = self.lines[chan]
            l.set_xdata(self.countData)
            l.set_ydata(self.DataMat[0:i, chan])

        #smallMat = self.DataMat[~np.isnan(self.DataMat)]
        try:
            self.DataMat[i-1, -1] = self.str_currentTemp.get()
        except ValueError as e:
            print(e)

        smallMat = self.DataMat[i-1]
        self.plotRange[0] = np.min(np.append(smallMat[self.channelList], self.plotRange[0]))
        self.plotRange[1] = np.max(np.append(smallMat[self.channelList], self.plotRange[1]))

        #print(self.plotRange)

        self.plot1.set_xlim(-1, np.floor((i-1)/30 + 1) * 30)
        self.plot1.set_ylim(self.plotRange[0]-1, self.plotRange[1]+1)
        #self.plot1.set_ylim(0, 400)
        self.canvas.draw()

        if self.csv_writer:
            self.csv_writer.writerow(np.concatenate(([i], smallMat)))
            #print(printString + '\n')


    def finishTest(self):
        
        # End of Experiment
        if self.output_file:
            self.csv_writer = None
            self.output_file.close();
            
        if not self.countData:
            return;

        self.DataMat = self.DataMat[0:self.countData[-1]]

        DataMean = np.mean(self.DataMat, 0)
        DataStd = np.std(self.DataMat, 0)

        print("%d samples successfully read" % (len(self.countData)))
        for chan in self.channelList:
            print(f"Channel {chan}: ")
            print("Capacitance: %0.4f +- %0.4f pF" % (DataMean[chan], DataStd[chan]))
            print("Conductance: %0.4f +- %0.4f mS" % (DataMean[chan+4], DataStd[chan+4]))
        
        self.btn_text.set("Begin Measurement")
        self.isMeasuring = 0;
        # Plot Data
        #self.plotData(self.filePath)
        return

    def processFreeData(self, dataVec):
        
        print("Writing %d datapoints" % len(dataVec))
        
        for i in range(0, 64, 2):
            self.csv_writer.writerow([dataVec[i], dataVec[i+1]])
        
        #print("All Clear Sent")
        self.SerialObj.write(b'K\n') # Send all clear to receive more data
        return

    # Loads data from a file and plots it on the interface
    # def plotData(self, readDataFilePath):
        
    #     xdata = []
    #     ydata = []
    #     self.plot1.clear()
    #     with open(readDataFilePath, newline='') as read_file:
    #         csv_reader = csv.DictReader(read_file, quoting=csv.QUOTE_NONNUMERIC, delimiter=',', quotechar='|')
    #         for row in csv_reader:
    #            xdata.append(row['Time'])
    #            ydata.append(row['C'])
    #     self.plot1.plot(xdata, ydata, marker = 'o', fillstyle = 'full')
    #     self.plot1.set_xlim(-1, np.max(xdata)+1)
    #     self.plot1.set_ylim(np.min(ydata)*0.9 - 1, np.max(ydata)*1.3 + 1)
    #     self.canvas.draw()
    #     return

    def cancelMeasurement(self):
        try: 
            self.SerialObj.timeout = 1
            self.SerialObj.write(b'X\n') # Cancel Ongoing Test
            self.csv_writer = None
            self.output_file.close()
            print("Collection Finished.")
        except: 
            self.eqcStatus.set("Failed to Start test to COM Port")
        return
    
    #def onClickcb(self):
    #    print("Button Toggled")
    #    self.root.after(200, self.channelAdjust)
        return

    def channelAdjust(self):
        i = 0
        #print("Channels Adjusted")
        self.channelBin = 0
        self.channelList = []
        for var in self.channelVars:
            if var.get() == 1:
                self.channelList.append(i)
                self.channelBin = self.channelBin + (1 << i)
            i+=1

        # Send to MCU
        #sendData = bytearray('L' + str(self.channelBin) + '\n', 'ascii')
        #self.SerialObj.write(sendData)
        
        return

    def on_close(self):
         if tk.messagebox.askokcancel("Quit", "Do you want to quit the program?"):
            if self.isMeasuring:
                self.startStop()
            if self.isHeating:
                self.startHeating()
            self.root.destroy()


# Main Program Execution
if __name__ == "__main__":
    print("Launching GenII Interface...")
    root = tk.Tk() # Create Root Tkinter Instance
    root.geometry("480x272")
    root.minsize(480,272)
    root.maxsize(480,272)
    IOSLEEPTIME = 500
    ERR_IOSLEEPTIME = 200
    app = GenII_Interface(root) # Create Main Application Object
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop();

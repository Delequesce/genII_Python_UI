from matplotlib.figure import Figure
from RingBuffer import *
from BlitManager import *
import tkinter as tk
import tkinter.ttk as ttk
import numpy as np
import time, csv, serial, sys, glob
import struct
import serial.tools.list_ports
from tkinter.filedialog import askopenfilename, asksaveasfilename
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg,  
NavigationToolbar2Tk)
import signal
import posix_ipc
import datetime
import os

class GenII_Interface:

    # Class Constants
    QUEUE_NAME_UAUI = "/uart_ui_message_queue"
    QUEUE_NAME_UIUA = "/ui_uart_message_queue"
    #MY_SIGNAL = signal.SIGUSR2
    TEMPARRAYSIZE = 60
    DATAVECSIZE = 28

    def __init__(self, root, use_mq = True):

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

        # Variables for labels and entries
        self.str_filePath = tk.StringVar()
        self.str_runT = tk.StringVar(value = "1800")
        self.str_incTemp = tk.StringVar(value = "37")
        self.str_currentTemp = tk.StringVar(value= "N/A")
        self.str_heaterStatus = tk.StringVar(value="Heater Off")
        self.str_tpeak_est = []
        self.str_deltaEps_est = []
        self.str_smax_est = []
        for i in range(4):
            self.str_tpeak_est.append(tk.StringVar(value = "n/a")) 
            self.str_deltaEps_est.append(tk.StringVar(value = "n/a"))
            self.str_smax_est.append(tk.StringVar(value = "n/a"))

        self.timerVar = tk.StringVar()
        self.timerVar.set('')

        # Tasks
        self.mq_task = None

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
        self.redrawCounter = 10
        self.channelBin = 0
        self.DataMat = []
        self.prevTime = 0
        self.oldDataVec = np.zeros(self.DATAVECSIZE)
        self.output_file = None
        self.csv_writer = None
        self.tempArray = RingBuffer(self.TEMPARRAYSIZE)
        self.tempStabilityThreshold = 0.5
        self.bsWindow = None
        self.fakeData = False
        self.noSerial = False
        self.NUMDATAMAX = 1800
        
        # Initialize first frame
        self.forward()

        # Setup message queues and signals
        if use_mq:
            self.setupMQ()

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
        btn_EQC = ttk.Button(fr_main, text = "Perform Daily EQC", style = "AccentButton", command = lambda: self.openBoardSelectWindow(True))
        btn_calib = ttk.Button(fr_main, text = "Perform Calibration", style = "AccentButton", command = lambda: self.openBoardSelectWindow(False))
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
        self.heaterStatus = ["Heater Off", "Heating System", "Stable Temperature Achieved", "Heater Start Error", "Heater Stop Error"]

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
        lbl_smax = ttk.Label(fr_resultsParams, text = "smax")
        lbl_tpeak_est = []
        lbl_deltaEps_est = []
        lbl_smax_est = []
        for x in self.str_tpeak_est:
            lbl_tpeak_est.append(ttk.Label(fr_resultsParams, textvariable=x))
        
        for x in self.str_deltaEps_est:
            lbl_deltaEps_est.append(ttk.Label(fr_resultsParams, textvariable=x))

        for x in self.str_smax_est:
            lbl_smax_est.append(ttk.Label(fr_resultsParams, textvariable=x))

        lbl_chan1.grid(row = 0, column = 1, padx = 5, pady = 5)
        lbl_chan2.grid(row = 0, column = 2, padx = 5, pady = 5)
        lbl_chan3.grid(row = 0, column = 3, padx = 5, pady = 5)
        lbl_chan4.grid(row = 0, column = 4, padx = 5, pady = 5)
        lbl_tpeak.grid(row = 1, column = 0, padx = 5, pady = 5)
        lbl_deltaEps.grid(row = 2, column = 0, padx = 5, pady = 5)
        lbl_smax.grid(row = 3, column = 0, padx = 5, pady = 5)

        i = 1
        for x in lbl_tpeak_est:
            x.grid(row = 1, column = i, padx = 5, pady = 5)
            i+=1
        
        i = 1
        for x in lbl_deltaEps_est:
            x.grid(row = 2, column = i, padx = 5, pady = 5)
            i+=1

        i = 1
        for x in lbl_smax_est:
            x.grid(row = 3, column = i, padx = 5, pady = 5)
            i+=1

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
        if not readDataFilePath:
            return
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
    
    # Function to connect to message queues
    def setupMQ(self):

        self.mq_inbox = posix_ipc.MessageQueue(self.QUEUE_NAME_UAUI)
        self.mq_outbox = posix_ipc.MessageQueue(self.QUEUE_NAME_UIUA)

        # Request notifications for queue from ui
        #self.mq_inbox.request_notification(self.MY_SIGNAL)

        # Register my signal handler
        #signal.signal(self.MY_SIGNAL, self.handle_signal)
        
        # Set up loop to check message queues
        self.mq_task = self.root.after(200, self.checkMessageQueue)

        return

    # Callback function for handling the specified user signal
    # def handle_signal(self, signal_number, stack_frame):
    #     numMess = self.mq_inbox.current_messages
    #     while numMess > 0: 
    #         #print("Remaining Messages: %d" % numMess)
    #         message, priority = self.mq_inbox.receive()
    #         # RECEIVED MESSAGES ARE IN BYTE FORMAT
    #         #message = message.decode('ascii')
            

    #         #print("Message received: %s" % (message))

    #         # Act on command (PROCESS INPUTS
    #         self.processInputs(message)
    #         numMess = self.mq_inbox.current_messages
        
    #     # Re-register for notifications
    #     self.mq_inbox.request_notification(self.MY_SIGNAL)
    #     return

    # Checks the message queue and handles all of the awaiting messages
    def checkMessageQueue(self):
        numMess = self.mq_inbox.current_messages
        while numMess > 0: 
            message, priority = self.mq_inbox.receive()

            # Act on command (PROCESS INPUTS
            #print("Message received: %s" % (message))
            self.processInputs(message)
            numMess = self.mq_inbox.current_messages

        self.mq_task = self.root.after(200, self.checkMessageQueue)

    ### Button Callback Functions

    # This function sends a command through the UART handler to the MCU 
    # to check that the signal path is working correctly
    def connectToDevice(self):

        print("Connecting to Device")
        self.cv_statusLights.itemconfig(self.light_connect, fill="yellow")

        if not self.writeToMCU(b'C\n'):
            print("Failed to Connect to Device")
            self.cv_statusLights.itemconfig(self.light_connect, fill="red")
            return 

        # Update UI with connection status
        self.deviceStatus.set("Device Successfully Connected")
        self.cv_statusLights.itemconfig(self.light_connect, fill="green")

        # Flush inbox before entering main loop
        #self.handle_signal(0, 0)
        print("Successfully Connected")

        return
    
    # Sends a command to the MCU through the UART Handler
    def writeToMCU(self, message, ack = True):

        if self.noSerial:
            return 1


        # Send command and wait for acknowledgement from uart (create signal mask to block interrupts)
        #signal.pthread_sigmask(signal.SIG_BLOCK, {self.MY_SIGNAL})
        #self.mq_inbox.request_notification(None)
        self.root.after_cancel(self.mq_task)

        # Flush inbox
        while self.mq_outbox.current_messages > 0:
            self.mq_outbox.receive()

        print("Sending Message to MCU")
        self.mq_outbox.send(message)
        
        if not ack:
            return 1
        
        #print("Waiting for inbox")
        temp = self.mq_inbox.current_messages
        while temp < 1:
            #print(temp)
            temp = self.mq_inbox.current_messages
            time.sleep(0.05)
        
        #print("Loop escaped")
        response, priority = self.mq_inbox.receive()

        #signal.pthread_sigmask(signal.SIG_UNBLOCK, {self.MY_SIGNAL})
        #self.mq_inbox.request_notification(self.MY_SIGNAL)
        self.root.after(200, self.checkMessageQueue)
        #print("Checking response")
        if response == b'K':
            print("Success!")
            return 1
        else: 
            print("Failure")
            return 0
        
        return 0

    def performCalibration(self, boardNumber):

        self.bsWindow.destroy()

        sendData = bytearray('B' + str(boardNumber) + '\n', 'ascii')

        if not self.writeToMCU(sendData):
            self.calibStatus.set("Failed to Start Calibration")
            return 
        
        self.calibStatus.set("Waiting for Calibration to complete")
        return

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
    
        self.calibStatus.set("Calibration Successful")
        return

    # Opens a window for selecting the appropriate board. 
    def openBoardSelectWindow(self, isQC):
        bsWindow = tk.Toplevel(self.root)
        bsWindow.title('Board Selection Window')

        lbl_boardNumber = ttk.Label(bsWindow, text= "Board Number")
        bn_radial = tk.IntVar()
        if isQC:
            btn_run = ttk.Button(bsWindow, text = "Begin Quality Check", style="AccentButton", 
                                 command = lambda: self.performEQC(bn_radial.get()))
            lbl_helpText = ttk.Label(bsWindow, text = "Please insert a QC Board and select the correct ID")
            N_Boards = 5
        else: 
            btn_run = ttk.Button(bsWindow, text = "Begin Calibration", style="AccentButton", 
                                 command = lambda: self.performCalibration(bn_radial.get()))
            lbl_helpText = ttk.Label(bsWindow, text = "Please insert a Calibration Board and select the correct ID")
            N_Boards = 5

        lbl_helpText.grid(row=0, column=0, columnspan=N_Boards, pady=2)
        lbl_boardNumber.grid(row=1, column=0, columnspan=N_Boards, pady=2)
        for i in range(N_Boards):
            ttk.Radiobutton(bsWindow, text = f'{i}', variable=bn_radial, value = i).grid(row=2, column=i)
        
        btn_run.grid(row=3, column=0, columnspan=N_Boards, pady=2)

        self.bsWindow = bsWindow

        return

    def performEQC(self, boardNumber):

        self.bsWindow.destroy()
        sendData = bytearray('Q' + str(boardNumber) + '\n', 'ascii')

        if not self.writeToMCU(sendData):
            self.calibStatus.set("Failed to Start Calibration")
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

        # Status is Idle -> Heating -> Stable
        stat = self.str_heaterStatus.get()

        if stat == self.heaterStatus[0] or stat == self.heaterStatus[3]: #Idle, Start Heating
            # Toggle Heater State and wait for response
            if not self.writeToMCU(b'H\n'):
                self.str_heaterStatus.set(self.heaterStatus[3]) # Heater Start Error
                return

            self.str_heaterStatus.set(self.heaterStatus[1])
            self.heatBtn_text.set(self.heatBtnText[1])
        else: # Stop Heating
            # Toggle Heater State and wait for response
            if not self.writeToMCU(b'H\n'):
                self.str_heaterStatus.set(self.heaterStatus[4]) # Heater Stop Error
                return
            
            self.str_heaterStatus.set(self.heaterStatus[0])
            self.heatBtn_text.set(self.heatBtnText[0])
            self.tempArray = RingBuffer(self.TEMPARRAYSIZE) # Re-initialize temperature array as empty Ring Buffer
        
        return
    
    ### Takes messages from UART handler and decides what to do with them
    # List of Control Characters:
    # - C = 67: Calibration Data
    # - D = 68: Regular Impedance Data
    # - E = 69: Error/General Messages
    # - Q = 81: EQC Data
    # - T = 84: Temperature Measurements
    # - X = 88: Measurement stop

    def processInputs(self, message):
        #print("Processing Inputs")
        controlChar = message[0] # INDEXING A BYTES OBJECT GIVES YOU AN INT
        #print(controlChar)
        #print(b'E')

        if controlChar == 67:
            dataVec = self.decodeMessage(message, ignoreErrors = True, split = True)
            self.finishCalibration(dataVec)
            return
        
        if controlChar == 68:
            # Ideally breaks into self.DATAVECSIZE element list (28 as of 4/15/25)
            dataVec = self.decodeMessage(message, ignoreErrors = False, split = True)
            if len(dataVec) < self.DATAVECSIZE:
                dataVec = self.oldDataVec

            #print(dataVec)
            self.printAndStore(dataVec)
            self.oldDataVec = dataVec
            return
        if controlChar == 69:
            decoded_message = self.decodeMessage(message, ignoreErrors = False, split = False)
            if decoded_message:
                print(decoded_message)
            return
        
        if controlChar == 81:
            dataVec = self.decodeMessage(message, ignoreErrors = False, split = True)
            if len(dataVec) > 1:
                self.finishEQC(dataVec)
            return
        
        if controlChar == 84:
            #print("Temperature")
            decoded_message = self.decodeMessage(message, ignoreErrors = False, split = False)
            self.str_currentTemp.set(decoded_message[0:-4]) #Increase number to reduce how many decimals are printed
            
            # Create moving average to see when temperature becomes stable (if last X measurements were within Y degrees of each other)
            #if self.isHeating and len(self.tempArray.data) == self.TEMPARRAYSIZE:
            #    self.tempArray.add(float(line[0:-4]))
            #    if np.std(self.tempArray.data) < self.tempStabilityThreshold:
            #        self.str_heaterStatus.set(self.heaterStatus[2])
            return
        
        if controlChar == 88:
            print("Finishing Test")
            self.finishTest()
            return
        
        print("Invalid Control Character %s" % controlChar)
        return

    # Converts message from byte array to string (char array)
    def decodeMessage(self, message, ignoreErrors = False, split = False):
        message = message[1:] # Chop off control Character
        try:
            if ignoreErrors:
                decoded_line = message.decode(encoding='ascii', errors = 'ignore')
            else:
                decoded_line = message.decode(encoding='ascii')
        except Exception as e:
            print(e)
            #self.io_task = self.root.after(ERR_IOSLEEPTIME, self.processInputs)
            return 0
        #decoded_line = message
        if split:
            decoded_line = decoded_line[0:-1].split('!')

        return decoded_line
        

    # Command board to begin taking measurements and sending data    
    def beginMeasurement(self):

        # isTestingUI = False
        # if isTestingUI:
        #     # Initialize plot
        #     self.plot1.cla()
        #     for i in range(1):
        #         self.plot1.plot([], [], 'o-', label = f"Ch {i+1}", markersize=4, animated=True)

        #     self.lines = self.plot1.get_lines()
        #     self.plot1.set_xlabel("Time (s)")
        #     self.plot1.set_ylabel("Capacitance (pF)")
        #     self.plot1.legend(loc='upper left', prop={'size':6})
        #     self.plot1.set_xlim(0, 100)
        #     self.plot1.set_ylim(0, 100)

        #     # Create Blitting Manager to handle canvas and line updates and redraws
        #     self.bm = BlitManager(self.canvas, self.lines)

        #     # Run loop to plot data
        #     xData = np.arange(0, 100)
        #     for j in range(100):
        #         self.lines[0].set_xdata(xData[0:j])
        #         self.lines[0].set_ydata(xData[0:j])
        #         self.bm.update()
        #     return


        invalid = 0
        self.filePath = self.str_filePath.get()
        self.plotRange = np.array([90, 110])

        # Cancel Any previously ongoing test on MCU End
        if not self.writeToMCU(b'X\n'):
            print("Test Cancel Failure")
        
        # Copy template file and write basic data
        template_file = None
        if self.filePath:
            try:
                template_file = open("DataFileTemplate.csv")
            except FileNotFoundError as e:
                tk.messagebox.showerror(title="File Not Found Error", 
                                        message="Template Data File Not Found. Test Aborting")
                return
            
        if template_file:
            readerObj = csv.reader(template_file, delimiter=',')
            
            date = datetime.date.today().strftime("%Y-%m-%d")
            id = "NULL"
            
            with open(self.filePath, 'w') as output_file:
                writerObj = csv.writer(output_file, delimiter = ',')
                rowCounter = 0
                for row in readerObj:
                    if rowCounter == 2:
                        row[1] = date
                    if rowCounter == 3:
                        row[1] = id
                    writerObj.writerow(row)
                    rowCounter = rowCounter + 1

            # Reopen file in append mode to continuously write data
            self.output_file = open(self.filePath, 'a', newline = '')
            self.csv_writer = csv.writer(self.output_file, delimiter = ',')

        # Send command to device to start measurement. Cancel reads during this process
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
        if not self.writeToMCU(sendData):
            print("Failed to Write new test parameters")
            self.cancelMeasurement()
            return 

        # Command new test
        self.dontInterrupt = False
        if not self.writeToMCU(b'N\n'):
            print("Cannot Start Test")
        
        self.btn_text.set(self.measBtnText[1])

        # Reinitialize data vectors
        self.DataMat = np.empty((intrunT, 9))
        self.DataMat[:] = np.nan

        self.countData = []
        self.redrawCounter = 10

        # Initialize plot
        self.plot1.cla()
        self.plot1.clear()
        for i in range(4):
            self.plot1.plot([], [], 'o-', label = f"Ch {i+1}", markersize=4, animated=True)

        self.lines = self.plot1.get_lines()
        self.plot1.set_xlabel("Time (s)")
        self.plot1.set_ylabel("Capacitance (pF)")
        self.plot1.legend(loc='upper left', prop={'size':6})
        self.plot1.set_xlim(-1, 30)

        # Create Blitting Manager to handle canvas and line updates and redraws
        self.bm = BlitManager(self.canvas, self.lines)
        
        i = 0
        self.channelBin = 0
        for var in self.channelVars:
            if var.get() == 1:
                self.channelList.append(i)
                self.channelBin = self.channelBin + (1 << i)
            i+=1

        # Set Start Time
        #self.prevTime = time.perf_counter()

        # After function exits, input processing thread will continue to run and handle incoming data
        #self.io_task = tk.after(100, self.processInputs) # Schedule new read in 500 msec

        # If we are using fake data, instead of returning, just directly write the data to the necessary tables
        if self.fakeData:
            with open("FakeDataFile.csv", 'r') as data_file:
                readerObj = csv.reader(data_file, delimiter=',')
                discard = next(readerObj)
                rowCounter = 0
                for row in readerObj:
                    self.printAndStore(row)
                    if rowCounter > self.NUMDATAMAX:
                        break
                    rowCounter = rowCounter + 1

            dataVec = np.asarray([[0, 600, 0.167, 950,  0.004, 850], 
                                [1, 600,  0.167, 950, 0.004, 850],
                                [2, 160,  0.133, 280, 0.004, 230],
                                [3, 160,  0.133, 280, 0.004, 230]], dtype='U5')
            
            for chan in self.channelList:
                self.setOutputParams(dataVec[chan])

            self.finishTest()
        return
    

    #def storeTemps(self, line):
    #    with open('C://Users/cdeli/Desktop/TemperatureLog.csv', 'a', newline = '') as output_file:
    #        csv_writer = csv.writer(output_file, delimiter = ',', quoting = csv.QUOTE_NONNUMERIC, quotechar='|')
    #        csv_writer.writerow([float(line)])

    # DataVec comes in a [C1, G1, Tpeak, DE, DE_Time, Smax, Smax_Time, C2, G2, ... ]
    def printAndStore(self, dataVec):

        # Use to calculate time in between each collection
        #currTime = time.perf_counter()
        #print(currTime - self.prevTime)
        #self.prevTime = currTime
        # Get current count
        self.countData.append(len(self.countData) + 1)
        i = self.countData[-1]

        #print(f"Data Point {i}, Data Vector: {dataVec}")
        useOldData = False
        
        # Process Data Vector
        CVec = []
        GVec = []

        try:
            for C, G in zip(dataVec[0::7], dataVec[1::7]):
                CVec.append(float(C[:-1]))
                GVec.append(float(G[:-1]))

        except Exception as e:
            useOldData = True
            print("DataVec Format Error, using old vector")
            print(dataVec)
        
        if useOldData:
            for C, G in zip(self.oldDataVec[0::7], self.oldDataVec[1::7]):
                CVec.append(float(C[:-1]))
                GVec.append(float(G[:-1]))
            return

        for chan in self.channelList:
            self.DataMat[i-1, chan] = CVec[chan]
            self.DataMat[i-1, chan+4] = GVec[chan]
            l = self.lines[chan]
            l.set_xdata(self.countData)
            l.set_ydata(self.DataMat[0:i, chan])

        try:
            self.DataMat[i-1, -1] = self.str_currentTemp.get()
        except Exception as e:
            self.DataMat[i-1, -1] = 0
            #print(e)

        smallMat = self.DataMat[i-1]
        if smallMat.size == 0:
            return
        smallMatMin= np.min(smallMat[self.channelList])
        smallMatMax= np.max(smallMat[self.channelList])
        if smallMatMin < self.plotRange[0]:
            self.plotRange[0] = smallMatMin
        if smallMatMax > self.plotRange[1]:
            self.plotRange[1] = smallMatMax

        if self.csv_writer:
            dataToWrite = np.concatenate(([np.round(i/60, 3)], smallMat))
            dataToWrite = list(map(lambda t: "%0.3f" % t, dataToWrite))
            self.csv_writer.writerow(dataToWrite)

        self.plot1.set_xlim(-1, np.floor((i-1)/30 + 1) * 30)
        self.plot1.set_ylim(self.plotRange[0]-1, self.plotRange[1]+1)
        #self.plot1.set_ylim(0, 400)

        # Have the blitting manager update the artists
        if self.redrawCounter > 9:
            self.canvas.draw()
            self.redrawCounter = 0
        else:
            self.bm.update()
            self.redrawCounter+=1


        # Set Output params if different/time

        for chan in self.channelList:
            self.str_tpeak_est[chan].set(dataVec[7*chan+2])
            self.str_deltaEps_est[chan].set(dataVec[7*chan+3])
            self.str_smax_est[chan].set(dataVec[7*chan+5])

        #time_elapsed = time.perf_counter() - start_time
        #print(f"time_elapsed: {time_elapsed:0.3f}")


    def finishTest(self):
        
        # End of Experiment
        if self.output_file:
            self.csv_writer = None
            self.output_file.close()
            
        if not self.countData:
            return

        self.DataMat = self.DataMat[0:self.countData[-1]]

        # Calculate mean and variance of data (for fixed chip testing)
        DataMean = np.mean(self.DataMat, 0)
        DataStd = np.std(self.DataMat, 0)
        N, M = self.DataMat.shape

        print("%d samples successfully read" % (N))
        # for chan in self.channelList:
        #     print(f"Channel {chan}: ")
        #     print("Capacitance: %0.4f +- %0.4f pF" % (DataMean[chan], DataStd[chan]))
        #     print("Conductance: %0.4f +- %0.4f mS" % (DataMean[chan+4], DataStd[chan+4]))
        
        # Normalize Plot based on output params, if available
        normCDataMat = np.zeros((N, 4))
        if self.isMeasuring:
            for chan in self.channelList:
                tpeak = None
                peakVal = None
                try:
                    tpeak = int(float(self.str_tpeak_est[chan].get()))
                    peakVal = self.DataMat[tpeak,chan]
                except ValueError as e:
                    print("No Valid Tpeak Reported\n")
                    break
                if not peakVal:
                    break

                # Normalize Data (NumPy handles divide by zero cases automatically)
                timeVec = np.round(np.divide(self.countData , 60), decimals=3)
                normCDataMat[:,chan] = np.round(np.divide(self.DataMat[:,chan],peakVal), decimals=3)
                self.plot1.cla()
                for chan in self.channelList:
                    self.plot1.plot(timeVec, normCDataMat, marker = 'o', label = f"Ch {chan}", markersize = 4, fillstyle = 'full')
                #self.plot1.legend("Channel 1", "Channel 2", "Channel 3")
                self.plot1.set_xlim(-1, timeVec[-1] + 1)
                self.plot1.set_ylim(0.7, np.max([1.01, np.max(normCDataMat)]))
                self.plot1.set_xlabel("Time (min)")
                self.plot1.set_ylabel("Normalized Permittivity (real)")
                self.plot1.legend(loc='upper left', prop={'size':6})
                self.canvas.draw()
        
        # Set state for next test
        self.btn_text.set("Begin Measurement")
        self.isMeasuring = 0

        # Write Normalized Data and Output Params to file (even if it is bad)
        if not self.filePath:
            return
        
        tempFile = "tempFile.csv"
        with open(self.filePath, 'r', newline='') as input_file:
            readerObj = csv.reader(input_file, delimiter=',')
            with open(tempFile, 'w', newline = '') as output_file:
                csv_writer = csv.writer(output_file, delimiter = ',')
                # Take each row and copy it to the temporary file, adding new data as needed
                # Rows 8-13 are output params
                # Data starts at row 18
                outputParamTable = np.zeros((6, 4), dtype='U5')
                for chan in self.channelList:
                    outputParamTable[0, chan] = self.str_tpeak_est[chan].get()
                    outputParamTable[1, chan] = self.str_deltaEps_est[chan].get()
                    outputParamTable[2, chan] = self.str_smax_est[chan].get()
                    outputParamTable[3, chan] = "n/a"
                    outputParamTable[4, chan] = "n/a"
                    outputParamTable[5, chan] = "n/a"

                rowCount = 1
                for row in readerObj:
                    if rowCount < 14 and rowCount > 7:
                        row[1:5] = outputParamTable[rowCount-8]
                    if rowCount > 17:
                        row[10:14] = normCDataMat[rowCount-18]

                    csv_writer.writerow(row)
                    rowCount = rowCount + 1

                # For testing only
                for x in range(N):
                    row = np.zeros(14)
                    row[10:14] = normCDataMat[x]
                    csv_writer.writerow(row)


        # Rename tempFile to be the actual file and delete the old file
        os.remove(self.filePath)
        os.rename(tempFile, self.filePath)

        tk.messagebox.showinfo(title="Test Finished", message="Test Completed Successfully")

        return

    def calculateParameters(self, DataMat, channelList):
        simpleMax = False
        N, M = DataMat.shape
        Tpeak = np.zeros(M)
        Tpeak[:] = np.nan
        DeltaEps = np.zeros(M)
        DeltaEps[:] = np.nan
        smax = np.zeros(M)
        smax[:] = np.nan
        normC = np.zeros((N, M))
        normSlp = np.zeros((N-1, M))
        startJ = 60 # Number of seconds to start looking for Tpeak After
        N_slp_ma = 3
        N_C_ma = 12
        cnv_window_c = np.ones(N_C_ma)
        cnv_window_slp = np.ones(N_slp_ma)
        try:
            for chan in channelList:
                Cdata = DataMat[:,chan]
                Cdata_filt = np.convolve(Cdata, cnv_window_c, 'valid')/N_C_ma
                Cdata_filt = np.concatenate((Cdata[:(N_C_ma-1)], Cdata_filt))
                C_slp = np.diff(Cdata_filt)
                C_slp_filt = np.convolve(C_slp, cnv_window_slp, 'valid')/N_slp_ma
                C_slp_filt = np.concatenate((C_slp[:(N_slp_ma-1)], C_slp_filt))
                if simpleMax: # Maximum Value
                    TpeakI = np.argmax(Cdata)
                    Tpeak[chan] = Cdata[TpeakI]
                else: # Zero Crossing
                    j = 0
                    changeArray = C_slp_filt < 0
                    tempArr = np.where(changeArray[startJ:N-1])[0]
                    tempArr = tempArr[:5] + startJ
                    #print(tempArr)
                    if len(tempArr) < 2:
                        continue
                    while tempArr[j+1] > tempArr[j]:
                        j+=1
                        if j == 4:
                            mFlag = 1
                            break

                    if mFlag:
                        TpeakI = round(np.median(tempArr))
                    else:
                        TpeakI = tempArr[j]

                    Tpeak[chan] = TpeakI

                # Normalize Data
                maxPf = Cdata[TpeakI]
                normC[:,chan] = np.divide(Cdata,maxPf)
                normSlp[:,chan] = np.divide(C_slp, maxPf)

                # Delta Epsilon
                # Stop condition is Slope < 0.00002
                # Once normC has fallen by 1% from peak (0.01)
                deltaEpsI = np.nan
                if simpleMax:
                    DeltaEps[chan] = np.min(Cdata[TpeakI:])
                else:
                    slope_thresh = -0.00002
                    fall_thresh = 0.99
                    if TpeakI != N:
                        for n, val in enumerate(normSlp[TpeakI:, chan]):
                            if normC[n + TpeakI, chan] > fall_thresh:
                                continue

                            if val > slope_thresh:
                                deltaEpsI = TpeakI + n
                                DeltaEps[chan] = np.round(1-normC[deltaEpsI, chan], 4)
                                break
                
                # Find Smax
                endCheck = N if np.isnan(deltaEpsI) else deltaEpsI + 1
                smaxI = TpeakI + np.argmin(normC[TpeakI:endCheck, chan])
                smax[chan] = np.abs(np.round(normC[smaxI, chan], 4))

                # Store values
                self.str_tpeak_est[chan].set(Tpeak[chan])
                self.str_deltaEps_est[chan].set(DeltaEps[chan])
                self.str_smax_est[chan].set(smax[chan])

        except Exception as e:
            print(e)
            print("Error in calculating parameters")

    # Sets the parameter estimate values upon transfer from MCU
    def setOutputParams(self, outputVec):
        chan = int(outputVec[0])
        self.str_tpeak_est[chan].set(outputVec[1])
        self.str_deltaEps_est[chan].set(outputVec[2])
        self.str_smax_est[chan].set(outputVec[4])
        return

    # Loads data from a file and plots it on the interface
    def plotData(self, readDataFilePath):
        
        timeData = []
        cData = []
        self.plot1.clear()
        with open(readDataFilePath, newline='') as read_file:
            csv_reader = csv.DictReader(read_file, quoting=csv.QUOTE_NONNUMERIC, delimiter=',', quotechar='|')
            for row in csv_reader:
                timeData.append(row['Time'])
                cData.append([row['C1'], row['C2'], row['C3'], row['C4']])

        cData = np.array(cData)
        for i in range(4):
            self.plot1.plot(timeData, cData[:,i], marker = 'o', markersize = 4, label = f"Ch {i+1}", fillstyle = 'full')

        self.plot1.set_xlim(-1, np.max(timeData)+1)
        self.plot1.set_ylim(np.min(cData)*0.9 - 1, np.max(cData)*1.1 + 1)
        self.plot1.set_xlabel("Time (s)")
        self.plot1.set_ylabel("Capacitance (pF)")
        self.plot1.legend(loc='upper left', prop={'size':6})
        self.canvas.draw()

        # Calculate Parameters
        self.calculateParameters(cData, [0, 1, 2, 3])

        # Enable only for pictures
        pictures = False
        if pictures:
            self.str_heaterStatus.set(self.heaterStatus[2])
            self.str_currentTemp.set("37.0")
            self.heatBtn_text.set(self.heatBtnText[1])
            self.btn_text.set(self.measBtnText[1])

        return

    def cancelMeasurement(self):
        # Cancel Ongoing Test
        if not self.writeToMCU(b'X\n'):
            print("Test Cancel Failure")
            return
        
        print("Collection Finished.")
        self.finishTest()
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
        
        return

    def on_close(self):
         if tk.messagebox.askokcancel("Quit", "Do you want to quit the program?"):
            self.writeToMCU(b'END', ack=False)
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
    root.mainloop()

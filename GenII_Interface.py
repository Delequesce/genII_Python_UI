from matplotlib.figure import Figure
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
        self.str_tpeak_est = tk.StringVar(value = "0s")
        self.str_deltaEps_est = tk.StringVar(value = "0")
        self.str_tpeak_est_conf = tk.StringVar(value = "0%")
        self.str_deltaEps_est_conf = tk.StringVar(value = "0%")

        # Frames
        self.frameList.append(self.createTopWindow(root)) # Create a top window element for root instance
        self.frameList.append(self.createParamWindow(root))
        self.frameList.append(self.creatTestRunWindow(root))

        # Other
        self.exit_code = bytearray([0, 1, 2, 3])
        self.CData = []
        self.GData = []
        self.output_file = None
        self.csv_writer = None

        # Initialize first frame
        self.forward()
        

    def createTopWindow(self, root):
        root.minsize(root.winfo_width(), root.winfo_height())
        # Get Height of Screen
        width = int(root.winfo_screenwidth()/4)
        height = int(root.winfo_screenheight()*0.75)
        x_coordinate = 2000
        y_coordinate = 300
        #root.geometry("{}x{}+{}+{}".format(width, height, x_coordinate, y_coordinate))
        root.title("MIA Generation II Interface")
        style = ttk.Style(root)
        root.tk.call('source', 'Azure-ttk-theme/azure.tcl') # Imports TCL file for styling
        style.theme_use('azure')
        style.configure("AccentButton", foreground = 'white')

        # Frames and canvases
        fr_main = ttk.Frame(root);
        cv_statusLights = tk.Canvas(fr_main, width = 100, height = 100)
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
        offset = 20;
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
        lbl_deviceStatus.grid(row = 0, column = 2, padx = 5, pady = 5)
        lbl_eqcStatus.grid(row = 1, column = 2, padx = 5, pady = 5)
        lbl_calibStatus.grid(row = 2, column = 2, padx = 5, pady = 5)

        #root.update()

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
        lbl_runTime = ttk.Label(fr_params, text = "Run Time (min)")
        lbl_incTemp = ttk.Label(fr_params, text = "Incubation Temperature (C)")
        lbl_channels = ttk.Label(fr_params, text = "Active Channels")
        lbl_fpath = ttk.Label(fr_params, text= "Filepath")
        lbl_runTime.grid(row = 0, column = 0, padx = 5, pady = 5)
        lbl_incTemp.grid(row = 1, column = 0, padx = 5, pady = 5)
        lbl_channels.grid(row = 2, column = 0, padx = 5, pady = 5)
        lbl_fpath.grid(row = 3, column = 0, padx = 5, pady = 5)

        # Entry Boxes
        
        ent_runTime = ttk.Entry(fr_params, textvariable= self.str_runT, width = 10)
        ent_incTemp = ttk.Entry(fr_params, textvariable= self.str_incTemp, width = 10)
        ent_filePath = ttk.Entry(fr_filePath, textvariable= self.str_filePath, width = 50)
        ent_runTime.grid(row = 0, column = 1, padx = 5, pady = 5)
        ent_incTemp.grid(row = 1, column = 1, padx = 5, pady = 5)
        ent_filePath.grid(row = 0, column = 1, columnspan = 2, pady = 5)
        #ent_filePath.bind("<1>", self.openSaveDialog) # Will launch when entry box is left-clicked

        # Buttons
        btn_next = ttk.Button(fr_params, text = "Continue", style = "AccentButton", command = self.forward)
        btn_back = ttk.Button(fr_params, text = "Back", style = "AccentButton", command = self.previous)
        btn_fileEdit = ttk.Button(fr_filePath, text = "...", style = "AccentButton", command = self.openSaveDialog)
        btn_next.grid(row = 0, column = 2, pady = 5)
        btn_back.grid(row = 1, column = 2, pady = 5)
        btn_fileEdit.grid(row = 0, column = 0) # Should be just to the left of the filepath text box

        channelVars = []
        for i in range(4):
            tempVar = tk.IntVar(value = 1);
            channelVars.append(tempVar);
            ttk.Checkbutton(fr_channels, text=f"Ch{i+1}",variable=tempVar, 
                onvalue=1, offvalue=0).grid(row = int(i/2), column = i % 2, padx = 5, pady = 1)

        return fr_params
    
    def creatTestRunWindow(self, root):
        fr_testWindow = ttk.Frame(root)
        fr_leftInfo = ttk.Frame(fr_testWindow);
        fr_vis = ttk.Frame(fr_testWindow)
        fr_paramEst = ttk.Labelframe(fr_testWindow, text = "Current Parameter Estimates", labelanchor='n')

        # Components
        btn_startHeating = ttk.Button(fr_leftInfo, text = "Start Heating", style = "AccentButton", command = self.startHeating)
        btn_beginMeasurement = ttk.Button(fr_leftInfo, text = "Begin Measurement", style = "AccentButton", command = self.beginMeasurement)
        btn_loadData = ttk.Button(fr_leftInfo, text = "Load Data", style = "AccentButton", command = self.loadAndPlotData)
        btn_back  = ttk.Button(fr_leftInfo, text = "Back", style = "AccentButton", command = self.previous)

        lbl_tempLabel = ttk.Label(fr_leftInfo, text="Current Temp (C):")
        lbl_currentTemp = ttk.Label(fr_leftInfo, textvariable=self.str_currentTemp)

        lbl_tpeak = ttk.Label(fr_paramEst, text = "Tpeak")
        lbl_deltaEps = ttk.Label(fr_paramEst, text = u'{x}{y}max'.format(x = '\u0394', y = '\u03B5'))
        lbl_tpeak_est = ttk.Label(fr_paramEst, textvariable=self.str_tpeak_est)
        lbl_deltaEps_est = ttk.Label(fr_paramEst, textvariable=self.str_deltaEps_est)
        lbl_tpeak_est_conf = ttk.Label(fr_paramEst, textvariable=self.str_tpeak_est_conf)
        lbl_deltaEps_est_conf = ttk.Label(fr_paramEst, textvariable=self.str_deltaEps_est_conf)
        
        # Layout Grid
        fr_leftInfo.grid(row = 0, column = 0)
        fr_paramEst.grid(row = 1, column=0)
        fr_vis.grid(row = 0, column = 1, rowspan=2, columnspan=3)
        btn_startHeating.grid(row = 0, column = 0, columnspan=2, pady = 5)
        lbl_tempLabel.grid(row = 1, column = 0, pady = 5)
        lbl_currentTemp.grid(row = 1, column = 1, pady = 5)
        btn_beginMeasurement.grid(row = 2, column = 0, columnspan=2)
        btn_loadData.grid(row=3, column = 0, columnspan=2)
        btn_back.grid(row = 4, column = 0, columnspan=2)
        lbl_tpeak.grid(row = 0, column = 0, padx = 5, pady = 5)
        lbl_deltaEps.grid(row = 1, column = 0, padx = 5, pady = 5)
        lbl_tpeak_est.grid(row = 0, column = 2, padx = 5, pady = 5)
        lbl_deltaEps_est.grid(row = 1, column = 2, padx = 5, pady = 5)
        lbl_tpeak_est_conf.grid(row = 0, column = 3, padx = 5, pady = 5)
        lbl_deltaEps_est_conf.grid(row = 1, column = 3, padx = 5, pady = 5)

        # Plot
        fig = Figure(figsize = (5.7, 2.5), dpi = 100)
        plot1 = fig.add_axes([0.1, 0.3, 0.8, 0.6], autoscale_on = True)
        plot1.set_xlabel("Time (s)")
        plot1.set_ylabel("Capacitance (pF)")
        self.plot1 = plot1

        # Visual Frame
        self.canvas = FigureCanvasTkAgg(fig, master = fr_vis)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack()

        return fr_testWindow

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

    # Button Callback Functions
    def connectToDevice(self):
        ret = 0;

        list = serial.tools.list_ports.comports()
        connected = []
        print("Connected COM ports:") 
        for element in list:
            connected.append(element.device)
            print(str(element.device) + ": " + element.description)
            if element.manufacturer == 'SEGGER':
                genII_port = element.device

        # if sys.platform.startswith('win'):
        #     ports = ['COM%s' % (i+1) for i in range(256)]
        # elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        #     ports = glob.glob('/dev/tty[A-Za-z]*')
        # elif sys.platform.startswith('darwin'):
        #     ports = glob.glob('/dev/tty.*')
        # else:
        #     raise EnvironmentError('Unsupported platform')

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
        except Exception as e:
            self.deviceStatus.set("Failed to Access COM Port")
            print(e)
            return

        print("Port Succesfully Opened")

        SerialObj.reset_output_buffer()

        # Wakeup and Check Connection Status Command. Function is blocking until timeout
        try: 
            SerialObj.reset_input_buffer()
            SerialObj.write(b'C') 
        except: # Timeout exception
             self.deviceStatus.set("Failed to Write to COM Port")
             return
        
        print("Connection Command Written to Port")

        # Wait for MCU to Process and write return data

        time.sleep(1)
        
        try: 
            statusReturn = SerialObj.readline(1)[0]  # MCU should have acknowledged write and responded with single byte, 'K'
        except: # Timeout exception
             self.deviceStatus.set("Failed to Read from COM Port")
             return
        if statusReturn != 75: # Ascii 'K'
            self.deviceStatus.set("Device Failed to Connect")
            print("Device did not acknowledge connection request")
            return

        # Update UI with connection status
        self.deviceStatus.set("Device Successfully Connected")
        self.cv_statusLights.itemconfig(self.light_connect, fill="green")

        # Return open serial object for future communications
        self.SerialObj = SerialObj

        # Flush Buffers to await new temperature data 
        self.SerialObj.reset_input_buffer()
        self.SerialObj.reset_output_buffer()

        # Call periodic read
        self.SerialObj.timeout = 0 # No timeout
        self.processInputs()
    

    def performCalibration(self):
        try: 
            self.SerialObj.write(b'B')
        except: 
            self.calibStatus.set("Failed to Write to COM Port")
            return
        
        self.calibStatus.set("Waiting for Calibration to complete")

    def finishCalibration(self, Zfb_real, Zfb_imag):

        #if Zfb_real == 0:
        #   self.eqcStatus.set("Calibration Failed")
        #    return

        print("New Calibration Value: %s + %s j" % (Zfb_real, Zfb_imag))
    
        self.eqcStatus.set("Calibration Successful")
        return


    def performEQC(self):
        try: 
            self.SerialObj.write(b'Q')
        except: 
            self.eqcStatus.set("Failed to Write to COM Port")
            return
        self.cv_statusLights.itemconfig(self.light_EQC, fill="yellow")
        self.eqcStatus.set("Waiting for EQC to complete")
        #self.root.after(3000, self.finishEQC) # Non-blocking wait until calibration has finished
        return
    
    def finishEQC(self, rms_error):

        if rms_error > 10:
            self.cv_statusLights.itemconfig(self.light_EQC, fill="red")
            self.eqcStatus.set("EQC Failed")
            return

        print("EQC error value: %0.3f" % rms_error)
    
        self.cv_statusLights.itemconfig(self.light_EQC, fill="green")
        self.eqcStatus.set("EQC Passed")
        return
    
    def startHeating(self):
        try: 
            self.SerialObj.write(b'H')
        except: 
            self.eqcStatus.set("Failed to Write to COM Port")
            return
        
        return

    # General handler function for serial comms
    def processInputs(self):
        self.SerialObj.timeout = 0
        try:
            line = self.SerialObj.readline().decode(encoding='ascii')
        except:
            print("Invalid Read")
            self.io_task = self.root.after(IOSLEEPTIME, self.processInputs) # Schedule new read in 500 msec
            return

        n_line = len(line)
        if n_line < 1:
            print("Message too short")
            self.io_task = self.root.after(IOSLEEPTIME, self.processInputs) # Schedule new read in 500 msec
            return
        #print(line)
        messageString = line[1:-1]
        match line[0]:
            case 'E': # Error Code
                print(messageString)
            case 'D': # Data (C and G)
                dataVec = messageString.split('!')
                #print(dataVec)
                if len(dataVec) > 1:
                    C = dataVec[0]
                    G = dataVec[1]
                    print("Capacitance: %s\nConductance: %s" % (C, G))
                    self.CData.append(C)
                    self.GData.append(G)
            case 'C': # Calibration return values
                #print(messageString)
                dataVec = messageString.split('!')
                self.finishCalibration(dataVec[0], dataVec[1])
            case 'X': # Measurement finish
                self.finishTest()
            case 'Q':
                self.finishEQC(messageString)
            case 'T': # Temperature Reading
                print("Temperature: %s" % messageString)
                self.str_currentTemp.set(messageString)
            case _: # No match 
                print("Invalid Read")

        self.io_task = self.root.after(IOSLEEPTIME, self.processInputs) # Schedule new read in 500 msec

    # Command board to begin taking measurements and sending data    
    def beginMeasurement(self):

        self.filePath = self.str_filePath.get()

        # Clear output file and write header
        with open(self.filePath, 'w', newline = '') as output_file:
            csv_writer = csv.writer(output_file, delimiter = ',', quoting = csv.QUOTE_NONNUMERIC, quotechar='|')
            csv_writer.writerow(['Time', 'C', 'G'])
        
        # Reopen file in append mode to continuously write data
        self.output_file = open(self.filePath, 'a', newline = '')
        self.csv_writer = csv.writer(self.output_file, delimiter = ',', quoting=csv.QUOTE_NONNUMERIC)

        # Reinitialize data vectors
        self.CData = []
        self.GData = []

        # Send command to device to start measurement. Cancel reads during this process
        #tk.after_cancel(self.io_task)
        try: 
            self.SerialObj.timeout = 1
            self.SerialObj.write(b'N')
        except: 
            self.eqcStatus.set("Failed to Start test to COM Port")
            return
        
        # After function exits, input processing thread will continue to run and handle incoming data
        #self.io_task = tk.after(100, self.processInputs) # Schedule new read in 500 msec
        return
    
    def finishTest(self):
        i = 0;
        C_Numeric = np.asarray(self.CData).astype(float)
        G_Numeric = np.asarray(self.GData).astype(float)
        if self.csv_writer:
            for C, G in zip(self.CData, self.GData):
                self.csv_writer.writerow([i, C, G])
                i+=1
        
            # End of Experiment
            self.output_file.close();
            C_mean = np.mean(C_Numeric)
            G_mean = np.mean(G_Numeric)
            print("%d samples successfully read" % (i-1))
            print("Capacitance: %0.4f +- %0.4f pF" % (C_mean, np.std(C_Numeric)))
            print("Conductance: %0.4f +- %0.4f mS" % (G_mean, np.std(G_Numeric)))
        
        # Plot Data
        #self.plotData(self.filePath)
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


# Main Program Execution
if __name__ == "__main__":
    print("Launching GenII Interface...")
    root = tk.Tk() # Create Root Tkinter Instance
    IOSLEEPTIME = 200
    app = GenII_Interface(root) # Create Main Application Object
    root.mainloop();
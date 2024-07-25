from matplotlib.figure import Figure
import tkinter as tk
import tkinter.ttk as ttk
import numpy as np
import time, csv, serial, sys, glob
import serial.tools.list_ports
from tkinter.filedialog import askopenfilename, asksaveasfilename
from matplotlib.backends.backend_tkagg import (FigureCanvasTkAgg,  
NavigationToolbar2Tk)

class GenII_Interface:

    def __init__(self, root):
        self.deviceStatus = tk.StringVar()
        self.deviceStatus.set("No Devices Connected")
        self.eqcStatus = tk.StringVar()
        self.eqcStatus.set("EQC has not been run today")
        self.frameList = []
        self.frame_ctr = -1
        self.plot1 = None
        self.SerialObj = None
        self.str_filePath = tk.StringVar()
        self.str_runT = tk.StringVar(value = "30")
        self.str_incTemp = tk.StringVar(value = "37")
        self.str_currentTemp = tk.StringVar(value= "N/A")
        self.str_tpeak_est = tk.StringVar(value = "0s")
        self.str_deltaEps_est = tk.StringVar(value = "0")
        self.str_tpeak_est_conf = tk.StringVar(value = "0%")
        self.str_deltaEps_est_conf = tk.StringVar(value = "0%")
        self.frameList.append(self.createTopWindow(root)) # Create a top window element for root instance
        self.frameList.append(self.createParamWindow(root))
        self.frameList.append(self.creatTestRunWindow(root))
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
        btn_newTest = ttk.Button(fr_main, text = "Setup New Test", style = "AccentButton", command = self.forward)
        btn_connect.grid(row = 0, column = 0, pady = 5)
        btn_EQC.grid(row = 1, column = 0, pady = 5)
        btn_newTest.grid(row = 2, column = 0, pady = 5)

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
        lbl_deviceStatus.grid(row = 0, column = 2, padx = 5, pady = 5)
        lbl_eqcStatus.grid(row = 1, column = 2, padx = 5, pady = 5)

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

        # Flush Buffers
        SerialObj.reset_input_buffer()
        SerialObj.reset_output_buffer()

        # Wakeup and Check Connection Status Command. Function is blocking until timeout
        try: 
            SerialObj.write(b'C') 
        except: # Timeout exception
             self.deviceStatus.set("Failed to Write to COM Port")
             return
        
        print("Connection Command Written to Port")

        # Wait for MCU to Process and write return data

        time.sleep(1)
        
        try: 
            statusReturn = SerialObj.read(SerialObj.in_waiting)  # MCU should have acknowledged write and responded with single byte, 'K'
        except: # Timeout exception
             self.deviceStatus.set("Failed to Read from COM Port")
             return

        if not statusReturn or statusReturn != b'K':
            self.deviceStatus.set("Device Failed to Connect")
            print("Device did not acknowledge connection request")
            return
        
        # Update UI with connection status
        self.deviceStatus.set("Device Successfully Connected")
        self.cv_statusLights.itemconfig(self.light_connect, fill="green")

        # Return open serial object for future communications
        self.SerialObj = SerialObj
    
    def performEQC(self):
        try: 
            self.SerialObj.write(b'Q')
        except: 
            self.eqcStatus.set("Failed to Write to COM Port")
            return
        
        self.eqcStatus.set("Waiting for EQC to complete")
        time.after(3000, self.finishEQC) # Non-blocking wait until calibration has finished
        return
    
    def finishEQC(self):
        try: 
            EQCReturn = self.SerialObj.read(1)  # MCU should have acknowledged write and responded with single byte, 'K'
        except: # Timeout exception
             self.eqcStatus.set("Failed to Read from COM Port")
             return
        
        if EQCReturn != b'K':
            return
    
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

    # Command board to begin taking measurements and sending data    
    def beginMeasurement(self):

        # Flush Buffers
        self.SerialObj.reset_input_buffer()
        self.SerialObj.reset_output_buffer()

        filePath = self.str_filePath.get()
        # Clear output file and write header
        with open(filePath, 'w', newline = '') as output_file:
            csv_writer = csv.writer(output_file, delimiter = ',', quoting = csv.QUOTE_NONNUMERIC, quotechar='|')
            csv_writer.writerow(['Sample', 'Measurement'])
        
        # Reopen file in append mode to continuously write data
        output_file = open(filePath, 'a', newline = '')
        csv_writer = csv.writer(output_file, delimiter = ',', quoting=csv.QUOTE_NONNUMERIC)

        BUFFER_THRESHOLD = 1024;
        #self.SerialObj.timeout = 10;

        try: 
            self.SerialObj.write(b'N')
            self.SerialObj.timeout = 2
        except: 
            self.eqcStatus.set("Failed to Start test to COM Port")
            return
        
        # Data will be periodically transmitted by the device to the input buffer (1024 Bytes).
        N_Measurements = 10

        # Attempts to read half of the buffer. Returns when 512 bytes are read, 
        # timeout is reached, or newline character is read
        
        max_code = 2**16 -1
        ref_v = 3
        rx_data = []
        i = 1
        # Loop to collect data from device
        while 1:
            data = self.SerialObj.read_until(b"eor") # Read until new line from device or until timeout (5000 msec)
            v = len(data)
            data = data[0:-3] # Remove stop bytes
            #print("Data Read: %d" % v)
            if len(data) < 2:
                break
            for msb, lsb in zip(data[0::2], data[1::2]):
                    parsed_data = ref_v * ((msb << 8) + lsb)/max_code
                    #print(parsed_data)
                    rx_data.append(parsed_data)
                    #count+=1
            self.SerialObj.write(b'K') # Send all clear to receive more data

        # Finally write to file
        for x in rx_data:
            csv_writer.writerow([i, x])
            i+=1
        
        # End of Experiment
        output_file.close();
        print("%d samples successfully read" % (i-1))
        
        # Plot Data
        self.plotData(filePath)
        return

    # Loads data from a file and plots it on the interface
    def plotData(self, readDataFilePath):
        
        xdata = []
        ydata = []
        self.plot1.clear()
        with open(readDataFilePath, newline='') as read_file:
            csv_reader = csv.DictReader(read_file, quoting=csv.QUOTE_NONNUMERIC, delimiter=',', quotechar='|')
            for row in csv_reader:
               xdata.append(row['Sample'])
               ydata.append(row['Measurement'])
        self.plot1.plot(xdata, ydata, marker = 'o', fillstyle = 'full')
        self.plot1.set_xlim(-1, np.max(xdata)+1)
        self.plot1.set_ylim(np.min(ydata)*0.9 - 1, np.max(ydata)*1.3 + 1)
        self.canvas.draw()
        return


# Main Program Execution
if __name__ == "__main__":
    print("Launching GenII Interface...")
    root = tk.Tk() # Create Root Tkinter Instance
    app = GenII_Interface(root) # Create Main Application Object
    root.mainloop();
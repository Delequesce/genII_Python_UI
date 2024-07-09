from matplotlib.figure import Figure
import tkinter as tk
import tkinter.ttk as ttk
import numpy as np
import serial
import time
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
        root.tk.call('source', '../Azure-ttk-theme/azure.tcl')
        #style.theme_use('azure')
        root.tk.call("set_theme", "azure")
        style.configure("AccentButton", foreground = 'white')

        # Frames and canvases
        fr_main = ttk.Frame(root);
        cv_statusLights = tk.Canvas(fr_main, width = 100, height = 100)
        #fr_main.pack()
        
        # Buttons
        btn_connect = ttk.Button(fr_main, text = "Connect to Device", style = "Accent.TButton", command = self.connectToDevice)
        btn_EQC = ttk.Button(fr_main, text = "Perform Daily EQC", style = "Accent.TButton", command = self.performEQC)
        btn_newTest = ttk.Button(fr_main, text = "Setup New Test", style = "Accent.TButton", command = self.forward)
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
        btn_next = ttk.Button(fr_params, text = "Continue", style = "Accent.TButton", command = self.forward)
        btn_back = ttk.Button(fr_params, text = "Back", style = "Accent.TButton", command = self.previous)
        btn_fileEdit = ttk.Button(fr_filePath, text = "...", style = "Accent.TButton", command = self.openSaveDialog)
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
        btn_startHeating = ttk.Button(fr_leftInfo, text = "Start Heating", style = "Accent.TButton", command = self.startHeating)
        btn_beginMeasurement = ttk.Button(fr_leftInfo, text = "Begin Measurement", style = "Accent.TButton", command = self.beginMeasurement)
        btn_back  = ttk.Button(fr_leftInfo, text = "Back", style = "Accent.TButton", command = self.previous)

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
        btn_back.grid(row = 3, column = 0, columnspan=2)
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

        # Visual Frame
        canvas = FigureCanvasTkAgg(fig, master = fr_vis)
        canvas.draw()
        canvas.get_tk_widget().pack()

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


    # Button Callback Functions
    def connectToDevice(self):
        ret = 0;
        try:
            SerialObj = serial.Serial('/dev/ttyS3') # Port is immediately opened upon creation. 
        except:
            self.deviceStatus.set("Failed to Access COM Port")
            return

        SerialObj.baudrate = 115200
        SerialObj.bytesize = 8
        SerialObj.partiy = 'N'
        SerialObj.stopbits = 1
        SerialObj.timeout = 5  # 5 second wait

        time.sleep(3) 
        try: 
            SerialObj.write(b'C') # Wakeup and Check Connection Status Command. Function is blocking until timeout
        except: # Timeout exception
             self.deviceStatus.set("Failed to Write to COM Port")
             return
        time.sleep(1) # Wait for MCU to Process and write return data
        try: 
            statusReturn = SerialObj.read(1)  # MCU should have acknowledged write and responded with single byte, 'K'
        except: # Timeout exception
             self.deviceStatus.set("Failed to Read from COM Port")
             return

        if statusReturn != b'K':
            self.deviceStatus.set("Device Failed to Connect")
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
        return
    
    def beginMeasurement(self):
        return


# Main Program Execution
if __name__ == "__main__":
    print("Launching GenII Interface...")
    root = tk.Tk() # Create Root Tkinter Instance
    app = GenII_Interface(root) # Create Main Application Object
    root.mainloop();
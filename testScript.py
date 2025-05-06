from GenII_Interface import GenII_Interface
import tkinter as tk
import numpy as np
import traceback
import os

class TestingScript:

    def __init__(self):
        self.root = tk.Tk() # Create Root Tkinter Instance
        self.root.geometry("480x272")
        self.root.minsize(480,272)
        self.root.maxsize(480,272)
        IOSLEEPTIME = 500
        ERR_IOSLEEPTIME = 200
        self.app = GenII_Interface(self.root, use_mq=False, device_present=False) # Create Main Application Object
    
    # Basic things that should be run for most tests
    def setUp(self):
        pass
        
    def observeInterface(self):
        self.app.root.mainloop()
        return

    def test_finishTest(self):

        # Necessary Setup
        self.app.channelList = [0,1,2,3]
        for chan in self.app.channelList:
            self.app.str_tpeak_est[chan].set("1")
        N = 5
        self.app.DataMat = np.random.rand(N, 8)
        self.app.countData = range(N+1)
        self.app.filePath = "NewDataFile.csv"
        self.app.isMeasuring = True

        os.system(f"cp DataFileTemplate.csv {self.app.filePath}")

        # Run test
        try:
            self.app.finishTest()
        except Exception as e:
            print(traceback.format_exc())
            #print(e)
        print("Random Data Matrix")
        print(self.app.DataMat)

    def test_fullMeasurement(self):
        self.app.noSerial = True
        self.app.fakeData = True
        self.app.NUMDATAMAX = 1800
        self.app.str_filePath.set("DataFile2.csv")

        # FakeDataFile.csv has to be populated for this to work
        self.app.root.protocol("WM_DELETE_WINDOW", self.app.on_close)
        self.app.root.mainloop()

        pass

if __name__ == "__main__":
    testObj = TestingScript()
    testObj.observeInterface()
    #testObj.setUp()
    #testObj.test_finishTest()
    #testObj.test_fullMeasurement()
    #testObj.app.root.destroy()
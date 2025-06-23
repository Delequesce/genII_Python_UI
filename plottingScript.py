import matplotlib.pyplot as plt
import csv
import sys
import numpy as np

MAX_VECTOR_SIZE = 7200
t = np.zeros((MAX_VECTOR_SIZE, 1), dtype=np.float64)
CData_Raw = np.zeros((MAX_VECTOR_SIZE, 4), dtype=np.float64)
GData = np.zeros((MAX_VECTOR_SIZE, 4), dtype=np.float64)
temperatureData = np.zeros((MAX_VECTOR_SIZE, 1), dtype=np.float64)
CData_Norm = np.zeros((MAX_VECTOR_SIZE, 4), dtype=np.float64)


rowCounter = 0
I = 0
with open(sys.argv[1]) as template_file:#open("DataFileTemplate.csv")
    readerObj = csv.reader(template_file, delimiter=',')
    discard = None
    for row in readerObj:
        if rowCounter < 17:
            rowCounter = rowCounter + 1
            continue

        # Add incoming data to submatrices
        I = rowCounter-17
        t[I] = np.float64(row[0])
        #print(t[I])
        CData_Raw[I][:] = np.float64(row[1:5])
        #print(np.float64(row[1:5]))
        GData[I][:] = np.float64(row[5:9])
        temperatureData[I] = np.float64(row[9])
        CData_Norm[I][:] = np.float64(row[10:15])
        # Increment row counter
        rowCounter = rowCounter + 1

        #if rowCounter > 100:
        #    break

N = I-1

# Plotting
variableToPlot = 'c'
normOrRaw = 'norm'
channels = (0, 1, 2, 3)
l = len(sys.argv)
if l > 4:
    channels = tuple(eval(sys.argv[4]))
if l > 3:
    normOrRaw = sys.argv[3].lower()
if l > 2:
    variableToPlot = sys.argv[2].lower()

if variableToPlot == 'c' and normOrRaw == 'raw':
    plt.plot(t[0:N], CData_Raw[0:N, channels])
    plt.xlabel('Time (min)')
    plt.ylabel('Capacitance (pF)')
elif variableToPlot == 'c' and normOrRaw == 'norm':
    plt.plot(t[0:N], CData_Norm[0:N, channels])
    plt.xlabel('Time (min)')
    plt.ylabel('Normalized Real Permittivity')
elif variableToPlot == 'g':
    plt.plot(t[0:N], GData[0:N, channels])
    plt.xlabel('Time (min)')
    plt.ylabel('Conductance (mS)')
elif variableToPlot == 'temperature':
    plt.plot(t[0:N], temperatureData[0:N])
    plt.xlabel('Time (min)')
    plt.ylabel('Capacitance (pF)')
else:
    print("Invalid plotting parameters. Please put 'c', 'g', or 'temperature' and either 'raw' or 'norm'")
    quit()

plt.legend(['Channel 1', 'Channel 2', 'Channel 3', 'Channel 4'])
plt.show()
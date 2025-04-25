import serial
import signal
import posix_ipc
from GracefulExit import GracefulExit as ge
import time
import subprocess
import os


class UART_Manager:

    # Constants
    QUEUE_NAME_UAUI = "/uart_ui_message_queue"
    QUEUE_NAME_UIUA = "/ui_uart_message_queue"
    MY_SIGNAL = signal.SIGUSR1
    GENIIPORT = "/dev/serial0" # For main system using Raspberry Pi
    #GENIIPORT = "/dev/ttyACM0" # This is for my cpu acting in place of the pi for testing
    MCUCODES = bytearray("BCDEQTXZ", 'ascii')
    IOSLEEPTIME = 0.1 # In sec
    DEFAULT_WRITE_ATTEMPTS = 2
    DEFAULT_MESSAGE_READ = 3
    # - B: Battery Level
    # - C: Calibration Data
    # - D: Regular Impedance Data
    # - E: Error/General Messages
    # - Q: EQC Data
    # - T: Temperature Measurements
    # - X: Measurement stop
    # - Z: Messages to bypass UI

    def __init__(self):

        # Basic Variables
        #self.dontInterrupt = True
        self.ui_connected = False
        self.testing = False # Used for testing without a serial port
        self.output_waiting = False

        # Set up graceful exiter for keyboard interrupts
        self.flag = ge()

        # Create the message queues.
        self.mq_outbox = posix_ipc.MessageQueue(self.QUEUE_NAME_UAUI, posix_ipc.O_CREX)
        self.mq_inbox = posix_ipc.MessageQueue(self.QUEUE_NAME_UIUA, posix_ipc.O_CREX)

        # Request notifications for queue from ui
        self.mq_inbox.request_notification(self.MY_SIGNAL)

        # Register my signal handler
        signal.signal(self.MY_SIGNAL, self.handle_signal)

        # Set up serial port and connect to MCU
        if self.testing:
            self.serialObject = None
        else:
            self.setUpSerialPort(self.GENIIPORT)
        return

    # Callback function for handling the specified user signal
    def handle_signal(self, signal_number, stack_frame):
        self.output_waiting = True

    # Set up serial object and connect to device
    def setUpSerialPort(self, port_name):
        SerialObj = serial.Serial(baudrate = 115200, timeout = 5, 
                            bytesize=8, parity='N', stopbits=1)
        
        SerialObj.port=port_name # If you don't specify it in the constructor, you have to call .open() to open it later
        try:
            print("Attempting connection to %s" % str(port_name))
            SerialObj.open()
            print("Port Succesfully Opened")
        except Exception as e:
            #self.deviceStatus.set("Failed to Access COM Port")
            print(e)
            return None
        
        # Reset buffers
        SerialObj.reset_input_buffer()
        SerialObj.reset_output_buffer()

        self.serialObject = SerialObj
        # Make sure the MCU is on the other side
        if not self.deviceAck(self.DEFAULT_MESSAGE_READ, self.DEFAULT_WRITE_ATTEMPTS, b'C\n'):
            print("No acknowledgement from device")
            return None
        
        print("Connection to MCU Acknowledged")

        # Optionally write new test command to observe data out before involving UI
        # input()
        # if not self.deviceAck(self.DEFAULT_MESSAGE_READ, self.DEFAULT_WRITE_ATTEMPTS, b'N\n'):
        #     print("Test Failed to Start")
        #     return None

        return

    
    # Function that sends commands to MCU and checks for appropriate acknowledgement
    def deviceAck(self, N_Count, N_Attempt, writeData):

        if self.testing:
            ret =  self.deviceAckTesting(N_Count, N_Attempt, writeData)
            #print ("Returned Value: %d" % ret)
            return ret
        
        self.serialObject.timeout = 1
        #self.dontInterrupt = True
        acked = False
        attemptCounter = 0
        while attemptCounter < N_Attempt:
            count = 0
            try: 
                #print("Attempting to Write Command")
                self.serialObject.write(writeData)
            except: 
                print("Write Error to COM Port")

            time.sleep(0.05)

            #print("Waiting for Ack")
            while count < N_Count:
                response = self.serialObject.readline()
                #print(response)
                acked = (response == b'K\n')
                if acked:
                    print("Command Acknowledged")
                    #self.dontInterrupt = False
                    self.serialObject.timeout = None
                    return 1

                count+=1
            attemptCounter+=1

        #self.dontInterrupt = False
        self.serialObject.timeout = None
        return 0

    # Function that sends commands to MCU and checks for appropriate acknowledgement
    def deviceAckTesting(self, N_Count, N_Attempt, writeData):
        
        acked = False
        attemptCounter = 0
        while attemptCounter < N_Attempt:
            count = 0
            try: 
                #print("Attempting to Write Command")
                print(writeData)
            except: 
                print("Write Error to COM Port")

            time.sleep(0.1)

            #print("Waiting for Ack")
            while count < N_Count:
                #print("Enter 'K' to acknowledge")
                #acked = (bytes(input()) == b'K')
                acked = True
                if acked:
                    #print("Command Acknowledged")
                    return 1

                count+=1
            attemptCounter+=1

        return 0

    # def readAndDecode(self):
    #     line = self.SerialObj.readline()
    #     # try:
    #     #     # Converts Bytearray into string (char array)
    #     #     decoded_line = line.decode(encoding='ascii')
    #     # except Exception as e:
    #     #     print(e)
    #     #     return None

    #     return line

    # Run loop to wait for serial port events. Should have blocking read calls to allow CPU to thread intelligently
    def mainloop(self):

        self.serialObject.timeout = None
        while True: 

            # Check for keyboard interrupt 
            if self.flag.exit():
                self.on_exit()
                break

            # Handle writes to MCU
            if self.output_waiting:
                message, priority = self.mq_inbox.receive()
                #message = message.decode('ascii')

                print("Message received: %s" % (message))

                # Register prescence of UI
                if message == b'END':
                    self.ui_connected = False
                    print("UI Disconnected")
                    self.mq_outbox.send(b'K')
                else:
                    self.ui_connected = True
                    # Forward command to MCU and let UI know it was successfully transmitted
                    if self.deviceAck(self.DEFAULT_MESSAGE_READ, self.DEFAULT_WRITE_ATTEMPTS, message):
                        print("Ack Sent to UI")
                        self.mq_outbox.send(b'K')
                    else:
                        self.mq_outbox.send(b'V')

                # Re-register for notifications
                self.output_waiting = False
                self.mq_inbox.request_notification(self.MY_SIGNAL)

            # Read single control character and then decide what action to take
            validCharacter = False
            #print(self.serialObject.in_waiting)
            for j in range(self.serialObject.in_waiting):
                controlChar = self.serialObject.read(1)
                #print(f"j: {j}, controlChar: {controlChar}")
                #print(f"Character {controlChar}")
                # Check if control character is a permitted value
                if controlChar not in self.MCUCODES:
                    #print("Unknown control character. Ignoring")
                    continue
                else:
                    #print("Character Found")
                    #print(controlChar)
                    validCharacter = True
                    break
                
                #print("Final Character:")
                #print(controlChar)
                # Set a flag
                #print("Valid Character Found: %s" % controlChar)

            if not validCharacter:
                # Invoke scheduler  
                time.sleep(self.IOSLEEPTIME)
                continue

            # If control character was valid, read the rest of the message
            message = self.serialObject.readline()
            #print("Message:")
            #print(message)
            # print("Character: ")
            # print(controlChar)

            # For commands that don't need UI involvement
            if message[0] == 90:
                if message[0:3] == b'ZZZ':
                    # Clean up serial port and message queues. Also lets MCU know that command was succesfully received
                    self.on_exit()
                    print("Shutdown System Commanded")
                    os.system(["sudo shutdown -h now"])
                else: 
                    print(message)
                continue

            # No need to post messages if there is noone listening
            if not self.ui_connected:
                continue

            # For everything else, forward to UI
            if self.mq_outbox.current_messages > 3:
                #print("Outbox is full!!!")
                self.mq_outbox.receive()

            # Add back the controlCharacter so the UI can understand what to do with it
            message = controlChar + message
            #print("Sending message to UI:")
            #print(message)
            self.mq_outbox.send(message)

        return
    
    # Testing version (no serial)
    def mainloopTesting(self):
        i = 0
        while True: 
            
            i = i + 1
            # Check for keyboard interrupt 
            if self.flag.exit():
                self.on_exit()
                break

            # Handle writes to MCU
            if self.output_waiting:
                message, priority = self.mq_inbox.receive()
                #message = message.decode('ascii')

                print("Message received: %s" % (message))

                # Register prescence of UI
                if message == b'END':
                    self.ui_connected = False
                    self.mq_outbox.send(b'K')
                else:
                    self.ui_connected = True
                    # Forward command to MCU and let UI know it was successfully transmitted
                    #print("Checking for acknowledgement")
                    if self.deviceAck(self.DEFAULT_MESSAGE_READ, self.DEFAULT_WRITE_ATTEMPTS, message):
                        #print("Response sent to UI")
                        #print("Current Outbox Message Count: %d" % self.mq_outbox.current_messages)
                        self.mq_outbox.send(b'K')
                    else:
                        self.mq_outbox.send(b'V')
                
                # Re-register for notifications
                self.output_waiting = False
                self.mq_inbox.request_notification(self.MY_SIGNAL)

            #print("Entering Serial Read Section")
            # Read single control character and then decide what action to take
            if i % 100  == 0:
                controlChar = b'E'
                message = b"Hello World\n"
            
                # Check if control character is a permitted value
                if controlChar not in self.MCUCODES:
                    print("Unknown control character. Ignoring")
                    continue

                # If control character was valid, read the rest of the message
                #print("Enter a message for the UI")
                #message = bytes(input(), 'ascii')
                #message = self.serialObject.readline()

                # For commands that don't need UI involvement
                if controlChar == b'Z':
                    if message == b'ZZZ':
                        print("Shutdown System Commanded")
                        #subprocess.run(["sudo shutdown -h now"])
                    else: 
                        print(message)
                    continue

                # No need to post messages if there is noone listening
                if not self.ui_connected:
                    continue

                # For everything else, forward to UI
                if self.mq_outbox.current_messages > 3:
                    self.mq_outbox.receive()

                print("Sending message to UI: " % message)
                # Add back the controlCharacter so the UI can understand what to do with it
                message = controlChar + message
                self.mq_outbox.send(message)
            else:
                # Invoke scheduler    
                time.sleep(self.IOSLEEPTIME)

        return

    def on_exit(self):

        # Send Disconnect Command to MCU
        print("Stopping Any Active Tests")
        self.deviceAck(self.DEFAULT_MESSAGE_READ, self.DEFAULT_WRITE_ATTEMPTS, b'X\n')

        print("Disconnecting from MCU")
        self.deviceAck(self.DEFAULT_MESSAGE_READ, self.DEFAULT_WRITE_ATTEMPTS, b'Y\n')

        # Destroy Message Queues
        print("Destroying the message queues.")
        self.mq_inbox.close()
        self.mq_outbox.close()
        posix_ipc.unlink_message_queue(self.QUEUE_NAME_UIUA)
        posix_ipc.unlink_message_queue(self.QUEUE_NAME_UAUI)

        # Close Serial Port
        print("Closing Serial Port")
        self.serialObject.close()

        return


if __name__ == "__main__":
    print("Launching UART Manager")
    
    # Create class instance
    um = UART_Manager()
    if um.testing:
        um.mainloopTesting()
        exit()

    if not um.serialObject:
        print("Error Initializing UART Manager. Exiting...")
        exit()

    # Do something...
    um.mainloop()

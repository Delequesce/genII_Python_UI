import posix_ipc
import serial

QUEUE_NAME_UAUI = "/uart_ui_message_queue"
QUEUE_NAME_UIUA = "/ui_uart_message_queue"

PORTNAME = "/dev/ttyACM0"

try:
    posix_ipc.unlink_message_queue(QUEUE_NAME_UAUI)
    s = "message queue %s removed" % QUEUE_NAME_UAUI
    print(s)
except:
    print("queue doesn't need cleanup")

try:
    posix_ipc.unlink_message_queue(QUEUE_NAME_UIUA)
    s = "message queue %s removed" % QUEUE_NAME_UIUA
    print(s)
except:
    print("queue doesn't need cleanup")

try:
    SerialObj = serial.Serial()
    SerialObj.port = PORTNAME
    print(SerialObj)
    SerialObj.close()
    print("Serial Port Closed")

except:
    print("port doesn't need closing")

print("\nAll clean!")

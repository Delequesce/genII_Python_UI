import signal

class GracefulExit:

    def __init__(self):
        self.state = False
        # Overwrite interrupt handler with custom
        signal.signal(signal.SIGINT, self.change_state)

    def change_state(self, signum, frame):
        self.state = True
        # Change interrupt handler back to default
        print("\nInterrupt Received")
        signal.signal(signal.SIGINT, signal.SIG_DFL)

    def exit(self):
        return self.state
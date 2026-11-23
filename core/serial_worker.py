import serial
import threading

from PySide6.QtCore import QThread, Signal


class SerialWorker(QThread):

    data_received = Signal(bytes)
    connection_status = Signal(bool, str)

    def __init__(self, port, baudrate=115200):
        super().__init__()

        self.port = port
        self.baudrate = baudrate

        self.serial_port = None
        self.running = False

        self.serial_lock = threading.Lock()

    def run(self):

        try:
            self.serial_port = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=0.1,
                write_timeout=1
            )

            self.running = True

            self.connection_status.emit(
                True,
                f"Connected to {self.port}"
            )

            while self.running:

                if self.serial_port.in_waiting:
                    data = self.serial_port.read(
                        self.serial_port.in_waiting
                    )

                    if data:
                        self.data_received.emit(data)

        except serial.SerialException as error:

            self.connection_status.emit(
                False,
                str(error)
            )

        finally:

            self.running = False

            with self.serial_lock:

                if self.serial_port and self.serial_port.is_open:
                    self.serial_port.close()

                self.serial_port = None

            self.connection_status.emit(
                False,
                "Disconnected"
            )

    def send_data(self, data: bytes):

        try:
            with self.serial_lock:

                if self.serial_port and self.serial_port.is_open:
                    return self.serial_port.write(data)

        except serial.SerialException as error:

            self.connection_status.emit(
                False,
                f"TX error: {error}"
            )

        return 0

    def stop(self):

        self.running = False
        self.wait()
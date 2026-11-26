from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QComboBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QLabel,
    QLineEdit,
    QCheckBox,
    QHeaderView,
    QAbstractItemView
)

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QFileDialog, QMessageBox

from serial.tools import list_ports

from core.serial_worker import SerialWorker
from core.log_storage import LogStorage
from parsers.log_parser import LogParser, ParsedMessage

from pathlib import Path

class MainWindow(QMainWindow):

    LOG_COLORS = {
        "err": "#ff5555",
        "wrn": "#ffcc33",
        "inf": "#55cc88",
        "dbg": "#aaaaaa",
    }

    MAX_ROWS = 5000

    def __init__(self):

        super().__init__()

        self.setWindowTitle("ESP32 Serial Analyzer v0.3")
        self.resize(1200, 750)

        self.worker = None
        self.log_parser = LogParser()
        self.log_storage = LogStorage()
        self.viewing_log = False
        self.loading_log = False

        self.rx_bytes = 0
        self.tx_bytes = 0

        self.init_ui()
        self.refresh_ports()

    # -------------------------------------------------
    # UI
    # -------------------------------------------------

    def init_ui(self):

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)

        # CONNECTION PANEL

        connection_layout = QHBoxLayout()

        self.port_combo = QComboBox()
        self.baud_combo = QComboBox()

        self.baud_combo.addItems([
            "9600",
            "19200",
            "38400",
            "57600",
            "115200",
            "230400",
            "460800",
            "921600"
        ])

        self.baud_combo.setCurrentText("115200")

        self.refresh_button = QPushButton("Refresh")
        self.connect_button = QPushButton("Connect")
        self.disconnect_button = QPushButton("Disconnect")

        self.disconnect_button.setEnabled(False)

        connection_layout.addWidget(QLabel("Port:"))
        connection_layout.addWidget(self.port_combo)

        connection_layout.addWidget(QLabel("Baud:"))
        connection_layout.addWidget(self.baud_combo)

        connection_layout.addWidget(self.refresh_button)
        connection_layout.addWidget(self.connect_button)
        connection_layout.addWidget(self.disconnect_button)

        main_layout.addLayout(connection_layout)

        # STATUS

        self.status_label = QLabel("Disconnected")

        main_layout.addWidget(self.status_label)

        # FILTER PANEL

        filter_layout = QHBoxLayout()

        filter_layout.addWidget(QLabel("Log filters:"))

        self.filters = {}

        for level in ["err", "wrn", "inf", "dbg", "other"]:

            checkbox = QCheckBox(level.upper())
            checkbox.setChecked(True)

            checkbox.stateChanged.connect(
                self.apply_filters
            )

            self.filters[level] = checkbox

            filter_layout.addWidget(checkbox)

        filter_layout.addStretch()

        main_layout.addLayout(filter_layout)

        # LOG TABLE

        self.log_table = QTableWidget()

        self.log_table.setColumnCount(4)

        self.log_table.setHorizontalHeaderLabels([
            "TIME",
            "LEVEL",
            "MODULE",
            "MESSAGE"
        ])

        self.log_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )

        self.log_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )

        self.log_table.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection
        )

        self.log_table.verticalHeader().setVisible(False)

        header = self.log_table.horizontalHeader()

        header.setSectionResizeMode(
            0,
            QHeaderView.ResizeMode.ResizeToContents
        )

        header.setSectionResizeMode(
            1,
            QHeaderView.ResizeMode.ResizeToContents
        )

        header.setSectionResizeMode(
            2,
            QHeaderView.ResizeMode.ResizeToContents
        )

        header.setSectionResizeMode(
            3,
            QHeaderView.ResizeMode.Stretch
        )

        self.log_table.setAlternatingRowColors(True)

        main_layout.addWidget(self.log_table)

        # COMMAND PANEL

        command_layout = QHBoxLayout()

        self.command_input = QLineEdit()

        self.command_input.setPlaceholderText(
            "Enter command..."
        )

        self.command_format = QComboBox()

        self.command_format.addItems([
            "ASCII",
            "HEX"
        ])

        self.send_button = QPushButton("SEND")

        self.newline_checkbox = QCheckBox(
            "Append newline"
        )

        self.newline_checkbox.setChecked(True)

        command_layout.addWidget(QLabel(">"))
        command_layout.addWidget(self.command_input)
        command_layout.addWidget(self.command_format)
        command_layout.addWidget(self.send_button)
        command_layout.addWidget(self.newline_checkbox)

        main_layout.addLayout(command_layout)

        # BOTTOM PANEL

        bottom_layout = QHBoxLayout()

        self.clear_button = QPushButton("Clear log")

        self.start_logging_button = QPushButton("Start Logging")
        self.stop_logging_button = QPushButton("Stop Logging")
        self.save_log_button = QPushButton("Save Log As...")
        self.open_log_button = QPushButton("Open Log")
        self.return_live_button = QPushButton("Return to Live")

        self.stop_logging_button.setEnabled(False)
        self.return_live_button.setEnabled(False)

        self.logging_status_label = QLabel("Logging: OFF")

        self.counter_label = QLabel(
            "RX: 0 bytes | TX: 0 bytes"
        )

        bottom_layout.addWidget(self.clear_button)
        bottom_layout.addSpacing(15)

        bottom_layout.addWidget(self.start_logging_button)
        bottom_layout.addWidget(self.stop_logging_button)
        bottom_layout.addWidget(self.save_log_button)

        bottom_layout.addWidget(self.logging_status_label)
        bottom_layout.addWidget(self.open_log_button)
        bottom_layout.addWidget(self.return_live_button)

        bottom_layout.addStretch()

        bottom_layout.addWidget(self.counter_label)

        main_layout.addLayout(bottom_layout)

        # EVENTS

        self.refresh_button.clicked.connect(
            self.refresh_ports
        )

        self.connect_button.clicked.connect(
            self.connect_serial
        )

        self.disconnect_button.clicked.connect(
            self.disconnect_serial
        )

        self.send_button.clicked.connect(
            self.send_command
        )

        self.command_input.returnPressed.connect(
            self.send_command
        )

        self.clear_button.clicked.connect(
            self.clear_log
        )

        self.start_logging_button.clicked.connect(
            self.start_logging
        )

        self.stop_logging_button.clicked.connect(
            self.stop_logging
        )

        self.save_log_button.clicked.connect(
            self.save_log_as
        )

        self.open_log_button.clicked.connect(
            self.open_log
        )

        self.return_live_button.clicked.connect(
            self.return_to_live
        )

    # -------------------------------------------------
    # SERIAL CONNECTION
    # -------------------------------------------------

    def refresh_ports(self):

        current_port = self.port_combo.currentData()

        self.port_combo.clear()

        for port in list_ports.comports():

            self.port_combo.addItem(
                port.device,
                port.device
            )

        index = self.port_combo.findData(current_port)

        if index >= 0:
            self.port_combo.setCurrentIndex(index)

    def connect_serial(self):

        port = self.port_combo.currentData()

        if not port:
            return

        baudrate = int(
            self.baud_combo.currentText()
        )

        self.log_parser = LogParser()

        self.worker = SerialWorker(
            port,
            baudrate
        )

        self.worker.data_received.connect(
            self.on_data_received
        )

        self.worker.connection_status.connect(
            self.on_connection_status
        )

        self.worker.start()

        self.connect_button.setEnabled(False)
        self.disconnect_button.setEnabled(True)

    def disconnect_serial(self):

        if self.worker:

            self.worker.stop()
            self.worker = None

        self.connect_button.setEnabled(True)
        self.disconnect_button.setEnabled(False)

    def on_connection_status(self, connected, message):

        self.status_label.setText(message)

        if not connected:

            self.connect_button.setEnabled(True)
            self.disconnect_button.setEnabled(False)

    # -------------------------------------------------
    # LOG PROCESSING
    # -------------------------------------------------

    def on_data_received(self, data):

        self.rx_bytes += len(data)

        self.update_counters()

        messages = self.log_parser.feed(data)

        if self.viewing_log:
            return

        for message in messages:

            self.add_log_message(message)

            if self.log_storage.is_logging:
                self.log_storage.write_message(message)

    def add_log_message(self, message):

        table = self.log_table

        if not self.loading_log and table.rowCount() >= self.MAX_ROWS:
            table.removeRow(0)

        row = table.rowCount()

        table.insertRow(row)

        level = message.level or "other"

        color = self.LOG_COLORS.get(
            level,
            "#dddddd"
        )

        values = [
            message.timestamp or "",
            level.upper(),
            message.module or "",
            message.message if message.level else message.text
        ]

        for column, value in enumerate(values):

            item = QTableWidgetItem(value)

            item.setForeground(QColor(color))

            if column == 1:
                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignCenter
                )

            table.setItem(row, column, item)

        self.apply_row_filter(row)

        table.scrollToBottom()

    # -------------------------------------------------
    # FILTERS
    # -------------------------------------------------

    def apply_row_filter(self, row):

        level_item = self.log_table.item(row, 1)

        if level_item is None:
            return

        level = level_item.text().lower()

        checkbox = self.filters.get(level)

        if checkbox is None:
            checkbox = self.filters["other"]

        self.log_table.setRowHidden(
            row,
            not checkbox.isChecked()
        )

    def apply_filters(self):

        for row in range(self.log_table.rowCount()):

            self.apply_row_filter(row)

    # -------------------------------------------------
    # COMMAND TRANSMISSION
    # -------------------------------------------------

    def send_command(self):

        if not self.worker or not self.worker.isRunning():
            return

        command = self.command_input.text().strip()

        if not command:
            return

        # ASCII MODE

        if self.command_format.currentText() == "ASCII":

            data = command.encode("utf-8")

        # HEX MODE

        else:

            try:

                # Поддержка форматов:
                # FF 01 A5
                # FF01A5
                # 0xFF 0x01 0xA5

                hex_string = command.replace("0x", "")
                hex_string = hex_string.replace("0X", "")
                hex_string = hex_string.replace(" ", "")
                hex_string = hex_string.replace("\t", "")

                if len(hex_string) % 2 != 0:
                    raise ValueError(
                        "HEX string must contain pairs of digits."
                    )

                data = bytes.fromhex(hex_string)

            except ValueError as error:

                QMessageBox.warning(
                    self,
                    "Invalid HEX data",
                    str(error)
                )

                return

        # APPEND NEWLINE

        if self.newline_checkbox.isChecked():
            data += b"\n"
    
        # SEND DATA
    
        written = self.worker.send_data(data)
    
        self.tx_bytes += written
    
        self.update_counters()
    
        if written != len(data):
        
            QMessageBox.warning(
                self,
                "Transmission warning",
                f"Not all bytes were transmitted.\n"
                f"Expected: {len(data)}\n"
                f"Written: {written}"
            )
    
            return
    
        self.command_input.clear()

    # -------------------------------------------------
    # UTILITIES
    # -------------------------------------------------

    def update_counters(self):

        self.counter_label.setText(
            f"RX: {self.rx_bytes} bytes | "
            f"TX: {self.tx_bytes} bytes"
        )

    def clear_log(self):

        self.log_table.setRowCount(0)

        self.rx_bytes = 0
        self.tx_bytes = 0

        self.update_counters()

    # -------------------------------------------------
    # LOG STORAGE
    # -------------------------------------------------

    def start_logging(self):

        try:

            file_path = self.log_storage.start_logging()

            self.start_logging_button.setEnabled(False)
            self.stop_logging_button.setEnabled(True)

            self.logging_status_label.setText("Logging: ON")

            self.status_label.setText(
                f"Saving logs: {file_path.name}"
            )

        except Exception as error:

            QMessageBox.critical(
                self,
                "Logging error",
                str(error)
            )

    def stop_logging(self):

        self.log_storage.stop_logging()

        self.start_logging_button.setEnabled(True)
        self.stop_logging_button.setEnabled(False)

        self.logging_status_label.setText("Logging: OFF")

        self.status_label.setText("Logging stopped")


    def save_log_as(self):

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Log As",
            "",
            "JSON Lines (*.jsonl)"
        )

        if not file_path:
            return

        try:

            records = []

            for row in range(self.log_table.rowCount()):

                timestamp = self.log_table.item(row, 0).text()
                level = self.log_table.item(row, 1).text().lower()
                module = self.log_table.item(row, 2).text()
                message = self.log_table.item(row, 3).text()

                records.append({
                    "timestamp": timestamp or None,
                    "level": level if level != "other" else None,
                    "module": module or None,
                    "message": message,
                    "text": message
                })

            self.log_storage.save_records(
                records,
                file_path
            )

            QMessageBox.information(
                self,
                "Save Log",
                f"Log saved successfully:\n{file_path}"
            )

        except Exception as error:

            QMessageBox.critical(
                self,
                "Save error",
                str(error)
            )

    # -------------------------------------------------
    # LOG VIEWER
    # -------------------------------------------------

    def open_log(self):

        # Не допускаем смешивания текущей записи и открываемого файла.
        if self.log_storage.is_logging:

            QMessageBox.warning(
                self,
                "Logging is active",
                "Stop logging before opening another log file."
            )

            return

        # Если UART подключён, предупреждаем о переходе в режим просмотра.
        if self.worker and self.worker.isRunning():

            answer = QMessageBox.question(
                self,
                "UART is connected",
                "UART connection is active.\n\n"
                "Live messages will be temporarily hidden while "
                "viewing the saved log.\n\n"
                "Continue?",
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

            if answer != QMessageBox.StandardButton.Yes:
                return

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Log",
            str(self.log_storage.logs_dir),
            "JSON Lines (*.jsonl);;All files (*)"
        )

        if not file_path:
            return

        try:

            records = self.log_storage.load_log(file_path)

        except (OSError, UnicodeError) as error:

            QMessageBox.critical(
                self,
                "Open Log Error",
                str(error)
            )

            return

        # Загружаем файл только после успешного чтения.
        self.log_table.setRowCount(0)

        self.viewing_log = True
        self.loading_log = True

        try:

            for record in records:

                timestamp = record.get("timestamp")
                level = record.get("level")
                module = record.get("module")
                message = record.get("message")
                text = record.get("text")

                if not text:

                    text = (
                        f"[{timestamp or ''}] "
                        f"<{level or 'other'}> "
                        f"{module or ''}: "
                        f"{message or ''}"
                    )

                parsed_message = ParsedMessage(
                    text=text,
                    timestamp=timestamp,
                    level=level,
                    module=module,
                    message=message
                )

                self.add_log_message(parsed_message)

        finally:

            self.loading_log = False

        self.open_log_button.setEnabled(False)
        self.return_live_button.setEnabled(True)

        self.status_label.setText(
            f"Viewing log: {Path(file_path).name}"
        )

        self.log_table.scrollToBottom()

    def return_to_live(self):

        self.log_table.setRowCount(0)

        self.viewing_log = False

        self.open_log_button.setEnabled(True)
        self.return_live_button.setEnabled(False)

        if self.worker and self.worker.isRunning():

            self.status_label.setText(
                "Connected - Live monitoring"
            )

        else:

            self.status_label.setText(
                "Disconnected"
            )
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

from serial.tools import list_ports

from core.serial_worker import SerialWorker
from parsers.log_parser import LogParser


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

        self.setWindowTitle("ESP32 Serial Analyzer v0.2")
        self.resize(1200, 750)

        self.worker = None
        self.log_parser = LogParser()

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

        self.send_button = QPushButton("SEND")

        self.newline_checkbox = QCheckBox(
            "Append newline"
        )

        self.newline_checkbox.setChecked(True)

        command_layout.addWidget(QLabel(">"))
        command_layout.addWidget(self.command_input)
        command_layout.addWidget(self.send_button)
        command_layout.addWidget(self.newline_checkbox)

        main_layout.addLayout(command_layout)

        # BOTTOM PANEL

        bottom_layout = QHBoxLayout()

        self.clear_button = QPushButton("Clear log")

        self.counter_label = QLabel(
            "RX: 0 bytes | TX: 0 bytes"
        )

        bottom_layout.addWidget(self.clear_button)
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

        for message in messages:

            self.add_log_message(message)

    def add_log_message(self, message):

        table = self.log_table

        if table.rowCount() >= self.MAX_ROWS:
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

        command = self.command_input.text()

        if not command:
            return

        data = command.encode("utf-8")

        if self.newline_checkbox.isChecked():
            data += b"\n"

        written = self.worker.send_data(data)

        self.tx_bytes += written

        self.update_counters()

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
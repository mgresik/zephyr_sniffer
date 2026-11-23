import re

from dataclasses import dataclass
from typing import Optional


@dataclass
class ParsedMessage:
    text: str
    timestamp: Optional[str] = None
    level: Optional[str] = None
    module: Optional[str] = None
    message: Optional[str] = None


class LogParser:

    # ANSI CSI escape sequences
    ANSI_PATTERN = re.compile(
        r'\x1b\[[0-?]*[ -/]*[@-~]'
    )

    # Zephyr log format
    LOG_PATTERN = re.compile(
        r'^\[([^\]]+)\]\s*'
        r'<(err|wrn|inf|dbg)>\s*'
        r'([^:]+):\s*(.*)$',
        re.IGNORECASE
    )

    MAX_LINE_LENGTH = 65536

    def __init__(self):
        self.buffer = bytearray()

    def feed(self, data: bytes):

        self.buffer.extend(data)

        messages = []

        while True:

            try:
                newline_pos = self.buffer.index(b'\n')
            except ValueError:
                break

            raw_line = bytes(self.buffer[:newline_pos])

            del self.buffer[:newline_pos + 1]

            # Remove CR from CRLF
            raw_line = raw_line.rstrip(b'\r')

            text = raw_line.decode(
                'utf-8',
                errors='replace'
            )

            message = self.parse_line(text)

            messages.append(message)

        # Protect against unlimited growth if the device
        # sends data without newline characters.
        if len(self.buffer) > self.MAX_LINE_LENGTH:

            raw_line = bytes(self.buffer[:self.MAX_LINE_LENGTH])

            del self.buffer[:self.MAX_LINE_LENGTH]

            text = raw_line.decode(
                'utf-8',
                errors='replace'
            )

            messages.append(
                self.parse_line(text)
            )

        return messages

    def parse_line(self, text: str):

        # Remove ANSI escape sequences
        clean_text = self.ANSI_PATTERN.sub('', text)

        match = self.LOG_PATTERN.match(clean_text)

        if not match:

            return ParsedMessage(
                text=clean_text
            )

        timestamp, level, module, message = match.groups()

        return ParsedMessage(
            text=clean_text,
            timestamp=timestamp,
            level=level.lower(),
            module=module.strip(),
            message=message
        )
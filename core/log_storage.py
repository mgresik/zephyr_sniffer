import json
from pathlib import Path
from datetime import datetime


class LogStorage:

    def __init__(self):

        self.project_dir = Path(__file__).resolve().parent.parent

        self.logs_dir = self.project_dir / "logs"

        self.logs_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        self.file = None
        self.file_path = None

    @property
    def is_logging(self):

        return self.file is not None and not self.file.closed

    def start_logging(self, filename=None):

        if self.is_logging:
            raise RuntimeError("Logging is already active")

        if filename is None:

            timestamp = datetime.now().strftime(
                "%Y-%m-%d_%H-%M-%S"
            )

            filename = f"esp32_{timestamp}.jsonl"

        self.file_path = self.logs_dir / filename

        self.file = self.file_path.open(
            "x",
            encoding="utf-8"
        )

        return self.file_path

    def write_message(self, message):

        if not self.is_logging:
            return

        record = {
            "timestamp": message.timestamp,
            "level": message.level,
            "module": message.module,
            "message": message.message,
            "text": message.text
        }

        json_line = json.dumps(
            record,
            ensure_ascii=False
        )

        self.file.write(json_line + "\n")

        self.file.flush()

    def stop_logging(self):

        if self.is_logging:
            self.file.close()

        self.file = None
        self.file_path = None

    def load_log(self, file_path):

        records = []

        path = Path(file_path)

        with path.open(
            "r",
            encoding="utf-8"
        ) as log_file:

            for line_number, line in enumerate(log_file, start=1):

                line = line.strip()

                if not line:
                    continue

                try:

                    record = json.loads(line)

                    records.append(record)

                except json.JSONDecodeError:

                    print(
                        f"Invalid JSON at line {line_number}"
                    )

        return records

    def save_records(self, records, file_path):

        path = Path(file_path)

        with path.open(
            "w",
            encoding="utf-8"
        ) as log_file:

            for record in records:

                json_line = json.dumps(
                    record,
                    ensure_ascii=False
                )

                log_file.write(json_line + "\n")
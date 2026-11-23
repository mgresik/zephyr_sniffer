from core.log_storage import LogStorage
from parsers.log_parser import ParsedMessage


storage = LogStorage()

# Начинаем запись
file_path = storage.start_logging()

print("Logging started:", file_path)

# Создаём тестовые сообщения
messages = [
    ParsedMessage(
        text="[00:00:01.000] <inf> main: System started",
        timestamp="00:00:01.000",
        level="inf",
        module="main",
        message="System started"
    ),
    ParsedMessage(
        text="[00:00:02.000] <wrn> adc: ADC warning",
        timestamp="00:00:02.000",
        level="wrn",
        module="adc",
        message="ADC warning"
    ),
    ParsedMessage(
        text="Unknown message format",
    )
]

# Записываем сообщения
for message in messages:
    storage.write_message(message)

# Завершаем запись
storage.stop_logging()

print("Logging stopped")

# Загружаем файл
records = storage.load_log(file_path)

print("\nLoaded records:")

for record in records:
    print(record)

print("\nTotal records:", len(records))
import sys

from PySide6.QtWidgets import QApplication, QLabel

app = QApplication(sys.argv)

window = QLabel("PySide6 works!")
window.resize(400, 200)
window.show()

sys.exit(app.exec())
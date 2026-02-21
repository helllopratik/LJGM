import sys
from PyQt6.QtWidgets import QApplication
from gui.mapping_wizard import MappingWizard
from core.mapper import Mapper


app = QApplication(sys.argv)

mapper = Mapper()

if mapper.is_empty():
    window = MappingWizard()
else:
    window = MappingWizard()  # Later replace with main GUI

window.show()
sys.exit(app.exec())

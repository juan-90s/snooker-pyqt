import sys
from PySide6.QtWidgets import QApplication
import snooker

if __name__ == '__main__':
    
    app = QApplication([])
    game = snooker.SnookerBoard(500,800)
    game.show()
    sys.exit(app.exec())
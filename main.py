import sys
import logging
from PyQt6.QtWidgets import QApplication
from gui import MainWindow

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("MetaDate-JOOT")
    
    window = MainWindow()
    window.show()  
    
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())
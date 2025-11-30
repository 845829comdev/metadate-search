import os
import json
import webbrowser
from datetime import datetime
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QTreeWidget, QTreeWidgetItem, QLabel, QToolBar, QStatusBar,
    QFileDialog, QMessageBox, QHeaderView, QScrollArea, QMenu,
    QApplication
)
from PyQt6.QtCore import Qt, QSize, QObject, pyqtSignal, QThread
from PyQt6.QtGui import QAction, QPixmap, QFont, QColor
import logging

logger = logging.getLogger(__name__)

class ImageViewer(QLabel):
    """Компактный просмотрщик изображений"""
    def __init__(self):
        super().__init__()
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setText("Select Image")
        self.setMinimumSize(300, 300)
        self.setStyleSheet("""
            QLabel {
                background: #1e1e1e; 
                border: 1px solid #444;
                border-radius: 3px;
                color: #aaa;
                font-size: 12px;
                padding: 10px;
            }
        """)
    
    def load_image(self, path):
        try:
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                # Адаптивное масштабирование
                scaled = pixmap.scaled(350, 350, Qt.AspectRatioMode.KeepAspectRatio, 
                                     Qt.TransformationMode.SmoothTransformation)
                self.setPixmap(scaled)
                self.setText("")
        except Exception as e:
            self.setText(f"Load Error: {e}")

class MetadataTree(QTreeWidget):
    """Оптимизированное дерево метаданных"""
    def __init__(self):
        super().__init__()
        self.setHeaderLabels(["Property", "Value"])
        self.setColumnCount(2)
        self.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        
        # Улучшенные стили
        self.setStyleSheet("""
            QTreeWidget {
                background: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #444;
                border-radius: 3px;
                font-size: 11px;
                outline: none;
            }
            QTreeWidget::item {
                padding: 3px 5px;
                border-bottom: 1px solid #2a2a2a;
                height: 18px;
            }
            QTreeWidget::item:selected {
                background: #2d2d30;
                color: #ffffff;
            }
            QTreeWidget::item:hover {
                background: #252526;
            }
            QHeaderView::section {
                background: #2d2d30;
                color: #cccccc;
                padding: 6px 8px;
                border: none;
                font-weight: 600;
                font-size: 11px;
            }
        """)
        
        # Улучшенный шрифт
        font = QFont("Segoe UI", 9)
        self.setFont(font)
        
        # Контекстное меню
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._context_menu)
    
    def show_metadata(self, metadata):
        """Оптимизированное отображение метаданных"""
        self.clear()
        
        if not metadata:
            no_data_item = QTreeWidgetItem(self, ["No metadata", "Image contains no metadata"])
            return
            
        # Оптимизированная группировка
        categories = {
            "File Information": {},
            "Camera & Lens": {},
            "Capture Settings": {},
            "GPS & Location": {},
            "Date & Time": {},
            "Image Properties": {},
            "Color & Profiles": {},
            "EXIF Data": {},
            "RAW Information": {},
            "OSINT Intelligence": {},
            "Other Metadata": {}
        }
        
        # Быстрая группировка
        for key, value in metadata.items():
            key_lower = key.lower()
            
            if any(x in key_lower for x in ['file_', 'name', 'size', 'path', 'extension']):
                categories["File Information"][key] = value
            elif any(x in key_lower for x in ['make', 'model', 'lens', 'serial', 'camera', 'manufacturer']):
                categories["Camera & Lens"][key] = value
            elif any(x in key_lower for x in ['exposure', 'aperture', 'iso', 'focal', 'shutter', 'white', 'flash', 'metering']):
                categories["Capture Settings"][key] = value
            elif 'gps' in key_lower:
                categories["GPS & Location"][key] = value
            elif any(x in key_lower for x in ['date', 'time']):
                categories["Date & Time"][key] = value
            elif any(x in key_lower for x in ['width', 'height', 'mode', 'format', 'size', 'technical', 'image_']):
                categories["Image Properties"][key] = value
            elif any(x in key_lower for x in ['color', 'icc', 'profile']):
                categories["Color & Profiles"][key] = value
            elif 'raw' in key_lower:
                categories["RAW Information"][key] = value
            elif 'osint' in key_lower:
                categories["OSINT Intelligence"][key] = value
            elif 'exif' in key_lower:
                categories["EXIF Data"][key] = value
            else:
                categories["Other Metadata"][key] = value
        
        # Эффективное создание дерева
        for category_name, items in categories.items():
            if items:
                category_item = QTreeWidgetItem(self, [category_name, f"{len(items)}"])
                category_item.setExpanded(True)
                
                # Стиль категории
                category_font = QFont("Segoe UI", 9, QFont.Weight.Bold)
                category_item.setFont(0, category_font)
                category_item.setBackground(0, self._get_category_color(category_name))
                
                # Быстрое добавление элементов
                for key, value in items.items():
                    item = QTreeWidgetItem(category_item, [key, str(value)])
                    item.setToolTip(1, str(value))
                    
                    # Подсветка OSINT данных
                    if 'OSINT' in key:
                        item.setForeground(0, QColor(255, 215, 0))  # Золотой для OSINT
    
    def _get_category_color(self, category):
        """Цвета категорий"""
        colors = {
            "File Information": QColor(60, 60, 60),
            "Camera & Lens": QColor(45, 85, 155),
            "Capture Settings": QColor(35, 110, 75),
            "GPS & Location": QColor(180, 130, 40),
            "Date & Time": QColor(150, 75, 180),
            "Image Properties": QColor(55, 115, 165),
            "Color & Profiles": QColor(65, 170, 170),
            "EXIF Data": QColor(200, 100, 100),
            "RAW Information": QColor(220, 140, 50),
            "OSINT Intelligence": QColor(255, 165, 0),  # Оранжевый для OSINT
            "Other Metadata": QColor(100, 100, 100)
        }
        return colors.get(category, QColor(80, 80, 80))
    
    def _context_menu(self, pos):
        """Контекстное меню"""
        item = self.itemAt(pos)
        if item and item.parent():
            menu = QMenu(self)
            menu.setStyleSheet("""
                QMenu {
                    background: #2d2d30;
                    color: #cccccc;
                    border: 1px solid #444;
                }
                QMenu::item:selected {
                    background: #3e3e40;
                }
            """)
            
            copy_action = QAction("Copy Value", self)
            copy_action.triggered.connect(lambda: self._copy_value(item))
            menu.addAction(copy_action)
            
            # Для OSINT данных добавляем специальные действия
            item_text = item.text(1)
            if "OSINT" in item.text(0):
                if "http" in item_text and "maps" in item_text:
                    maps_action = QAction("Open in Browser", self)
                    maps_action.triggered.connect(lambda: webbrowser.open(item_text))
                    menu.addAction(maps_action)
                elif "Search" in item.text(0) and "http" in item_text:
                    search_action = QAction("Open Search", self)
                    search_action.triggered.connect(lambda: webbrowser.open(item_text))
                    menu.addAction(search_action)
            
            menu.exec(self.mapToGlobal(pos))
    
    def _copy_value(self, item):
        """Копировать значение"""
        QApplication.clipboard().setText(item.text(1))


class ExtractionWorker(QObject):
    """Worker для запуска тяжёлого анализа в отдельном потоке"""
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, extractor, path):
        super().__init__()
        self.extractor = extractor
        self.path = path

    def run(self):
        try:
            result = self.extractor.extract_osint_metadata(self.path)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))

class MainWindow(QMainWindow):
    """Главное окно - оптимизированное"""
    def __init__(self):
        super().__init__()
        from core import UltraMetadataExtractor
        
        self.extractor = UltraMetadataExtractor()
        self.current_file = None
        self.current_metadata = None
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Настройка компактного интерфейса"""
        self.setWindowTitle("MetaDate-JOOT - OSINT Edition")
        self.setGeometry(50, 50, 1400, 750)  # Более компактный размер
        
        # Установка темной темы
        self.setStyleSheet("""
            QMainWindow {
                background: #1e1e1e;
                color: #d4d4d4;
            }
            QWidget {
                background: #1e1e1e;
                color: #d4d4d4;
                font-family: Segoe UI, Arial, sans-serif;
            }
            QToolBar {
                background: #2d2d30;
                border: none;
                spacing: 2px;
                padding: 3px;
            }
            QToolButton {
                background: #3c3c3c;
                color: #cccccc;
                border: 1px solid #555;
                border-radius: 3px;
                padding: 5px 8px;
                font-size: 11px;
                font-weight: 500;
            }
            QToolButton:hover {
                background: #4a4a4a;
                border: 1px solid #666;
            }
            QToolButton:pressed {
                background: #5a5a5a;
            }
            QStatusBar {
                background: #2d2d30;
                color: #aaaaaa;
                font-size: 10px;
                padding: 4px;
            }
            QSplitter::handle {
                background: #444;
                width: 1px;
            }
            QSplitter::handle:hover {
                background: #666;
            }
        """)
        
        # Центральный виджет
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # Компактный сплиттер
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        
        # Изображение (компактное)
        self.image_view = ImageViewer()
        splitter.addWidget(self.image_view)
        
        # Метаданные
        self.metadata_tree = MetadataTree()
        splitter.addWidget(self.metadata_tree)
        
        # Баланс размеров
        splitter.setSizes([350, 950])
        layout.addWidget(splitter)
        
        # Панель инструментов
        self._create_toolbar()
        
        # Статусбар
        self.statusBar().showMessage("Ready - Select image for OSINT analysis")
    
    def _create_toolbar(self):
        """Создать компактную панель инструментов"""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setIconSize(QSize(16, 16))
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
        # Компактные кнопки
        self.open_action = QAction("Open Image", self)
        self.open_action.setShortcut("Ctrl+O")
        self.open_action.setStatusTip("Open image file")
        self.open_action.triggered.connect(self._open_file)
        toolbar.addAction(self.open_action)
        
        toolbar.addSeparator()
        
        self.export_action = QAction("Export JSON", self)
        self.export_action.setStatusTip("Export metadata to JSON")
        self.export_action.triggered.connect(self._export_json)
        toolbar.addAction(self.export_action)

        self.open_map_action = QAction("Open Map", self)
        self.open_map_action.setStatusTip("Open location map if available")
        self.open_map_action.triggered.connect(self._open_map)
        toolbar.addAction(self.open_map_action)
        
        self.clear_action = QAction("Clear", self)
        self.clear_action.setStatusTip("Clear all data")
        self.clear_action.triggered.connect(self._clear)
        toolbar.addAction(self.clear_action)

    def _set_ui_busy(self, busy: bool):
        """Блокировка/разблокировка основных действий во время анализа"""
        self.open_action.setEnabled(not busy)
        self.export_action.setEnabled(not busy)
        self.open_map_action.setEnabled(not busy)
        self.clear_action.setEnabled(not busy)
    
    def _open_file(self):
        """Открыть файл"""
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Image File", "",
            "Image Files (*.jpg *.jpeg *.png *.tiff *.tif *.webp *.bmp *.cr2 *.nef *.arw *.orf *.rw2 *.dng);;All Files (*.*)"
        )
        
        if path:
            self._process_image(path)
    
    def _process_image(self, path):
        """Обработать изображение с OSINT-анализом"""
        # Запускаем тяжёлую работу в отдельном потоке, чтобы GUI не вис
        try:
            self.statusBar().showMessage("Deep OSINT analysis in progress...")
            self.image_view.load_image(path)

            # Блокируем UI действия
            self._set_ui_busy(True)

            # Создаём поток и worker
            self._thread = QThread()
            self._worker = ExtractionWorker(self.extractor, path)
            self._worker.moveToThread(self._thread)

            self._thread.started.connect(self._worker.run)
            self._worker.finished.connect(self._on_extraction_finished)
            self._worker.error.connect(self._on_extraction_error)

            # Очистка потоков после завершения
            self._worker.finished.connect(self._thread.quit)
            self._worker.finished.connect(self._worker.deleteLater)
            self._thread.finished.connect(self._thread.deleteLater)

            self._thread.start()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to start processing: {e}")
            self.statusBar().showMessage("Error starting processing")

    def _on_extraction_error(self, msg):
        QMessageBox.critical(self, "Error", f"Failed to process image: {msg}")
        self._set_ui_busy(False)
        self.statusBar().showMessage("Error processing image")

    def _on_extraction_finished(self, metadata):
        try:
            path = None
            if 'File_Path' in metadata:
                path = metadata.get('File_Path')

            self.metadata_tree.show_metadata(metadata)
            self.current_metadata = metadata
            self.current_file = path

            file_name = os.path.basename(path) if path else 'Unknown'
            osint_count = sum(1 for key in metadata.keys() if 'OSINT_' in key)
            gps_present = any('GPS' in key and 'Coordinates' in key for key in metadata.keys())

            status_msg = f"Loaded: {file_name} | Total: {len(metadata)} | OSINT: {osint_count}"
            if gps_present:
                status_msg += " | GPS Located"

            self.statusBar().showMessage(status_msg)
        except Exception as e:
            logger.exception(f"Error updating UI after extraction: {e}")
            self.statusBar().showMessage("Error updating UI")
        finally:
            self._set_ui_busy(False)
    
    def _export_json(self):
        """Экспорт в JSON"""
        if not self.current_metadata:
            QMessageBox.warning(self, "Export", "No metadata to export")
            return
            
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Metadata", 
            f"metadata_osint_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            "JSON Files (*.json)"
        )
        
        if path:
            try:
                data = {
                    "file": self.current_file,
                    "export_date": datetime.now().isoformat(),
                    "metadata_count": len(self.current_metadata),
                    "metadata": self.current_metadata
                }
                
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                    
                QMessageBox.information(self, "Success", f"Metadata exported to: {path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export: {e}")

    def _open_map(self):
        """Открыть карту локации если есть"""
        if not self.current_metadata:
            return
            
        # Ищем файл карты или URL
        map_file = None
        map_url = None
        
        for key, value in self.current_metadata.items():
            if 'OSINT_Map_File' in key:
                map_file = value
            elif 'OSINT_Google_Maps' in key:
                map_url = value
                break
            elif 'GPS_Google_Maps' in key:
                map_url = value
                break
        
        if map_url:
            webbrowser.open(map_url)
        elif map_file and os.path.exists(map_file):
            webbrowser.open(f"file://{map_file}")
        else:
            QMessageBox.information(self, "Map", "No location map available for this image")
    
    def _clear(self):
        """Очистить всё"""
        self.image_view.clear()
        self.metadata_tree.clear()
        self.current_file = None
        self.current_metadata = None
        self.statusBar().showMessage("Ready - Select image for OSINT analysis")
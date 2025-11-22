"""PySide6 GUI for gensi with Transmission-like queue interface."""

import sys
import asyncio
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field
from enum import Enum

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QProgressBar, QLabel, QFileDialog, QMessageBox, QDialog,
    QLineEdit, QDialogButtonBox, QToolBar, QMenu
)
from PySide6.QtCore import Qt, QThread, Signal, QSettings, QSize, QTimer
from PySide6.QtGui import QAction, QPixmap, QIcon

from .core.processor import GensiProcessor, ProcessingProgress


class ItemStatus(Enum):
    """Status of a queue item."""
    QUEUED = "Queued"
    PROCESSING = "Processing"
    COMPLETED = "Completed"
    ERROR = "Error"
    PAUSED = "Paused"


@dataclass
class QueueItem:
    """Represents a .gensi file in the processing queue."""
    gensi_path: Path
    output_dir: Path
    status: ItemStatus = ItemStatus.QUEUED
    progress: int = 0
    message: str = ""
    cover_data: Optional[bytes] = None
    output_path: Optional[Path] = None
    error: Optional[str] = None


class ProcessorThread(QThread):
    """Thread for processing a .gensi file."""

    progress_updated = Signal(ProcessingProgress)
    finished_success = Signal(Path)
    finished_error = Signal(str)

    def __init__(self, gensi_path: Path, output_dir: Path, max_parallel: int = 5, cache_enabled: bool = True):
        super().__init__()
        self.gensi_path = gensi_path
        self.output_dir = output_dir
        self.max_parallel = max_parallel
        self.cache_enabled = cache_enabled
        self._stop_requested = False

    def run(self):
        """Run the processor in a thread."""
        try:
            def progress_callback(prog: ProcessingProgress):
                if not self._stop_requested:
                    self.progress_updated.emit(prog)

            # Run async processing
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            processor = GensiProcessor(
                self.gensi_path,
                self.output_dir,
                progress_callback,
                self.max_parallel,
                self.cache_enabled
            )
            output_path = loop.run_until_complete(processor.process())
            loop.close()

            if not self._stop_requested:
                self.finished_success.emit(output_path)

        except Exception as e:
            if not self._stop_requested:
                self.finished_error.emit(str(e))

    def stop(self):
        """Request the thread to stop."""
        self._stop_requested = True


class SettingsDialog(QDialog):
    """Settings dialog for the application."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(400)

        layout = QVBoxLayout()

        # Output directory setting
        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel("Default Output Directory:"))
        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setPlaceholderText("Same as input file")
        output_layout.addWidget(self.output_dir_edit)

        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_output_dir)
        output_layout.addWidget(browse_btn)
        layout.addLayout(output_layout)

        # Parallel downloads setting
        parallel_layout = QHBoxLayout()
        parallel_layout.addWidget(QLabel("Max Parallel Downloads:"))
        self.parallel_edit = QLineEdit("5")
        self.parallel_edit.setMaximumWidth(50)
        parallel_layout.addWidget(self.parallel_edit)
        parallel_layout.addStretch()
        layout.addLayout(parallel_layout)

        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setLayout(layout)

        # Load settings
        self._load_settings()

    def _browse_output_dir(self):
        """Browse for output directory."""
        dir_path = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if dir_path:
            self.output_dir_edit.setText(dir_path)

    def _load_settings(self):
        """Load settings from QSettings."""
        settings = QSettings("Gensi", "GensiApp")
        output_dir = settings.value("output_dir", "")
        parallel = settings.value("max_parallel", "5")

        self.output_dir_edit.setText(output_dir)
        self.parallel_edit.setText(parallel)

    def get_settings(self):
        """Get the current settings."""
        return {
            'output_dir': self.output_dir_edit.text() or None,
            'max_parallel': int(self.parallel_edit.text() or "5")
        }


class MainWindow(QMainWindow):
    """Main application window with Transmission-like interface."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gensi - EPUB Generator")
        self.setMinimumSize(900, 600)

        # Queue management
        self.queue: list[QueueItem] = []
        self.current_thread: Optional[ProcessorThread] = None

        # Settings
        self.settings = QSettings("Gensi", "GensiApp")
        self.output_dir = self.settings.value("output_dir", None)
        self.max_parallel = int(self.settings.value("max_parallel", "5"))

        # Setup UI
        self._setup_ui()
        self._setup_menu()
        self._setup_toolbar()

        # Start processing timer
        self.process_timer = QTimer()
        self.process_timer.timeout.connect(self._process_next_queued)
        self.process_timer.start(1000)  # Check every second

    def _setup_ui(self):
        """Setup the user interface."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)

        # Queue table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["File", "Status", "Progress", "Message", "Output"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

        # Button bar
        button_layout = QHBoxLayout()

        self.add_btn = QPushButton("Add Files")
        self.add_btn.clicked.connect(self._add_files)
        button_layout.addWidget(self.add_btn)

        self.remove_btn = QPushButton("Remove")
        self.remove_btn.clicked.connect(self._remove_selected)
        button_layout.addWidget(self.remove_btn)

        self.clear_completed_btn = QPushButton("Clear Completed")
        self.clear_completed_btn.clicked.connect(self._clear_completed)
        button_layout.addWidget(self.clear_completed_btn)

        button_layout.addStretch()

        self.settings_btn = QPushButton("Settings")
        self.settings_btn.clicked.connect(self._show_settings)
        button_layout.addWidget(self.settings_btn)

        layout.addLayout(button_layout)

    def _setup_menu(self):
        """Setup the menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("File")

        add_action = QAction("Add Files", self)
        add_action.triggered.connect(self._add_files)
        file_menu.addAction(add_action)

        file_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Edit menu
        edit_menu = menubar.addMenu("Edit")

        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self._show_settings)
        edit_menu.addAction(settings_action)

        # Help menu
        help_menu = menubar.addMenu("Help")

        about_action = QAction("About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _setup_toolbar(self):
        """Setup the toolbar."""
        toolbar = QToolBar()
        toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(toolbar)

        add_action = QAction("Add", self)
        add_action.triggered.connect(self._add_files)
        toolbar.addAction(add_action)

        remove_action = QAction("Remove", self)
        remove_action.triggered.connect(self._remove_selected)
        toolbar.addAction(remove_action)

    def _add_files(self):
        """Add .gensi files to the queue."""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select .gensi files",
            "",
            "Gensi files (*.gensi);;All files (*.*)"
        )

        for file_path in file_paths:
            gensi_path = Path(file_path)
            output_dir = Path(self.output_dir) if self.output_dir else gensi_path.parent

            item = QueueItem(
                gensi_path=gensi_path,
                output_dir=output_dir,
                status=ItemStatus.QUEUED
            )
            self.queue.append(item)

        self._update_table()

    def _remove_selected(self):
        """Remove selected items from the queue."""
        selected_rows = set(index.row() for index in self.table.selectedIndexes())

        if not selected_rows:
            return

        # Can't remove items being processed
        for row in sorted(selected_rows, reverse=True):
            if row < len(self.queue):
                if self.queue[row].status == ItemStatus.PROCESSING:
                    QMessageBox.warning(
                        self,
                        "Cannot Remove",
                        "Cannot remove items that are currently being processed."
                    )
                    return

        # Remove items
        for row in sorted(selected_rows, reverse=True):
            if row < len(self.queue):
                del self.queue[row]

        self._update_table()

    def _clear_completed(self):
        """Clear completed items from the queue."""
        self.queue = [
            item for item in self.queue
            if item.status not in [ItemStatus.COMPLETED, ItemStatus.ERROR]
        ]
        self._update_table()

    def _show_settings(self):
        """Show the settings dialog."""
        dialog = SettingsDialog(self)
        if dialog.exec() == QDialog.Accepted:
            settings = dialog.get_settings()
            self.output_dir = settings['output_dir']
            self.max_parallel = settings['max_parallel']

            # Save settings
            self.settings.setValue("output_dir", self.output_dir or "")
            self.settings.setValue("max_parallel", str(self.max_parallel))

    def _show_about(self):
        """Show the about dialog."""
        QMessageBox.about(
            self,
            "About Gensi",
            "Gensi v0.1.0\n\n"
            "Generate EPUB files from web sources using .gensi recipe files.\n\n"
            "Built with PySide6, curl_cffi, lxml, and nh3."
        )

    def _update_table(self):
        """Update the table with current queue."""
        self.table.setRowCount(len(self.queue))

        for row, item in enumerate(self.queue):
            # File name
            self.table.setItem(row, 0, QTableWidgetItem(item.gensi_path.name))

            # Status
            status_item = QTableWidgetItem(item.status.value)
            if item.status == ItemStatus.ERROR:
                status_item.setForeground(Qt.red)
            elif item.status == ItemStatus.COMPLETED:
                status_item.setForeground(Qt.darkGreen)
            self.table.setItem(row, 1, status_item)

            # Progress
            progress_bar = QProgressBar()
            progress_bar.setValue(item.progress)
            self.table.setCellWidget(row, 2, progress_bar)

            # Message
            self.table.setItem(row, 3, QTableWidgetItem(item.message))

            # Output
            output_text = str(item.output_path.name) if item.output_path else ""
            self.table.setItem(row, 4, QTableWidgetItem(output_text))

    def _process_next_queued(self):
        """Process the next queued item."""
        # Check if already processing
        if self.current_thread and self.current_thread.isRunning():
            return

        # Find next queued item
        for item in self.queue:
            if item.status == ItemStatus.QUEUED:
                self._start_processing(item)
                break

    def _start_processing(self, item: QueueItem):
        """Start processing a queue item."""
        item.status = ItemStatus.PROCESSING
        item.progress = 0
        item.message = "Starting..."
        self._update_table()

        # Create and start processor thread
        self.current_thread = ProcessorThread(
            item.gensi_path,
            item.output_dir,
            self.max_parallel
        )
        self.current_thread.progress_updated.connect(
            lambda prog: self._on_progress(item, prog)
        )
        self.current_thread.finished_success.connect(
            lambda path: self._on_success(item, path)
        )
        self.current_thread.finished_error.connect(
            lambda error: self._on_error(item, error)
        )
        self.current_thread.start()

    def _on_progress(self, item: QueueItem, progress: ProcessingProgress):
        """Handle progress updates."""
        # Calculate progress percentage
        if progress.stage == 'parsing':
            item.progress = 5
        elif progress.stage == 'cover':
            item.progress = 10
        elif progress.stage == 'index':
            item.progress = 20
        elif progress.stage == 'article':
            if progress.total > 0:
                item.progress = 20 + int((progress.current / progress.total) * 60)
            else:
                item.progress = 20
        elif progress.stage == 'building':
            item.progress = 85
        elif progress.stage == 'done':
            item.progress = 100

        item.message = progress.message
        self._update_table()

    def _on_success(self, item: QueueItem, output_path: Path):
        """Handle successful processing."""
        item.status = ItemStatus.COMPLETED
        item.progress = 100
        item.message = "Completed"
        item.output_path = output_path
        self._update_table()

    def _on_error(self, item: QueueItem, error: str):
        """Handle processing error."""
        item.status = ItemStatus.ERROR
        item.message = f"Error: {error}"
        item.error = error
        self._update_table()

    def closeEvent(self, event):
        """Handle window close event."""
        # Stop current processing
        if self.current_thread and self.current_thread.isRunning():
            reply = QMessageBox.question(
                self,
                "Processing in Progress",
                "A file is currently being processed. Are you sure you want to quit?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                self.current_thread.stop()
                self.current_thread.wait()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


def main():
    """Main entry point for the GUI application."""
    app = QApplication(sys.argv)
    app.setApplicationName("Gensi")
    app.setOrganizationName("Gensi")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    main()

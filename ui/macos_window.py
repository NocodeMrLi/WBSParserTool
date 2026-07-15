from __future__ import annotations

import queue
import os
import sys
import threading
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from app_info import APP_VERSION, AUTHOR_CONTACT_NOTE, AUTHOR_NAME, WECHAT_QR_PATH
from config.config_manager import ApiConfig, get_config_dir, load_api_config, save_api_config
from core.ai_client import parse_online, test_connection
from core.document_reader import SUPPORTED_EXTENSIONS, read_document
from core.exporters import TASK_FILE_NAME, WBS_FILE_NAME, export_deliverables, save_deliverable
from core.rule_parser import parse_locally


class MacMainWindow:
    def __init__(self):
        os.environ.setdefault("LANG", "zh_CN.UTF-8")
        os.environ.setdefault("LC_CTYPE", "zh_CN.UTF-8")
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.app.setApplicationName("WBSParserTool")
        self.app.setQuitOnLastWindowClosed(True)
        self.app.setFont(QFont("Helvetica Neue", 13))

        icon_path = _resource_path("assets/app_icon_preview.png")
        if icon_path.exists():
            self.app.setWindowIcon(QIcon(str(icon_path)))

        self.window = QWidget()
        self.window.setWindowTitle("WBS任务拆解工具")
        self.window.setFixedSize(820, 560)

        self.event_queue: queue.Queue = queue.Queue()
        self.deliverables: list[tuple[str, Path]] = []
        self.is_busy = False
        self.selected_path = ""

        self._build_ui()
        self.timer = QTimer()
        self.timer.timeout.connect(self._poll_events)
        self.timer.start(100)

    def run(self) -> None:
        self.window.show()
        self.window.raise_()
        self.window.activateWindow()
        self.app.exec()

    def _build_ui(self) -> None:
        self.window.setStyleSheet(
            """
            QWidget {
                background: #f5f6f8;
                color: #1d1d1f;
                font-family: "Helvetica Neue";
                font-size: 13px;
            }
            QGroupBox {
                background: rgba(255, 255, 255, 0.88);
                border: 1px solid #d8dee6;
                border-radius: 10px;
                margin-top: 12px;
                padding: 12px;
                font-weight: 600;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
                color: #1d1d1f;
            }
            QLineEdit, QListWidget {
                background: #ffffff;
                border: 1px solid #cfd6df;
                border-radius: 7px;
                padding: 6px 8px;
            }
            QPushButton {
                background: #ffffff;
                border: 1px solid #c8cdd4;
                border-radius: 7px;
                padding: 6px 14px;
            }
            QPushButton:pressed {
                background: #e9edf2;
            }
            QPushButton:disabled {
                color: #9aa3af;
                background: #f1f3f5;
            }
            QProgressBar {
                background: #ffffff;
                border: 1px solid #cfd6df;
                border-radius: 7px;
                height: 12px;
                text-align: center;
            }
            QProgressBar::chunk {
                background: #0a84ff;
                border-radius: 6px;
            }
            """
        )

        root = QVBoxLayout(self.window)
        root.setContentsMargins(22, 18, 22, 14)
        root.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("WBS任务拆解工具")
        title.setStyleSheet("font-size: 22px; font-weight: 700; background: transparent;")
        header.addWidget(title)
        header.addStretch()
        version = QLabel(f"版本 {APP_VERSION}")
        version.setStyleSheet("color: #667085; background: transparent;")
        header.addWidget(version)
        self.author_button = QPushButton("联系作者")
        self.author_button.clicked.connect(self.open_author_dialog)
        header.addWidget(self.author_button)
        root.addLayout(header)

        doc_group = QGroupBox("需求文档")
        doc_layout = QHBoxLayout(doc_group)
        doc_layout.setContentsMargins(12, 14, 12, 12)
        self.file_entry = QLineEdit()
        self.file_entry.setReadOnly(True)
        doc_layout.addWidget(self.file_entry, 1)
        self.upload_button = QPushButton("上传")
        self.upload_button.clicked.connect(self.on_upload)
        doc_layout.addWidget(self.upload_button)
        root.addWidget(doc_group)

        controls = QHBoxLayout()
        controls.setSpacing(12)
        action_group = QGroupBox("解析方式")
        action_layout = QHBoxLayout(action_group)
        action_layout.setContentsMargins(12, 14, 12, 12)
        self.local_button = QPushButton("本地解析")
        self.local_button.clicked.connect(lambda: self.start_parse("local"))
        self.online_button = QPushButton("在线解析")
        self.online_button.clicked.connect(lambda: self.start_parse("online"))
        self.api_button = QPushButton("API配置")
        self.api_button.clicked.connect(self.open_api_config)
        action_layout.addWidget(self.local_button)
        action_layout.addWidget(self.online_button)
        action_layout.addWidget(self.api_button)
        action_layout.addStretch()
        controls.addWidget(action_group, 1)

        progress_group = QGroupBox("解析进度")
        progress_layout = QVBoxLayout(progress_group)
        progress_layout.setContentsMargins(12, 14, 12, 12)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.status_label = QLabel("等待上传需求文档。")
        self.status_label.setStyleSheet("color: #667085; background: transparent;")
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.status_label)
        controls.addWidget(progress_group, 1)
        root.addLayout(controls)

        delivery_group = QGroupBox("交付文件（工作分解结构_WBS、任务清单）")
        delivery_layout = QHBoxLayout(delivery_group)
        delivery_layout.setContentsMargins(12, 14, 12, 12)
        self.deliverable_list = QListWidget()
        self.deliverable_list.itemSelectionChanged.connect(self._refresh_save_button)
        delivery_layout.addWidget(self.deliverable_list, 1)

        side = QVBoxLayout()
        self.save_button = QPushButton("存储")
        self.save_button.clicked.connect(self.on_save)
        self.save_button.setEnabled(False)
        self.desktop_button = QPushButton("存到桌面")
        self.desktop_button.clicked.connect(self.on_save_to_desktop)
        self.desktop_button.setEnabled(False)
        self.clear_button = QPushButton("清空状态")
        self.clear_button.clicked.connect(self.on_clear_state)
        side.addWidget(self.save_button)
        side.addWidget(self.desktop_button)
        side.addWidget(self.clear_button)
        side.addStretch()
        delivery_layout.addLayout(side)
        root.addWidget(delivery_group, 1)

    def on_upload(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self.window,
            "选择需求文档",
            "",
            "需求文档 (*.pdf *.docx *.txt)",
        )
        if not path:
            return
        suffix = Path(path).suffix.lower()
        if suffix not in SUPPORTED_EXTENSIONS:
            QMessageBox.warning(self.window, "格式不支持", "仅支持 .pdf、.docx、.txt 文件。")
            return

        self.selected_path = path
        self.file_entry.setText(path)
        self.status_label.setText("文档已选择，可以开始解析。")
        self.progress_bar.setValue(0)
        self._clear_deliverables()

    def start_parse(self, mode: str) -> None:
        source_path = self.selected_path.strip()
        if not source_path:
            QMessageBox.warning(self.window, "请先上传", "请先上传 .pdf、.docx 或 .txt 需求文档。")
            return
        if mode == "online" and not load_api_config().is_complete:
            QMessageBox.warning(self.window, "需要 API 配置", "请先点击“API配置”，填写并保存自己的 API 信息。")
            return
        if self.is_busy:
            return

        self._set_busy(True)
        self._clear_deliverables()
        self.progress_bar.setValue(0)
        self.status_label.setText("准备解析...")
        threading.Thread(target=self._parse_worker, args=(mode, source_path), daemon=True).start()

    def _parse_worker(self, mode: str, source_path: str) -> None:
        try:
            source = Path(source_path)
            self.event_queue.put(("progress", 10, "正在读取文档..."))
            text = read_document(source_path)
            if not text.strip():
                raise ValueError("文档未提取到有效文本。")

            if mode == "online":
                self.event_queue.put(("progress", 35, "正在调用在线解析..."))
                result = parse_online(text, load_api_config(), source.name)
            else:
                self.event_queue.put(("progress", 35, "正在执行本地解析..."))
                result = parse_locally(text, source_path)

            self.event_queue.put(("progress", 75, "正在生成交付文件..."))
            files = export_deliverables(result, _temp_output_dir())
            self.event_queue.put(("finished", files))
        except Exception as exc:
            self.event_queue.put(("failed", str(exc)))

    def _poll_events(self) -> None:
        try:
            while True:
                event = self.event_queue.get_nowait()
                kind = event[0]
                if kind == "progress":
                    self.progress_bar.setValue(event[1])
                    self.status_label.setText(event[2])
                elif kind == "finished":
                    self._show_deliverables(event[1])
                    self.progress_bar.setValue(100)
                    self.status_label.setText("解析完成，请选择交付文件后存储，或直接存到桌面。")
                    self._set_busy(False)
                elif kind == "failed":
                    self.progress_bar.setValue(0)
                    self.status_label.setText("解析失败。")
                    self._set_busy(False)
                    QMessageBox.critical(self.window, "解析失败", event[1])
        except queue.Empty:
            pass

    def _show_deliverables(self, files: dict) -> None:
        self._clear_deliverables()
        self.deliverables = [
            (WBS_FILE_NAME, Path(files["wbs"])),
            (TASK_FILE_NAME, Path(files["tasks"])),
        ]
        for name, _path in self.deliverables:
            self.deliverable_list.addItem(name)

    def on_save(self) -> None:
        selected = self._selected_deliverable()
        if selected is None:
            return
        name, source = selected

        default_target = _desktop_dir() / name
        target, _ = QFileDialog.getSaveFileName(
            self.window,
            "保存交付文件",
            str(default_target),
            _file_filter(source),
        )
        if not target:
            return

        target_path = Path(target)
        if not target_path.suffix:
            target_path = target_path.with_suffix(source.suffix)

        try:
            save_deliverable(source, target_path)
        except Exception as exc:
            QMessageBox.critical(self.window, "保存失败", str(exc))
            return
        QMessageBox.information(self.window, "保存成功", f"文件已保存到：\n{target_path}")

    def on_save_to_desktop(self) -> None:
        selected = self._selected_deliverable()
        if selected is None:
            return
        name, source = selected
        target_path = _unique_path(_desktop_dir() / name)

        try:
            save_deliverable(source, target_path)
        except Exception as exc:
            QMessageBox.critical(self.window, "保存失败", str(exc))
            return
        QMessageBox.information(self.window, "保存成功", f"文件已保存到桌面：\n{target_path}")

    def open_api_config(self) -> None:
        ApiConfigDialog(self.window).exec()

    def open_author_dialog(self) -> None:
        dialog = QDialog(self.window)
        dialog.setWindowTitle("关于 / 联系作者")
        dialog.setFixedSize(380, 460)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(18, 18, 18, 18)
        title = QLabel("WBS任务拆解工具")
        title.setStyleSheet("font-size: 16px; font-weight: 700;")
        layout.addWidget(title)
        layout.addWidget(QLabel(f"版本：{APP_VERSION}"))
        layout.addWidget(QLabel(f"作者：{AUTHOR_NAME}"))
        note = QLabel(AUTHOR_CONTACT_NOTE)
        note.setWordWrap(True)
        layout.addWidget(note)

        qr_path = _resource_path(WECHAT_QR_PATH)
        if qr_path.exists():
            image = QLabel()
            image.setAlignment(Qt.AlignCenter)
            image.setPixmap(QIcon(str(qr_path)).pixmap(260, 260))
            layout.addWidget(image)
            layout.addWidget(QLabel("扫码联系作者"), alignment=Qt.AlignCenter)
        else:
            missing = QLabel("将微信二维码图片放到 assets/wechat_qr.png 后重新打包，这里会自动显示。")
            missing.setWordWrap(True)
            layout.addWidget(missing)

        layout.addStretch()
        close = QPushButton("关闭")
        close.clicked.connect(dialog.accept)
        layout.addWidget(close, alignment=Qt.AlignRight)
        dialog.exec()

    def on_clear_state(self) -> None:
        if self.is_busy:
            return
        self.selected_path = ""
        self.file_entry.clear()
        self.progress_bar.setValue(0)
        self.status_label.setText("等待上传需求文档。")
        self._clear_deliverables()

    def _clear_deliverables(self) -> None:
        self.deliverables = []
        self.deliverable_list.clear()
        self._refresh_save_button()

    def _refresh_save_button(self) -> None:
        enabled = self.deliverable_list.currentRow() >= 0 and not self.is_busy
        self.save_button.setEnabled(enabled)
        self.desktop_button.setEnabled(enabled)

    def _set_busy(self, busy: bool) -> None:
        self.is_busy = busy
        enabled = not busy
        for button in (self.upload_button, self.local_button, self.online_button, self.api_button, self.clear_button):
            button.setEnabled(enabled)
        self._refresh_save_button()

    def _selected_deliverable(self) -> tuple[str, Path] | None:
        row = self.deliverable_list.currentRow()
        if row < 0:
            QMessageBox.warning(self.window, "请选择文件", "请先选择一份交付文件。")
            return None

        name, source = self.deliverables[row]
        if not source.exists():
            QMessageBox.warning(self.window, "文件不存在", "交付文件不存在，请重新解析。")
            return None
        return name, source


class ApiConfigDialog(QDialog):
    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setWindowTitle("API配置")
        self.setFixedSize(600, 260)
        config = load_api_config()
        self.base_url_input = QLineEdit(config.base_url)
        self.api_key_input = QLineEdit(config.api_key)
        self.api_key_input.setEchoMode(QLineEdit.Password)
        self.model_input = QLineEdit(config.model)
        self.status_label = QLabel("支持 OpenAI 兼容的 Chat Completions 接口。")
        self.status_label.setStyleSheet("color: #667085;")
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 14)
        title = QLabel("API配置")
        title.setStyleSheet("font-size: 16px; font-weight: 700;")
        layout.addWidget(title)

        form = QGridLayout()
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)
        form.addWidget(QLabel("API Base URL："), 0, 0)
        form.addWidget(self.base_url_input, 0, 1)
        form.addWidget(QLabel("API Key："), 1, 0)
        form.addWidget(self.api_key_input, 1, 1)
        form.addWidget(QLabel("模型名称："), 2, 0)
        form.addWidget(self.model_input, 2, 1)
        layout.addLayout(form)
        layout.addWidget(self.status_label)

        buttons = QHBoxLayout()
        buttons.addStretch()
        self.test_button = QPushButton("测试连接")
        self.test_button.clicked.connect(self.on_test)
        save_button = QPushButton("保存配置")
        save_button.clicked.connect(self.on_save)
        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(self.reject)
        buttons.addWidget(self.test_button)
        buttons.addWidget(save_button)
        buttons.addWidget(cancel_button)
        layout.addLayout(buttons)

    def current_config(self) -> ApiConfig:
        return ApiConfig(
            base_url=self.base_url_input.text(),
            api_key=self.api_key_input.text(),
            model=self.model_input.text(),
        )

    def on_test(self) -> None:
        config = self.current_config()
        self.test_button.setEnabled(False)
        self.status_label.setText("正在测试连接...")

        def worker() -> None:
            try:
                test_connection(config)
            except Exception as exc:
                QTimer.singleShot(0, lambda: self._test_done(False, str(exc)))
            else:
                QTimer.singleShot(0, lambda: self._test_done(True, "API 连接可用。"))

        threading.Thread(target=worker, daemon=True).start()

    def _test_done(self, ok: bool, message: str) -> None:
        self.test_button.setEnabled(True)
        self.status_label.setText(message)
        if ok:
            QMessageBox.information(self, "测试成功", message)
        else:
            QMessageBox.warning(self, "测试失败", message)

    def on_save(self) -> None:
        config = self.current_config()
        if not config.is_complete:
            QMessageBox.warning(self, "配置不完整", "请填写 API Base URL、API Key 和模型名称。")
            return
        save_api_config(config)
        QMessageBox.information(self, "保存成功", "API 配置已保存到本机用户目录。")
        self.accept()


def _temp_output_dir() -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return get_config_dir() / "temp" / timestamp


def _resource_path(relative_path: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    return base / relative_path


def _desktop_dir() -> Path:
    desktop = Path.home() / "Desktop"
    if desktop.exists():
        return desktop
    return Path.home()


def _unique_path(path: Path) -> Path:
    if not path.exists():
        return path

    for index in range(1, 1000):
        candidate = path.with_name(f"{path.stem} ({index}){path.suffix}")
        if not candidate.exists():
            return candidate
    return path


def _file_filter(source: Path) -> str:
    if source.suffix.lower() == ".xlsx":
        return "Excel 工作簿 (*.xlsx)"
    if source.suffix.lower() == ".docx":
        return "Word 文档 (*.docx)"
    return "所有文件 (*)"

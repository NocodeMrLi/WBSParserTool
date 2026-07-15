from __future__ import annotations

import queue
import sys
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, font as tkfont, messagebox, ttk

from app_info import APP_VERSION, AUTHOR_CONTACT_NOTE, AUTHOR_NAME, WECHAT_QR_PATH
from config.config_manager import get_config_dir, load_api_config
from core.ai_client import parse_online
from core.document_reader import SUPPORTED_EXTENSIONS, read_document
from core.exporters import TASK_FILE_NAME, WBS_FILE_NAME, export_deliverables, save_deliverable
from core.rule_parser import parse_locally
from ui.api_config_dialog import ApiConfigDialog


IS_MACOS = sys.platform == "darwin"
MAC_BACKGROUND = "#eef1f4"
MAC_PANEL = "#fbfcfd"
MAC_PANEL_ALT = "#f6f8fa"
MAC_BORDER = "#d8dee6"
MAC_TEXT = "#1d1d1f"
MAC_MUTED = "#667085"
MAC_ACCENT = "#0a84ff"


class MainWindow:
    def __init__(self):
        self.root = tk.Tk()
        _configure_platform_style(self.root)
        _set_window_icon(self.root)
        self.root.title("WBS任务拆解工具")
        self.root.geometry("820x560" if IS_MACOS else "740x480")
        self.root.resizable(False, False)

        self.selected_path = tk.StringVar(value="")
        self.status_var = tk.StringVar(value="等待上传需求文档。")
        self.progress_var = tk.IntVar(value=0)
        self.event_queue: queue.Queue = queue.Queue()
        self.deliverables: list[tuple[str, Path]] = []
        self.is_busy = False
        self.author_qr_image = None

        self._build_ui()
        self.root.after(100, self._poll_events)

    def run(self) -> None:
        self.root.mainloop()

    def _build_ui(self) -> None:
        if IS_MACOS:
            self._build_macos_ui()
        else:
            self._build_classic_ui()

    def _build_classic_ui(self) -> None:
        root_frame = ttk.Frame(self.root, padding=(12, 12, 12, 8))
        root_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        doc_group = ttk.LabelFrame(root_frame, text="需求文档", padding=10)
        doc_group.pack(fill=tk.X, pady=(0, 10))
        self.file_entry = ttk.Entry(doc_group, textvariable=self.selected_path, state="readonly")
        self.file_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        self.upload_button = ttk.Button(doc_group, text="上传", command=self.on_upload)
        self.upload_button.pack(side=tk.LEFT)

        action_group = ttk.LabelFrame(root_frame, text="解析方式", padding=10)
        action_group.pack(fill=tk.X, pady=(0, 10))
        self.local_button = ttk.Button(action_group, text="本地解析", command=lambda: self.start_parse("local"))
        self.local_button.pack(side=tk.LEFT, padx=(0, 8))
        self.online_button = ttk.Button(action_group, text="在线解析", command=lambda: self.start_parse("online"))
        self.online_button.pack(side=tk.LEFT, padx=(0, 8))
        self.api_button = ttk.Button(action_group, text="API配置", command=self.open_api_config)
        self.api_button.pack(side=tk.LEFT)

        progress_group = ttk.LabelFrame(root_frame, text="解析进度", padding=10)
        progress_group.pack(fill=tk.X, pady=(0, 10))
        self.progress_bar = ttk.Progressbar(progress_group, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X)
        ttk.Label(progress_group, textvariable=self.status_var).pack(anchor=tk.W, pady=(8, 0))

        delivery_group = ttk.LabelFrame(root_frame, text="交付文件（工作分解结构_WBS、任务清单）", padding=10)
        delivery_group.pack(fill=tk.BOTH, expand=True)

        list_frame = ttk.Frame(delivery_group)
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        self.deliverable_list = tk.Listbox(list_frame, height=5, exportselection=False)
        self.deliverable_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.deliverable_list.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.deliverable_list.configure(yscrollcommand=scrollbar.set)
        self.deliverable_list.bind("<<ListboxSelect>>", lambda _event: self._refresh_save_button())

        button_frame = ttk.Frame(delivery_group)
        button_frame.pack(side=tk.RIGHT, fill=tk.Y)
        self.save_button = ttk.Button(button_frame, text="存储", command=self.on_save, state=tk.DISABLED)
        self.save_button.pack(anchor=tk.N)
        self.desktop_button = ttk.Button(button_frame, text="存到桌面", command=self.on_save_to_desktop, state=tk.DISABLED)
        self.desktop_button.pack(anchor=tk.N, pady=(8, 0))
        self.clear_button = ttk.Button(button_frame, text="\u6e05\u7a7a\u72b6\u6001", command=self.on_clear_state)
        self.clear_button.pack(anchor=tk.N, pady=(8, 0))

        footer_frame = ttk.Frame(self.root, padding=(12, 0, 12, 10))
        footer_frame.pack(side=tk.BOTTOM, fill=tk.X)
        ttk.Label(footer_frame, text=f"\u7248\u672c {APP_VERSION}").pack(side=tk.LEFT)
        ttk.Label(footer_frame, text=f"\u4f5c\u8005\uff1a{AUTHOR_NAME}").pack(side=tk.LEFT, padx=(18, 0))
        ttk.Button(footer_frame, text="\u8054\u7cfb\u4f5c\u8005", command=self.open_author_dialog).pack(side=tk.RIGHT)

    def _build_macos_ui(self) -> None:
        self.root.configure(bg=MAC_BACKGROUND)

        root_frame = ttk.Frame(self.root, padding=(18, 16, 18, 10))
        root_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        header = ttk.Frame(root_frame)
        header.pack(fill=tk.X, pady=(0, 12))
        ttk.Label(header, text="WBS任务拆解工具", font=("", 20, "bold")).pack(side=tk.LEFT)
        ttk.Button(header, text="联系作者", command=self.open_author_dialog).pack(side=tk.RIGHT)
        ttk.Label(header, text=f"版本 {APP_VERSION}", foreground=MAC_MUTED).pack(side=tk.RIGHT, padx=(0, 12))

        doc_group = ttk.LabelFrame(root_frame, text="需求文档", padding=(12, 10))
        doc_group.pack(fill=tk.X, pady=(0, 12))
        doc_row = ttk.Frame(doc_group)
        doc_row.pack(fill=tk.X)
        self.file_entry = ttk.Entry(doc_row, textvariable=self.selected_path, state="readonly")
        self.file_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.upload_button = ttk.Button(doc_row, text="上传", command=self.on_upload)
        self.upload_button.pack(side=tk.LEFT)

        controls = ttk.Frame(root_frame)
        controls.pack(fill=tk.X, pady=(0, 12))

        action_group = ttk.LabelFrame(controls, text="解析方式", padding=(12, 10))
        action_group.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 12))
        action_row = ttk.Frame(action_group)
        action_row.pack(fill=tk.X)
        self.local_button = ttk.Button(action_row, text="本地解析", command=lambda: self.start_parse("local"))
        self.local_button.pack(side=tk.LEFT, padx=(0, 8))
        self.online_button = ttk.Button(action_row, text="在线解析", command=lambda: self.start_parse("online"))
        self.online_button.pack(side=tk.LEFT, padx=(0, 8))
        self.api_button = ttk.Button(action_row, text="API配置", command=self.open_api_config)
        self.api_button.pack(side=tk.LEFT)

        progress_group = ttk.LabelFrame(controls, text="解析进度", padding=(12, 10))
        progress_group.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.progress_bar = ttk.Progressbar(progress_group, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X)
        ttk.Label(progress_group, textvariable=self.status_var, foreground=MAC_MUTED).pack(anchor=tk.W, pady=(8, 0))

        delivery_group = ttk.LabelFrame(root_frame, text="交付文件（工作分解结构_WBS、任务清单）", padding=(12, 10))
        delivery_group.pack(fill=tk.BOTH, expand=True)

        delivery_body = ttk.Frame(delivery_group)
        delivery_body.pack(fill=tk.BOTH, expand=True)

        list_frame = ttk.Frame(delivery_body)
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 12))
        self.deliverable_list = tk.Listbox(
            list_frame,
            height=6,
            exportselection=False,
            activestyle="none",
            borderwidth=0,
            relief=tk.FLAT,
            highlightthickness=0,
            bg="#ffffff",
            fg=MAC_TEXT,
            selectbackground=MAC_ACCENT,
            selectforeground="#ffffff",
        )
        self.deliverable_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=1, pady=1)
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.deliverable_list.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.deliverable_list.configure(yscrollcommand=scrollbar.set)
        self.deliverable_list.bind("<<ListboxSelect>>", lambda _event: self._refresh_save_button())

        button_frame = ttk.Frame(delivery_body)
        button_frame.pack(side=tk.RIGHT, fill=tk.Y)
        self.save_button = ttk.Button(button_frame, text="存储", command=self.on_save, state=tk.DISABLED)
        self.save_button.pack(anchor=tk.N, fill=tk.X)
        self.desktop_button = ttk.Button(
            button_frame,
            text="存到桌面",
            command=self.on_save_to_desktop,
            state=tk.DISABLED,
        )
        self.desktop_button.pack(anchor=tk.N, fill=tk.X, pady=(8, 0))
        self.clear_button = ttk.Button(button_frame, text="清空状态", command=self.on_clear_state)
        self.clear_button.pack(anchor=tk.N, fill=tk.X, pady=(8, 0))

    def on_upload(self) -> None:
        path = filedialog.askopenfilename(
            title="选择需求文档",
            filetypes=[("需求文档", "*.pdf *.docx *.txt")],
        )
        if not path:
            return
        suffix = Path(path).suffix.lower()
        if suffix not in SUPPORTED_EXTENSIONS:
            messagebox.showwarning("格式不支持", "仅支持 .pdf、.docx、.txt 文件。", parent=self.root)
            return

        self.selected_path.set(path)
        self.status_var.set("文档已选择，可以开始解析。")
        self.progress_var.set(0)
        self._clear_deliverables()

    def start_parse(self, mode: str) -> None:
        source_path = self.selected_path.get().strip()
        if not source_path:
            messagebox.showwarning("请先上传", "请先上传 .pdf、.docx 或 .txt 需求文档。", parent=self.root)
            return
        if mode == "online" and not load_api_config().is_complete:
            messagebox.showwarning("需要 API 配置", "请先点击“API配置”，填写并保存自己的 API 信息。", parent=self.root)
            return
        if self.is_busy:
            return

        self._set_busy(True)
        self._clear_deliverables()
        self.progress_var.set(0)
        self.status_var.set("准备解析...")

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
                    self.progress_var.set(event[1])
                    self.status_var.set(event[2])
                elif kind == "finished":
                    self._show_deliverables(event[1])
                    self.progress_var.set(100)
                    self.status_var.set("解析完成，请选择交付文件后存储，或直接存到桌面。")
                    self._set_busy(False)
                elif kind == "failed":
                    self.progress_var.set(0)
                    self.status_var.set("解析失败。")
                    self._set_busy(False)
                    messagebox.showerror("解析失败", event[1], parent=self.root)
        except queue.Empty:
            pass
        self.root.after(100, self._poll_events)

    def _show_deliverables(self, files: dict) -> None:
        self._clear_deliverables()
        self.deliverables = [
            (WBS_FILE_NAME, Path(files["wbs"])),
            (TASK_FILE_NAME, Path(files["tasks"])),
        ]
        for name, _path in self.deliverables:
            self.deliverable_list.insert(tk.END, name)

    def on_save(self) -> None:
        selected = self._selected_deliverable()
        if selected is None:
            return
        name, source = selected

        target = filedialog.asksaveasfilename(
            title="保存交付文件",
            initialdir=str(_desktop_dir()),
            initialfile=name,
            defaultextension=source.suffix,
            filetypes=[(_file_type_label(source), f"*{source.suffix}"), ("所有文件", "*.*")],
        )
        if not target:
            return

        target_path = Path(target)
        if not target_path.suffix:
            target_path = target_path.with_suffix(source.suffix)

        try:
            save_deliverable(source, target_path)
        except Exception as exc:
            messagebox.showerror("保存失败", str(exc), parent=self.root)
            return

        messagebox.showinfo("保存成功", f"文件已保存到：\n{target_path}", parent=self.root)

    def on_save_to_desktop(self) -> None:
        selected = self._selected_deliverable()
        if selected is None:
            return
        name, source = selected
        target_path = _unique_path(_desktop_dir() / name)

        try:
            save_deliverable(source, target_path)
        except Exception as exc:
            messagebox.showerror("保存失败", str(exc), parent=self.root)
            return

        messagebox.showinfo("保存成功", f"文件已保存到桌面：\n{target_path}", parent=self.root)

    def open_api_config(self) -> None:
        ApiConfigDialog(self.root)

    def open_author_dialog(self) -> None:
        dialog = tk.Toplevel(self.root)
        dialog.title("\u5173\u4e8e / \u8054\u7cfb\u4f5c\u8005")
        _set_window_icon(dialog)
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        qr_path = _resource_path(WECHAT_QR_PATH)
        has_qr = qr_path.exists()
        dialog.geometry("360x470" if has_qr else "360x230")

        frame = ttk.Frame(dialog, padding=16)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="WBS\u4efb\u52a1\u62c6\u89e3\u5de5\u5177", font=("", 12, "bold")).pack(anchor=tk.W)
        ttk.Label(frame, text=f"\u7248\u672c\uff1a{APP_VERSION}").pack(anchor=tk.W, pady=(8, 0))
        ttk.Label(frame, text=f"\u4f5c\u8005\uff1a{AUTHOR_NAME}").pack(anchor=tk.W, pady=(4, 0))
        ttk.Label(frame, text=AUTHOR_CONTACT_NOTE, wraplength=320).pack(anchor=tk.W, pady=(10, 0))

        if has_qr:
            try:
                self.author_qr_image = tk.PhotoImage(file=str(qr_path))
                ttk.Label(frame, image=self.author_qr_image).pack(pady=(14, 8))
                ttk.Label(frame, text="\u626b\u7801\u8054\u7cfb\u4f5c\u8005").pack()
            except tk.TclError:
                ttk.Label(frame, text="\u5fae\u4fe1\u4e8c\u7ef4\u7801\u52a0\u8f7d\u5931\u8d25\u3002").pack(anchor=tk.W, pady=(14, 0))
        else:
            ttk.Label(
                frame,
                text="\u5c06\u5fae\u4fe1\u4e8c\u7ef4\u7801\u56fe\u7247\u653e\u5230 assets/wechat_qr.png \u540e\u91cd\u65b0\u6253\u5305\uff0c\u8fd9\u91cc\u4f1a\u81ea\u52a8\u663e\u793a\u3002",
                wraplength=320,
            ).pack(anchor=tk.W, pady=(14, 0))

        ttk.Button(frame, text="\u5173\u95ed", command=dialog.destroy).pack(anchor=tk.E, pady=(16, 0))

    def on_clear_state(self) -> None:
        if self.is_busy:
            return
        self.selected_path.set("")
        self.progress_var.set(0)
        self.status_var.set("\u7b49\u5f85\u4e0a\u4f20\u9700\u6c42\u6587\u6863\u3002")
        self._clear_deliverables()

    def _clear_deliverables(self) -> None:
        self.deliverables = []
        self.deliverable_list.delete(0, tk.END)
        self._refresh_save_button()

    def _refresh_save_button(self) -> None:
        state = tk.NORMAL if self.deliverable_list.curselection() and not self.is_busy else tk.DISABLED
        self.save_button.configure(state=state)
        self.desktop_button.configure(state=state)

    def _set_busy(self, busy: bool) -> None:
        self.is_busy = busy
        state = tk.DISABLED if busy else tk.NORMAL
        self.upload_button.configure(state=state)
        self.local_button.configure(state=state)
        self.online_button.configure(state=state)
        self.api_button.configure(state=state)
        self.clear_button.configure(state=state)
        self._refresh_save_button()

    def _selected_deliverable(self) -> tuple[str, Path] | None:
        selection = self.deliverable_list.curselection()
        if not selection:
            messagebox.showwarning("请选择文件", "请先选择一份交付文件。", parent=self.root)
            return None

        name, source = self.deliverables[selection[0]]
        if not source.exists():
            messagebox.showwarning("文件不存在", "交付文件不存在，请重新解析。", parent=self.root)
            return None
        return name, source


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


def _file_type_label(source: Path) -> str:
    suffix = source.suffix.lower()
    if suffix == ".xlsx":
        return "Excel 工作簿"
    if suffix == ".docx":
        return "Word 文档"
    return "交付文件"


def _set_window_icon(root: tk.Misc) -> None:
    if IS_MACOS:
        icon_path = _resource_path("assets/app_icon_preview.png")
        if icon_path.exists():
            try:
                image = tk.PhotoImage(file=str(icon_path))
                root.iconphoto(True, image)
                root._app_icon_photo = image
            except tk.TclError:
                pass
        return

    icon_path = _resource_path("assets/app_icon.ico")
    if icon_path.exists():
        try:
            root.iconbitmap(str(icon_path))
        except tk.TclError:
            pass


def _configure_platform_style(root: tk.Tk) -> None:
    if not IS_MACOS:
        return

    root.configure(bg=MAC_BACKGROUND)
    root.option_add("*Font", "TkDefaultFont")
    try:
        tkfont.nametofont("TkDefaultFont").configure(size=13)
        tkfont.nametofont("TkTextFont").configure(size=13)
        tkfont.nametofont("TkMenuFont").configure(size=13)
    except tk.TclError:
        pass

    style = ttk.Style(root)
    try:
        style.theme_use("aqua")
    except tk.TclError:
        pass
    style.configure("TFrame", background=MAC_BACKGROUND)
    style.configure("TLabel", background=MAC_BACKGROUND, foreground=MAC_TEXT)
    style.configure("TLabelframe", background=MAC_BACKGROUND)
    style.configure("TLabelframe.Label", background=MAC_BACKGROUND, foreground=MAC_TEXT)
    style.configure("TButton", padding=(12, 4))
    style.configure("TEntry", padding=(6, 3))

    try:
        root.createcommand("tk::mac::ShowPreferences", lambda: None)
    except tk.TclError:
        pass


def _mac_panel(parent: tk.Misc) -> tk.Frame:
    return tk.Frame(
        parent,
        bg=MAC_PANEL,
        highlightthickness=1,
        highlightbackground=MAC_BORDER,
        highlightcolor=MAC_BORDER,
    )


def _mac_panel_inner(parent: tk.Misc) -> tk.Frame:
    inner = tk.Frame(parent, bg=MAC_PANEL, padx=16, pady=14)
    inner.pack(fill=tk.BOTH, expand=True)
    return inner

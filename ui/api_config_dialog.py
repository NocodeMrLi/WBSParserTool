import queue
import threading
import sys
import tkinter as tk
from tkinter import messagebox, ttk

from config.config_manager import ApiConfig, load_api_config, save_api_config
from core.ai_client import test_connection


IS_MACOS = sys.platform == "darwin"
MAC_BACKGROUND = "#eef1f4"
MAC_PANEL = "#fbfcfd"
MAC_BORDER = "#d8dee6"
MAC_TEXT = "#1d1d1f"
MAC_MUTED = "#667085"


class ApiConfigDialog:
    def __init__(self, parent: tk.Tk):
        self.parent = parent
        self.window = tk.Toplevel(parent)
        self.window.title("API配置")
        self.window.geometry("600x285" if IS_MACOS else "540x230")
        self.window.resizable(False, False)
        self.window.transient(parent)
        self.window.grab_set()
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)
        self.is_closed = False
        if IS_MACOS:
            self.window.configure(bg=MAC_BACKGROUND)

        config = load_api_config()
        self.is_testing = False
        self.test_run_id = 0
        self.test_queue: queue.Queue = queue.Queue()
        self.base_url_var = tk.StringVar(value=config.base_url)
        self.api_key_var = tk.StringVar(value=config.api_key)
        self.model_var = tk.StringVar(value=config.model)
        self.status_var = tk.StringVar(value="支持 OpenAI 兼容的 Chat Completions 接口。")

        self._build_ui()

    def _build_ui(self) -> None:
        if IS_MACOS:
            self._build_macos_ui()
            return

        frame = ttk.Frame(self.window, padding=14)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="API Base URL：").grid(row=0, column=0, sticky=tk.W, pady=6)
        base_input = ttk.Entry(frame, textvariable=self.base_url_var, width=52)
        base_input.grid(row=0, column=1, sticky=tk.EW, pady=6)

        ttk.Label(frame, text="API Key：").grid(row=1, column=0, sticky=tk.W, pady=6)
        key_input = ttk.Entry(frame, textvariable=self.api_key_var, width=52, show="*")
        key_input.grid(row=1, column=1, sticky=tk.EW, pady=6)

        ttk.Label(frame, text="模型名称：").grid(row=2, column=0, sticky=tk.W, pady=6)
        model_input = ttk.Entry(frame, textvariable=self.model_var, width=52)
        model_input.grid(row=2, column=1, sticky=tk.EW, pady=6)

        status = ttk.Label(frame, textvariable=self.status_var, foreground="#555555")
        status.grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=(8, 10))

        button_frame = ttk.Frame(frame)
        button_frame.grid(row=4, column=0, columnspan=2, sticky=tk.E)

        self.test_button = ttk.Button(button_frame, text="测试连接", command=self.on_test)
        self.test_button.pack(side=tk.LEFT, padx=4)
        ttk.Button(button_frame, text="保存配置", command=self.on_save).pack(side=tk.LEFT, padx=4)
        ttk.Button(button_frame, text="取消", command=self.on_close).pack(side=tk.LEFT, padx=4)

        frame.columnconfigure(1, weight=1)

    def _build_macos_ui(self) -> None:
        frame = ttk.Frame(self.window, padding=(18, 16, 18, 14))
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="API配置", font=("", 15, "bold")).grid(
            row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 8)
        )

        ttk.Label(frame, text="API Base URL：").grid(row=1, column=0, sticky=tk.W, pady=6)
        base_input = ttk.Entry(frame, textvariable=self.base_url_var, width=50)
        base_input.grid(row=1, column=1, sticky=tk.EW, pady=6)

        ttk.Label(frame, text="API Key：").grid(row=2, column=0, sticky=tk.W, pady=6)
        key_input = ttk.Entry(frame, textvariable=self.api_key_var, width=50, show="*")
        key_input.grid(row=2, column=1, sticky=tk.EW, pady=6)

        ttk.Label(frame, text="模型名称：").grid(row=3, column=0, sticky=tk.W, pady=6)
        model_input = ttk.Entry(frame, textvariable=self.model_var, width=50)
        model_input.grid(row=3, column=1, sticky=tk.EW, pady=6)

        ttk.Label(frame, textvariable=self.status_var, foreground=MAC_MUTED).grid(
            row=4, column=0, columnspan=2, sticky=tk.W, pady=(10, 12)
        )

        button_frame = ttk.Frame(frame)
        button_frame.grid(row=5, column=0, columnspan=2, sticky=tk.E)

        self.test_button = ttk.Button(button_frame, text="测试连接", command=self.on_test)
        self.test_button.pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(button_frame, text="保存配置", command=self.on_save).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(button_frame, text="取消", command=self.on_close).pack(side=tk.LEFT)

        frame.columnconfigure(1, weight=1)

    def current_config(self) -> ApiConfig:
        return ApiConfig(
            base_url=self.base_url_var.get(),
            api_key=self.api_key_var.get(),
            model=self.model_var.get(),
        )

    def on_test(self) -> None:
        if self.is_testing:
            return
        config = self.current_config()
        self.is_testing = True
        self.test_run_id += 1
        run_id = self.test_run_id
        self.test_button.configure(state=tk.DISABLED)
        self.status_var.set("正在测试连接... 最多等待 30 秒。")

        def worker() -> None:
            try:
                test_connection(config)
            except Exception as exc:
                self.test_queue.put((run_id, False, str(exc)))
            else:
                self.test_queue.put((run_id, True, "API 连接可用。"))

        threading.Thread(target=worker, daemon=True).start()
        self.window.after(100, self._poll_test_result)
        self.window.after(30000, lambda current_run=run_id: self._test_timeout(current_run))

    def _poll_test_result(self) -> None:
        if self.is_closed:
            return
        try:
            run_id, ok, message = self.test_queue.get_nowait()
        except queue.Empty:
            if self.is_testing:
                self.window.after(100, self._poll_test_result)
            return
        if run_id != self.test_run_id:
            if self.is_testing:
                self.window.after(100, self._poll_test_result)
            return
        self._test_done(ok, message)

    def _test_timeout(self, run_id: int) -> None:
        if self.is_closed or not self.is_testing or run_id != self.test_run_id:
            return
        self._test_done(
            False,
            "测试连接超过 30 秒未完成，请检查网络、API Base URL、模型名称或 API Key 后重试。",
        )

    def _test_done(self, ok: bool, message: str) -> None:
        if self.is_closed:
            return
        self.is_testing = False
        self.test_button.configure(state=tk.NORMAL)
        self.status_var.set(message)
        if ok:
            messagebox.showinfo("测试成功", message, parent=self.window)
        else:
            messagebox.showwarning("测试失败", message, parent=self.window)

    def on_save(self) -> None:
        config = self.current_config()
        if not config.is_complete:
            messagebox.showwarning("配置不完整", "请填写 API Base URL、API Key 和模型名称。", parent=self.window)
            return
        save_api_config(config)
        messagebox.showinfo("保存成功", "API 配置已保存到本机用户目录。", parent=self.window)
        self.on_close()

    def on_close(self) -> None:
        if self.is_closed:
            return
        self.is_closed = True
        try:
            self.window.destroy()
        except tk.TclError:
            pass

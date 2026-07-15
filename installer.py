from __future__ import annotations

import sys
import threading
from pathlib import Path
from tkinter import BooleanVar, StringVar, Tk, filedialog, messagebox, ttk

from installer_core import APP_NAME, get_default_install_dir, install_application


class InstallerApp:
    def __init__(self):
        self.root = Tk()
        self.root.title(f"{APP_NAME} 安装程序")
        self._set_window_icon()
        self.root.geometry("560x220")
        self.root.resizable(False, False)

        self.install_dir_var = StringVar(value=str(get_default_install_dir()))
        self.status_var = StringVar(value="请选择安装位置，然后点击安装。")
        self.shortcut_var = BooleanVar(value=True)

        self._build_ui()

    def _build_ui(self) -> None:
        frame = ttk.Frame(self.root, padding=14)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text=f"安装 {APP_NAME}").grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 12))

        ttk.Label(frame, text="安装位置：").grid(row=1, column=0, sticky="w")
        entry = ttk.Entry(frame, textvariable=self.install_dir_var, width=52)
        entry.grid(row=1, column=1, sticky="ew", padx=(0, 8))
        ttk.Button(frame, text="浏览", command=self.on_browse).grid(row=1, column=2, sticky="e")

        ttk.Checkbutton(frame, text="创建桌面和开始菜单快捷方式", variable=self.shortcut_var).grid(
            row=2, column=0, columnspan=3, sticky="w", pady=(10, 8)
        )

        self.progress = ttk.Progressbar(frame, mode="indeterminate")
        self.progress.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(4, 6))

        ttk.Label(frame, textvariable=self.status_var).grid(row=4, column=0, columnspan=3, sticky="w")

        button_frame = ttk.Frame(frame)
        button_frame.grid(row=5, column=0, columnspan=3, sticky="e", pady=(14, 0))
        self.install_button = ttk.Button(button_frame, text="安装", command=self.on_install)
        self.install_button.pack(side="left", padx=4)
        ttk.Button(button_frame, text="取消", command=self.root.destroy).pack(side="left", padx=4)

        frame.columnconfigure(1, weight=1)

    def on_browse(self) -> None:
        path = filedialog.askdirectory(title="选择安装位置", initialdir=self.install_dir_var.get())
        if path:
            self.install_dir_var.set(path)

    def on_install(self) -> None:
        install_dir = Path(self.install_dir_var.get().strip())
        if not install_dir:
            messagebox.showwarning("安装位置无效", "请先选择安装位置。", parent=self.root)
            return

        payload = self._payload_path()
        if not payload.exists():
            messagebox.showerror("安装失败", f"找不到安装包内置文件：{payload}", parent=self.root)
            return

        self.install_button.configure(state="disabled")
        self.progress.start(10)
        self.status_var.set("正在安装...")

        def worker() -> None:
            try:
                target = install_application(payload, install_dir, self.shortcut_var.get(), self._icon_path())
            except Exception as exc:
                self.root.after(0, lambda: self._finish_install(False, str(exc), None))
            else:
                self.root.after(0, lambda: self._finish_install(True, "安装完成。", target))

        threading.Thread(target=worker, daemon=True).start()

    def _finish_install(self, ok: bool, message: str, target: Path | None) -> None:
        self.progress.stop()
        self.install_button.configure(state="normal")
        self.status_var.set(message)
        if ok:
            messagebox.showinfo("安装成功", f"{message}\n\n程序位置：\n{target}", parent=self.root)
            self.root.destroy()
        else:
            messagebox.showerror("安装失败", message, parent=self.root)

    def run(self) -> None:
        self.root.mainloop()

    def _payload_path(self) -> Path:
        base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
        return base / "payload" / APP_NAME / f"{APP_NAME}.exe"

    def _icon_path(self) -> Path:
        base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
        return base / "assets" / "app_icon.ico"

    def _set_window_icon(self) -> None:
        icon_path = self._icon_path()
        if icon_path.exists():
            try:
                self.root.iconbitmap(str(icon_path))
            except Exception:
                pass


def main() -> int:
    app = InstallerApp()
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

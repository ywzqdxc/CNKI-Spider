import customtkinter as ctk
from tkinter import ttk
import tkinter as tk


class ModernButton(ctk.CTkButton):
    """现代化按钮"""

    def __init__(self, master, **kwargs):
        super().__init__(
            master,
            font=("Arial", 12, "bold"),
            corner_radius=8,
            **kwargs
        )


class ScrollableFrame(ctk.CTkScrollableFrame):
    """可滚动框架"""

    def __init__(self, master, **kwargs):
        super().__init__(
            master,
            **kwargs
        )


class ProgressDialog(ctk.CTkToplevel):
    """进度对话框"""

    def __init__(self, parent, title="处理中", message="请稍候..."):
        super().__init__(parent)
        self.title(title)
        self.geometry("300x150")
        self.resizable(False, False)

        # 居中显示
        self.transient(parent)
        self.grab_set()

        # 创建界面
        self.label = ctk.CTkLabel(self, text=message, font=("Arial", 12))
        self.label.pack(pady=20)

        self.progress = ctk.CTkProgressBar(self, width=250)
        self.progress.pack(pady=10)
        self.progress.set(0)

        self.cancel_button = ModernButton(
            self,
            text="取消",
            command=self.cancel,
            width=100
        )
        self.cancel_button.pack(pady=10)

        self.cancelled = False

    def cancel(self):
        """取消操作"""
        self.cancelled = True
        self.destroy()

    def update_progress(self, value: float):
        """更新进度"""
        self.progress.set(value)
        self.update()

    def update_message(self, message: str):
        """更新消息"""
        self.label.configure(text=message)
        self.update()
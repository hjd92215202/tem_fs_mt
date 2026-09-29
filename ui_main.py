# ui_main.py
import sys
import time
import os

# ----------------- 修复 Qt 平台插件路径 -----------------
if hasattr(sys, "_MEIPASS"):
    plugin_path = os.path.join(sys._MEIPASS, "PySide6", "plugins")
    os.environ["QT_PLUGIN_PATH"] = plugin_path
# -------------------------------------------------------

from PySide6.QtCore import Qt, QPoint, QThread, Signal
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QMenu
)
from PySide6.QtGui import QFont, QAction
from src.win_monitor import WindowsMonitor


class HardwareWorker(QThread):
    """后台采集线程：防止硬件 Update() 阻塞 UI 拖动和渲染"""
    data_updated = Signal(float, str)

    def __init__(self):
        super().__init__()
        self.running = True
        self.monitor = None

    def run(self):
        try:
            self.monitor = WindowsMonitor()
        except Exception as e:
            print(f"[Worker Error] 监控驱动初始化失败: {e}")
            return

        while self.running:
            sensors = self.monitor.get_sensors()
            cpu_temp = None
            cpu_name = "CPU"

            # 优先匹配常见的 CPU 关键温度标签
            for s in sensors:
                if s.category == "temperature":
                    name_lower = s.name.lower()
                    if any(k in name_lower for k in ["tctl", "package", "core max", "cpu core #1", "cpu"]):
                        cpu_temp = s.value
                        cpu_name = s.name.split("-")[-1].strip()
                        break
            
            # 兜底：采用主板检测到的有效温度
            if cpu_temp is None:
                for s in sensors:
                    if s.category == "temperature" and s.value > 25.0:
                        cpu_temp = s.value
                        cpu_name = s.name
                        break

            if cpu_temp is not None:
                self.data_updated.emit(cpu_temp, cpu_name)

            time.sleep(1.2)

        if self.monitor:
            self.monitor.close()

    def stop(self):
        self.running = False
        self.wait()


class FloatWindow(QWidget):
    """悬浮窗主界面"""
    def __init__(self):
        super().__init__()
        self.drag_position = QPoint()

        self._init_window_flags()
        self._init_ui()
        self._init_worker()

    def _init_window_flags(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        # 精简后尺寸调整得更小巧
        self.resize(110, 48)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(0)

        # 温度大数字显示
        self.label_temp = QLabel("--.- °C", self)
        self.label_temp.setFont(QFont("Consolas", 16, QFont.Weight.Bold))
        layout.addWidget(self.label_temp, alignment=Qt.AlignmentFlag.AlignCenter)

        # 现代暗色微透毛玻璃卡片
        self.setStyleSheet("""
            QWidget {
                background-color: rgba(23, 25, 30, 0.88);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 10px;
            }
        """)

    def _init_worker(self):
        self.worker = HardwareWorker()
        self.worker.data_updated.connect(self.update_display)
        self.worker.start()

    def update_display(self, temp: float, name: str):
        # 根据温度动态调整文字颜色
        if temp < 55.0:
            color = "#00E676"  # 绿色
        elif temp < 75.0:
            color = "#FFD600"  # 黄色
        elif temp < 85.0:
            color = "#FF9100"  # 橙色
        else:
            color = "#FF1744"  # 红色警告

        self.label_temp.setText(f"{temp:.1f} °C")
        self.label_temp.setStyleSheet(f"color: {color};")
        # 移除了引发崩溃的 self.label_title.setText(name[:16])

    # ================== 鼠标拖动支持 ==================
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    # ================== 右键菜单支持 ==================
    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #202228;
                color: #FFFFFF;
                border: 1px solid #444;
                border-radius: 6px;
                padding: 4px;
            }
            QMenu::item:selected {
                background-color: #3B82F6;
            }
        """)

        # 切换置顶
        is_top = bool(self.windowFlags() & Qt.WindowType.WindowStaysOnTopHint)
        action_top = QAction("取消置顶" if is_top else "开启置顶", self)
        action_top.triggered.connect(self.toggle_top)
        menu.addAction(action_top)

        menu.addSeparator()

        # 退出程序
        action_quit = QAction("退出", self)
        action_quit.triggered.connect(self.close)
        menu.addAction(action_quit)

        menu.exec(event.globalPos())

    def toggle_top(self):
        if self.windowFlags() & Qt.WindowType.WindowStaysOnTopHint:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        self.show()

    def closeEvent(self, event):
        self.worker.stop()
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FloatWindow()
    window.show()
    sys.exit(app.exec())
# ui_main.py
import sys
import time
from PySide6.QtCore import Qt, QPoint, QThread, Signal
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QMenu
)
from PySide6.QtGui import QFont, QAction, QColor

# 引入之前写好的 Windows 监控类
from src.win_monitor import WindowsMonitor


class HardwareWorker(QThread):
    """后台采集线程：防止硬件 Update() 阻塞 UI 拖动和渲染"""
    data_updated = Signal(float, str)  # 传递 (当前温度, 传感器名称)

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
                    # 识别 AMD 的 Tctl/Tdie、Intel 的 Package 或 Core 平均温度
                    if any(k in name_lower for k in ["tctl", "package", "core max", "cpu core #1", "cpu"]):
                        cpu_temp = s.value
                        cpu_name = s.name.split("-")[-1].strip()
                        break
            
            # 兜底：如果没匹配到 CPU 专用字样，则采用主板检测到的有效温度（如之前的 IT8613E #3）
            if cpu_temp is None:
                for s in sensors:
                    if s.category == "temperature" and s.value > 25.0:
                        cpu_temp = s.value
                        cpu_name = s.name
                        break

            if cpu_temp is not None:
                self.data_updated.emit(cpu_temp, cpu_name)

            time.sleep(1.2)  # 每 1.2 秒轮询一次

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
        # 1. 无边框窗口
        # 2. 窗口永远置顶
        # 3. Tool 类型：不抢占焦点且不在 Windows Alt+Tab 任务切换中显得突兀
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        # 背景透明（配合 QSS 实现圆角和半透明玻璃效果）
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(150, 75)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(2)

        # 标题/传感器说明
        self.label_title = QLabel("CPU TEMP", self)
        self.label_title.setFont(QFont("Segoe UI", 8, QFont.Weight.DemiBold))
        self.label_title.setStyleSheet("color: rgba(255, 255, 255, 0.65); letter-spacing: 1px;")
        layout.addWidget(self.label_title, alignment=Qt.AlignmentFlag.AlignHCenter)

        # 温度大数字显示
        self.label_temp = QLabel("--.- °C", self)
        self.label_temp.setFont(QFont("Consolas", 18, QFont.Weight.Bold))
        layout.addWidget(self.label_temp, alignment=Qt.AlignmentFlag.AlignHCenter)

        # 窗口整体样式（现代暗色卡片 + 细边框 + 圆角）
        self.setStyleSheet("""
            QWidget {
                background-color: rgba(23, 25, 30, 0.88);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 12px;
            }
        """)

    def _init_worker(self):
        self.worker = HardwareWorker()
        self.worker.data_updated.connect(self.update_display)
        self.worker.start()

    def update_display(self, temp: float, name: str):
        # 根据温度动态调整文字颜色
        if temp < 55.0:
            color = "#00E676"  # 绿色（凉爽/低载）
        elif temp < 75.0:
            color = "#FFD600"  # 黄色（温热/中载）
        elif temp < 85.0:
            color = "#FF9100"  # 橙色（高载）
        else:
            color = "#FF1744"  # 红色（过热警告）

        self.label_temp.setText(f"{temp:.1f} °C")
        self.label_temp.setStyleSheet(f"color: {color};")
        self.label_title.setText(name[:16])

    # ================== 鼠标拖动支持 ==================
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # 记录点击位置与窗口左上角的偏移量
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            # 拖动移动窗口
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
        # 动态开关置顶
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
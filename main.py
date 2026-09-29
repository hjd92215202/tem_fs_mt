# main.py
import sys
import time
import platform
import os  # <-- 引入 os 模块

def init_monitor():
    current_os = platform.system()
    if current_os == "Windows":
        from src.win_monitor import WindowsMonitor
        return WindowsMonitor()
    elif current_os == "Darwin":
        from src.mac_monitor import MacMonitor
        return MacMonitor()
    else:
        raise NotImplementedError(f"本程序仅支持 Windows 与 macOS，当前系统: {current_os}")

def clear_screen():
    """跨平台安全清屏"""
    os.system("cls" if platform.system() == "Windows" else "clear")

def main():
    try:
        monitor = init_monitor()
    except Exception as e:
        print(f"\n[启动失败] {e}")
        if platform.system() == "Windows":
            print("👉 提示：Windows 下请确认已将 LibreHardwareMonitorLib.dll 放入 libs 文件夹，并以【管理员身份】运行！")
        sys.exit(1)

    print(f"✅ 成功初始化底层监控，当前系统: {platform.system()}")
    time.sleep(1)

    try:
        while True:
            sensors = monitor.get_sensors()

            clear_screen()  # <-- 使用系统原生清屏，不再出现乱码与滚屏
            print(f"=== 硬件监控运行中 [{platform.system()}] (Ctrl+C 退出) ===")
            print(f"{'类型':<12} | {'传感器名称':<35} | {'读数'}")
            print("-" * 65)

            if not sensors:
                print("暂无数据 (可能未检测到有效工作的传感器)")

            for item in sensors:
                print(item)

            time.sleep(2)
            
    except KeyboardInterrupt:
        print("\n\n正在安全退出监控...")
    finally:
        if hasattr(monitor, "close"):
            monitor.close()
        print("已退出。")

if __name__ == "__main__":
    main()
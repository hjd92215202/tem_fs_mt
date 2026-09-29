# src/win_monitor.py
import os
import sys
import clr
from src.models import SensorItem

def get_dll_path(filename="LibreHardwareMonitorLib.dll"):
    """兼容 PyInstaller 打包后的动态资源寻址"""
    if hasattr(sys, "_MEIPASS"):
        # 打包成单个 exe 运行时，文件在临时解压目录
        base_path = sys._MEIPASS
    else:
        # 本地开发运行时，定位到项目根目录
        base_path = os.path.abspath(".")
    
    # 优先去 libs 目录查找，其次查找同级目录
    potential_paths = [
        os.path.join(base_path, "libs", filename),
        os.path.join(base_path, filename)
    ]
    for p in potential_paths:
        if os.path.exists(p):
            return p
            
    raise FileNotFoundError(f"未找到监控驱动库: {filename}，已查找路径: {potential_paths}")

class WindowsMonitor:
    def __init__(self, dll_path=None):
        # 自动解析真实路径
        abs_dll = get_dll_path() if dll_path is None else os.path.abspath(dll_path)
        
        # 兼容 pythonnet 3.x
        import System
        from System.Reflection import Assembly
        Assembly.LoadFrom(abs_dll)
        clr.AddReference(abs_dll)

        from LibreHardwareMonitor.Hardware import Computer, SensorType
        self.SensorType = SensorType
        
        self.computer = Computer()
        self.computer.IsCpuEnabled = True
        self.computer.IsMotherboardEnabled = True
        self.computer.IsGpuEnabled = True
        self.computer.IsFanControllerEnabled = True
        self.computer.Open()


    def get_sensors(self) -> list[SensorItem]:
        results = []
        for hardware in self.computer.Hardware:
            self._update_hardware_recursive(hardware, results)
        return results

    def _update_hardware_recursive(self, hardware, results):
        """递归更新硬件及其所有子硬件节点"""
        hardware.Update()
        
        # 采集当前硬件节点的所有传感器
        for sensor in hardware.Sensors:
            self._collect_sensor(sensor, results)
            
        # 递归遍历所有子硬件 (SubHardware)
        for sub_hardware in hardware.SubHardware:
            self._update_hardware_recursive(sub_hardware, results)

    def _collect_sensor(self, sensor, results):
        if sensor.Value is None:
            return

        val = float(sensor.Value)

        # 1. 温度传感器采集
        if sensor.SensorType == self.SensorType.Temperature:
            # 过滤规则：主板未接线针脚通常恒定在 0℃、14℃ 或大于 120℃
            # 如果是正常读数，则收录
            if 15.0 < val < 115.0:
                results.append(SensorItem(
                    category="temperature",
                    name=f"{sensor.Hardware.Name} - {sensor.Name}",
                    value=round(val, 1),
                    unit="°C"
                ))

        # 2. 风扇传感器采集
        elif sensor.SensorType == self.SensorType.Fan:
            results.append(SensorItem(
                category="fan",
                name=f"{sensor.Hardware.Name} - {sensor.Name}",
                value=round(val, 0),
                unit="RPM"
            ))

    def close(self):
        self.computer.Close()
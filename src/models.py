# src/models.py
from dataclasses import dataclass

@dataclass
class SensorItem:
    category: str      # 'temperature' (温度) 或 'fan' (风扇)
    name: str          # 传感器名称，例如 "CPU Core #1", "Main Fan"
    value: float       # 数值
    unit: str          # "°C" 或 "RPM"

    def __str__(self):
        return f"[{self.category.upper():<11}] {self.name:<32} : {self.value:>6.1f} {self.unit}"
# src/mac_monitor.py
import ctypes
import ctypes.util
import struct
from src.models import SensorItem

# 声明 SMC 数据结构
class SMCVersion(ctypes.Structure):
    _fields_ = [("major", ctypes.c_uint8), ("minor", ctypes.c_uint8),
                ("build", ctypes.c_uint8), ("reserved", ctypes.c_uint8),
                ("release", ctypes.c_uint16)]

class SMCPLimitData(ctypes.Structure):
    _fields_ = [("version", ctypes.c_uint16), ("length", ctypes.c_uint16),
                ("cpuPLimit", ctypes.c_uint32), ("gpuPLimit", ctypes.c_uint32),
                ("memPLimit", ctypes.c_uint32)]

class SMCKeyInfoData(ctypes.Structure):
    _fields_ = [("dataSize", ctypes.c_uint32), ("dataType", ctypes.c_uint32),
                ("dataAttributes", ctypes.c_uint8)]

class SMCParamStruct(ctypes.Structure):
    _fields_ = [
        ("key", ctypes.c_uint32),
        ("vers", SMCVersion),
        ("pLimitData", SMCPLimitData),
        ("keyInfo", SMCKeyInfoData),
        ("result", ctypes.c_uint8),
        ("status", ctypes.c_uint8),
        ("data8", ctypes.c_uint8),
        ("data32", ctypes.c_uint32),
        ("bytes", ctypes.c_uint8 * 32)
    ]

class MacMonitor:
    def __init__(self):
        iokit_path = ctypes.util.find_library("IOKit")
        self.iokit = ctypes.cdll.LoadLibrary(iokit_path)
        self.conn = self._open_smc()

    def _open_smc(self):
        matching = self.iokit.IOServiceMatching(b"AppleSMC")
        service = self.iokit.IOServiceGetMatchingService(0, matching)
        if not service:
            return None
        conn = ctypes.c_void_p()
        # 0: 客户端类型
        kr = self.iokit.IOServiceOpen(service, self.iokit.mach_task_self(), 0, ctypes.byref(conn))
        self.iokit.IOObjectRelease(service)
        return conn if kr == 0 else None

    def _read_smc_val(self, key_str: str):
        if not self.conn:
            return None
        
        # 将 4 字符转为整型 Key
        key_int = struct.unpack(">I", key_str.encode("ascii"))[0]
        
        # 第一步：获取 Key 元数据 (大小/类型)
        inp = SMCParamStruct()
        out = SMCParamStruct()
        inp.key = key_int
        inp.data8 = 9  # SMC_CMD_READ_KEYINFO
        
        size = ctypes.c_size_t(ctypes.sizeof(SMCParamStruct))
        kr = self.iokit.IOConnectCallStructMethod(
            self.conn, 2, ctypes.byref(inp), size, ctypes.byref(out), ctypes.byref(size)
        )
        if kr != 0:
            return None

        val_size = out.keyInfo.dataSize
        data_type = out.keyInfo.dataType

        # 第二步：获取具体数据
        inp.keyInfo.dataSize = val_size
        inp.data8 = 5  # SMC_CMD_READ_BYTES
        kr = self.iokit.IOConnectCallStructMethod(
            self.conn, 2, ctypes.byref(inp), size, ctypes.byref(out), ctypes.byref(size)
        )
        if kr != 0:
            return None

        # 解码：fpe2 类型 (转速常用，表示 14 位整数 + 2 位小数)
        if data_type == 0x66706532:  # 'fpe2'
            raw = (out.bytes[0] << 8) | out.bytes[1]
            return float(raw >> 2)
        # 解码：flt 类型 (32位浮点)
        elif data_type == 0x666C7420: # 'flt '
            return struct.unpack("<f", bytes(out.bytes[:4]))[0]
        # 解码：sp78 类型 (有符号 8.8 固定点数，常用于温度)
        elif data_type == 0x73703738: # 'sp78'
            raw = (out.bytes[0] << 8) | out.bytes[1]
            return float(raw) / 256.0
            
        return None

    def get_sensors(self) -> list[SensorItem]:
        results = []
        if not self.conn:
            return results

        # 1. 读取风扇转速 (F0Ac: Fan 0 Actual, F1Ac: Fan 1 Actual)
        for i, key in enumerate(["F0Ac", "F1Ac"]):
            val = self._read_smc_val(key)
            if val is not None and val >= 0:
                results.append(SensorItem(
                    category="fan",
                    name=f"Fan #{i+1} ({'Left' if i==0 else 'Right'})",
                    value=round(val, 0),
                    unit="RPM"
                ))

        # 2. 读取温度 (常见 Key: TC0P - Intel CPU, Tp09/Tp0T - M系列芯片集群)
        temp_keys = [("TC0P", "CPU Die"), ("Tp09", "Apple Silicon CPU Efficiency"), ("Tp0T", "Apple Silicon CPU Performance")]
        for key, label in temp_keys:
            val = self._read_smc_val(key)
            if val is not None and 10 < val < 115:  # 过滤异常读数
                results.append(SensorItem(
                    category="temperature",
                    name=label,
                    value=round(val, 1),
                    unit="°C"
                ))
                break  # 命中一种方案即可

        # 提示：如果为 MacBook Air，本身是无风扇设计，风扇列表为空属于正常
        return results

    def close(self):
        if self.conn:
            self.iokit.IOServiceClose(self.conn)
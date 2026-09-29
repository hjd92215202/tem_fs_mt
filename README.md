## 激活环境
```
python -m venv venv
```
放开当前用户的脚本执行权限
```
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

.\venv\Scripts\Activate.ps1
```
## 安装依赖
```
pip install -r requirements.txt
```
## 运行
```
python main.py
```
## 清理旧的编译缓存
```
Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue

Remove-Item *.spec -ErrorAction SilentlyContinue
```
## 打包
```
pyinstaller -F -w --uac-admin --add-data "libs\*.dll;libs" -n "CpuTempOverlay" ui_main.py
```

```
pyinstaller -F -w --uac-admin `
  --add-data "libs\*.dll;libs" `
  --add-data "venv\Lib\site-packages\PySide6\plugins\platforms;PySide6\plugins\platforms" `
  --add-data "venv\Lib\site-packages\PySide6\plugins\styles;PySide6\plugins\styles" `
  --exclude-module PySide6.QtQml `
  --exclude-module PySide6.QtQuick `
  --exclude-module PySide6.QtNetwork `
  --exclude-module PySide6.QtPdf `
  --exclude-module PySide6.QtSvg `
  --exclude-module PySide6.QtSql `
  --exclude-module PySide6.QtXml `
  --exclude-module PySide6.QtMultimedia `
  --exclude-module PySide6.Qt3DCore `
  --exclude-module PySide6.QtSensors `
  --exclude-module PySide6.QtBluetooth `
  -n "CpuTempOverlay" ui_main.py
```

## 删除内核驱动
```
Get-CimInstance Win32_SystemDriver | Where-Object { $_.PathName -like "HardwareMonitor.sys" } | Select-Object Name, State, PathName
```


### 1. 停止该驱动服务 name
```
sc.exe stop R0HardwareMonitor
```

### 2. 从系统中注销该服务
```
sc.exe delete R0HardwareMonitor
```
### 3. 彻底删除该文件
```
Remove-Item -Force .\dist\HardwareMonitor.sys
```



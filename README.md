## 激活环境
放开当前用户的脚本执行权限

Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

.\venv\Scripts\Activate.ps1

## 安装依赖
pip install -r requirements.txt

## 运行
python main.py

## 清理旧的编译缓存
Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue

Remove-Item *.spec -ErrorAction SilentlyContinue

## 打包
pyinstaller -F -w --uac-admin --add-data "libs\*.dll;libs" -n "CpuTempOverlay" ui_main.py


## 删除内核驱动
Get-CimInstance Win32_SystemDriver | Where-Object { $_.PathName -like "HardwareMonitor.sys" } | Select-Object Name, State, PathName


### 1. 停止该驱动服务 name
sc.exe stop R0HardwareMonitor

### 2. 从系统中注销该服务
sc.exe delete R0HardwareMonitor

### 3. 彻底删除该文件
Remove-Item -Force .\dist\HardwareMonitor.sys
## 激活环境
.\venv\Scripts\activate.bat

## 清理旧的编译缓存
Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue
Remove-Item *.spec -ErrorAction SilentlyContinue
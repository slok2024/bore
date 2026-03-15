bore 是一个简单的 CLI 工具，用于创建到本地主机的隧道。

pyinstaller --noconsole --onefile ^
--add-data "bore32.exe;." ^
--add-data "bore64.exe;." ^
bore.py


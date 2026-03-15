import sys
import os
import subprocess
import threading
import re
import webbrowser
import shutil
import tkinter as tk
from tkinter import messagebox, ttk
import time

def get_bore_executable():
    arch_str = os.environ.get("PROCESSOR_ARCHITECTURE", "x86").upper()
    wow64_arch = os.environ.get("PROCESSOR_ARCHITEW6432", "").upper()
    is_64bit = (arch_str == "AMD64" or wow64_arch == "AMD64")
    target_exe = "bore64.exe" if is_64bit else "bore32.exe"
    
    if hasattr(sys, 'frozen'):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        
    local_path = os.path.join(base_dir, target_exe)
    
    if not os.path.exists(local_path) and hasattr(sys, '_MEIPASS'):
        bundled_path = os.path.join(sys._MEIPASS, target_exe)
        if os.path.exists(bundled_path):
            try:
                shutil.copy2(bundled_path, local_path)
            except:
                pass
                
    return local_path, "x64" if is_64bit else "x86"

class BoreGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Bore 内网穿透工具 - 客户端")
        self.root.geometry("500x480")
        
        self.bore_exe, self.arch = get_bore_executable()
        self.process = None
        
        self.create_widgets()
        
        # 绑定窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_widgets(self):
        info_frame = ttk.LabelFrame(self.root, text=" 系统与内核信息 ")
        info_frame.pack(fill="x", padx=10, pady=5)
        ttk.Label(info_frame, text=f"当前系统架构: {self.arch}").pack(anchor="w", padx=5)
        exe_name = os.path.basename(self.bore_exe)
        self.status_label = ttk.Label(info_frame, text=f"调用内核: {exe_name}", foreground="blue")
        self.status_label.pack(anchor="w", padx=5)

        config_frame = ttk.LabelFrame(self.root, text=" 参数配置 ")
        config_frame.pack(fill="x", padx=10, pady=5)
        ttk.Label(config_frame, text="本地端口:").grid(row=0, column=0, padx=5, pady=5)
        self.port_entry = ttk.Entry(config_frame)
        self.port_entry.insert(0, "8000")
        self.port_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ttk.Label(config_frame, text="远程服务器:").grid(row=1, column=0, padx=5, pady=5)
        self.server_entry = ttk.Entry(config_frame)
        self.server_entry.insert(0, "bore.pub")
        self.server_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        ctrl_frame = tk.Frame(self.root)
        ctrl_frame.pack(pady=10)
        self.start_btn = ttk.Button(ctrl_frame, text="启动穿透", command=self.start_bore)
        self.start_btn.pack(side="left", padx=5)
        self.stop_btn = ttk.Button(ctrl_frame, text="停止并清理", command=self.stop_bore, state="disabled")
        self.stop_btn.pack(side="left", padx=5)

        output_frame = ttk.LabelFrame(self.root, text=" 运行状态与公网地址 ")
        output_frame.pack(fill="both", expand=True, padx=10, pady=5)
        self.url_display = ttk.Entry(output_frame, font=("Consolas", 10, "bold"), foreground="green")
        self.url_display.pack(fill="x", padx=5, pady=5)
        self.open_btn = ttk.Button(output_frame, text="点击在浏览器中打开地址", command=self.open_browser, state="disabled")
        self.open_btn.pack(pady=2)

        log_frame = tk.Frame(output_frame)
        log_frame.pack(fill="both", expand=True, padx=5, pady=5)
        self.log_text = tk.Text(log_frame, height=8, font=("Consolas", 9), wrap="none")
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.log_text.pack(side="left", fill="both", expand=True)

    def log(self, message):
        clean_msg = re.sub(r'\x1b\[[0-9;]*m', '', message)
        self.log_text.insert(tk.END, clean_msg + "\n")
        self.log_text.see(tk.END)

    def start_bore(self):
        # 确保启动前内核文件存在（如果被手动删除了则重新释放）
        self.bore_exe, _ = get_bore_executable()
        
        port = self.port_entry.get()
        server = self.server_entry.get()
        if not os.path.exists(self.bore_exe):
            messagebox.showerror("错误", "无法释放或找到内核文件")
            return

        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.log("--- 正在启动服务 ---")
        self.thread = threading.Thread(target=self.run_process, args=(port, server), daemon=True)
        self.thread.start()

    def run_process(self, port, server):
        cmd = [self.bore_exe, "local", port, "--to", server]
        try:
            self.process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1, creationflags=subprocess.CREATE_NO_WINDOW
            )
            for line in self.process.stdout:
                self.log(line.strip())
                match = re.search(r"listening at ([\w\.-]+:\d+)", line)
                if match:
                    full_url = f"http://{match.group(1)}"
                    self.root.after(0, self.update_url, full_url)
        except Exception as e:
            self.root.after(0, self.log, f"错误: {str(e)}")

    def update_url(self, url):
        self.url_display.delete(0, tk.END)
        self.url_display.insert(0, url)
        self.open_btn.config(state="normal")

    def open_browser(self):
        url = self.url_display.get()
        if url: webbrowser.open(url)

    def cleanup_kernel(self):
        """ 尝试删除释放出来的内核文件 """
        if os.path.exists(self.bore_exe):
            try:
                # 稍微等待进程完全退出锁定
                time.sleep(0.2)
                os.remove(self.bore_exe)
                self.log(f"已清理内核文件: {os.path.basename(self.bore_exe)}")
            except:
                pass

    def stop_bore(self):
        if self.process:
            self.process.terminate()
            self.process.wait() # 等待进程结束
            self.process = None
        self.log("--- 服务已停止 ---")
        self.cleanup_kernel()
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.open_btn.config(state="disabled")
        self.url_display.delete(0, tk.END)

    def on_closing(self):
        """ 退出程序时的处理 """
        if self.process:
            self.process.terminate()
        self.cleanup_kernel()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = BoreGUI(root)
    root.mainloop()
"""快速测试脚本 - 自动输入 Y 跳过人工审核"""
import subprocess
import sys
import os

# 设置 UTF-8 编码
os.environ['PYTHONIOENCODING'] = 'utf-8'

# 先安装依赖
print("Installing dependencies...")
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "duckduckgo-search"], check=True)

# 运行主脚本，模拟输入 "Y"
print("\nStarting research system...")
print("(Auto input 'Y' to skip human review)\n")

process = subprocess.Popen(
    [sys.executable, "industry_research_agent.py"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    encoding='utf-8',
    errors='replace'
)

# 自动输入 Y
try:
    output, _ = process.communicate(input="Y\n", timeout=300)
    print(output)
except subprocess.TimeoutExpired:
    process.kill()
    print("Timeout! Process killed.")

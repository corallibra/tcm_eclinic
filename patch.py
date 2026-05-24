# -*- coding: utf-8 -*-
"""
fix_logger_shutdown_safety_final.py
===================================
功能：
✅ 自动检测并删除旧版本 patch 插入的错误 closeEvent()（含 \"\"\" 转义问题）
✅ 插入正确的 closeEvent() 安全退出逻辑
✅ 自动创建备份 (.bak)
✅ 自动执行语法检查 (compileall)
"""

from pathlib import Path
import re
import compileall

ROOT = Path(__file__).resolve().parent
GUI_FILE = ROOT / "src" / "ui" / "gui_main.py"

if not GUI_FILE.exists():
    raise FileNotFoundError(f"❌ 未找到目标文件: {GUI_FILE}")

print(f"🔍 目标文件: {GUI_FILE}")

# === 读取文件 ===
text = GUI_FILE.read_text(encoding="utf-8")
original_text = text

# === Step 1️⃣ 删除旧的错误版本 closeEvent() ===
# 捕获所有包含 “窗口关闭时清理日志 handler” 的 closeEvent 定义（无论是否带转义）
old_pattern = re.compile(
    r"def\s+closeEvent\s*\([^)]*\):[\s\S]{0,600}?super\(\)\.closeEvent\(event\)",
    re.MULTILINE,
)
matches = list(old_pattern.finditer(text))
if matches:
    print(f"🧹 检测到旧版本 closeEvent() 共 {len(matches)} 处，正在移除...")
    text = old_pattern.sub("", text)

# === Step 2️⃣ 插入新的正确版本 closeEvent() ===
if "def closeEvent" not in text:
    close_event_code = '''
    def closeEvent(self, event):
        """窗口关闭时清理日志 handler，防止 QTextEditHandler 已被销毁"""
        try:
            import logging
            for handler in list(self.log.handlers):
                if hasattr(handler, "close"):
                    handler.close()
                self.log.removeHandler(handler)
            self.log.handlers.clear()
            self.log.info("日志系统已安全关闭。")
        except Exception as e:
            print(f"[警告] 关闭日志处理器时出错: {e}")
        super().closeEvent(event)
'''

    pattern = re.compile(r"class\s+MainWindow\s*\([^)]*\):")
    match = pattern.search(text)
    if not match:
        raise ValueError("❌ 未找到 MainWindow 类定义，请确认 gui_main.py 文件结构。")

    # 找到最后一个 def 的缩进点
    insertion_point = text.rfind("    def ", match.end())
    if insertion_point == -1:
        insertion_point = len(text)

    text = text[:insertion_point] + close_event_code + "\n" + text[insertion_point:]
    print("✅ 已插入新的 closeEvent() 安全退出逻辑。")
else:
    print("ℹ️ 已存在正确的 closeEvent()，无需插入。")

# === Step 3️⃣ 写入备份并保存 ===
backup_file = GUI_FILE.with_suffix(".bak")
backup_file.write_text(original_text, encoding="utf-8")
GUI_FILE.write_text(text, encoding="utf-8")
print(f"📦 已备份原文件 → {backup_file}")
print(f"🎯 修改完成: {GUI_FILE}")

# === Step 4️⃣ 自动语法验证 ===
print("\n🧠 正在执行语法检查 (compileall)...")
if compileall.compile_file(str(GUI_FILE), quiet=1):
    print("✅ 语法检查通过。")
else:
    print("⚠️ 检测到语法错误，请打开文件检查缩进。")

print("\n💡 请运行: python main.py 并关闭窗口，验证是否无退出异常。")

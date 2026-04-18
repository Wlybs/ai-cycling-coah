"""
公共工具函数，供所有脚本共享使用。
"""
import sys
import os
import json


def setup_encoding():
    """Windows 环境下强制 stdout 使用 UTF-8。"""
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8')


def get_warehouse_dir():
    """从环境变量读取数据仓库根目录，默认 ./icu_data_warehouse。"""
    return os.getenv("OUTPUT_WAREHOUSE_DIR", "./icu_data_warehouse")


def save_json(data, folder, filename):
    """将数据序列化为 JSON 并保存，自动创建目录。"""
    os.makedirs(folder, exist_ok=True)
    full_path = os.path.join(folder, filename)
    with open(full_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    return full_path


def load_json(filepath):
    """读取 JSON 文件，失败时返回 None。"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None

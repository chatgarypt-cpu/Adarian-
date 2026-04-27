"""
test7_1 运行脚本 - 注入 JSON 解析修复
不修改源代码，通过 monkey patch 解决中文引号解析问题
"""

import sys
import os
import re
import json
import ast

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入并 patch
import src.phase1_entity_extraction as phase1

def _parse_json_candidate_fixed(candidate: str):
    """修复版：处理字符串值中的中文引号"""
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass

    normalized = candidate.replace("{{", "{").replace("}}", "}")
    normalized = re.sub(r",(\s*[}\]])", r"\1", normalized)
    normalized = re.sub(r"\bNone\b", "null", normalized)
    normalized = re.sub(r"\bTrue\b", "true", normalized)
    normalized = re.sub(r"\bFalse\b", "false", normalized)

    try:
        return json.loads(normalized)
    except json.JSONDecodeError:
        pass

    # 新增：将字符串值内部的中文引号替换为普通字符（只替换值内部的，不替换 key）
    # 策略：将中文引号替换为普通空格字符，避免被解析器误判
    # 这样不会影响 JSON key 的引号（因为 key 使用的是英文引号）
    normalized_fixed = normalized

    # 只替换中文引号为单引号（在字符串值内部，单引号不会被误判为边界）
    # 因为 JSON 字符串边界是英文双引号，中文引号是全角字符，换成单引号后不会被误判
    normalized_fixed = normalized_fixed.replace('"', "'")
    normalized_fixed = normalized_fixed.replace('"', "'")
    normalized_fixed = normalized_fixed.replace(''', "'")
    normalized_fixed = normalized_fixed.replace(''', "'")

    python_literal = re.sub(r"\btrue\b", "True", normalized_fixed)
    python_literal = re.sub(r"\bfalse\b", "False", python_literal)
    python_literal = re.sub(r"\bnull\b", "None", python_literal)

    return ast.literal_eval(python_literal)

# Monkey patch
phase1._parse_json_candidate = _parse_json_candidate_fixed

print("[注入] JSON 解析修复已加载，处理中文引号问题")

# 设置命令行参数
sys.argv = ["run_test7_1_injected.py", "seeds/test7_1.txt"]

# 运行 main
from main import main

if __name__ == "__main__":
    main()
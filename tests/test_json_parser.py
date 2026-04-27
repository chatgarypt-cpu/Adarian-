"""
test_json_parser.py - JSON Parser 中文引号兼容层单元测试
---

测试 _normalize_inner_cjk_quotes() 和 _parse_json_candidate() 的中文引号处理能力。

新增于：v1.2.0（test7_1 白盒测试收口修复）
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.phase1_entity_extraction import _normalize_inner_cjk_quotes, _parse_json_candidate


def run_tests():
    """运行所有测试"""
    test = TestNormalizeInnerCJKQuotes()
    test2 = TestParseJsonCandidate()

    tests_passed = 0
    tests_failed = 0

    # TestNormalizeInnerCJKQuotes
    print("=== TestNormalizeInnerCJKQuotes ===")
    for name, method in [
        ("case1_no_cjk_quotes", test.test_case1_no_cjk_quotes),
        ("case2_cjk_quotes_in_value", test.test_case2_cjk_quotes_in_value),
        ("case3_json_key_not_affected", test.test_case3_json_key_not_affected),
        ("case4_none_true_false_compatible", test.test_case4_none_true_false_compatible),
        ("case5_mixed_cjk_quotes", test.test_case5_mixed_cjk_quotes),
        ("case6_real_test7_1_pattern", test.test_case6_real_test7_1_pattern),
    ]:
        try:
            method()
            print(f"✓ {name}")
            tests_passed += 1
        except Exception as e:
            print(f"✗ {name}: {e}")
            tests_failed += 1

    # TestParseJsonCandidate
    print("=== TestParseJsonCandidate ===")
    for name, method in [
        ("valid_json_direct_path", test2.test_valid_json_direct_path),
        ("trailing_comma", test2.test_trailing_comma),
        ("double_braces", test2.test_double_braces),
        ("cjk_quotes_with_other_issues", test2.test_cjk_quotes_with_other_issues),
    ]:
        try:
            method()
            print(f"✓ {name}")
            tests_passed += 1
        except Exception as e:
            print(f"✗ {name}: {e}")
            tests_failed += 1

    print(f"\n总结: {tests_passed} passed, {tests_failed} failed")
    return tests_failed == 0


class TestNormalizeInnerCJKQuotes:
    """测试 _normalize_inner_cjk_quotes() helper 函数"""

    def test_case1_no_cjk_quotes(self):
        """Case 1: 合法 JSON，无中文引号，应保持不变"""
        input_str = '{"event_type": "执法程序争议"}'
        output = _normalize_inner_cjk_quotes(input_str)
        assert output == input_str
        # 验证 JSON 解析成功
        parsed = _parse_json_candidate(output)
        assert parsed["event_type"] == "执法程序争议"

    def test_case2_cjk_quotes_in_value(self):
        """Case 2: 字符串 value 内含中文引号，应成功解析"""
        # 使用 Unicode escape 确保正确的中文引号字符
        # U+201C = 左中文双引号 "，U+201D = 右中文双引号 "
        LEFT_CJK_DQ = "“"  # "
        RIGHT_CJK_DQ = "”"  # "
        input_str = '{"event_summary": "深圳公交站劝烟纠纷引发' + LEFT_CJK_DQ + '裸检' + RIGHT_CJK_DQ + '争议", "event_type": "执法程序争议"}'
        output = _normalize_inner_cjk_quotes(input_str)
        # 中文引号应被替换为单引号
        assert LEFT_CJK_DQ not in output
        assert RIGHT_CJK_DQ not in output
        # 验证 JSON 解析成功
        parsed = _parse_json_candidate(input_str)
        assert "event_summary" in parsed
        # 语义应保留（单引号表示引用）
        assert "裸检" in parsed["event_summary"] or "'裸检'" in parsed["event_summary"]

    def test_case3_json_key_not_affected(self):
        """Case 3: JSON key 的双引号不得被破坏"""
        LEFT_CJK_DQ = "“"  # "
        RIGHT_CJK_DQ = "”"  # "
        input_str = '{"event_summary": "深圳公交站引发' + LEFT_CJK_DQ + '裸检' + RIGHT_CJK_DQ + '争议"}'
        output = _normalize_inner_cjk_quotes(input_str)
        # JSON key 的边界英文双引号应保留
        assert '"event_summary"' in output
        parsed = _parse_json_candidate(input_str)
        assert "event_summary" in parsed

    def test_case4_none_true_false_compatible(self):
        """Case 4: None / True / False 兼容逻辑如原有行为存在，不得回归"""
        # 测试 None -> null 兼容
        input_str = '{"test_none": None, "test_true": True, "test_false": False}'
        parsed = _parse_json_candidate(input_str)
        assert parsed["test_none"] is None
        assert parsed["test_true"] is True
        assert parsed["test_false"] is False

    def test_case5_mixed_cjk_quotes(self):
        """Case 5: 混合中文单引号和双引号"""
        # U+2018 = 左中文单引号 '，U+2019 = 右中文单引号 '
        LEFT_CJK_SQ = "‘"  # '
        RIGHT_CJK_SQ = "’"  # '
        input_str = '{"text": "他说' + LEFT_CJK_SQ + '执法不当' + RIGHT_CJK_SQ + '引发争议"}'
        output = _normalize_inner_cjk_quotes(input_str)
        # 中文单引号应被替换为普通单引号
        assert LEFT_CJK_SQ not in output
        assert RIGHT_CJK_SQ not in output
        parsed = _parse_json_candidate(input_str)
        assert "text" in parsed

    def test_case6_real_test7_1_pattern(self):
        """Case 6: test7_1 实际场景"""
        LEFT_CJK_DQ = "“"  # "
        RIGHT_CJK_DQ = "”"  # "
        input_str = '{"event_summary": "深圳公交站劝烟纠纷引发执法程序争议，境外媒体炒作' + LEFT_CJK_DQ + '裸检' + RIGHT_CJK_DQ + '指控"}'
        parsed = _parse_json_candidate(input_str)
        assert "event_summary" in parsed
        # 验证语义保留
        assert "裸检" in parsed["event_summary"] or "'裸检'" in parsed["event_summary"]


class TestParseJsonCandidate:
    """测试 _parse_json_candidate() 整体行为"""

    def test_valid_json_direct_path(self):
        """合法 JSON 应直接 json.loads 成功"""
        input_str = '{"a": 1, "b": "test"}'
        parsed = _parse_json_candidate(input_str)
        assert parsed["a"] == 1
        assert parsed["b"] == "test"

    def test_trailing_comma(self):
        """尾逗号应被 normalization 处理"""
        input_str = '{"a": 1, "b": "test",}'
        parsed = _parse_json_candidate(input_str)
        assert parsed["a"] == 1
        assert parsed["b"] == "test"

    def test_double_braces(self):
        """双花括号应被 normalization 处理"""
        input_str = '{{"a": 1}}'
        parsed = _parse_json_candidate(input_str)
        assert parsed["a"] == 1

    def test_cjk_quotes_with_other_issues(self):
        """中文引号 + 其他问题（尾逗号）应能处理"""
        LEFT_CJK_DQ = "“"  # "
        RIGHT_CJK_DQ = "”"  # "
        input_str = '{"event_summary": "深圳公交站引发' + LEFT_CJK_DQ + '裸检' + RIGHT_CJK_DQ + '争议",}'
        parsed = _parse_json_candidate(input_str)
        assert "event_summary" in parsed


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
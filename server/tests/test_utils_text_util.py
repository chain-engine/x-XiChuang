# -*- coding: utf-8 -*-
"""
文本工具类单元测试
"""

from src.utils.text_util import TextUtil


class TestKMPSearch:
    """KMP 子串匹配测试"""

    def test_match_found(self):
        assert TextUtil.match_sub_str("hello world", "world") == 6

    def test_match_at_start(self):
        assert TextUtil.match_sub_str("hello world", "hello") == 0

    def test_no_match(self):
        assert TextUtil.match_sub_str("hello world", "xyz") == -1

    def test_empty_string(self):
        assert TextUtil.match_sub_str("", "hello") == -1

    def test_chinese_text(self):
        assert TextUtil.match_sub_str("你好世界", "世界") == 2

    def test_repeated_pattern(self):
        assert TextUtil.match_sub_str("abcabcabc", "abc") == 0

    def test_partial_match(self):
        """部分匹配时应回溯正确"""
        assert TextUtil.match_sub_str("abababc", "ababc") == 2


class TestGetSameStartEnd:
    """最长前后缀测试"""

    def test_single_char(self):
        assert TextUtil.get_same_start_end("a") == [0]

    def test_empty_string(self):
        assert TextUtil.get_same_start_end("") == []

    def test_repeated_prefix(self):
        result = TextUtil.get_same_start_end("abab")
        assert len(result) == 4


class TestIsStr:
    """字符串判断测试"""

    def test_string(self):
        assert TextUtil.is_str("hello") is True

    def test_bytes(self):
        assert TextUtil.is_str(b"hello") is True

    def test_int(self):
        assert TextUtil.is_str(123) is False

    def test_none(self):
        assert TextUtil.is_str(None) is False

    def test_list(self):
        assert TextUtil.is_str([1, 2]) is False


class TestChineseDetection:
    """中文检测测试"""

    def test_all_chinese(self):
        assert TextUtil.is_all_chinese("你好世界") is True

    def test_not_all_chinese(self):
        assert TextUtil.is_all_chinese("你好abc") is False

    def test_contains_chinese(self):
        assert TextUtil.is_contains_chinese("hello你好") is True

    def test_no_chinese(self):
        assert TextUtil.is_contains_chinese("hello") is False

    def test_empty_string(self):
        assert TextUtil.is_all_chinese("") is True
        assert TextUtil.is_contains_chinese("") is False


class TestHashFunctions:
    """哈希函数测试"""

    def test_md5_deterministic(self):
        assert TextUtil.calculate_md5("test") == TextUtil.calculate_md5("test")

    def test_md5_different_inputs(self):
        assert TextUtil.calculate_md5("a") != TextUtil.calculate_md5("b")

    def test_sha1_deterministic(self):
        assert TextUtil.calculate_sha1("test") == TextUtil.calculate_sha1("test")

    def test_sha256_deterministic(self):
        assert TextUtil.calculate_sha256("test") == TextUtil.calculate_sha256("test")

    def test_crc32_deterministic(self):
        assert TextUtil.calculate_crc32("test") == TextUtil.calculate_crc32("test")

    def test_md5_length(self):
        assert len(TextUtil.calculate_md5("test")) == 32

    def test_sha1_length(self):
        assert len(TextUtil.calculate_sha1("test")) == 40

    def test_sha256_length(self):
        assert len(TextUtil.calculate_sha256("test")) == 64


class TestHashValidation:
    """哈希值校验测试"""

    def test_valid_md5(self):
        assert TextUtil.is_md5_value("d41d8cd98f00b204e9800998ecf8427e") is True

    def test_invalid_md5(self):
        assert TextUtil.is_md5_value("not-a-md5") is False

    def test_valid_sha1(self):
        assert TextUtil.is_sha1_value("da39a3ee5e6b4b0d3255bfef95601890afd80709") is True

    def test_invalid_sha1(self):
        assert TextUtil.is_sha1_value("not-a-sha1") is False

    def test_valid_sha256(self):
        assert TextUtil.is_sha256_value(
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        ) is True

    def test_invalid_sha256(self):
        assert TextUtil.is_sha256_value("not-a-sha256") is False


class TestStringSimilar:
    """字符串相似度测试"""

    def test_identical_strings(self):
        assert TextUtil.string_similar("hello", "hello") == 1.0

    def test_completely_different(self):
        assert TextUtil.string_similar("abc", "xyz") < 0.5

    def test_similar_strings(self):
        ratio = TextUtil.string_similar("hello", "hallo")
        assert 0.5 < ratio < 1.0


class TestConvertChToArabic:
    """汉字数字转阿拉伯数字测试"""

    def test_basic_conversion(self):
        assert TextUtil.convert_ch_to_arabic("一二三") == "123"

    def test_mixed_content(self):
        assert TextUtil.convert_ch_to_arabic("第一二三章") == "第123章"

    def test_no_chinese_numbers(self):
        assert TextUtil.convert_ch_to_arabic("hello") == "hello"


class TestGetCharMaxIndex:
    """字符最大索引测试"""

    def test_found(self):
        assert TextUtil.get_char_max_index("hello", "l") == 3

    def test_single_occurrence(self):
        assert TextUtil.get_char_max_index("hello", "h") == 0

    def test_not_found_raises(self):
        import pytest
        with pytest.raises(ValueError):
            TextUtil.get_char_max_index("hello", "z")

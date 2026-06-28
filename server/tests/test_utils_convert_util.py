# -*- coding: utf-8 -*-
"""
数据转换工具类单元测试
"""

import pytest

from src.utils.convert_util import ConvertUtil


class TestXmlDataToJsonData:
    """XML 数据转 JSON 测试"""

    def test_simple_xml(self):
        xml = "<root><name>test</name><age>18</age></root>"
        result = ConvertUtil.xml_data_to_json_data(xml)
        assert result["root"]["name"] == "test"
        assert result["root"]["age"] == "18"

    def test_nested_xml(self):
        xml = "<root><person><name>张三</name></person></root>"
        result = ConvertUtil.xml_data_to_json_data(xml)
        assert result["root"]["person"]["name"] == "张三"

    def test_invalid_xml_raises(self):
        with pytest.raises(Exception):
            ConvertUtil.xml_data_to_json_data("not xml")


class TestYamlConversion:
    """YAML 转换测试"""

    def test_yaml_load(self):
        yaml_str = "name: test\nage: 18\n"
        result = ConvertUtil.yaml_load(yaml_str)
        assert result["name"] == "test"
        assert result["age"] == 18

    def test_yaml_dump(self):
        data = {"name": "test", "age": 18}
        result = ConvertUtil.yaml_dump(data)
        assert "name: test" in result
        assert "age: 18" in result

    def test_yaml_round_trip(self):
        original = {"key": "value", "list": [1, 2, 3]}
        yaml_str = ConvertUtil.yaml_dump(original)
        loaded = ConvertUtil.yaml_load(yaml_str)
        assert loaded == original


class TestFloatToInt:
    """float_to_int 测试"""

    def test_int_input(self):
        assert ConvertUtil.float_to_int(42) == 42

    def test_float_input(self):
        assert ConvertUtil.float_to_int(3.7) == 3

    def test_string_int(self):
        assert ConvertUtil.float_to_int("42") == 42

    def test_string_float(self):
        assert ConvertUtil.float_to_int("3.7") == 3


class TestDictToObj:
    """字典转对象测试"""

    def test_simple_dict(self):
        obj = ConvertUtil.dict_to_obj({"name": "张三", "age": 18})
        assert obj.name == "张三"
        assert obj.age == 18

    def test_nested_dict(self):
        obj = ConvertUtil.dict_to_obj({"person": {"name": "test"}})
        assert obj.person.name == "test"

    def test_non_dict_passthrough(self):
        assert ConvertUtil.dict_to_obj("hello") == "hello"
        assert ConvertUtil.dict_to_obj(42) == 42

    def test_empty_dict(self):
        obj = ConvertUtil.dict_to_obj({})
        assert dict(obj) == {}

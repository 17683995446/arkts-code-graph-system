import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

from src.parser import ArkTSParser, LocalArkTSParser
from src.models import ParsedFile


class TestLocalArkTSParser:
    def test_parse_functions(self):
        parser = LocalArkTSParser()
        
        code = """
function getData(): string {
  return "test"
}

async function fetchUser(id: number): User {
  return { name: "test" }
}
"""
        result = parser.parse_content(code, "test.ets")
        
        assert len(result.functions) == 2
        assert result.functions[0].name == "getData"
        assert result.functions[0].return_type == "string"
        assert result.functions[1].name == "fetchUser"
        assert result.functions[1].return_type == "User"

    def test_parse_component_struct(self):
        parser = LocalArkTSParser()
        
        code = """
@Entry
@Component
struct MyComponent {
  build() {
    Column() {}
  }
}
"""
        result = parser.parse_content(code, "test.ets")
        
        assert len(result.classes) == 1
        assert result.classes[0].name == "MyComponent"
        assert "Component" in result.classes[0].modifiers

    def test_parse_regular_struct(self):
        parser = LocalArkTSParser()
        
        code = """
struct DataModel {
  id: number
  name: string
}
"""
        result = parser.parse_content(code, "test.ets")
        
        assert len(result.classes) == 1
        assert result.classes[0].name == "DataModel"

    def test_parse_interface(self):
        parser = LocalArkTSParser()
        
        code = """
interface UserInfo {
  name: string
  age: number
}

export interface Config {
  theme: string
}
"""
        result = parser.parse_content(code, "test.ets")
        
        assert len(result.interfaces) == 2
        assert result.interfaces[0].name == "UserInfo"
        assert result.interfaces[1].name == "Config"

    def test_parse_imports(self):
        parser = LocalArkTSParser()
        
        code = """
import { User } from './user'
import { Api } from './api'
import * as Utils from './utils'
import Helper from './helper'
"""
        result = parser.parse_content(code, "test.ets")
        
        assert len(result.imports) == 4
        assert result.imports[0].import_path == "./user"
        assert result.imports[1].import_path == "./api"
        assert result.imports[2].import_path == "./utils"
        assert result.imports[2].is_wildcard == True

    def test_no_duplicate_classes(self):
        parser = LocalArkTSParser()
        
        code = """
@Component
struct Index {
  build() {}
}

struct Index {
  value: number
}
"""
        result = parser.parse_content(code, "test.ets")
        
        class_names = [c.name for c in result.classes]
        assert class_names.count("Index") == 1

    def test_empty_code(self):
        parser = LocalArkTSParser()
        result = parser.parse_content("", "empty.ets")
        
        assert len(result.functions) == 0
        assert len(result.classes) == 0
        assert len(result.interfaces) == 0


class TestArkTSParserMock:
    def test_prompt_contains_requirements(self):
        parser = ArkTSParser(api_key="test")
        
        assert "函数定义" in parser._prompt_template
        assert "类定义" in parser._prompt_template
        assert "接口定义" in parser._prompt_template
        assert "import语句" in parser._prompt_template
        assert "函数调用关系" in parser._prompt_template

    def test_parser_config(self):
        parser = ArkTSParser(
            api_key="test-key",
            model="custom/model",
            base_url="https://custom.api.com"
        )
        
        assert parser.api_key == "test-key"
        assert parser.model == "custom/model"
        assert parser.base_url == "https://custom.api.com"

    def test_parse_content_uses_replace_not_format(self):
        parser = ArkTSParser(api_key="test")
        
        test_code = '{"test": "value with {braces}"}'
        prompt = parser._prompt_template.replace("{code}", test_code)
        
        assert "{code}" not in prompt
        assert test_code in prompt

    @pytest.mark.asyncio
    async def test_parse_content_success(self):
        import json
        parser = ArkTSParser(api_key="test-key")
        
        mock_response = {
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "functions": [{"name": "testFunc", "return_type": "void"}],
                        "classes": [],
                        "interfaces": [],
                        "properties": [],
                        "imports": [],
                        "calls": []
                    })
                }
            }]
        }
        
        mock_session = AsyncMock()
        mock_response_obj = AsyncMock()
        mock_response_obj.status = 200
        mock_response_obj.json = AsyncMock(return_value=mock_response)
        mock_response_obj.__aenter__ = AsyncMock(return_value=mock_response_obj)
        mock_response_obj.__aexit__ = AsyncMock(return_value=None)
        
        mock_session.post = MagicMock(return_value=mock_response_obj)
        mock_session.closed = False
        mock_session.close = AsyncMock()
        
        parser._session = mock_session
        
        result = await parser.parse_content("struct Test {}", "test.ets")
        
        assert isinstance(result, ParsedFile)
        assert len(result.functions) == 1
        assert result.functions[0].name == "testFunc"

    @pytest.mark.asyncio
    async def test_parse_content_handles_json_error(self):
        parser = ArkTSParser(api_key="test-key")
        
        mock_response = {
            "choices": [{
                "message": {
                    "content": "这不是有效的JSON"
                }
            }]
        }
        
        mock_session = AsyncMock()
        mock_response_obj = AsyncMock()
        mock_response_obj.status = 200
        mock_response_obj.json = AsyncMock(return_value=mock_response)
        mock_response_obj.__aenter__ = AsyncMock(return_value=mock_response_obj)
        mock_response_obj.__aexit__ = AsyncMock(return_value=None)
        
        mock_session.post = MagicMock(return_value=mock_response_obj)
        mock_session.closed = False
        mock_session.close = AsyncMock()
        
        parser._session = mock_session
        
        result = await parser.parse_content("code", "test.ets")
        
        assert isinstance(result, ParsedFile)

    @pytest.mark.asyncio
    async def test_parse_content_handles_api_error(self):
        parser = ArkTSParser(api_key="test-key")
        
        mock_session = AsyncMock()
        mock_response_obj = AsyncMock()
        mock_response_obj.status = 500
        mock_response_obj.text = AsyncMock(return_value="Internal Server Error")
        mock_response_obj.__aenter__ = AsyncMock(return_value=mock_response_obj)
        mock_response_obj.__aexit__ = AsyncMock(return_value=None)
        
        mock_session.post = MagicMock(return_value=mock_response_obj)
        mock_session.closed = False
        mock_session.close = AsyncMock()
        
        parser._session = mock_session
        
        result = await parser.parse_content("code", "test.ets")
        
        assert isinstance(result, ParsedFile)

    def test_parse_file_reads_file_content(self):
        parser = ArkTSParser(api_key="test-key")
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ets', delete=False) as f:
            f.write("struct TestComponent {}")
            temp_path = f.name
        
        try:
            with patch.object(parser, 'parse_content', new_callable=AsyncMock) as mock_parse:
                mock_parse.return_value = ParsedFile()
                result = parser.parse_file_sync(temp_path)
                
                mock_parse.assert_called_once()
                args = mock_parse.call_args[0]
                assert "struct TestComponent {}" in args[0]
        finally:
            Path(temp_path).unlink()

    @pytest.mark.asyncio
    async def test_close_session(self):
        parser = ArkTSParser(api_key="test-key")
        
        mock_session = AsyncMock()
        mock_session.closed = False
        mock_session.close = AsyncMock()
        
        parser._session = mock_session
        
        await parser.close()
        
        mock_session.close.assert_called_once()


class TestParsedFileModel:
    def test_from_dict_parses_all_fields(self):
        data = {
            "functions": [
                {"name": "func1", "return_type": "void", "params": [], "modifiers": ["public"]}
            ],
            "classes": [
                {"name": "MyClass", "extends": "Base", "modifiers": ["export"]}
            ],
            "interfaces": [
                {"name": "MyInterface", "modifiers": []}
            ],
            "properties": [
                {"name": "prop1", "type": "string"}
            ],
            "imports": [
                {"import_path": "./utils", "import_type": "import", "is_wildcard": False}
            ],
            "calls": [
                {"callee_name": "helper", "line_number": 10}
            ]
        }
        
        parsed = ParsedFile.from_dict(data)
        
        assert len(parsed.functions) == 1
        assert len(parsed.classes) == 1
        assert len(parsed.interfaces) == 1
        assert len(parsed.properties) == 1
        assert len(parsed.imports) == 1
        assert len(parsed.calls) == 1
        
        assert parsed.functions[0].name == "func1"
        assert parsed.classes[0].name == "MyClass"
        assert parsed.interfaces[0].name == "MyInterface"
        assert parsed.properties[0].name == "prop1"
        assert parsed.imports[0].import_path == "./utils"
        assert parsed.calls[0].callee_name == "helper"

    def test_from_dict_handles_empty(self):
        parsed = ParsedFile.from_dict({})
        
        assert len(parsed.functions) == 0
        assert len(parsed.classes) == 0
        assert len(parsed.interfaces) == 0
        assert len(parsed.properties) == 0
        assert len(parsed.imports) == 0
        assert len(parsed.calls) == 0

    def test_to_dict(self):
        parsed = ParsedFile(
            functions=[],
            classes=[],
            interfaces=[],
            properties=[],
            imports=[],
            calls=[]
        )
        
        result = parsed.to_dict()
        
        assert "functions" in result
        assert "classes" in result
        assert "interfaces" in result
        assert "properties" in result
        assert "imports" in result
        assert "calls" in result

import re
import json
import asyncio
import aiohttp
from pathlib import Path
from typing import Optional
import structlog

from .models import ParsedFile, FunctionInfo, ClassInfo, InterfaceInfo, PropertyInfo, ImportInfo, CallInfo

logger = structlog.get_logger()


class LocalArkTSParser:
    def __init__(self):
        self.compiled_patterns = {
            'function': re.compile(
                r'(?:^|\n)(?:export\s+)?function\s*(\*)?\s*([^\s(]+)\s*\(([^)]*)\)\s*(?::\s*([\w<>, ]+))?\s*\{',
                re.MULTILINE | re.UNICODE
            ),
            'class': re.compile(
                r'@?(\w+)?\s*(?:struct|class)\s+(\w+)\s*(?:extends\s+(\w+))?\s*(?:implements\s+([^{]+))?\s*\{',
                re.MULTILINE
            ),
            'interface': re.compile(
                r'(?:export\s+)?interface\s+(\w+)\s*(?:extends\s+([^{]+))?\s*\{',
                re.MULTILINE
            ),
            'import': re.compile(
                r'import\s+(?:\{\s*([^}]+)\s*\}|(\w+)|(\*\s+as\s+\w+))\s+from\s+[\'"]([^\'"]+)[\'"]',
                re.MULTILINE
            ),
            'decorator': re.compile(r'@(\w+)', re.MULTILINE),
            'async_function': re.compile(
                r'(?:^|\n)(?:export\s+)?async\s+function\s*(\*)?\s*([^\s(]+)\s*\(([^)]*)\)\s*(?::\s*([\w<>, ]+))?\s*\{',
                re.MULTILINE | re.UNICODE
            ),
            'class_method': re.compile(
                r'(?:^|\n)\s*(?:(public|private|protected)\s+)+([^\s(]+)\s*\(([^)]*)\)\s*(?::\s*([\w<>, |]+))?\s*\{',
                re.MULTILINE | re.UNICODE
            ),
            'class_method_async': re.compile(
                r'(?:^|\n)\s*(?:(public|private|protected)\s+)+async\s+function\s*(\*)?\s*([^\s(]+)\s*\(([^)]*)\)\s*(?::\s*([\w<>, |]+))?\s*\{',
                re.MULTILINE | re.UNICODE
            )
        }
    
    def parse_file(self, file_path: str) -> ParsedFile:
        try:
            file_content = Path(file_path).read_text(encoding='utf-8')
        except UnicodeDecodeError:
            logger.warning("file_encoding_issue", file_path=file_path, encoding="utf-8")
            try:
                file_content = Path(file_path).read_text(encoding='latin-1')
            except Exception:
                logger.error("file_read_failed", file_path=file_path)
                return ParsedFile()
        return self.parse_content(file_content, file_path)
    
    async def parse_file_async(self, file_path: str) -> ParsedFile:
        return self.parse_file(file_path)
    
    def parse_content(self, code: str, source: str = "unknown") -> ParsedFile:
        result = ParsedFile()
        
        lines = code.split('\n')
        
        for match in self.compiled_patterns['function'].finditer(code):
            generator_marker = match.group(1)
            func_name = match.group(2)
            params_str = match.group(3)
            return_type = match.group(4)
            start_line = code[:match.start()].count('\n') + 1
            
            params = []
            if params_str.strip():
                for param in params_str.split(','):
                    param = param.strip()
                    if ':' in param:
                        p_name, p_type = param.split(':', 1)
                        params.append({
                            'name': p_name.strip(),
                            'type': p_type.strip()
                        })
                    elif param:
                        params.append({
                            'name': param.strip(),
                            'type': 'any'
                        })
            
            modifiers = []
            if generator_marker:
                modifiers.append('generator')
            
            result.functions.append(FunctionInfo(
                name=func_name,
                return_type=return_type.strip() if return_type else None,
                params=params,
                modifiers=modifiers,
                start_line=start_line
            ))
        
        for match in self.compiled_patterns['async_function'].finditer(code):
            generator_marker = match.group(1)
            func_name = match.group(2)
            params_str = match.group(3)
            return_type = match.group(4)
            start_line = code[:match.start()].count('\n') + 1
            
            params = []
            if params_str.strip():
                for param in params_str.split(','):
                    param = param.strip()
                    if ':' in param:
                        p_name, p_type = param.split(':', 1)
                        params.append({
                            'name': p_name.strip(),
                            'type': p_type.strip()
                        })
                    elif param:
                        params.append({
                            'name': param.strip(),
                            'type': 'any'
                        })
            
            modifiers = ['async']
            if generator_marker:
                modifiers.append('generator')
            
            result.functions.append(FunctionInfo(
                name=func_name,
                return_type=return_type.strip() if return_type else None,
                params=params,
                modifiers=modifiers,
                start_line=start_line
            ))
        
        for match in self.compiled_patterns['class_method'].finditer(code):
            modifier = match.group(1)
            func_name = match.group(2)
            params_str = match.group(3)
            return_type = match.group(4)
            start_line = code[:match.start()].count('\n') + 1
            
            params = []
            if params_str.strip():
                for param in params_str.split(','):
                    param = param.strip()
                    if ':' in param:
                        p_name, p_type = param.split(':', 1)
                        params.append({
                            'name': p_name.strip(),
                            'type': p_type.strip()
                        })
                    elif param:
                        params.append({
                            'name': param.strip(),
                            'type': 'any'
                        })
            
            modifiers = [modifier]
            
            result.functions.append(FunctionInfo(
                name=func_name,
                return_type=return_type.strip() if return_type else None,
                params=params,
                modifiers=modifiers,
                start_line=start_line
            ))
        
        for match in self.compiled_patterns['class_method_async'].finditer(code):
            modifier = match.group(1)
            generator_marker = match.group(2)
            func_name = match.group(3)
            params_str = match.group(4)
            return_type = match.group(5)
            start_line = code[:match.start()].count('\n') + 1
            
            params = []
            if params_str.strip():
                for param in params_str.split(','):
                    param = param.strip()
                    if ':' in param:
                        p_name, p_type = param.split(':', 1)
                        params.append({
                            'name': p_name.strip(),
                            'type': p_type.strip()
                        })
                    elif param:
                        params.append({
                            'name': param.strip(),
                            'type': 'any'
                        })
            
            modifiers = [modifier, 'async']
            if generator_marker:
                modifiers.append('generator')
            
            result.functions.append(FunctionInfo(
                name=func_name,
                return_type=return_type.strip() if return_type else None,
                params=params,
                modifiers=modifiers,
                start_line=start_line
            ))
        
        seen_classes = set()
        for match in self.compiled_patterns['class'].finditer(code):
            decorator = match.group(1)
            class_name = match.group(2)
            extends = match.group(3)
            implements = match.group(4)
            start_line = code[:match.start()].count('\n') + 1
            
            modifiers = []
            if decorator:
                modifiers.append(decorator)
            
            if class_name not in seen_classes:
                seen_classes.add(class_name)
                result.classes.append(ClassInfo(
                    name=class_name,
                    extends=extends,
                    implements=implements,
                    modifiers=modifiers,
                    start_line=start_line
                ))
        
        for match in self.compiled_patterns['interface'].finditer(code):
            interface_name = match.group(1)
            extends = match.group(2)
            start_line = code[:match.start()].count('\n') + 1
            
            result.interfaces.append(InterfaceInfo(
                name=interface_name,
                extends=extends,
                modifiers=[],
                start_line=start_line
            ))
        
        for match in self.compiled_patterns['import'].finditer(code):
            named_imports = match.group(1)
            default_import = match.group(2)
            namespace_import = match.group(3)
            import_path = match.group(4)
            
            is_wildcard = namespace_import is not None
            
            result.imports.append(ImportInfo(
                import_path=import_path,
                import_type='import',
                is_wildcard=is_wildcard
            ))
        
        logger.info(
            "local_parse_completed",
            source=source,
            functions=len(result.functions),
            classes=len(result.classes),
            interfaces=len(result.interfaces),
            imports=len(result.imports)
        )
        
        return result


class ArkTSParser:
    def __init__(
        self,
        api_key: str,
        model: str = "qwen/qwen2.5-coder-7b-instruct",
        base_url: str = "https://api.siliconflow.cn/v1",
        use_local_fallback: bool = True
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self._session: Optional[aiohttp.ClientSession] = None
        self.use_local_fallback = use_local_fallback
        self._local_parser = LocalArkTSParser()
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def parse_file(self, file_path: str) -> ParsedFile:
        file_content = Path(file_path).read_text(encoding='utf-8')
        return await self.parse_content(file_content, file_path)
    
    async def parse_content(self, code: str, source: str = "unknown") -> ParsedFile:
        prompt = self._prompt_template.replace("{code}", code)
        
        max_retries = 1
        last_error = None
        
        for attempt in range(max_retries):
            try:
                session = await self._get_session()
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.1,
                        "max_tokens": 4096
                    },
                    timeout=aiohttp.ClientTimeout(total=20)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.debug(
                            "api_error",
                            status=response.status,
                            error=error_text,
                            attempt=attempt + 1
                        )
                        last_error = f"API returned {response.status}: {error_text}"
                        continue
                    
                    result = await response.json()
                    content = result["choices"][0]["message"]["content"]
                    
                    content = content.strip()
                    if content.startswith("```json"):
                        content = content[7:]
                    if content.startswith("```"):
                        content = content[3:]
                    if content.endswith("```"):
                        content = content[:-3]
                    content = content.strip()
                    
                    parsed_data = json.loads(content)
                    parsed = ParsedFile.from_dict(parsed_data)
                    
                    logger.info(
                        "file_parsed",
                        source=source,
                        functions=len(parsed.functions),
                        classes=len(parsed.classes),
                        interfaces=len(parsed.interfaces)
                    )
                    
                    return parsed
            
            except asyncio.TimeoutError:
                logger.debug("api_timeout", attempt=attempt + 1)
                last_error = "API请求超时"
            
            except json.JSONDecodeError as e:
                logger.debug("json_parse_error", error=str(e), attempt=attempt + 1)
                last_error = f"JSON解析失败: {e}"
            
            except Exception as e:
                logger.debug("parse_error", error=str(e), attempt=attempt + 1)
                last_error = str(e)
        
        if self.use_local_fallback:
            logger.debug("using_local_fallback", source=source)
            return self._local_parser.parse_content(code, source)
        
        logger.error("parse_failed_after_retries", source=source, error=last_error)
        return ParsedFile()
    
    def parse_file_sync(self, file_path: str) -> ParsedFile:
        return asyncio.run(self.parse_file(file_path))
    
    def parse_content_sync(self, code: str, source: str = "unknown") -> ParsedFile:
        return asyncio.run(self.parse_content(code, source))
    
    _prompt_template = '''你是一个ArkTS代码分析器。请分析以下代码文件，提取代码结构信息。

要求：
1. 识别所有函数定义（包括名称、参数、返回值、修饰符、行号）
2. 识别所有类定义（包括名称、继承、实现、修饰符）
3. 识别所有接口定义
4. 识别所有成员变量（包括所属类）
5. 识别所有import语句
6. 识别所有函数调用关系（被调用的函数名和行号）

输出格式（严格JSON，不要包含任何其他内容）：
{
  "functions": [
    {
      "name": "函数名",
      "return_type": "返回类型",
      "params": [{"name": "参数名", "type": "类型"}],
      "modifiers": ["public", "static", "async"],
      "start_line": 10,
      "end_line": 25,
      "doc_comment": "文档注释"
    }
  ],
  "classes": [
    {
      "name": "类名",
      "extends": "父类名",
      "implements": "实现的接口",
      "modifiers": ["public", "export"],
      "start_line": 1,
      "end_line": 100,
      "doc_comment": "类文档注释"
    }
  ],
  "interfaces": [
    {
      "name": "接口名",
      "extends": "继承的接口",
      "modifiers": ["export"],
      "start_line": 5,
      "end_line": 20,
      "doc_comment": "接口文档注释"
    }
  ],
  "properties": [
    {
      "name": "属性名",
      "type": "类型",
      "modifiers": ["private", "readonly"],
      "default_value": "默认值",
      "class_id": null
    }
  ],
  "imports": [
    {
      "import_path": "./utils",
      "import_type": "import",
      "is_wildcard": false
    }
  ],
  "calls": [
    {
      "callee_name": "被调用的函数名",
      "line_number": 15,
      "callee_file_path": null
    }
  ]
}

代码内容：
{code}'''

from dataclasses import dataclass, field, asdict
from typing import Optional
import json


@dataclass
class FunctionInfo:
    name: str
    return_type: Optional[str] = None
    params: list[dict] = field(default_factory=list)
    modifiers: list[str] = field(default_factory=list)
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    doc_comment: Optional[str] = None

    def to_db_tuple(self, file_id: int) -> tuple:
        return (
            file_id,
            self.name,
            self.return_type,
            json.dumps(self.params, ensure_ascii=False),
            json.dumps(self.modifiers, ensure_ascii=False),
            self.start_line,
            self.end_line,
            self.doc_comment
        )

    @classmethod
    def from_dict(cls, data: dict) -> "FunctionInfo":
        return cls(
            name=data.get("name", ""),
            return_type=data.get("return_type"),
            params=data.get("params", []),
            modifiers=data.get("modifiers", []),
            start_line=data.get("start_line"),
            end_line=data.get("end_line"),
            doc_comment=data.get("doc_comment")
        )


@dataclass
class ClassInfo:
    name: str
    extends: Optional[str] = None
    implements: Optional[str] = None
    modifiers: list[str] = field(default_factory=list)
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    doc_comment: Optional[str] = None

    def to_db_tuple(self, file_id: int) -> tuple:
        return (
            file_id,
            self.name,
            self.extends,
            self.implements,
            json.dumps(self.modifiers, ensure_ascii=False),
            self.start_line,
            self.end_line,
            self.doc_comment
        )

    @classmethod
    def from_dict(cls, data: dict) -> "ClassInfo":
        return cls(
            name=data.get("name", ""),
            extends=data.get("extends"),
            implements=data.get("implements"),
            modifiers=data.get("modifiers", []),
            start_line=data.get("start_line"),
            end_line=data.get("end_line"),
            doc_comment=data.get("doc_comment")
        )


@dataclass
class InterfaceInfo:
    name: str
    extends: Optional[str] = None
    modifiers: list[str] = field(default_factory=list)
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    doc_comment: Optional[str] = None

    def to_db_tuple(self, file_id: int) -> tuple:
        return (
            file_id,
            self.name,
            self.extends,
            json.dumps(self.modifiers, ensure_ascii=False),
            self.start_line,
            self.end_line,
            self.doc_comment
        )

    @classmethod
    def from_dict(cls, data: dict) -> "InterfaceInfo":
        return cls(
            name=data.get("name", ""),
            extends=data.get("extends"),
            modifiers=data.get("modifiers", []),
            start_line=data.get("start_line"),
            end_line=data.get("end_line"),
            doc_comment=data.get("doc_comment")
        )


@dataclass
class PropertyInfo:
    name: str
    type: Optional[str] = None
    modifiers: list[str] = field(default_factory=list)
    default_value: Optional[str] = None
    class_id: Optional[int] = None

    def to_db_tuple(self, file_id: int) -> tuple:
        return (
            file_id,
            self.class_id,
            self.name,
            self.type,
            json.dumps(self.modifiers, ensure_ascii=False),
            self.default_value
        )

    @classmethod
    def from_dict(cls, data: dict) -> "PropertyInfo":
        return cls(
            name=data.get("name", ""),
            type=data.get("type"),
            modifiers=data.get("modifiers", []),
            default_value=data.get("default_value"),
            class_id=data.get("class_id")
        )


@dataclass
class ImportInfo:
    import_path: str
    import_type: str = "import"
    is_wildcard: bool = False

    def to_db_tuple(self, file_id: int) -> tuple:
        return (
            file_id,
            self.import_path,
            self.import_type,
            1 if self.is_wildcard else 0
        )

    @classmethod
    def from_dict(cls, data: dict) -> "ImportInfo":
        return cls(
            import_path=data.get("import_path", ""),
            import_type=data.get("import_type", "import"),
            is_wildcard=data.get("is_wildcard", False)
        )


@dataclass
class CallInfo:
    callee_name: str
    line_number: int
    callee_file_path: Optional[str] = None
    function_id: Optional[int] = None

    def to_db_tuple(self, file_id: int) -> tuple:
        return (
            file_id,
            self.function_id,
            self.callee_name,
            self.callee_file_path,
            self.line_number
        )

    @classmethod
    def from_dict(cls, data: dict) -> "CallInfo":
        return cls(
            callee_name=data.get("callee_name", ""),
            line_number=data.get("line_number", 0),
            callee_file_path=data.get("callee_file_path"),
            function_id=data.get("function_id")
        )


@dataclass
class FileInfo:
    path: str
    hash: str
    modified: int
    last_parsed: int = 0

    def to_db_tuple(self) -> tuple:
        return (self.path, self.hash, self.modified, self.last_parsed)

    @classmethod
    def from_db_row(cls, row: tuple) -> "FileInfo":
        return cls(
            path=row[1],
            hash=row[2],
            modified=row[3],
            last_parsed=row[4]
        )


@dataclass
class ParsedFile:
    functions: list[FunctionInfo] = field(default_factory=list)
    classes: list[ClassInfo] = field(default_factory=list)
    interfaces: list[InterfaceInfo] = field(default_factory=list)
    properties: list[PropertyInfo] = field(default_factory=list)
    imports: list[ImportInfo] = field(default_factory=list)
    calls: list[CallInfo] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "ParsedFile":
        return cls(
            functions=[FunctionInfo.from_dict(f) for f in data.get("functions", [])],
            classes=[ClassInfo.from_dict(c) for c in data.get("classes", [])],
            interfaces=[InterfaceInfo.from_dict(i) for i in data.get("interfaces", [])],
            properties=[PropertyInfo.from_dict(p) for p in data.get("properties", [])],
            imports=[ImportInfo.from_dict(imp) for imp in data.get("imports", [])],
            calls=[CallInfo.from_dict(c) for c in data.get("calls", [])]
        )

    def to_dict(self) -> dict:
        return {
            "functions": [asdict(f) for f in self.functions],
            "classes": [asdict(c) for c in self.classes],
            "interfaces": [asdict(i) for i in self.interfaces],
            "properties": [asdict(p) for p in self.properties],
            "imports": [asdict(imp) for imp in self.imports],
            "calls": [asdict(c) for c in self.calls]
        }

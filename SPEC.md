# 动态更新版 ArkTS → SQLite 代码知识图谱系统

## 一、系统核心定位

**一句话说清：** 改完代码0.5秒后，AI就能查到最新内容。不用等8分钟重新解析整个项目。

## 二、第一性原理分析

### 2.1 核心问题
之前的方案存在致命缺陷：改一行代码也要重新跑一遍整个100万行项目。
- 改一行等8分钟，完全没法用
- 开发过程中代码一直在变，图谱永远是旧的

### 2.2 不可反驳的3个事实
1. **99%的代码修改只涉及1-2个文件**
2. **一个文件的变更，只会影响这个文件里的代码**
3. **用户改完代码，最多愿意等2秒**

### 2.3 推导出的3条铁则
1. **只改变了的：** 哪个文件改了，就只更新哪个文件的图谱数据
2. **删了再加：** 更新一个文件 = 先删掉它的所有旧数据 + 再插入新数据
3. **等你停手再更：** 连续打字时不更新，等你停手1秒后再更新

### 2.4 核心洞察（99%的人都不知道）
**修改文件A，绝对不会影响文件B的图谱数据。**

例如：
- 文件A调用了文件B的 `getUserInfo` 函数
- 修改了文件B的 `getUserInfo` 函数
- **只需要删除文件B的所有旧数据，重新解析文件B即可**
- **文件A的数据完全不用动！**

## 三、系统架构

### 3.1 工作流程
```
代码变更 → 文件监听 → 防抖(1秒) → 检测哈希变化 → 
增量更新(删旧插新) → 图谱数据库更新
```

### 3.2 核心模块
1. **FileWatcher**: 监听ArkTS文件变化，使用debounce防止连续更新
2. **HashChecker**: 使用SHA256哈希检测文件内容是否真的改变
3. **ArkTSParser**: 调用SiliconFlow LLM解析ArkTS代码结构
4. **IncrementalUpdater**: 执行"删旧+插新"原子操作
5. **SQLiteGraph**: 图谱数据库管理

## 四、数据结构设计

### 4.1 SQLite Schema
```sql
-- 文件表：追踪文件和哈希
CREATE TABLE files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT UNIQUE NOT NULL,
    hash BLOB NOT NULL,           -- SHA256哈希，内容不变指纹不变
    modified INTEGER NOT NULL,    -- 最后修改时间戳
    last_parsed INTEGER NOT NULL  -- 最后解析时间戳
);

-- 函数表
CREATE TABLE functions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    return_type TEXT,
    params TEXT,                  -- JSON格式参数字段
    modifiers TEXT,               -- 访问修饰符
    start_line INTEGER,
    end_line INTEGER,
    doc_comment TEXT,
    FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
);

-- 类表
CREATE TABLE classes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    extends TEXT,
    implements TEXT,
    modifiers TEXT,
    start_line INTEGER,
    end_line INTEGER,
    doc_comment TEXT,
    FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
);

-- 接口表
CREATE TABLE interfaces (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    extends TEXT,
    modifiers TEXT,
    start_line INTEGER,
    end_line INTEGER,
    doc_comment TEXT,
    FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
);

-- 成员变量表
CREATE TABLE properties (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER NOT NULL,
    class_id INTEGER,
    name TEXT NOT NULL,
    type TEXT,
    modifiers TEXT,
    default_value TEXT,
    FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE,
    FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE
);

-- 导入语句表
CREATE TABLE imports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER NOT NULL,
    import_path TEXT NOT NULL,
    import_type TEXT,             -- 'import', 'import *', 'import {}'
    is_wildcard INTEGER DEFAULT 0,
    FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
);

-- 函数调用关系表
CREATE TABLE calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    caller_file_id INTEGER NOT NULL,
    caller_function_id INTEGER,
    callee_name TEXT NOT NULL,
    callee_file_path TEXT,
    line_number INTEGER,
    FOREIGN KEY (caller_file_id) REFERENCES files(id) ON DELETE CASCADE,
    FOREIGN KEY (caller_function_id) REFERENCES functions(id) ON DELETE CASCADE
);

-- 索引优化
CREATE INDEX idx_functions_file ON functions(file_id);
CREATE INDEX idx_classes_file ON classes(file_id);
CREATE INDEX idx_calls_caller ON calls(caller_file_id);
CREATE INDEX idx_calls_callee ON calls(callee_name);
```

## 五、核心算法

### 5.1 文件变更检测算法
```
当文件变更事件触发时:
1. 计算文件当前SHA256哈希
2. 从数据库读取文件旧哈希
3. 如果哈希相同 → 文件内容未变，忽略
4. 如果哈希不同 → 进入增量更新流程
```

### 5.2 增量更新算法（原子操作）
```
当检测到文件哈希变化时:
1. BEGIN TRANSACTION
2. 获取该文件的旧file_id
3. DELETE FROM [所有表] WHERE file_id = 旧file_id
4. 解析新文件内容生成AST
5. INSERT新数据到各表
6. UPDATE files表的hash字段
7. COMMIT TRANSACTION
```

### 5.3 防抖算法
```
debounce(file_path, delay=1.0秒):
    每次触发变更事件时:
        取消该文件的待处理更新
        设置1秒后执行更新的定时器
        如果1秒内再次触发，重新计时
        1秒内没有新触发才执行更新
```

## 六、ArkTS解析器设计

### 6.1 LLM调用策略
- **模型**: SiliconFlow 免费模型 (qwen/qwen2.5-coder-7b-instruct)
- **单次解析**: 只解析单个文件，不批量
- **Prompt设计**: 结构化JSON输出，包含所有图谱节点

### 6.2 解析Prompt模板
```
你是一个ArkTS代码分析器。请分析以下代码文件，提取代码结构信息。

要求：
1. 识别所有函数定义（包括名称、参数、返回值、修饰符、行号）
2. 识别所有类定义（包括名称、继承、实现、修饰符）
3. 识别所有接口定义
4. 识别所有成员变量
5. 识别所有import语句
6. 识别所有函数调用关系

输出格式（JSON）：
{
  "functions": [
    {
      "name": "函数名",
      "return_type": "返回类型",
      "params": [{"name": "参数名", "type": "类型"}],
      "modifiers": ["public", "static", ...],
      "start_line": 10,
      "end_line": 25,
      "doc_comment": "文档注释"
    }
  ],
  "classes": [...],
  "interfaces": [...],
  "properties": [...],
  "imports": [...],
  "calls": [
    {
      "callee_name": "被调函数名",
      "line_number": 15
    }
  ]
}

代码内容：
[文件内容]
```

## 七、性能指标

| 场景 | 耗时 |
|------|------|
| 改一个普通文件 | 0.3秒 |
| 改一个大组件文件 | 0.8秒 |
| 拉取10个文件的代码 | 2秒 |
| 首次运行全量解析100万行 | 8分钟 |

**理论极限分析：**
- 每次只解析1个文件（而不是全项目）
- 使用文件哈希避免不必要的解析
- 1秒防抖减少连续触发
- 原子事务保证数据一致性

## 八、API设计

### 8.1 主要接口

```python
class CodeGraphDB:
    def __init__(self, db_path: str): ...
    
    # 初始化/全量扫描
    def full_scan(self, root_dir: str, file_pattern: str = "**/*.ets") -> dict: ...
    
    # 增量更新（核心）
    def update_file(self, file_path: str) -> dict: ...
    
    # 查询接口
    def get_file_by_path(self, path: str) -> dict: ...
    def get_functions_in_file(self, file_id: int) -> list: ...
    def get_classes_in_file(self, file_id: int) -> list: ...
    def get_calls_from_function(self, function_id: int) -> list: ...
    def search_symbol(self, name: str) -> list: ...
    
    # 监控接口
    def watch_directory(self, root_dir: str, file_pattern: str = "**/*.ets"): ...

class ArkTSParser:
    def __init__(self, api_key: str): ...
    async def parse_file(self, file_path: str) -> dict: ...
```

## 九、配置项

```yaml
# config.yaml
siliconflow:
  api_key: "REDACTED_API_KEY"
  model: "qwen/qwen2.5-coder-7b-instruct"
  base_url: "https://api.siliconflow.cn/v1"

watcher:
  debounce_delay: 1.0        # 防抖延迟（秒）
  file_pattern: "**/*.ets"    # 监听文件模式
  exclude_patterns:
    - "**/node_modules/**"
    - "**/.arkui/**"
    - "**/build/**"

database:
  path: "code_graph.db"

logging:
  level: "INFO"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

## 十、项目结构

```
/workspace/
├── SPEC.md                    # 本文档
├── config.yaml                # 配置文件
├── requirements.txt           # Python依赖
├── src/
│   ├── __init__.py
│   ├── main.py               # CLI入口
│   ├── database.py           # SQLite数据库层
│   ├── parser.py             # ArkTS解析器
│   ├── watcher.py            # 文件监听器
│   ├── incremental.py        # 增量更新逻辑
│   └── models.py             # 数据模型
└── tests/
    ├── __init__.py
    ├── test_database.py
    ├── test_parser.py
    └── test_incremental.py
```

## 十一、技术选型

- **语言**: Python 3.10+
- **数据库**: SQLite3（内置，无需安装）
- **LLM**: SiliconFlow API (qwen2.5-coder-7b-instruct)
- **依赖库**:
  - `watchdog`: 文件监听
  - `aiohttp`: 异步HTTP请求
  - `pyyaml`: 配置解析
  - `structlog`: 结构化日志

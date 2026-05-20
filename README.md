# 动态更新版 ArkTS → SQLite 代码知识图谱

一个现代化的、功能完整的代码知识图谱系统，支持实时监听ArkTS项目并自动构建可视化的知识图谱。

## 🎯 功能特性

### 核心功能
- **增量更新**：只解析有变化的文件，基于哈希值检测变化
- **本地解析**：高性能正则表达式解析器，无需API调用
- **LLM增强**：可选的LLM辅助解析，提供更精准的代码分析
- **实时监听**：基于watchdog的文件变化自动监听
- **SQLite存储**：高性能轻量级关系型数据库
- **可视化界面**：现代化React+TypeScript前端

### 可视化功能
- 📊 仪表板：统计信息概览
- 📁 文件浏览器：代码库树状结构
- 🔍 搜索功能：快速查找函数、类、接口
- 🕸️ 知识图谱：力导向图可视化
- 📝 实时日志：WebSocket推送更新信息

## 🚀 快速开始

### 1. 安装依赖

```bash
# 后端依赖
pip install -r requirements.txt
pip install fastapi uvicorn psutil

# 前端依赖
cd frontend
npm install
```

### 2. 配置（可选）

编辑 `config.yaml` 配置LLM解析器（可选，系统默认使用本地解析器）：

```yaml
api:
  api_key: "your-siliconflow-api-key"  # 从 https://cloud.siliconflow.cn 获取
  model: "qwen/qwen2.5-coder-7b-instruct"
  base_url: "https://api.siliconflow.cn/v1"

db:
  path: "knowledge_graph.db"

watcher:
  debounce_seconds: 1.0
```

### 3. 运行项目

#### 启动后端：

```bash
# 方式1：带完整可视化界面
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 方式2：纯命令行工具
python -m src.main --path test-arkts-project --watch
```

#### 开发模式（仅前端）：

```bash
cd frontend
npm run dev
```

打开浏览器访问：http://localhost:8000

### 4. 使用示例

#### 命令行工具：

```bash
# 仅分析项目
python -m src.main --path test-arkts-project

# 监听项目变化
python -m src.main --path test-arkts-project --watch

# 自定义数据库路径
python -m src.main --path test-arkts-project --db my_graph.db
```

#### 运行测试：

```bash
# 单元测试
python -m pytest tests/ -v

# 压力测试
python stress_test.py --path test-arkts-project
```

## 📁 项目结构

```
.
├── backend/                # FastAPI后端
│   ├── main.py            # API服务
│   └── dist/              # 前端构建产物
├── frontend/              # React前端
│   ├── src/
│   │   ├── components/    # UI组件
│   │   ├── pages/         # 页面
│   │   └── store/         # 状态管理
│   └── package.json
├── src/                   # 核心模块
│   ├── models.py          # 数据模型
│   ├── database.py        # 数据库操作
│   ├── parser.py          # 代码解析器
│   ├── incremental.py     # 增量更新
│   └── watcher.py         # 文件监听
├── tests/                 # 测试文件
├── test-arkts-project/    # 示例测试项目
├── config.yaml            # 配置文件
├── requirements.txt       # Python依赖
└── SPEC.md               # 完整技术规范
```

## 🛠️ 技术栈

### 后端
- **Python 3.12+**
- **SQLite3** 数据存储
- **FastAPI** API服务
- **watchdog** 文件监听
- **aiohttp** 异步HTTP客户端
- **structlog** 结构化日志

### 前端
- **React 18**
- **TypeScript**
- **Tailwind CSS**
- **Zustand** 状态管理
- **Vite** 构建工具
- **Lucide** 图标库

## 🔧 核心模块说明

### 1. Parser（解析器）
- `ArkTSParser`: LLM驱动的高级解析器
- `LocalArkTSParser`: 高性能本地解析器（默认）
- 自动降级机制：LLM失败时自动使用本地解析器

### 2. Database（数据库）
- 规范化表结构设计
- 外键级联删除
- 哈希值比较实现增量更新
- 事务安全的操作

### 3. Incremental（增量更新）
- 计算文件哈希值
- 只处理变化的文件
- 原子化替换旧数据

### 4. Watcher（文件监听）
- 1秒防抖优化
- 支持新增、修改、删除事件
- WebSocket实时通知

## 📊 API接口

### REST API
- `GET /api/stats` - 获取统计信息
- `GET /api/files` - 获取文件列表
- `GET /api/files/{id}` - 获取文件详情
- `GET /api/search?q=...` - 搜索功能
- `GET /api/graph` - 获取图谱数据
- `POST /api/watch/start` - 启动监听
- `POST /api/watch/stop` - 停止监听

### WebSocket
- `ws:///ws/logs` - 实时日志推送

## 🎨 界面预览

1. **仪表板页面**：显示文件、函数、类、接口总数
2. **文件浏览器**：树状结构查看代码库
3. **搜索页面**：全局搜索代码元素
4. **知识图谱**：力导向图可视化
5. **日志页面**：实时显示更新信息

## ✅ 测试覆盖

- 完整的单元测试（35+个）
- 压力测试脚本
- 100%测试通过率

## 🔐 许可证

MIT License

---

## 💡 开发建议

1. **首次使用**：从 `test-arkts-project` 开始体验
2. **大型项目**：默认使用本地解析器获得最佳性能
3. **开发调试**：使用 `--watch` 模式获得实时反馈
4. **贡献代码**：确保所有测试通过后再提交PR

## 📞 问题反馈

如遇到问题，请查看：
- SPEC.md - 完整技术规范
- 终端日志 - 使用 `structlog` 输出详细调试信息

# AGENTS.md — edai

一个面向 EDA 工具的 LLM 驱动的 TUI 工具。

## 项目结构

- **源码布局**：源码根目录为 `src/`，包位于 `src/edai/` 下。
- **单一包**：`edai`。导入路径 `edai.*` 映射到 `src/edai/`。

`edai/` 下的模块：

| 模块 | 文件 | 说明 |
|---|---|---|
| 顶层 | `__init__.py` | 包初始化，定义 `__version__ = "0.1.0"` |
| 顶层 | `__main__.py` | CLI 入口点，`main(argv: list[str] \| None = None) -> int` |
| `agent/` | `__init__.py`, `base.py` | `Agent` 类（LLM 聊天封装）、`AgentConfig` 数据类 |
| `backend.py` | — | `Backend` 类——带异步 I/O 的持久子进程包装器 |
| `tool/` | `__init__.py`, `base.py`, `manager.py`, `builtin.py`, `repl.py` | 工具抽象层（详见下方） |
| `error/` | `__init__.py` | 集中式异常层级 |

### tool/ 子包

```
Tool (ABC)                    — base.py
├── BashExec                  — builtin.py   (一次性 bash 命令执行)
└── ReplExec                  — repl.py      (REPL 风格二进制交互)

ToolsMgr                      — manager.py   (工具注册表与调度器)
```

- **`Tool`**：抽象基类——`name`、`description`、`parameters_schema()`、`execute(**kwargs) -> dict[str, Any]`、`to_openai_function()`。
- **`BashExec`**：通过 `subprocess.run` 执行 bash 命令，返回 `{"returncode": ..., "stdout": ..., "stderr": ...}`。
- **`ReplExec`**：包装 `Backend` 与二进制 REPL 交互（如 Python 解释器）。操作：`start`（启动）、`eval`（发送输入并读取输出）、`stop`（停止）。
- **`ToolsMgr`**：管理工具注册、按名称查找并生成 OpenAI 函数调用模式。

### 错误层级 (`edai.error`)

```
EdaiError
├── AgentError
│   ├── ConfigurationError
│   ├── ModelError
│   └── ToolError
│       ├── ToolNotFoundError
│       ├── ToolExecutionError
│       └── ToolInvalidParamError
├── BackendError
│   ├── BackendNotRunningError
│   └── BackendTimeoutError
└── ConfigError
    ├── ConfigNotFoundError
    └── ConfigParseError
```

### 测试文件

| 文件 | 测试内容 |
|---|---|
| `test_agent.py` | `Agent` 类——初始化、聊天、流式传输、重置、错误（19 项测试） |
| `test_backend.py` | `Backend` 类——生命周期、I/O、错误、边界情况（34 项测试） |
| `test_tool.py` | `Tool` ABC、`ToolsMgr`、`BashExec`（31 项测试） |
| `test_repl.py` | `ReplExec`——生命周期、错误、模式（15 项测试） |
| `test_cli.py` | CLI 参数解析（4 项测试） |
| `test_version.py` | 版本号存在且可解析（2 项测试） |
| `conftest.py` | 共享 pytest fixture |

## 环境变量

创建 `.env` 文件（通过 `python-dotenv` 加载）：

```env
LLM_BASE_URL="https://api.deepseek.com"
LLM_MODEL_ID="deepseek-v4-flash"
LLM_API_KEY="sk-..."

# 测试开关——设置为 "true" 即可针对真实 API 运行集成测试。
# 未设置或为 "false" 时，测试套件使用 mock / 跳过真实 API 测试。
EDAI_TEST_REAL_API=true
```

## 依赖

运行时依赖（`requirements.txt` 及 `pyproject.toml`）：
- `openai>=1.0.0` — LLM API 客户端
- `python-dotenv>=1.0.0` — `.env` 文件加载

开发依赖（`requirements-dev.txt` 及 `pyproject.toml [dev]`）：
- `pytest>=8.0`、`pytest-cov>=5.0`
- `ruff>=0.3.0`、`mypy>=1.8.0`
- `pre-commit>=3.6.0`

快速安装：
```bash
pip install -r requirements.txt        # 仅运行时
pip install -r requirements-dev.txt    # 运行时 + 开发工具
```

## 开发者命令

| 命令 | 操作 |
|---|---|
| `make install` | `pip install -e .` |
| `make install-dev` | `pip install -e ".[dev]"` |
| `make test` | `python -m pytest`（默认参数：`-v --tb=short`）|
| `make test-cov` | pytest 加 `--cov=edai --cov-report=term-missing` |
| `make lint` | 先执行 `ruff check src/ tests/`，再执行 `mypy src/ tests/` |
| `make format` | `ruff format src/ tests/` |
| `make clean` | 清理构建产物和缓存 |
| `make dist` | 构建 sdist + wheel |

通过 `PYTEST_ARGS=...` 进行针对性测试：
```
make test PYTEST_ARGS="tests/test_cli.py"
```

控制是否使用真实 API 运行测试：
```
EDAI_TEST_REAL_API=true make test   # 包括真实 API 调用
EDAI_TEST_REAL_API=false make test  # 仅 mock 测试（速度快）
```

## 工具链

- **Python** >= 3.10。
- **Ruff**：行长度 100，lint 规则 `E,F,I,N,W,UP`。
- **Mypy**：严格模式（`strict = true`），`ignore_missing_imports = true`。
- **pytest**：测试文件为 `tests/` 下的 `test_*.py`。
- **构建**：setuptools，`pyproject.toml` 为唯一真相来源。

所有工具配置均位于 `pyproject.toml`。

## 工作流程

1. `make install-dev`——第一步（以可编辑模式安装包及开发依赖）。
2. `make format`——提交前自动格式化。
3. `make lint`——同时运行 ruff 和 mypy，两者必须通过。
4. `make test`——所有测试必须通过。

`make lint` 需单独在 `make test` 之前运行。Lint 是阻塞式检查——目前没有 pre-commit 钩子或 CI。

## 特殊文件

- `.env`——API 凭据及测试开关（不提交至 git）。
- `.opencode/opencode.json`——OpenCode 插件配置（`oh-my-opencode-slim`）。
- `.opencode/.gitignore`——阻止提交 `.opencode` 目录下的 node_modules/ 和包文件。
- 无 `.github/`、无 `.pre-commit-config.yaml`、无 CI。

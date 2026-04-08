# Socialwares 框架重构 — 执行计划

> 基于 framework-refactor.md 设计文档

## Phase 1：App 声明式 API

**目标**：实现 `from socialwares import App`，用户可以在 `socialware.py` 中声明式定义 App。

### 1.1 创建包骨架

```
src/socialwares/
├── __init__.py       ← 导出 App
├── app.py            ← App, Flow 类
└── py.typed          ← PEP 561 类型标记
```

更新 `pyproject.toml`：
```toml
[project]
name = "socialwares"
version = "0.2.0"
dependencies = ["pyyaml>=6.0", "click>=8.0"]

[project.scripts]
socialwares = "socialwares.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

验证：`uv pip install -e .` + `python -c "from socialwares import App"`

### 1.2 实现 App 类

```python
# src/socialwares/app.py

class App:
    def __init__(self, name: str, description: str = ""):
        ...
    def scope(self, content: str | None = None, *, file: str | None = None):
        ...
    def role(self, name: str, content: str | None = None, *, file: str | None = None):
        ...
    def action(self, name: str, *, role: list[str]):
        ...
    def flow(self, name: str, *, resource: str) -> Flow:
        ...
    def commitment(self, name: str, *, from_: tuple, to: tuple, condition: str, on_violation: tuple | None = None):
        ...

class Flow:
    def states(self, *names: str):
        ...
    def transition(self, from_state: str, action: str, to_state: str, *, role: list[str]):
        ...
```

关键行为：
- `scope()` / `role()`: 接受 inline string 或 `file=` 路径，存储到 App 内部
- `action()`: 注册 action → role 映射。action 名 = `agent/flow/` 下目录名（编译时校验）
- `flow()`: 返回 Flow 对象，定义状态机
- `commitment()`: 注册约束

### 1.3 测试

```python
# tests/test_app.py
def test_app_basic():
    app = App("test")
    app.scope("test scope")
    app.role("default", "test role")
    app.action("check_health", role=["default"])
    assert app.name == "test"
    assert "default" in app.roles
    assert "check_health" in app.actions

def test_app_file_loading(tmp_path):
    (tmp_path / "scope.md").write_text("file scope")
    app = App("test")
    app.scope(file=str(tmp_path / "scope.md"))
    assert app._scope_content == "file scope"

def test_flow():
    app = App("test")
    flow = app.flow("lifecycle", resource="task")
    flow.states("draft", "done")
    flow.transition("draft", "complete", "done", role=["default"])
    assert len(app.flows) == 1
```

### 交付标准

- [ ] `from socialwares import App` 可用
- [ ] 所有 API 支持 inline string + file= 双模式
- [ ] 类型标注完整
- [ ] 测试覆盖所有 API

---

## Phase 2：编译器

**目标**：`deploy.sh` (358 行 bash) 重写为 `compiler.py`，输入 App 对象 + agent/ 文件，输出 .runtime/。

### 2.1 搬入 adapters

```bash
agent/adapters/ → src/socialwares/adapters/
```

保持现有接口不变，只移动位置。

### 2.2 实现 compiler.py

编译器按四原语组织，每个原语一个编译步骤：

```python
# src/socialwares/compiler.py

class Compiler:
    def __init__(self, app: App, config: dict):
        self.app = app
        self.config = config  # pyproject.toml [tool.socialwares]

    def compile(self, output_dir: str = ".runtime") -> CompileResult:
        """主编译流程：四原语 → .runtime/"""
        self._validate_flow()        # Flow: 校验每个 action 有对应的 SKILL.md
        self._compile_scope_and_role()  # Scope + Role → 每个 role 的 SOUL.md
        self._inject_flow_to_soul()  # Flow: 状态机定义注入 SOUL.md
        self._link_flow_skills()     # Flow: symlink skill 目录到各 role
        self._generate_flow_yaml()   # Flow: 从 App 对象序列化 → flow.yaml
        self._generate_commitment()  # Commitment: 从 App 对象序列化 → commitment.yaml
        self._generate_hooks()       # 适配器相关 hook 配置
        self._generate_manifest()    # 编译清单
        return CompileResult(...)
```

### 2.3 四原语编译细节

**Scope + Role → SOUL.md**

从 deploy.sh 第 121-127 行迁移。对每个 role：
```
scope.md 内容 + "\n---\n" + {role}.md 内容 → .runtime/agents/{role}/SOUL.md
```

**Flow → SOUL.md 注入（状态机部分）**

从 deploy.sh 第 130-159 行迁移。现在数据来源从 flow.yaml 变为 App 对象：

```python
def _inject_flow_to_soul(self):
    """将 socialware.py 中定义的状态机序列化为文本，追加到 SOUL.md"""
    for flow in self.app.flows:
        text = f"\n---\n\n## Workflows\n### {flow.name} (resource: {flow.resource})\n"
        for t in flow.transitions:
            roles = ", ".join(t.role)
            text += f"  {t.from_state} → {t.action} (by {roles}) → {t.to_state}\n"
        # 追加到该 flow 涉及的 role 的 SOUL.md
        for role_name in self._roles_in_flow(flow):
            soul_path = self.output / "agents" / role_name / "SOUL.md"
            soul_path.write_text(soul_path.read_text() + text)
```

**Flow → skill symlink**

从 deploy.sh 第 162-190 行迁移。根据 App 对象的 action→role 映射（不再读 flow.yaml）：

```python
def _link_flow_skills(self):
    """为每个 role symlink 其 action 对应的 skill 目录"""
    for action in self.app.actions:
        skill_dir = self.agent_dir / "flow" / action.name
        for role_name in action.roles:
            link = self.output / "agents" / role_name / skills_subdir / action.name
            link.symlink_to(skill_dir.resolve())
```

**Flow → flow.yaml（新增，编译产物）**

deploy.sh 中 flow.yaml 是源文件。现在改为从 App 对象生成：

```python
def _generate_flow_yaml(self):
    """将 App 的 action/flow 定义序列化为 flow.yaml"""
    data = {
        "direct_actions": [
            {"action": a.name, "role": a.roles}
            for a in self.app.actions
            if not any(a.name in [t.action for t in f.transitions] for f in self.app.flows)
        ],
        "flows": {
            f.name: {
                "resource": f.resource,
                "transitions": [
                    {"from": t.from_state, "action": t.action, "to": t.to_state, "role": t.role}
                    for t in f.transitions
                ]
            }
            for f in self.app.flows
        }
    }
    yaml.dump(data, (self.output / "flow.yaml").open("w"))
```

**Commitment → commitment.yaml（新增，编译产物）**

```python
def _generate_commitment(self):
    """将 App 的 commitment 定义序列化为 commitment.yaml"""
    data = {
        "commitments": [
            {
                "id": c.name,
                "from": {"role": c.from_[0], "action": c.from_[1]},
                "to": {"role": c.to[0], "action": c.to[1]},
                "condition": c.condition,
                "on_violation": {"role": c.on_violation[0], "action": c.on_violation[1]}
                    if c.on_violation else None,
            }
            for c in self.app.commitments
        ]
    }
    yaml.dump(data, (self.output / "commitment.yaml").open("w"))
```

**Hooks 生成**

从 deploy.sh 第 199-344 行迁移。按适配器（claude/codex/kimi）生成不同的 hook 配置文件：

| 适配器 | Skills 目录 | Hook 配置 | Prompt 文件 |
|--------|------------|-----------|------------|
| claude | `.claude/skills/` | `.claude/settings.local.json` | `SOUL.md` |
| codex | `.agents/skills/` | `.codex/hooks.json` + `config.toml` | `AGENTS.md` |
| kimi | `.agents/skills/` | 无 | `AGENTS.md` |

### 2.4 加载 socialware.py

```python
# src/socialwares/loader.py

def load_app(path: str = "socialware.py") -> App:
    """用 importlib 动态加载 socialware.py 中的 app 对象"""
    import importlib.util
    spec = importlib.util.spec_from_file_location("socialware", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if not hasattr(mod, "app"):
        raise ValueError(f"{path} 中未找到 app 对象")
    return mod.app
```

### 2.5 测试

```python
def test_compile_basic(tmp_path):
    """编译最简 App，验证输出结构"""

def test_compile_validates_missing_skill(tmp_path):
    """注册了 action 但没有 SKILL.md → 报错"""

def test_soul_merges_scope_and_role(tmp_path):
    """SOUL.md = scope + --- + role"""

def test_soul_injects_workflow(tmp_path):
    """SOUL.md 末尾包含状态机文本"""

def test_generates_flow_yaml(tmp_path):
    """从 App 对象正确生成 flow.yaml"""

def test_generates_commitment_yaml(tmp_path):
    """从 App 对象正确生成 commitment.yaml"""

def test_skill_symlink_per_role(tmp_path):
    """每个 role 只 symlink 分配给它的 skill"""

def test_hooks_claude_adapter(tmp_path):
    """claude 适配器生成 .claude/settings.local.json"""

def test_hooks_codex_adapter(tmp_path):
    """codex 适配器生成 .codex/hooks.json + config.toml"""
```

### 2.6 对比验证

在现有 workspace 上同时跑 bash deploy 和 Python compile，diff 输出确认一致。

### 交付标准

- [ ] `Compiler(app, config).compile()` 生成完整的 `.runtime/`
- [ ] 四原语编译逻辑清晰对应：Scope+Role→SOUL.md, Flow→注入+symlink+flow.yaml, Commitment→commitment.yaml
- [ ] 生成 compile_manifest.yaml
- [ ] 支持 claude/codex/kimi 三种适配器
- [ ] 和 bash deploy.sh 输出对比一致

---

## Phase 3：CLI + Runner

**目标**：实现 `socialwares` CLI 命令，替代 Makefile + shell 脚本。

### 3.1 CLI 框架

```python
# src/socialwares/cli.py
import click

@click.group()
def main():
    pass

@main.command()
@click.argument("name")
def new(name: str):
    """创建新项目"""

@main.command()
@click.option("--adapter", default=None)
def deploy(adapter: str | None):
    """编译四原语"""

@main.command()
@click.option("--role", required=True)
def start(role: str):
    """启动 agent（本地开发）"""

@main.command()
@click.argument("source")
@click.option("--channel", required=True)
def install(source: str, channel: str):
    """安装 App 到 IRC 频道"""

@main.command()
@click.argument("agent_name")
@click.option("--role", required=True)
@click.option("--channel", required=True)
def assign(agent_name: str, role: str, channel: str):
    """给 agent 分配 role"""

@main.command()
@click.argument("app_name")
@click.option("--channel", required=True)
def uninstall(app_name: str, channel: str):
    """卸载 App"""
```

### 3.2 `socialwares new`

从 `templates/` 复制项目模板到目标目录：
1. 复制 `agent/` 目录（四原语 + evolve skills + scripts）
2. 渲染 `socialware.py.j2` → `socialware.py`（填入项目名）
3. 渲染 `pyproject.toml.j2` → `pyproject.toml`
4. 复制 `src/api.py`、`app/`

### 3.3 `socialwares deploy`

1. 读取 `pyproject.toml` 的 `[tool.socialwares]` 配置
2. `load_app("socialware.py")` 加载 App 对象
3. `Compiler(app, config).compile()` 编译
4. 打印编译结果摘要

### 3.4 `socialwares start`

Runner（合并 start.sh + start_agent.py）：

```python
# src/socialwares/runner.py

class Runner:
    def start(self, role: str, adapter: str, runtime_dir: str):
        """启动单个 role 的 agent"""
        project_dir = runtime_dir / "agents" / role
        # TUI 模式：启动 Claude Code，--project-dir 指向 role 目录
        # SDK 模式：调用 adapter SDK

    def start_multi(self, roles: list[str], adapter: str, runtime_dir: str):
        """多角色启动（tmux 多窗格）"""
```

支持：
- `socialwares start --role default`（单角色）
- `socialwares start --role default,reviewer,evolver`（多角色，tmux）

### 3.5 `socialwares install / assign / uninstall`

#### install

```python
def install(source: str, channel: str):
    """git clone + 编译 + 启动后端"""
    app_dir = SOCIALWARES_HOME / "apps" / app_name  # ~/.socialwares/apps/{name}/
    subprocess.run(["git", "clone", source, str(app_dir)])
    # 在 app_dir 中执行 deploy
    app = load_app(app_dir / "socialware.py")
    config = load_config(app_dir / "pyproject.toml")
    Compiler(app, config).compile(output_dir=app_dir / ".runtime")
    # 启动 FastAPI 后端
    start_backend(app_dir)
```

#### assign — zchat 注入调研

**目标**：把 `.runtime/agents/{role}/` 的内容注入到 zchat agent 的 workspace。

**zchat agent workspace 现状**：
- 路径：`/tmp/zchat-{username}_{agent_name}/`（由 `_create_workspace` 生成）
- 状态文件：`~/.local/state/zchat/agents.json`（记录 workspace 路径）
- workspace 内容：agent 启动时由 `start.sh` 生成 `.claude/settings.local.json` + `.mcp.json`

**注入方式**：

```python
def assign(agent_name: str, role: str, channel: str):
    """将 role 配置注入到 zchat agent 的 workspace"""

    # 1. 找到 agent 的 workspace 路径
    #    读取 ~/.local/state/zchat/agents.json
    #    找到 agent_name 对应的 workspace 字段
    workspace = get_agent_workspace(agent_name)

    # 2. 注入 SOUL.md
    #    zchat claude agent 的 prompt 文件是 SOUL.md（或 CLAUDE.md）
    #    需要注入到 workspace 根目录
    soul_src = app_dir / ".runtime" / "agents" / role / "SOUL.md"
    shutil.copy(soul_src, workspace / "SOUL.md")

    # 3. 注入 skills
    #    zchat start.sh 生成了 .claude/settings.local.json（MCP 配置）
    #    我们需要追加 skills 目录，不能覆盖 settings.local.json
    #    skills 通过 symlink 注入
    skills_src = app_dir / ".runtime" / "agents" / role / ".claude" / "skills"
    skills_dst = workspace / ".claude" / "skills"
    if skills_dst.exists():
        shutil.rmtree(skills_dst)
    skills_dst.symlink_to(skills_src.resolve())

    # 4. 注入 hooks（追加，不覆盖 zchat 已有的 settings）
    #    zchat 的 settings.local.json 有 MCP permissions
    #    socialwares 的 settings.local.json 有 hooks
    #    需要 merge 两个 JSON
    zchat_settings = json.loads((workspace / ".claude" / "settings.local.json").read_text())
    sw_settings = json.loads((app_dir / ".runtime" / "agents" / role / ".claude" / "settings.local.json").read_text())
    merged = deep_merge(zchat_settings, sw_settings)
    (workspace / ".claude" / "settings.local.json").write_text(json.dumps(merged, indent=2))

    # 5. 注入 commitment.yaml + flow.yaml（参考文件）
    shutil.copy(app_dir / ".runtime" / "commitment.yaml", workspace / "commitment.yaml")
    shutil.copy(app_dir / ".runtime" / "flow.yaml", workspace / "flow.yaml")
```

**关键注意点**：
- zchat 的 `.claude/settings.local.json` 已有 MCP permissions（`mcp__zchat-channel__reply` 等），不能覆盖
- socialwares 的 hooks（log_prompt, log_tool）需要追加到同一个文件
- 解决方案：JSON deep merge，保留 zchat 的 permissions + 追加 socialwares 的 hooks

**zchat 需要提供的接口**（当前 mock，后续对接）：

```python
def get_agent_workspace(agent_name: str) -> Path:
    """读取 zchat agents.json，返回 agent 的 workspace 路径"""
    state_file = Path.home() / ".local/state/zchat/agents.json"
    agents = json.loads(state_file.read_text())
    agent = agents.get(agent_name)
    if not agent:
        raise ValueError(f"zchat agent '{agent_name}' not found")
    return Path(agent["workspace"])
```

**Mock 实现**（Phase 3 使用，Phase 5 替换为真实调用）：

```python
def get_agent_workspace(agent_name: str) -> Path:
    """Mock：返回本地测试目录"""
    mock_dir = Path.home() / ".socialwares" / "mock_agents" / agent_name
    mock_dir.mkdir(parents=True, exist_ok=True)
    # 模拟 zchat 的初始文件
    (mock_dir / ".claude").mkdir(exist_ok=True)
    (mock_dir / ".claude" / "settings.local.json").write_text('{"permissions":{"allow":[]}}')
    return mock_dir
```

#### uninstall

```python
def uninstall(app_name: str, channel: str):
    # 1. 找到所有 assigned 的 agent，清除注入的文件
    # 2. 停止 FastAPI 后端
    # 3. 可选：删除 ~/.socialwares/apps/{name}/
```

### 3.6 搬入模板

```bash
# 现有文件搬入 templates/
agent/                → src/socialwares/templates/agent/
src/app.py            → src/socialwares/templates/src/api.py
```

新增模板文件：
- `src/socialwares/templates/socialware.py.j2`
- `src/socialwares/templates/pyproject.toml.j2`

### 3.7 pip 包发布

```bash
# 构建
uv build
# → dist/socialwares-0.2.0.tar.gz
# → dist/socialwares-0.2.0-py3-none-any.whl

# 发布到 PyPI（需要一次性配置 API token）
uv publish
# → https://pypi.org/project/socialwares/

# 或发布到 git（不需要 PyPI）
git tag v0.2.0
git push --tags
# 别人：pip install git+https://github.com/ezagent42/Socialwares.git@v0.2.0
```

### 3.8 测试

```python
def test_new_creates_project(tmp_path):
    """socialwares new 生成完整项目结构"""

def test_deploy_cli(tmp_path):
    """socialwares deploy 读取 socialware.py 并编译"""

def test_start_single_role():
    """socialwares start --role default 启动成功"""

def test_assign_mock(tmp_path):
    """socialwares assign 注入文件到 mock workspace"""

def test_assign_merges_settings(tmp_path):
    """注入不覆盖 zchat 已有的 settings"""
```

### 交付标准

- [ ] `socialwares new <name>` 生成有内容的项目
- [ ] `socialwares deploy` 读取 socialware.py + pyproject.toml 编译
- [ ] `socialwares start --role <role>` 启动 agent（TUI + SDK）
- [ ] `socialwares start --role a,b,c` 多角色 tmux
- [ ] `socialwares install` git clone + deploy + 启动后端
- [ ] `socialwares assign` 注入到 mock workspace（JSON merge 正确）
- [ ] `uv build` 可构建 + `pip install git+...` 可安装

---

## Phase 4：测试 + 清理

**目标**：迁移现有测试，清理不再需要的文件。

### 4.1 迁移现有测试

| 现有测试 | 适配方式 |
|---------|---------|
| test_deploy.py | 改为调用 Compiler 而不是 bash |
| test_check_structure.py | 路径适配 |
| test_diagnose.py | 路径适配 |
| test_eval_script.py | 路径适配 |
| test_hooks.py | 改为验证 compiler 生成的 hooks |
| test_create_workspace.py | 改为验证 `socialwares new` |

### 4.2 新增测试

| 测试 | 覆盖范围 |
|------|---------|
| test_app.py | App 声明式 API |
| test_compiler.py | 编译器 |
| test_cli.py | CLI 命令 |
| test_loader.py | socialware.py 加载 |
| test_e2e.py | new → deploy → start 完整流程 |

### 4.3 清理

删除：
- `Makefile`, `agent/Makefile.template`
- `claude.sh`
- `scripts/create-my-socialware.py`
- `agent/deploy.sh`, `agent/start.sh`
- `agent/adapters/`（已搬入 pip 包）
- `.socialware/workspace/`
- `agent/flow/flow.yaml`（变成编译产物）
- `agent/commitment/`（变成编译产物）

### 4.4 E2E 验证

```bash
# 完整流程
socialwares new test-app
cd test-app
socialwares deploy
uvicorn src.api:api --port 8001 &
socialwares start --role default    # 验证 agent 启动
socialwares start --role evolver    # 验证 evolver 启动
# 手动测试："check health" / "check structure"
```

### 交付标准

- [ ] 所有现有测试迁移通过
- [ ] 新增测试覆盖 App API + 编译器 + CLI
- [ ] E2E 流程验证通过
- [ ] 不再需要的文件已清理
- [ ] `uv build` 构建成功
- [ ] `pip install git+https://github.com/ezagent42/Socialwares.git` 可用

---

## 依赖关系

```
Phase 1 (App API)
    │
    ▼
Phase 2 (编译器)  ← 依赖 App 对象作为输入
    │
    ▼
Phase 3 (CLI + Runner + assign mock + pip 发布)
    │
    ▼
Phase 4 (测试 + 清理)
```

Phase 1→2→3 严格串行。Phase 4 可以和 Phase 3 部分并行。

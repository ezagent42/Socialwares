# 打包 E2E 测试记录

## 问题 1：开发模式安装后 CLI 命令不可用

**现象**：`uv pip install -e .` 成功，但 `socialwares --help` 报 `command not found`。

**原因**：`uv pip install` 安装到项目的 `.venv/` 虚拟环境中，CLI 入口脚本在 `.venv/bin/socialwares`，不在系统 PATH 中。

**解决**：
```bash
# 方式 1：通过 uv run 调用
uv run socialwares --help

# 方式 2：激活虚拟环境
source .venv/bin/activate
socialwares --help
```

**备注**：正式发布到 PyPI 后，用户用 `pip install socialwares`（全局安装）或 `pipx install socialwares` 不会有此问题。开发模式下是预期行为。

## 问题 2：agent/ 目录下 flow/commitment 只有 README 没有模板

**现象**：仓库根目录的 `agent/flow/` 和 `agent/commitment/` 只剩 README.md，没有实际模板内容。`agent/flow/README.md` 中仍引用旧的 flow.yaml 内容。

**需要决定**：agent/ 目录如何组织——是保留作为参考文档，还是删除（内容已在 `src/socialwares/templates/` 中）。

## 问题 3：模板中没有 commitment 目录

**现象**：`src/socialwares/templates/agent/` 下没有 `commitment/` 目录。`socialwares new task-review` 生成的项目 `agent/` 下也没有 `commitment/`。

**原因**：重构时 commitment 从文件定义改为 `socialware.py` 声明式定义，commitment.yaml 变成编译产物。但模板中应该保留 `agent/commitment/README.md` 作为参考文档，说明 commitment 在 socialware.py 中定义。

## 问题 4：socialware.py 模板引导性不足

**现象**：`socialwares new` 生成的 `socialware.py` 没有按四原语组织，缺少清晰的注释引导用户填写。

**期望**：模板应该按 Scope → Role → Flow（action + 状态机）→ Commitment 的顺序组织，每个原语有注释说明作用和填写方式，让用户一看就知道怎么改。

**额外问题**：模板中出现了"状态机"等专业术语，对用户有误导性。注释应使用更易懂的语言。

## 问题 5：E2E 测试说明不一致 + 缺少 cd 步骤

**现象 1**：Phase 3.1 中 `ls .runtime/agents/` 的预期输出只列了 `default reviewer evolver`，但实际每个角色有不同的 skills。reviewer 有 `check_health list_tasks review_task`，default 有 `check_health close_task create_task list_tasks submit_task`。测试说明中的预期输出需要更准确。

**现象 2**：Phase 2.2 步骤要求编辑 socialware.py 和创建 skill 目录，但没有提醒用户先 `cd task-review`（Phase 1.1 创建后用户可能还在父目录）。

**修复**：
- 测试说明中的 `ls` 预期输出要列出每个角色的完整 skill 列表
- Phase 2 开头加 `cd task-review` 提醒

## 问题 6：编译产物位置确认

**现象**：SOUL.md、commitment.yaml、flow.yaml 都在 `.runtime/agents/{role}/` 根目录，不在 `.claude/` 内。用户担心 agent 识别不到。

**结论：位置正确。**

```
.runtime/agents/default/
├── SOUL.md                    ← 在根目录（正确）
├── commitment.yaml            ← 在根目录（给 evolve scripts 读）
├── flow.yaml                  ← 在根目录（给 evolve scripts 读）
├── .workspace_root
└── .claude/
    ├── hooks/
    ├── settings.local.json
    └── skills/
```

- SOUL.md：Claude Code 通过 `--append-system-prompt-file SOUL.md` 注入（`shell.sh` 第 16-17 行），不是通过 `.claude/` 目录发现的。`socialwares start` 用 `--project-dir .runtime/agents/{role}/` 启动 Claude Code，SOUL.md 在该目录根下被读取。
- commitment.yaml / flow.yaml：不是 Claude Code 读的，是 evolve scripts（diagnose.py 等）读的参考文件。
- Codex 适配器用 `AGENTS.md` 替代 `SOUL.md`，同样在根目录。

## 问题 7：E2E 测试中 grep 命令语法错误

**现象**：`cat .runtime/agents/default/SOUL.md | grep -c "---"` 报错 `unrecognized option '---'`。

**原因**：`---` 被 grep 解析为选项参数。需要用 `--` 分隔选项和模式。

**修复**：测试说明中的命令改为：
```bash
grep -c -- "---" .runtime/agents/default/SOUL.md
```

## 问题 8：deploy 不幂等 — 切换适配器后旧 prompt 文件残留

**现象**：先 `socialwares deploy`（claude，生成 SOUL.md），再 `socialwares deploy --adapter codex`（生成 AGENTS.md），但 SOUL.md 没有被清除。两个 prompt 文件同时存在。

**原因**：编译器生成新适配器的 prompt 文件时，没有清除上一次不同适配器生成的 prompt 文件。

**修复**：编译器在写入 prompt 文件前，应先清除所有可能的 prompt 文件（SOUL.md、AGENTS.md），再写入当前适配器对应的那个。或者每次 deploy 先清空 `.runtime/agents/{role}/` 目录再重新生成。

## 问题 9：uvicorn 找不到 src.api:api

**现象**：`uvicorn src.api:api --port 8001` 报 `Attribute "api" not found in module "src.api"`。

**原因**：模板中的 `src/api.py` 里 FastAPI 实例变量名可能不是 `api`（可能是 `app`），或者 `src/` 不是 Python 包（缺少 `__init__.py`）。需要检查模板内容。

## 问题 10：socialwares start 报错 — adapters 包缺少 `__init__.py`

**现象**：`socialwares start --role default` 报 `TypeError: argument should be a str or an os.PathLike object where __fspath__ returns a str, not 'NoneType'`。

**原因**：`socialwares.adapters.__file__` 返回 None，说明 `src/socialwares/adapters/` 目录缺少 `__init__.py`，Python 把它当作 namespace package（没有 `__file__`）。

**修复**：在 `src/socialwares/adapters/` 下创建 `__init__.py`。

---

## 已修复记录（2026-03-31）

| 问题 | 修复方式 |
|------|---------|
| #2 agent/ README 过时 | 更新 flow/README.md 和 commitment/README.md |
| #3 模板缺 commitment | 添加 `templates/agent/commitment/README.md` |
| #4 socialware.py 引导不足 | 按四原语重写模板，去掉"状态机"术语 |
| #7 grep 语法 | E2E 文档改为 `grep -c -- "---"` |
| #8 deploy 不幂等 | 编译器写 prompt 前清除旧文件（SOUL.md/AGENTS.md） |
| #9 uvicorn 命令 | 模板和文档改为 `src.api:app` |
| #10 adapters __init__.py | 创建 `adapters/__init__.py` |

---

## 第二轮测试问题

## 问题 11：E2E Phase 2 仍缺少 cd 提示

**现象**：Phase 2.1 步骤直接开始编辑 socialware.py，但没有明确的 `cd task-review` 命令行。之前修复只加了一行提示文字（"> 确保在 task-review 项目目录下操作"），但用户仍然容易漏看，应该在 2.1 的 bash 代码块里加上 `cd task-review`。

## 问题 12：Phase 3.1 default skills 预期仍不一致

**现象**：实际 `ls .runtime/agents/default/.claude/skills/` 输出为 `check_health close_task create_task list_tasks submit_task`，包含了 flow transition 中的 `close_task` 和 `submit_task`。

**说明**：因为 `actions_for_role("default")` 会包含 flow transition 中 role=["default"] 的 action（submit_task、close_task），所以 default 角色有 5 个 skill 是正确行为。E2E 文档的预期已更新但需再次确认和实际输出完全一致。

## 问题 13：切换适配器后旧的适配器目录残留

**现象**：`socialwares deploy --adapter codex` 后，`.runtime/agents/{role}/` 下同时存在 `.claude/`（旧）和 `.agents/` + `.codex/`（新）。幂等修复只清理了 prompt 文件（SOUL.md/AGENTS.md），没有清理适配器相关的目录。

**需要修复**：deploy 切换适配器时，应该清除上一次适配器生成的目录（`.claude/`、`.agents/`、`.codex/`），只保留当前适配器的。

## 问题 14：端口占用 + Agent 不知道后端端口

**现象 1**：`uvicorn src.api:app --port 8001` 报端口被占用（之前测试时的进程未退出）。

**解决**：`kill $(lsof -t -i:8001)` 或 `fuser -k 8001/tcp` 杀掉旧进程。

**现象 2**：后端端口在 `pyproject.toml [tool.socialwares] api_port` 中配置，但 Agent 的 SKILL.md 中不知道后端跑在哪个端口。Agent 调用 API 时需要知道 `http://localhost:{port}`。

**需要讨论**：是否在编译时将 api_port 注入到 SOUL.md 或 SKILL.md 中？或者约定环境变量 `APP_PORT`？还是在 SOUL.md 中写死"后端在 localhost:8001"？

## 问题 15：SDK 模式未测试

**现象**：E2E 测试只覆盖了 TUI 模式（`socialwares start --role default`），没有测试 SDK 模式（`socialwares start --role default --prompt "check health"`）。

**需要**：
1. 确认 `socialwares start --role default --prompt "..."` 能正常调用 SDK adapter
2. 确认 SDK 模式的 session 保存到 `.runtime/data/sessions/`
3. 在 E2E 测试文档中补充 SDK 模式的测试步骤

## 问题 16：evolve_structure_check 脚本运行失败

**现象 1（uv run）**：`uv run agent/flow/evolve_structure_check/scripts/check_structure.py` 报错 — 在 task-review 项目中 `uv run` 尝试安装 `socialwares` 依赖，但 PyPI 上没有（尚未发布）。task-review 的 pyproject.toml 依赖 `socialwares>=0.2.0`，uv 会创建独立 venv 并尝试从 PyPI 解析。

**解决方向**：用户项目不应依赖从 PyPI 安装 socialwares——开发阶段应该用 editable install 或者 path 依赖。模板的 pyproject.toml 需要调整。

**已修复（第三轮）**：模板 pyproject.toml 改为 git 依赖 `socialwares @ git+https://github.com/ezagent42/Socialwares.git`。

**第四轮新问题**：git 依赖要求远程仓库有最新代码。当前 feat/dispatch 分支还没 push 到远程，导致 `uv run` 解析 git 依赖时 clone 失败。

## 问题 25：git 依赖需要远程仓库已 push

**现象**：`uv run agent/flow/evolve_*/scripts/*.py` 报 `Failed to download socialwares @ git+https://github.com/ezagent42/Socialwares.git` — git clone 失败。

**原因**：feat/dispatch 分支的代码还没 push 到 GitHub，远程仓库没有 socialwares pip 包的代码。

**解决**：push 当前分支到远程，或者模板 pyproject.toml 的 git URL 指定分支 `git+https://github.com/ezagent42/Socialwares.git@feat/dispatch`。

**更根本的问题**：在开发阶段（代码还没 push），git 依赖不可靠。需要一个本地开发时也能工作的方案。

**可能的方案**：
1. 模板 pyproject.toml 用 path 依赖：`socialwares @ file:///home/yaosh/projects/Socialwares` — 但路径写死不通用
2. SKILL.md 中用 `python` 代替 `uv run` — 绕过依赖解析
3. 用户项目的 venv 共享父项目的 venv（`--active` flag）
4. `socialwares deploy` 时在 .runtime/ 中生成一个 `.python-version` 或 symlink 指向框架的 venv

## 问题 26：evolve 脚本与编译产物格式不兼容

**现象**：Agent 自己用 `python` 跑 `check_structure.py`，发现两个 bug：

1. **commitment.yaml 格式不匹配**：编译器生成的是 list 格式 `commitments: [{id: C1, ...}]`，但脚本 `commitments.items()` 期望 dict 格式 `commitments: {C1: {...}}`
2. **flow.yaml 缺 states 字段**：编译器生成的 flow.yaml 只有 transitions，没有显式的 states 列表。脚本 `fdata.get("states", [])` 拿到空列表就报 "no states defined"

**根本原因**：evolve 脚本是按旧版 flow.yaml/commitment.yaml 的格式写的。编译器生成的新格式和旧格式不一致。

**需要修复**：
1. 编译器 `_generate_commitment_yaml` 改为 dict 格式（和旧版一致），或脚本适配 list 格式
2. 编译器 `_generate_flow_yaml` 加入 `states` 字段，或脚本从 transitions 推断 states

**注意**：Agent 可能已经在 task-review 目录下自行修改了脚本（他改了本地的而不是模板的）。需要把修复同步到 `src/socialwares/templates/` 中的模板。

**已修复**：编译器统一为 dict 格式 commitment + 显式 states 列表。

## 问题 27：evolver 运行 check structure / diagnose / evaluate 没有产生报告

**现象**：在 evolver 角色中执行 "check structure"、"diagnose"、"evaluate"，`.runtime/data/evolve/reports/` 下没有报告文件。

**可能原因**：
1. Agent 执行脚本时的工作目录不对——脚本在 `.runtime/agents/evolver/` 下运行（`--project-dir`），但报告写到相对路径 `.runtime/data/evolve/reports/`，这个路径是相对于项目根的。需要检查 `.workspace_root` 是否正确被读取。
2. 脚本跑成功了但 Agent 没有调用脚本——Agent 可能直接回答而不是执行 SKILL.md 中的 bash 命令。
3. `uv run` 失败（git 依赖问题），Agent fallback 到手动回答。

**更新**：报告有生成。但 eval 报告的 suggestions 字段为空。

## 问题 28：eval 报告 suggestions 为空

**现象**：`evolve_api_check` 的 eval 报告产生了，但 suggestions 字段为空。

**可能原因**：
1. 所有 eval cases 都 PASS 了（health check 通过），没有失败项，所以没有 suggestion
2. E2E 测试的 socialware.py 中定义了更多 action（create_task 等），但 eval_cases.yaml 只有默认的 health check 一条。用户没有为新增的 action 写 eval cases。

**实际问题**：eval 只检查"已有 case 是否通过"，没有检查"是否所有 action 都有 eval case 覆盖"。socialware.py 注册了 create_task、list_tasks、review_task 等 action，但 eval_cases.yaml 只覆盖了 health check，覆盖率不足应该产生 suggestion。

**需要修复**：`run_eval.py` 应该读取 flow.yaml，对比注册的 action 和 eval_cases 中覆盖的 action，对未覆盖的 action 生成 suggestion（如 "action 'create_task' has no eval case"）。

## 问题 29：跨平台兼容性

**现象**：hook 脚本（`log_prompt.sh`、`log_tool.sh`）是 bash 脚本，Windows 原生不支持。

**历史**：之前做过跨平台兼容性工作：
- `cf6fcd9`：claude.sh 中 uuidgen 替换为 python3 uuid（Windows 没有 uuidgen）
- `b222374`：base.py 添加 explicit UTF-8 encoding（Windows 默认 GBK）
- `9fd7fd0`：设置 PYTHONUTF8=1（Windows GBK decode 问题）
- `d9887b6`：deploy.sh 中 Windows python3 检测

**当前状态**：
- 编译器（compiler.py）：纯 Python，跨平台 ✓
- CLI（cli.py）：纯 Python，跨平台 ✓
- Evolve 脚本（*.py）：纯 Python，跨平台 ✓
- Hook 脚本（*.sh）：bash，Windows 需要 WSL/Git Bash ✗
- adapters/shell.sh：bash，Windows 需要 WSL ✗

**结论**：核心功能（编译、CLI、evolve 脚本）跨平台。Hook 和 adapter shell 脚本依赖 bash，但 Claude Code / Codex CLI 目前只在 macOS + Linux（含 WSL）上运行，实际不影响。未来如果要完全跨平台，hook 脚本需要改为 Python。

## 问题 30：install 判断"已安装"用目录而不是 installs.json

**现象**：`installs.json` 为空，但 `socialwares install` 报 "already installed"。`socialwares uninstall` 因为 installs.json 为空而找不到记录，无法卸载。死锁。

**原因**：install 命令检查 `app_dir.exists()`（目录是否存在），而 uninstall 检查 `installs.json`（记录是否存在）。两个判断不一致。之前 install 失败但目录已经 git clone 出来了，installs.json 没写入，导致状态不一致。

**需要修复**：install 应该以 `installs.json` 为准，或者 uninstall 也检查目录。最简单的修法：install 时如果目录存在但 installs.json 没记录，直接清掉目录重新安装。

## 问题 31：E2E 文档中 install/assign 路径和说明不准确

**现象**：
1. Phase 5.1 中 `ls ~/.socialwares/apps/task-review/.runtime/agents/` 路径过期，应为 `.socialware/workspace/test/apps/task-review/.runtime/agents/`
2. Phase 5.2 没说明 assign 在哪个目录执行（应在仓库根目录）
3. Phase 5.2 的 mock workspace 路径 `~/.socialwares/mock_agents/` 过期，应为 `.socialware/workspace/test/agents/`

**需要修复**：更新 release-e2e-test.md 中 Phase 5 的所有路径。

## 问题 32（TODO）：dev 角色缺少引导性 skill

**现象**：dev 角色目前只有 inspect 和 setup_claude，缺少开发引导。

**需要新增**：

1. **dev_init** — 引导首次开发（四原语构建）
   - 触发："开始开发"、"初始化"、"guide me"
   - 流程：引导用户逐步填写 scope → role → flow（action + SKILL.md）→ 状态流转 → commitment
   - 每一步给出模板和示例，用户确认后写入文件并注册到 socialware.py
   - 最后 deploy + 验证

2. **dev_iterate** — 引导持续开发（根据 evolve 报告改进）
   - 触发："继续改进"、"看报告"、"iterate"
   - 流程：读取 `.runtime/data/evolve/reports/` 最新报告，解读 suggestions，引导用户修改对应文件
   - 修改完后重新 deploy + 验证

**优先级**：中。先完成当前 E2E 测试和 bug 修复，再做。

## 问题 33（TODO）：socialwares new 支持从 git 拉模板

**需求**：`socialwares new my-app --from git@xxx/task-review.git`，clone 一个已有 socialware 作为新项目起点。

与 `install` 的区别：install 原封安装到频道；`new --from` 是 clone 后改名作为新项目继续开发。

## 问题 34（TODO）：基础 socialware 的仓库组织

**结论**：推荐 GitHub org 方式，每个 app 独立 repo：

```
github.com/socialwares/taskarena
github.com/socialwares/agentforge
github.com/socialwares/respool
```

独立版本、独立 issue、独立贡献者。社区 app 同样方式。未来 SocialwareHub 是这些仓库的索引。

---

## 第四轮综合审查（2026-03-31）

### 开发者完整工作流

```
pip install socialwares
socialwares new my-app
cd my-app
socialwares start --role dev      ← 进入 dev 角色
  "init"                          ← dev_init 引导四原语定义
  （交互式写 scope → role → flow → commitment）
  socialwares deploy              ← 编译
  开发前后端代码（API + SKILL.md）
  手动调试对话
socialwares start --role evolver  ← 切换到 evolver
  "check structure"               ← 结构一致性
  "evaluate"                      ← API 测试 + 覆盖率
  "diagnose"                      ← 对话数据诊断
socialwares start --role dev      ← 切回 dev
  "iterate"                       ← dev_iterate 读报告，引导修复
  修改 → deploy → 再测试
  定版 → git commit + push
```

### 工作流缺失项

| 缺失 | 说明 | 优先级 |
|------|------|--------|
| **dev_build skill** | TDD 引导：写测试 → 写代码 → 跑测试 → 验证。当前 dev 角色没有开发辅助 skill | 中 |
| **dev_release skill** | 定版收尾：git commit + tag + push + changelog。dev_iterate 改完后没有引导提交 | 中 |
| **SDK 模式测试** | `socialwares start --role default --prompt "check health"` 未在 E2E 中验证 | 高 |
| **evolve_auto 测试** | 注册了但 E2E 未验证 | 低 |
| **evolver 完整链路** | hooks → prompts → diagnose → violations → improve 数据流未端到端验证 | 高 |
| **`socialwares list` 独立测试** | 只在 install 输出中提到，没有独立验证 | 低 |

### 已实现 vs 缺失对照

| 步骤 | 当前状态 |
|------|---------|
| install + new | ✓ 完整 |
| start --role dev | ✓ 完整 |
| dev_init 引导四原语 | ✓ SKILL.md + references 已有 |
| dev 辅助开发（TDD） | ✗ 缺 dev_build skill |
| dev 辅助调试 | △ inspect 可看结构，但没有专门的调试 skill |
| 切换 evolver 测试 | ✓ 5 个 evolve skill |
| eval 覆盖率 suggestion | ✓ 已实现 |
| dev_iterate 读报告改进 | ✓ SKILL.md + references 已有 |
| 定版发布 | ✗ 缺 dev_release skill |
| new --from git 模板 | ✗ CLI 未实现 |

**现象 2（python 直接运行）**：`check_structure.py` 报 `flow.yaml not found`——因为现在 flow.yaml 是编译产物在 `.runtime/` 中，不在 `agent/` 下。脚本还在找旧路径。

**根本问题**：evolve scripts 是从旧架构搬过来的，内部硬编码了旧的文件路径（`agent/flow/flow.yaml`、`agent/commitment/commitment.yaml`）。重构后这些文件位置变了：
- flow.yaml → `.runtime/flow.yaml`（编译产物）
- commitment.yaml → `.runtime/commitment.yaml`（编译产物）
- 或者 evolve scripts 应该读 `.runtime/agents/{role}/flow.yaml`（编译时复制进去的）

**需要修复**：所有 evolve scripts 的路径引用需要适配新架构。

## 问题 17：Evolver 手动结构检查发现的多个问题

Agent 因脚本崩溃，手动执行结构检查，发现以下问题：

### 17a：inline 定义 role 不会自动创建文件

**现象**：`app.role("reviewer", "You review and approve tasks.")` 使用 inline 方式定义，编译成功（内容写入 SOUL.md），但 `agent/role/reviewer.md` 文件不存在。结构检查发现不一致。

**期望**：即使用 inline 方式定义，编译器也应该在 `agent/role/` 下生成对应的 .md 文件，保持四原语目录的完整性。或者 structure_check 应该认可 inline 定义。

### 17b：inspect 和 setup_claude 是孤立 skill

**现象**：模板包含 `agent/flow/inspect/SKILL.md` 和 `agent/flow/setup_claude/SKILL.md`，但 `socialware.py` 模板中没有注册这两个 action。它们存在但不会被编译到任何角色。

**结论**：inspect 和 setup_claude 是 dev 角色的 skill。dev 应该是模板内置的默认角色（和 default、evolver 一样）。需要：
1. 模板中添加 `agent/role/dev.md`
2. 模板 socialware.py 中注册 `app.role("dev", file="agent/role/dev.md")`
3. 模板 socialware.py 中注册 `app.action("inspect", role=["dev", "evolver"])` 和 `app.action("setup_claude", role=["dev"])`

### 17c：flow.yaml 和 commitment.yaml 是编译产物，不在 agent/ 下

**现象**：结构检查脚本期望在 `agent/` 下找到 flow.yaml 和 commitment.yaml，但新架构中这些是编译产物在 `.runtime/` 中。

**说明**：这不是 bug——是架构变化。但 evolve scripts 需要知道去 `.runtime/` 找这些文件，或者编译器提供参数指定路径。

## 问题 18：assign 的合并测试不充分

**现象**：E2E 测试中 assign 只验证了文件是否注入，没有验证合并行为——即 assign 后原有的 agent workspace 配置（如 zchat 的 MCP permissions、已有的 CLAUDE.md、其他 skills）是否保持不变。

**需要补充的测试场景**：
1. agent workspace 已有 `.claude/settings.local.json`（含 zchat MCP permissions）→ assign 后 permissions 仍在，hooks 追加进去
2. agent workspace 已有其他 skills → assign 后原有 skills 不被覆盖（只替换 skills 目录的 symlink）
3. agent workspace 已有 CLAUDE.md 或其他文件 → assign 后不被删除
4. 连续 assign 两次不同 role → 第二次应覆盖第一次的配置
5. assign 后 uninstall → workspace 恢复到 assign 前的状态（目前 uninstall 直接删除文件，不是恢复）
6. 已有 skills 目录下有其他 skill → assign 应该是追加 symlink，不是替换整个 skills 目录（当前实现是把整个 skills 目录替换为 symlink，会丢失已有 skills）

## 问题 19：install 安装目录不合理 + 缺少路径选项

**现象**：`socialwares install` 把 App 安装到 `~/.socialwares/apps/{name}/`，这是一个隐藏的全局目录。

**期望**：应该安装到 `.socialware/workspace/{channel}/{app}/` 下（和现有的 workspace 结构融合），或者至少支持 `--path` 选项让用户指定安装目录。

```bash
# 期望的行为：
socialwares install git@xxx/task-review.git --channel "#support"
# → .socialware/workspace/support/task-review/

# 或指定路径：
socialwares install git@xxx/task-review.git --path ./my-apps/task-review
```

**需要修复**：
1. 默认安装路径改为 `.socialware/workspace/{channel}/{app}/`
2. 支持 `--path` 选项覆盖默认路径

## 问题 20：assign 应支持指定 agent workspace 路径

**现象**：`socialwares assign alice-support --role default --channel "#support"` 通过 agent name 去找 zchat 的 workspace 路径（mock 或读 agents.json）。但 zchat 还在开发中，实际使用时用户可能需要直接指定路径。

**关于 agent workspace 的结构**：一个 agent 的 workspace 就是一个目录，`.claude/`（或 `.codex/`）在这个目录下。SOUL.md 也在这个目录根下。所以指定的路径是 `.claude/` 的上一级目录。

```
agent-workspace/          ← 这是 assign --path 指定的路径
├── SOUL.md               ← 注入到这里
├── flow.yaml             ← 注入到这里
├── commitment.yaml       ← 注入到这里
├── .workspace_root
└── .claude/              ← 适配器目录
    ├── settings.local.json  ← merge 注入
    └── skills/              ← symlink 注入
```

**澄清**：`.socialware/workspace/` 的组织应该是：

```
.socialware/workspace/
└── {channel-name}/              ← 对应 IRC 频道
    ├── agents/                  ← 频道内的 agent（每个 agent 一个目录）
    │   ├── alice-support/       ← agent workspace（Claude Code 的 project-dir）
    │   │   ├── SOUL.md
    │   │   ├── .claude/
    │   │   │   ├── settings.local.json
    │   │   │   └── skills/      ← symlink 到 app 的 skill
    │   │   ├── flow.yaml
    │   │   └── commitment.yaml
    │   └── bob-reviewer/
    │       └── ...
    └── apps/                    ← 频道安装的 app
        └── task-review/         ← git clone 到这里
            ├── socialware.py
            ├── agent/
            ├── src/
            └── .runtime/        ← 编译产物
```

**逻辑**：
- `socialwares install` → git clone app 到 `workspace/{channel}/apps/{app}/`，编译
- `socialwares assign` → 从 app 的 `.runtime/agents/{role}/` 把配置注入到 `workspace/{channel}/agents/{agent-name}/`
- 安装 app = 给频道里的 agent 注入更多设置（skills、hooks、SOUL.md 合并）
- 一个频道可以安装多个 app，agent 的配置是多个 app 叠加合并的结果

## 问题 21：Evolver 运行时链路未验证

**现象**：E2E 测试只到启动 evolver 为止，没有验证完整的数据链路：

1. **Hooks 是否工作**：和 default agent 对话后，`.runtime/data/prompts/current.jsonl` 是否有记录（UserPromptSubmit + PreToolUse hook 输出）
2. **Session 是否正确记录**：SDK 模式下 `.runtime/data/sessions/` 是否有 session 文件
3. **Diagnose 能否读取数据**：evolve_session_diagnose 能否读取 prompts 数据 + commitment.yaml，输出诊断报告
4. **Violations 是否写入**：诊断发现违反后，`.runtime/data/evolve/violations/` 是否有 violation 记录
5. **Improve 能否基于诊断结果工作**：evolve_improve 能否读取 violations 和 structure_check 结果

**需要补充的 E2E 测试步骤**：
```
① 启动 default agent，对话几轮 → 检查 .runtime/data/prompts/current.jsonl 有记录
② 启动 evolver → "diagnose" → 检查是否读取了 prompts 数据
③ 检查 .runtime/data/evolve/violations/ 是否有输出
④ "improve" → 检查是否基于诊断结果给出建议
⑤ SDK 模式：socialwares start --role default --prompt "check health" → 检查 .runtime/data/sessions/ 有文件
```

## 问题 22：dev 角色缺失

**现象**：模板中没有 dev 角色。dev 是默认内置角色（和 default、evolver 并列），负责开发环境配置，拥有 inspect 和 setup_claude 两个 skill。

**需要修复**：
1. 模板添加 `agent/role/dev.md`（之前重构时被删了）
2. 模板 socialware.py 注册 `app.role("dev", file="agent/role/dev.md")`
3. 模板 socialware.py 注册 `app.action("inspect", role=["dev", "evolver"])` 和 `app.action("setup_claude", role=["dev"])`
4. `socialwares start --role dev` 应该能启动 dev 角色并使用 inspect/setup_claude skill

## 第三轮测试问题

## 问题 23：deploy 后没有 dev 角色

**现象**：`socialwares deploy` 输出只有 default + evolver，没有 dev。

**原因**：模板 `socialware.py` 已经加了 `app.role("dev", ...)`，但用户是用旧版模板 `socialwares new` 生成的项目，`socialware.py` 里没有 dev。需要重新 `socialwares new` 或手动添加。

**实际原因**：E2E 文档 2.1 的 socialware.py 示例缺少 dev 角色和 inspect/setup_claude action。用户按文档操作会覆盖模板生成的 socialware.py，丢失 dev 相关内容。

**已修复**：E2E 文档 2.1 的 socialware.py 示例补充了 dev 角色。

## 问题 24（澄清）：codex 适配器生成 .agents/ 和 .codex/ 两个目录

**现象**：`socialwares deploy --adapter codex` 后每个 role 目录下有 `.agents/` 和 `.codex/` 两个目录。

**结论：这是正确行为，不是 bug。**（已确认来自 evolve-v3-plan.md 的三平台调研结果）

Codex CLI 的约定：
- `.agents/skills/` — skills 目录（Codex 读 skills 的位置）
- `.codex/hooks.json` — hooks 配置
- `.codex/config.toml` — 功能开关（`codex_hooks = true`）

对比 Claude Code 把 skills + hooks 都在 `.claude/` 下。这是两个平台不同的目录约定。

**需要修复**：
```bash
# install 到 channel 下
socialwares install git@xxx/task-review.git --channel "#support"
# → .socialware/workspace/support/apps/task-review/

# assign 注入到 channel 下的 agent
socialwares assign alice-support --role default --channel "#support"
# → .socialware/workspace/support/agents/alice-support/
```

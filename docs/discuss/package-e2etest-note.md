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

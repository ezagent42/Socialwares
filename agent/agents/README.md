# Agent 子定义目录

此目录存放从 AgentForge 下载或自动生成的子 agent 定义。

## 添加方式

1. **从模板下载**:
   ```bash
   uv run agent/skills/agentforge/scripts/download_template.py --source "github:org/templates/name"
   ```

2. **从角色配置生成**:
   ```bash
   uv run agent/skills/agentforge/scripts/generate_from_roles.py --config agent/skills/taskarena/config.yaml
   ```

3. **手动创建** (遵循 GitAgent 格式):
   ```
   agent-name/
   ├── agent.yaml
   └── SOUL.md
   ```

## 注意

- `_generated/` 子目录下的文件会被 .gitignore 忽略
- 手动创建的模板会被 git 追踪

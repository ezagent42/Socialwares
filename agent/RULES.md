# 开发约束

## 必须

- 所有 Python 代码必须使用 type hints
- 所有 API 必须映射到四原语 (Role/Flow/Commitment/Arena)
- 使用 uv 管理 Python 依赖，不使用 pip
- 每个 App 必须有 tests/ 目录和 >90% 覆盖率
- config.yaml 中的 roles/flows/commitments 必须与 .socialware.md 定义一致

## 禁止

- 不使用 pip/npm/npx (使用 uv/pnpm)
- 不在 agent/agents/ 手动创建文件 (通过 AgentForge scripts 生成)
- 不硬编码 API URL (使用 config.yaml)
- 不跳过 pre_send 权限检查

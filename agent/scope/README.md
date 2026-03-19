# Scope — Where

定义 App 级别的能力声明。

## 文件

- `SOUL.md` — Agent 能力声明
  - 对内: 定义 Agent 操作边界
  - 对外: 公开描述，供其他 Agent 读取

## deploy.sh 处理

`scope/SOUL.md` 会与每个 `role/{name}/SOUL.md` 合并，
生成该 role 专属的完整 SOUL.md。

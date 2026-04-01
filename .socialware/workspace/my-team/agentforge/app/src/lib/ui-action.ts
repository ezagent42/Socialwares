export interface UIAction {
  entity: string;
  action: string;
  targets: TargetItem[];
  context?: Record<string, any>;
}

export interface TargetItem {
  id: string;
  name: string;
  entity: string;
  [key: string]: any;
}

export function serializeUIAction(action: UIAction): string {
  return `\`\`\`ui_action\n${JSON.stringify(action, null, 2)}\n\`\`\``;
}

export function formatUIActionDisplay(action: UIAction): string {
  const names = action.targets.map((t) => t.name).join(", ");
  const count = action.targets.length;

  if (action.entity === "_dialog") {
    return action.action === "confirm" ? "确认" : "取消";
  }

  if (count === 0) return action.action;
  if (count === 1) return `${action.action} ${action.entity}: ${names}`;
  return `${action.action} ${count} 个 ${action.entity}: ${names}`;
}

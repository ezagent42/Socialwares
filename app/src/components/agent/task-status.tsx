import type { TaskStatus } from "@/types";
import { Badge } from "@/components/ui/badge";
import type { BadgeProps } from "@/components/ui/badge";

const STATUS_VARIANT: Record<TaskStatus, BadgeProps["variant"]> = {
  open: "outline",
  in_progress: "warning",
  submitted: "secondary",
  completed: "success",
  cancelled: "destructive",
};

const STATUS_LABEL: Record<TaskStatus, string> = {
  open: "Open",
  in_progress: "In Progress",
  submitted: "Submitted",
  completed: "Completed",
  cancelled: "Cancelled",
};

export function TaskStatusBadge({ status }: { status: TaskStatus }) {
  return (
    <Badge variant={STATUS_VARIANT[status]}>
      {STATUS_LABEL[status]}
    </Badge>
  );
}

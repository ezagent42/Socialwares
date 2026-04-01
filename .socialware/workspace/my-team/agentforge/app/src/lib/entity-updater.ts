import type { EntityStore, StructuredData } from "./types";

export function updateEntities(current: EntityStore, event: StructuredData): EntityStore {
  const next = { ...current };
  const { type, action, data } = event;

  switch (type) {
    case "agent":
      if (action === "created" || action === "updated") {
        next.agents = { ...next.agents, [data.id]: data };
      } else if (action === "deleted") {
        const { [data.id]: _, ...rest } = next.agents;
        next.agents = rest;
      } else if (action === "listed") {
        next.agents = {};
        for (const agent of data.agents ?? []) {
          next.agents[agent.id] = agent;
        }
      }
      break;

    case "role":
      if (action === "created" || action === "updated") {
        next.roles = { ...next.roles, [data.id]: data };
      } else if (action === "deleted") {
        const { [data.id]: _, ...rest } = next.roles;
        next.roles = rest;
      } else if (action === "listed") {
        const otherRoles = Object.fromEntries(
          Object.entries(next.roles).filter(([, r]: [string, any]) => r.agent_id !== data.agent_id)
        );
        next.roles = { ...otherRoles };
        for (const role of data.roles ?? []) {
          next.roles[role.id] = { ...role, agent_id: data.agent_id };
        }
      }
      break;

    case "skill":
      if (action === "created" || action === "updated") {
        next.skills = { ...next.skills, [data.id]: data };
      } else if (action === "deleted") {
        const { [data.id]: _, ...rest } = next.skills;
        next.skills = rest;
      } else if (action === "listed") {
        const otherSkills = Object.fromEntries(
          Object.entries(next.skills).filter(([, s]: [string, any]) => s.agent_id !== data.agent_id)
        );
        next.skills = { ...otherSkills };
        for (const skill of data.skills ?? []) {
          next.skills[skill.id] = { ...skill, agent_id: data.agent_id };
        }
      }
      break;
  }

  return next;
}

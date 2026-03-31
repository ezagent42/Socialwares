# Socialware App

This is a Socialware App template.

## Capabilities

- Health check (/health)
- (Add your App capabilities here)

## Boundaries

- (What the Agent should NOT do)
- (Participation rules: who can join, minimum members)

## Connections

- (External Apps this App can delegate to via /zchat)


---

# Default Agent

Default app user role.

## Identity

- Role: default
- Permissions: all operations

## Responsibilities

Operate the App according to user instructions.


---

## Workflows
### task_lifecycle (resource: task)
  draft → submit_task (by default) → submitted
  submitted → review_task (by reviewer) → reviewed
  reviewed → close_task (by default) → closed


---

## Backend

API: http://localhost:8001

"""CLI interface for CRUD operations — called by Agent via Bash tool."""
import argparse
import asyncio
import json
import sys

from src.db import Database
from src.crud import agent_crud, skill_crud


async def cmd_create_agent(args):
    db = Database(args.db)
    await db.init()
    result = await agent_crud.create_agent(db, args.user_id, args.name, args.description or "", args.role_md or "")
    print(json.dumps(result, ensure_ascii=False))


async def cmd_list_agents(args):
    db = Database(args.db)
    await db.init()
    result = await agent_crud.list_agents(db, args.user_id)
    print(json.dumps(result, ensure_ascii=False))


async def cmd_get_agent(args):
    db = Database(args.db)
    await db.init()
    result = await agent_crud.get_agent(db, args.user_id, args.agent_id)
    print(json.dumps(result, ensure_ascii=False))


async def cmd_delete_agent(args):
    db = Database(args.db)
    await db.init()
    result = await agent_crud.delete_agent(db, args.user_id, args.agent_id)
    print(json.dumps(result, ensure_ascii=False))


async def cmd_create_skill(args):
    db = Database(args.db)
    await db.init()
    result = await skill_crud.create_skill(db, args.agent_id, args.name, args.skill_md or "", args.description or "")
    print(json.dumps(result, ensure_ascii=False))


async def cmd_list_skills(args):
    db = Database(args.db)
    await db.init()
    result = await skill_crud.list_skills(db, args.agent_id)
    print(json.dumps(result, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(prog="crud-cli")
    sub = parser.add_subparsers(dest="command")

    p = sub.add_parser("create-agent")
    p.add_argument("--db", required=True)
    p.add_argument("--user-id", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--description", default="")
    p.add_argument("--role-md", default="")

    p = sub.add_parser("list-agents")
    p.add_argument("--db", required=True)
    p.add_argument("--user-id", required=True)

    p = sub.add_parser("get-agent")
    p.add_argument("--db", required=True)
    p.add_argument("--user-id", required=True)
    p.add_argument("--agent-id", required=True)

    p = sub.add_parser("delete-agent")
    p.add_argument("--db", required=True)
    p.add_argument("--user-id", required=True)
    p.add_argument("--agent-id", required=True)

    p = sub.add_parser("create-skill")
    p.add_argument("--db", required=True)
    p.add_argument("--agent-id", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--skill-md", default="")
    p.add_argument("--description", default="")

    p = sub.add_parser("list-skills")
    p.add_argument("--db", required=True)
    p.add_argument("--agent-id", required=True)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    cmd_map = {
        "create-agent": cmd_create_agent,
        "list-agents": cmd_list_agents,
        "get-agent": cmd_get_agent,
        "delete-agent": cmd_delete_agent,
        "create-skill": cmd_create_skill,
        "list-skills": cmd_list_skills,
    }
    asyncio.run(cmd_map[args.command](args))


if __name__ == "__main__":
    main()

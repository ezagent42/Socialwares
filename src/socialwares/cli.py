"""CLI 占位 — Phase 3 实现完整命令。"""

import click


@click.group()
def main() -> None:
    """Socialwares — 构建 Socialware App 的框架。"""


@main.command()
@click.argument("name")
def new(name: str) -> None:
    """创建新项目。"""
    click.echo(f"TODO: socialwares new {name}")


@main.command()
def deploy() -> None:
    """编译四原语。"""
    click.echo("TODO: socialwares deploy")

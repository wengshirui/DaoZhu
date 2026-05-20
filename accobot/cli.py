"""AccoBot CLI — interactive command-line interface.

Usage:
    accobot          # Start interactive chat
    accobot web      # Start web UI
"""

import sys

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory

from accobot import __version__
from accobot.config import ensure_home, load_config, load_env
from accobot.agent import AccoAgent

console = Console()


def print_banner():
    """Print the AccoBot welcome banner."""
    banner = f"""[bold gold1]AccoBot[/bold gold1] v{__version__} — 智能财务助手
[dim]输入财务相关问题开始对话，输入 /help 查看命令，输入 /quit 退出[/dim]"""
    console.print(Panel(banner, border_style="gold1"))


def handle_command(cmd: str, agent: AccoAgent) -> bool:
    """Handle slash commands. Returns True if should continue, False to exit."""
    cmd = cmd.strip().lower()

    if cmd in ("/quit", "/exit", "/q"):
        console.print("[dim]再见！[/dim]")
        return False
    elif cmd in ("/help", "/h"):
        help_text = """
**可用命令：**
- `/new` — 开始新对话
- `/history` — 查看对话历史
- `/config` — 查看当前配置
- `/help` — 显示帮助
- `/quit` — 退出
"""
        console.print(Markdown(help_text))
    elif cmd == "/new":
        agent.reset()
        console.print("[green]✓ 已开始新对话[/green]")
    elif cmd == "/history":
        history = agent.get_history()
        if not history:
            console.print("[dim]暂无对话历史[/dim]")
        else:
            for msg in history[-10:]:  # Show last 10 messages
                role = msg["role"]
                content = msg.get("content", "")
                if role == "user":
                    console.print(f"[bold blue]你：[/bold blue]{content}")
                elif role == "assistant" and content:
                    console.print(f"[bold green]Bot：[/bold green]{content[:100]}...")
    elif cmd == "/config":
        from accobot.config import load_config
        import yaml
        config = load_config()
        console.print(Panel(yaml.dump(config, allow_unicode=True), title="当前配置"))
    else:
        console.print(f"[yellow]未知命令：{cmd}，输入 /help 查看可用命令[/yellow]")

    return True


def run_interactive():
    """Run the interactive CLI chat loop."""
    # Setup
    home = ensure_home()
    load_env()
    config = load_config()

    print_banner()

    # Initialize agent
    def on_token(token: str):
        console.print(token, end="", highlight=False)

    agent = AccoAgent(config=config, on_token=on_token)

    # Setup prompt with history
    history_file = home / "cli_history"
    session = PromptSession(history=FileHistory(str(history_file)))

    while True:
        try:
            user_input = session.prompt("\n💬 > ").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]再见！[/dim]")
            break

        if not user_input:
            continue

        # Handle slash commands
        if user_input.startswith("/"):
            if not handle_command(user_input, agent):
                break
            continue

        # Chat with agent
        console.print()  # newline before response
        try:
            response = agent.chat(user_input)
            console.print()  # newline after streaming
        except Exception as e:
            console.print(f"\n[red]错误：{e}[/red]")


def main():
    """Main entry point."""
    args = sys.argv[1:]

    if not args:
        run_interactive()
    elif args[0] == "web":
        # Start web UI
        from accobot.web.server import start_server
        host = "127.0.0.1"
        port = 9120
        # Parse optional --port flag
        if "--port" in args:
            idx = args.index("--port")
            if idx + 1 < len(args):
                port = int(args[idx + 1])
        start_server(host=host, port=port)
    elif args[0] == "version":
        console.print(f"AccoBot v{__version__}")
    else:
        console.print(f"[yellow]未知命令：{args[0]}[/yellow]")
        console.print("用法：accobot [web|version]")


if __name__ == "__main__":
    main()

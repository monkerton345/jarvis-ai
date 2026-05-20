"""
Jarvis terminal UI using Rich.
Gives a clean, iron man-inspired console interface.
"""
import sys
import time
from datetime import datetime
from typing import Optional

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    from rich.live import Live
    from rich.columns import Columns
    from rich.align import Align
    from rich.rule import Rule
    from rich.theme import Theme
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# Iron Man / HUD color theme
JARVIS_THEME = {
    "jarvis.primary": "bright_cyan",
    "jarvis.secondary": "cyan",
    "jarvis.accent": "bright_white",
    "jarvis.dim": "grey54",
    "jarvis.user": "bright_white",
    "jarvis.response": "bright_cyan",
    "jarvis.system": "grey50",
    "jarvis.warning": "yellow",
    "jarvis.error": "red",
    "jarvis.success": "green",
}

JARVIS_BANNER = r"""
     ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗
     ██║██╔══██╗██╔══██╗██║   ██║██║██╔════╝
     ██║███████║██████╔╝██║   ██║██║███████╗
██   ██║██╔══██║██╔══██╗╚██╗ ██╔╝██║╚════██║
╚█████╔╝██║  ██║██║  ██║ ╚████╔╝ ██║███████║
 ╚════╝ ╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝
    Just A Rather Very Intelligent System
"""


class JarvisUI:
    def __init__(self, debug: bool = False):
        self.debug = debug
        if RICH_AVAILABLE:
            theme = Theme(JARVIS_THEME)
            self._console = Console(theme=theme, highlight=False)
        else:
            self._console = None

    def print_banner(self):
        if self._console:
            self._console.print(
                Panel(
                    Align.center(Text(JARVIS_BANNER, style="jarvis.primary")),
                    border_style="jarvis.secondary",
                    padding=(0, 2),
                )
            )
            self._console.print(
                Align.center(
                    Text(
                        f"v1.0  |  {datetime.now().strftime('%A, %B %d %Y')}  |  STARK INDUSTRIES",
                        style="jarvis.dim",
                    )
                )
            )
            self._console.print(Rule(style="jarvis.dim"))
        else:
            print("=" * 60)
            print("  J.A.R.V.I.S. — Just A Rather Very Intelligent System")
            print("=" * 60)

    def status(self, message: str, icon: str = "●"):
        ts = datetime.now().strftime("%H:%M:%S")
        if self._console:
            self._console.print(f"[jarvis.dim][{ts}][/] [jarvis.secondary]{icon}[/] [jarvis.dim]{message}[/]")
        else:
            print(f"[{ts}] {icon} {message}")

    def user_input_prompt(self) -> str:
        """Show input prompt and return user text input."""
        if self._console:
            self._console.print("\n[jarvis.dim]───────────────────────────────────────[/]")
            try:
                from rich.prompt import Prompt
                return Prompt.ask("[jarvis.accent]You[/]")
            except KeyboardInterrupt:
                return "exit"
        else:
            return input("\nYou: ").strip()

    def show_listening(self):
        if self._console:
            self._console.print("[jarvis.secondary]◉ Listening...[/]")
        else:
            print("◉ Listening...")

    def show_thinking(self):
        if self._console:
            self._console.print("[jarvis.dim]◌ Processing...[/]")
        else:
            print("◌ Processing...")

    def show_speaking(self):
        if self._console:
            self._console.print("[jarvis.dim]◎ Speaking...[/]")
        else:
            print("◎ Speaking...")

    def jarvis_response(self, text: str):
        """Display Jarvis's response."""
        if self._console:
            self._console.print(
                Panel(
                    Text(text, style="jarvis.response"),
                    title="[jarvis.secondary]J.A.R.V.I.S.[/]",
                    border_style="jarvis.secondary",
                    padding=(0, 1),
                )
            )
        else:
            print(f"\nJARVIS: {text}\n")

    def error(self, message: str):
        if self._console:
            self._console.print(f"[jarvis.error]✗ {message}[/]")
        else:
            print(f"ERROR: {message}")

    def warn(self, message: str):
        if self._console:
            self._console.print(f"[jarvis.warning]⚠ {message}[/]")
        else:
            print(f"WARNING: {message}")

    def success(self, message: str):
        if self._console:
            self._console.print(f"[jarvis.success]✓ {message}[/]")
        else:
            print(f"OK: {message}")

    def print_help(self):
        help_text = (
            "VOICE COMMANDS\n"
            "  Say 'Jarvis' or press Ctrl+Shift+J to activate\n\n"
            "TEXT MODE\n"
            "  Type anything — Jarvis will respond\n\n"
            "SPECIAL COMMANDS\n"
            "  clear       — Clear conversation history\n"
            "  voice on/off — Toggle voice input\n"
            "  mode text   — Switch to text-only mode\n"
            "  mode voice  — Switch to voice mode\n"
            "  help        — Show this message\n"
            "  exit/quit   — Shut down Jarvis\n"
        )
        if self._console:
            self._console.print(Panel(help_text, title="[jarvis.secondary]Help[/]", border_style="jarvis.dim"))
        else:
            print(help_text)

"""Output formatting for glam CLI."""

from __future__ import annotations

import json
import sys
from typing import Any

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    HAS_RICH = True
except ImportError:  # pragma: no cover - dependency is required at runtime
    HAS_RICH = False


class OutputFormatter:
    """Handles all output formatting (rich or plain/JSON)."""

    def __init__(self, json_output: bool = False, quiet: bool = False) -> None:
        self.json = json_output
        self.quiet = quiet
        self.console: Console | None = Console() if HAS_RICH and not json_output else None

    def _output(self, data: Any) -> None:
        """Output data in appropriate format."""
        if self.quiet:
            return

        if self.json:
            print(json.dumps(data, indent=2, default=str))
            return

        if self.console:
            return

        if isinstance(data, dict):
            for key, value in data.items():
                print(f"{key}: {value}")
            return

        print(data)

    def info(self, message: str) -> None:
        """Info message."""
        if self.quiet:
            return

        if self.json:
            print(json.dumps({"type": "info", "message": message}))
        elif self.console:
            self.console.print(f"[blue]INFO[/blue] {message}")
        else:
            print(f"INFO {message}")

    def success(self, message: str) -> None:
        """Success message."""
        if self.quiet:
            return

        if self.json:
            print(json.dumps({"type": "success", "message": message}))
        elif self.console:
            self.console.print(f"[green]OK[/green] {message}")
        else:
            print(f"OK {message}")

    def error(self, message: str) -> None:
        """Error message."""
        if self.json:
            print(json.dumps({"type": "error", "message": message}), file=sys.stderr)
        elif self.console:
            self.console.print(f"[red]ERROR[/red] {message}", style="red")
        else:
            print(f"ERROR {message}", file=sys.stderr)

    def warning(self, message: str) -> None:
        """Warning message."""
        if self.quiet:
            return

        if self.json:
            print(json.dumps({"type": "warning", "message": message}))
        elif self.console:
            self.console.print(f"[yellow]WARN[/yellow] {message}")
        else:
            print(f"WARN {message}")

    def user_info(self, user: dict[str, Any]) -> None:
        """Display user information."""
        if self.json:
            print(json.dumps(user, indent=2, default=str))
            return

        if self.console:
            table = Table(title="Account Information", show_header=False)
            table.add_column("Field", style="cyan")
            table.add_column("Value", style="white")

            for key, value in user.items():
                display_key = key.replace("_", " ").title()
                table.add_row(display_key, str(value))

            self.console.print(table)
            return

        print("Account Information:")
        print("-" * 20)
        for key, value in user.items():
            print(f"  {key}: {value}")

    def download_progress(self, current: int, total: int | None, item: str) -> None:
        """Show download progress."""
        if self.quiet or self.json:
            return

        if total:
            pct = (current / total) * 100
            message = f"[{current}/{total}] {pct:.1f}% - {item}"
        else:
            message = f"[{current}] {item}"

        if self.console:
            self.console.print(message, end="\r")
        else:
            print(message, end="\r", flush=True)

    def download_complete(self, count: int, directory: str) -> None:
        """Show download completion summary."""
        if self.quiet:
            return

        if self.json:
            print(
                json.dumps(
                    {
                        "type": "complete",
                        "count": count,
                        "directory": directory,
                    }
                )
            )
            return

        if self.console:
            self.console.print(
                Panel(
                    f"Downloaded [green]{count}[/green] items to\n[blue]{directory}[/blue]",
                    title="Complete",
                    border_style="green",
                )
            )
            return

        print(f"\nDownloaded {count} items to {directory}")

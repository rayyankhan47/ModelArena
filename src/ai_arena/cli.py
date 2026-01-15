"""Command-line interface for AI Arena."""

import typer
from rich.console import Console

app = typer.Typer()
console = Console()


@app.command()
def run(
    seed: str = typer.Option(None, help="Match seed for reproducible games"),
    rounds: int = typer.Option(None, help="Number of rounds to play"),
):
    """Run a live AI Arena match with Pygame visualization."""
    console.print("[bold blue]AI Arena[/bold blue] - Starting live match...")
    console.print("This is a stub - engine and orchestrator not yet implemented.")
    # TODO: Implement live match runner


@app.command()
def replay(
    match_id: str = typer.Argument(..., help="Match ID to replay"),
    speed: float = typer.Option(1.0, help="Playback speed multiplier"),
):
    """Replay a previously recorded match."""
    console.print(f"[bold blue]AI Arena[/bold blue] - Replaying match {match_id}...")
    console.print("This is a stub - replay system not yet implemented.")
    # TODO: Implement replay runner


@app.callback()
def callback():
    """AI Arena: Multi-agent competitive LLM reasoning using Backboard."""
    pass


if __name__ == "__main__":
    app()
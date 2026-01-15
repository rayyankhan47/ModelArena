"""Command-line interface for AI Arena."""

import typer
from rich.console import Console

from ai_arena.ui.pygame_app import run_demo

app = typer.Typer()
console = Console()


@app.command()
def run(
    seed: str = typer.Option(None, help="Match seed for reproducible games"),
    rounds: int = typer.Option(None, help="Number of rounds to play"),
    speed: float = typer.Option(1.0, help="Seconds per round (lower is faster)"),
    windowed: bool = typer.Option(False, help="Run in a window instead of fullscreen"),
):
    """Run a live AI Arena match with Pygame visualization."""
    console.print("[bold blue]AI Arena[/bold blue] - Starting live match...")
    run_demo(
        seed=seed or "demo_1",
        rounds=rounds or 15,
        speed=max(0.1, speed),
        fullscreen=not windowed,
    )


@app.command()
def replay(
    match_id: str = typer.Argument(..., help="Match ID to replay"),
    speed: float = typer.Option(1.0, help="Playback speed multiplier"),
):
    """Replay a previously recorded match."""
    console.print(f"[bold blue]AI Arena[/bold blue] - Replaying match {match_id}...")
    try:
        from ai_arena.storage.replay import replay_match
        replay_match(match_id, speed)
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@app.callback()
def callback():
    """AI Arena: Multi-agent competitive LLM reasoning using Backboard."""
    pass


if __name__ == "__main__":
    app()
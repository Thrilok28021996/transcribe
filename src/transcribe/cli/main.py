"""Command-line interface for Transcribe AI platform."""

from __future__ import annotations

import asyncio
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from transcribe import __version__
from transcribe.application.container import ServiceContainer
from transcribe.application.services import MeetingService
from transcribe.infrastructure.config import load_config
from transcribe.infrastructure.logging import setup_logging

console = Console()


@click.group()
@click.option("--config", "-c", type=click.Path(exists=True), help="Path to config YAML file.")
@click.option("--verbose", "-v", is_flag=True, help="Enable debug log output.")
@click.pass_context
def cli(ctx: click.Context, config: str | None, verbose: bool) -> None:
    """Transcribe AI — Local-first AI Meeting Memory Platform."""
    log_level = "DEBUG" if verbose else "INFO"
    setup_logging(level=log_level)

    app_config = load_config(config_path=config)
    if verbose:
        app_config.debug = True

    ctx.obj = ServiceContainer(config=app_config)


@cli.command()
def version() -> None:
    """Display software version."""
    console.print(f"[bold green]Transcribe AI[/bold green] v{__version__}")


@cli.command()
@click.pass_obj
def config_show(container: ServiceContainer) -> None:
    """Display current system configuration."""
    cfg = container.config
    table = Table(title="System Configuration", show_header=True, header_style="bold magenta")
    table.add_column("Category", style="cyan")
    table.add_column("Property", style="bold")
    table.add_column("Value", style="green")

    table.add_row("App", "environment", cfg.environment)
    table.add_row("App", "debug", str(cfg.debug))
    table.add_row("Speech", "provider", cfg.speech.provider)
    table.add_row("Speech", "model_size", cfg.speech.model_size)
    table.add_row("Diarization", "provider", cfg.diarization.provider)
    table.add_row("LLM", "provider", cfg.llm.provider)
    table.add_row("LLM", "model_name", cfg.llm.model_name)
    table.add_row("Vector Store", "provider", cfg.vector_store.provider)
    table.add_row("Storage", "markdown_dir", str(cfg.storage.markdown_dir))

    console.print(table)


@cli.command()
@click.pass_obj
def plugins_list(container: ServiceContainer) -> None:
    """List registered AI plugin interfaces and available implementations."""
    table = Table(title="Registered AI Plugins", show_header=True, header_style="bold cyan")
    table.add_column("Interface Role", style="yellow")
    table.add_column("Available Implementations", style="green")
    table.add_column("Active Provider", style="magenta")

    table.add_row(
        "SpeechRecognizer",
        ", ".join(container.speech_recognizers.list_plugins()),
        container.config.speech.provider,
    )
    table.add_row(
        "AlignmentEngine",
        ", ".join(container.alignment_engines.list_plugins()),
        "mock",
    )
    table.add_row(
        "DiarizationEngine",
        ", ".join(container.diarization_engines.list_plugins()),
        container.config.diarization.provider,
    )
    table.add_row(
        "SpeakerIdentifier",
        ", ".join(container.speaker_identifiers.list_plugins()),
        "mock",
    )
    table.add_row(
        "KnowledgeExtractor",
        ", ".join(container.knowledge_extractors.list_plugins()),
        container.config.llm.provider,
    )
    table.add_row(
        "MarkdownExporter",
        ", ".join(container.markdown_exporters.list_plugins()),
        "mock",
    )
    table.add_row(
        "EmbeddingProvider",
        ", ".join(container.embedding_providers.list_plugins()),
        container.config.vector_store.provider,
    )
    table.add_row(
        "LLMProvider",
        ", ".join(container.llm_providers.list_plugins()),
        container.config.llm.provider,
    )

    console.print(table)


@cli.command()
@click.argument("audio_path", type=click.Path(exists=True))
@click.option("--title", "-t", help="Custom title for the meeting.")
@click.option("--provider", "-p", help="Speech recognition provider override.")
@click.pass_obj
def process(container: ServiceContainer, audio_path: str, title: str | None, provider: str | None) -> None:
    """Run meeting memory processing pipeline on an audio file."""
    if provider:
        container.config.speech.provider = provider
    service = MeetingService(container=container)

    console.print(f"[bold blue]Processing audio file:[bold blue] {audio_path}")

    async def _run() -> None:
        result = await service.process_meeting(audio_path=audio_path, title=title)

        panel_content = (
            f"[bold green]Meeting Title:[/bold green] {result.meeting.title}\n"
            f"[bold green]Decisions Extracted:[/bold green] {len(result.extraction.decisions)}\n"
            f"[bold green]Tasks Extracted:[/bold green] {len(result.extraction.tasks)}\n"
            f"[bold green]Markdown Exported:[/bold green] [bold underline]{result.markdown_path}[/bold underline]\n"
        )
        console.print(Panel(panel_content, title="Processing Summary", border_style="green"))

    asyncio.run(_run())


@cli.command()
@click.argument("query", type=str)
@click.option("--top-k", "-k", default=5, help="Number of top semantic matches to retrieve.")
@click.pass_obj
def search(container: ServiceContainer, query: str, top_k: int) -> None:
    """Perform cross-meeting semantic search over indexed meetings and knowledge."""
    from transcribe.application.services.search_service import SearchService

    search_service = SearchService(container=container)

    async def _run_search() -> None:
        res = await search_service.search(query=query, top_k=top_k)

        table = Table(title=f"Semantic Search Results for: '{query}'", show_header=True)
        table.add_column("Type", style="cyan")
        table.add_column("Score", style="green")
        table.add_column("Matched Content", style="white")

        for match in res.matches:
            table.add_row(match.doc_type.upper(), f"{match.score:.2f}", match.text)

        console.print(table)

        if res.graph_context:
            console.print("\n[bold yellow]Related Knowledge Graph Context:[/bold yellow]")
            for ctx in res.graph_context:
                console.print(f"  • {ctx}")

    asyncio.run(_run_search())


@cli.command()
@click.argument("question", type=str)
@click.option("--top-k", "-k", default=5, help="Number of retrieved context chunks.")
@click.pass_obj
def ask(container: ServiceContainer, question: str, top_k: int) -> None:
    """Ask questions about past meetings, decisions, and tasks using local RAG."""
    from transcribe.application.services.assistant_service import RAGAssistantService

    assistant = RAGAssistantService(container=container)

    console.print(f"[bold cyan]Querying Meeting Memory:[bold cyan] '{question}'")

    async def _run_ask() -> None:
        result = await assistant.ask(question=question, top_k=top_k)

        panel = Panel(
            result.answer,
            title="[bold green]AI Assistant Answer[/bold green]",
            border_style="green",
        )
        console.print(panel)

        if result.sources:
            table = Table(title="Retrieved Source Citations", show_header=True)
            table.add_column("Type", style="yellow")
            table.add_column("Relevance Score", style="green")
            table.add_column("Source Snippet", style="white")

            for src in result.sources:
                table.add_row(src.doc_type.upper(), f"{src.score:.2f}", src.text)

            console.print(table)

@cli.command()
def audio_devices() -> None:
    """Inspect local audio hardware & system loopback hooks for Teams/Zoom capture."""
    from transcribe.infrastructure.system_audio_hook import SystemAudioHook

    hook = SystemAudioHook()
    devices = hook.list_devices()
    status = hook.get_setup_status()

    table = Table(title="Detected System Audio & Loopback Devices", show_header=True, header_style="bold cyan")
    table.add_column("Device ID", style="yellow")
    table.add_column("Device Name", style="bold white")
    table.add_column("Category", style="magenta")
    table.add_column("Platform", style="green")

    for dev in devices:
        table.add_row(dev.id, dev.name, dev.kind.upper(), dev.platform)

    console.print(table)

    status_color = "green" if status.is_ready else "yellow"
    console.print(f"\n[bold {status_color}]Teams/Zoom Call Capture Diagnostics:[/bold {status_color}]")
    for rec in status.recommendations:
        console.print(f"  • {rec}")


@cli.command()
@click.option("--duration", "-d", default=10, help="Recording duration in seconds.")
@click.option("--title", "-t", default=None, help="Optional meeting title.")
@click.option(
    "--mode", "-m",
    type=click.Choice(["mic", "system", "mixed"]),
    default="mixed",
    help="Audio capture mode: 'mic' (microphone only), 'system' (Teams call output), or 'mixed' (both).",
)
@click.option("--mic-device", help="Specific microphone device ID or name.")
@click.option("--system-device", help="Specific system loopback device ID or name (e.g. BlackHole/Loopback).")
@click.pass_obj
def record(
    container: ServiceContainer,
    duration: int,
    title: str | None,
    mode: str,
    mic_device: str | None,
    system_device: str | None,
) -> None:
    """Record live microphone and/or Teams system call audio and process meeting memory."""
    from datetime import datetime
    from transcribe.application.services.meeting_service import MeetingService
    from transcribe.infrastructure.system_audio_hook import SystemAudioHook

    rec_dir = container.config.storage.recordings_dir
    rec_dir.mkdir(parents=True, exist_ok=True)
    timestamp_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    out_file = rec_dir / f"meeting_{timestamp_str}.wav"

    console.print(f"[bold red]🔴 Recording live meeting audio ({mode.upper()} mode) for {duration} seconds...[/bold red]")
    console.print(f"[dim]Saving to {out_file}[/dim]")

    hook = SystemAudioHook()
    try:
        recorded_path = hook.record(
            output_path=out_file,
            duration_seconds=duration,
            mode=mode,  # type: ignore
            mic_device=mic_device,
            system_device=system_device,
        )
        console.print("[bold green]✓ Live audio capture complete![/bold green]")
    except Exception as err:
        console.print(f"[bold red]Recording failed: {err}[/bold red]")
        return

    console.print("[bold cyan]Processing meeting recording into memory...[/bold cyan]")
    service = MeetingService(container=container)

    async def _run_proc() -> None:
        meeting_title = title or f"Live Meeting Call ({mode.title()}, {duration}s)"
        result = await service.process_meeting(audio_path=recorded_path, title=meeting_title)
        console.print(f"[bold green]✓ Meeting processed![/bold green] Notes at [yellow]{result.markdown_path}[/yellow]")

    asyncio.run(_run_proc())



@cli.command()
@click.option("--host", "-h", default="127.0.0.1", help="Host IP to bind web server.")
@click.option("--port", "-p", default=8000, help="Port to run web server.")
@click.pass_obj
def serve(container: ServiceContainer, host: str, port: int) -> None:
    """Launch Transcribe AI Web UX Application Server."""
    import uvicorn
    from transcribe.web.app import create_app

    app = create_app(container=container)

    console.print(f"[bold green]Starting Transcribe AI Web UX Server...[/bold green]")
    console.print(f"[bold underline blue]http://{host}:{port}[/bold underline blue]")

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    cli()

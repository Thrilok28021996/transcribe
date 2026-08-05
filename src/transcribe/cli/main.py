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
@click.option("--stt-model", help="STT Whisper model size (e.g. large-v3-turbo, medium, small, base, tiny).")
@click.option("--stt-device", help="STT compute device (auto, mps, cuda, cpu).")
@click.option("--stt-provider", help="Speech recognition provider (faster-whisper, mock).")
@click.option("--llm-model", help="Local LLM model name (e.g. default, qwen2.5-7b-instruct).")
@click.option("--llm-provider", help="LLM provider (lm-studio, ollama, mock).")
@click.option("--llm-base", help="LM Studio API Base URL (e.g. http://localhost:1234/v1).")
@click.pass_obj
def config_set(
    container: ServiceContainer,
    stt_model: str | None,
    stt_device: str | None,
    stt_provider: str | None,
    llm_model: str | None,
    llm_provider: str | None,
    llm_base: str | None,
) -> None:
    """Update active STT and LM Studio local model settings."""
    from transcribe.infrastructure.config import save_config

    cfg = container.config
    updated = False

    if stt_model:
        cfg.speech.model_size = stt_model
        updated = True
    if stt_device:
        cfg.speech.device = stt_device  # type: ignore
        updated = True
    if stt_provider:
        cfg.speech.provider = stt_provider
        updated = True
    if llm_model:
        cfg.llm.model_name = llm_model
        updated = True
    if llm_provider:
        cfg.llm.provider = llm_provider
        updated = True
    if llm_base:
        cfg.llm.api_base = llm_base
        updated = True

    if updated:
        save_config(cfg)
        container.reload_plugins()
        console.print("[bold green]✓ Configuration updated and saved to transcribe.yaml[/bold green]")
    else:
        console.print("[yellow]No settings specified. Pass options like --stt-model large-v3-turbo --llm-model qwen2.5-7b[/yellow]")


@cli.command()
@click.option("--all", "-a", "delete_all", is_flag=True, help="Full reset: delete all recordings, meetings, vectors, speakers, and markdown notes.")
@click.option("--recordings-only", "-r", is_flag=True, help="Delete only accumulated raw audio recording files.")
@click.pass_obj
def cleanup(container: ServiceContainer, delete_all: bool, recordings_only: bool) -> None:
    """Clean up accumulated raw audio recordings and temporary storage files."""
    from transcribe.infrastructure.config import cleanup_storage

    res = cleanup_storage(container.config, delete_recordings=True, delete_all=delete_all)
    if delete_all:
        from transcribe.application.services.search_service import SearchService
        search_svc = SearchService(container=container)
        search_svc.vector_store.clear()
        search_svc.graph_store.clear()
        if hasattr(container.speaker_db, "clear"):
            container.speaker_db.clear()


    freed_mb = round(res["freed_bytes"] / (1024 * 1024), 2)
    deleted_count = res["deleted_files"]

    if delete_all:
        console.print(f"[bold red]🧹 Full data cleanup complete![/bold red] Removed {deleted_count} files ({freed_mb} MB freed). Storage reset.")
    else:
        console.print(f"[bold green]🧹 Raw recordings cleanup complete![/bold green] Removed {deleted_count} audio files ({freed_mb} MB freed).")


@cli.command()
@click.pass_obj
def speakers(container: ServiceContainer) -> None:
    """List all registered persistent speaker profiles."""
    from rich.table import Table
    spks = container.speaker_db.list_speakers()
    if not spks:
        console.print("[dim]No registered speaker profiles.[/dim]")
        return

    table = Table(title="Tracked Speaker Profiles")
    table.add_column("Speaker ID", style="cyan")
    table.add_column("Display Name", style="bold green")
    table.add_column("Aliases", style="yellow")
    table.add_column("Embedding", style="blue")
    table.add_column("Meetings", style="magenta")

    for s in spks:
        aliases_str = ", ".join(s.aliases) if s.aliases else "-"
        emb_str = "Active" if s.embedding else "None"
        table.add_row(s.id, s.name, aliases_str, emb_str, str(len(s.confidence_history)))

    console.print(table)


@cli.command()
@click.argument("speaker_id_or_name")
@click.argument("new_name")
@click.option("--alias", "-a", multiple=True, help="Optional alias names for this speaker.")
@click.pass_obj
def speaker_rename(container: ServiceContainer, speaker_id_or_name: str, new_name: str, alias: tuple[str, ...]) -> None:
    """Rename a speaker profile and update aliases."""
    spk = container.speaker_db.get_speaker(speaker_id_or_name) or container.speaker_db.find_by_name(speaker_id_or_name)
    if not spk:
        console.print(f"[bold red]Error:[/bold red] Speaker '{speaker_id_or_name}' not found.")
        return

    aliases_list = list(alias) if alias else None
    updated = container.speaker_db.update_speaker_details(spk.id, name=new_name, aliases=aliases_list)
    console.print(f"[bold green]✅ Speaker updated successfully![/bold green] '{spk.name}' -> [bold cyan]'{updated.name}'[/bold cyan] (ID: {updated.id})")


@cli.command()
@click.argument("audio_file", type=click.Path(exists=True, path_type=Path))
@click.option("--name", "-n", default=None, help="Optional name to assign/enroll if voice is unknown.")
@click.pass_obj
def identify_voice(container: ServiceContainer, audio_file: Path, name: str | None) -> None:
    """Identify speaker voice from an audio sample file and match against local database."""
    import asyncio

    from rich.table import Table

    from transcribe.domain.entities import TranscriptSegment

    console.print(f"[bold blue]🎙️ Analyzing voice sample:[/bold blue] {audio_file.name}")

    speaker_id_engine = container.get_speaker_identifier()
    dummy_seg = TranscriptSegment(meeting_id="sample", start=0.0, end=10.0, text="Voice Sample", speaker_id="SAMPLE")

    matched_name = asyncio.run(speaker_id_engine.identify(dummy_seg, audio_file))
    embedding = speaker_id_engine._extract_voice_embedding(dummy_seg, audio_file)
    match_speaker, score = container.speaker_db.match_voice_embedding(embedding)

    table = Table(title="Voice Identification Analysis")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="bold green")

    table.add_row("Audio File", audio_file.name)
    table.add_row("Identified Speaker", matched_name)

    if match_speaker:
        table.add_row("Match Confidence Score", f"{score * 100:.1f}%")
        table.add_row("Speaker ID", match_speaker.id)
        table.add_row("Known Aliases", ", ".join(match_speaker.aliases) if match_speaker.aliases else "None")
        console.print(table)
        console.print(f"\n[bold green]✅ Matched to existing local profile:[/bold green] [bold cyan]{match_speaker.name}[/bold cyan]")
    else:
        table.add_row("Match Status", "New / Unenrolled Voice")
        console.print(table)
        if name:
            new_name = name.strip()
            container.speaker_db.update_speaker_details(matched_name, name=new_name)
            console.print(f"\n[bold green]👤 Enrolled new voice profile as:[/bold green] [bold cyan]'{new_name}'[/bold cyan]")
        else:
            console.print(f"\n[bold yellow]ℹ️ Voice enrolled as profile:[/bold yellow] '{matched_name}'")
            console.print(f"   Rename anytime via: [dim]transcribe speaker-rename \"{matched_name}\" \"Real Name\"[/dim]")


@cli.command()
@click.pass_obj
def install_cli(container: ServiceContainer) -> None:
    """Install 'transcribe' CLI command symlink into user PATH (~/.local/bin/transcribe)."""
    import sys
    from pathlib import Path

    bin_dir = Path.home() / ".local" / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    target_symlink = bin_dir / "transcribe"

    transcribe_script = Path(sys.argv[0]).resolve()

    try:
        if target_symlink.exists() or target_symlink.is_symlink():
            target_symlink.unlink()

        target_symlink.symlink_to(transcribe_script)
        console.print(f"[bold green]✓ 'transcribe' CLI symlink installed at {target_symlink}[/bold green]")
        console.print("[dim]Ensure ~/.local/bin is in your PATH to run 'transcribe' from any terminal.[/dim]")
    except Exception as err:
        console.print(f"[bold red]Failed to install CLI symlink: {err}[/bold red]")





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

    console.print("[bold green]Starting Transcribe AI Web UX Server...[/bold green]")
    console.print(f"[bold underline blue]http://{host}:{port}[/bold underline blue]")

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    cli()

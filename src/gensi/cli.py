"""Command-line interface for gensi using click."""

import asyncio
import sys
from pathlib import Path
import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from .core.processor import process_gensi_file, ProcessingProgress


console = Console()


@click.group(invoke_without_command=True)
@click.pass_context
@click.version_option(version='0.1.0')
def main(ctx):
    """Gensi - Generate EPUB files from web sources using .gensi recipe files."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@main.command()
@click.argument('files', nargs=-1, type=click.Path(exists=True, path_type=Path), required=True)
@click.option(
    '--output-dir', '-o',
    type=click.Path(file_okay=False, path_type=Path),
    help='Output directory for EPUB files (default: same as input file)'
)
@click.option(
    '--parallel', '-p',
    type=int,
    default=5,
    help='Maximum number of parallel downloads (default: 5)'
)
@click.option(
    '--verbose', '-v',
    is_flag=True,
    help='Verbose output'
)
@click.option(
    '--no-cache',
    is_flag=True,
    help='Disable HTTP caching for this run'
)
def process(files, output_dir, parallel, verbose, no_cache):
    """
    Process one or more .gensi files to generate EPUB files.

    Examples:
        gensi process book.gensi
        gensi process *.gensi
        gensi process book1.gensi book2.gensi --output-dir ./output
    """
    for gensi_file in files:
        gensi_path = Path(gensi_file)

        if not gensi_path.suffix == '.gensi':
            console.print(f"[yellow]Warning: {gensi_path.name} doesn't have .gensi extension, skipping[/yellow]")
            continue

        console.print(f"\n[bold blue]Processing:[/bold blue] {gensi_path.name}")

        # Create progress bar
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            task = progress.add_task("[cyan]Initializing...", total=100)

            def progress_callback(prog: ProcessingProgress):
                if prog.stage == 'parsing':
                    progress.update(task, completed=5, description="[cyan]Parsing .gensi file")
                elif prog.stage == 'cover':
                    progress.update(task, completed=10, description="[cyan]Downloading cover")
                elif prog.stage == 'index':
                    progress.update(task, completed=20, description=f"[cyan]{prog.message}")
                elif prog.stage == 'article':
                    if prog.total > 0:
                        article_progress = 20 + int((prog.current / prog.total) * 60)
                        progress.update(task, completed=article_progress, description=f"[cyan]{prog.message}")
                elif prog.stage == 'building':
                    progress.update(task, completed=85, description="[cyan]Building EPUB")
                elif prog.stage == 'done':
                    progress.update(task, completed=100, description=f"[green]{prog.message}")
                elif prog.stage == 'error':
                    progress.update(task, description=f"[red]Error: {prog.message}")

                if verbose and prog.message:
                    console.print(f"  [dim]{prog.message}[/dim]")

            try:
                # Run async processing
                output_path = asyncio.run(process_gensi_file(
                    gensi_path,
                    output_dir,
                    progress_callback,
                    parallel,
                    cache_enabled=not no_cache
                ))

                console.print(f"[bold green]Success:[/bold green] {output_path}")

            except Exception as e:
                console.print(f"[bold red]Error processing {gensi_path.name}:[/bold red] {str(e)}")
                if verbose:
                    console.print_exception()
                sys.exit(1)


@main.command()
def clear_cache():
    """Clear the HTTP cache."""
    from .core.cache import HttpCache

    try:
        cache = HttpCache()
        stats_before = cache.get_stats()
        cache.clear()
        cache.close()

        console.print(f"[green]Cache cleared successfully![/green]")
        console.print(f"  Removed {stats_before['entry_count']} entries")
        console.print(f"  Freed {stats_before['size_bytes'] / 1024 / 1024:.2f} MB")
    except Exception as e:
        console.print(f"[red]Error clearing cache:[/red] {str(e)}")
        sys.exit(1)


@main.command()
def version():
    """Show version information."""
    console.print("Gensi version 0.1.0")


if __name__ == '__main__':
    main()

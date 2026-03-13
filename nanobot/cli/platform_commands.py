"""Platform node CLI commands."""

import asyncio
import typer
from rich.console import Console
from rich.table import Table
from rich.text import Text

from nanobot.platforms.macos import create_macos_menubar
from nanobot.platforms.ios import create_ios_node
from nanobot.platforms.android import create_android_node
from nanobot.nodes import NodeManager

console = Console()

platform_app = typer.Typer(
    name="platform",
    help="Manage platform nodes (macOS, iOS, Android)",
    no_args_is_help=True,
)


@platform_app.command()
def list_nodes():
    """List all connected platform nodes."""
    console.print("[bold]Connected Platform Nodes[/bold]\n")
    
    table = Table(title="Platform Nodes", show_header=True, header_style="bold magenta")
    table.add_column("Node ID", style="cyan")
    table.add_column("Platform", style="green")
    table.add_column("Device Name", style="yellow")
    table.add_column("Status", style="blue")
    
    # Placeholder - would fetch from actual node manager
    table.add_row("macos-menubar", "macOS", "macOS Menu Bar", "Connected")
    table.add_row("ios-node-1", "iOS", "iPhone 15 Pro", "Connected")
    table.add_row("android-node-1", "Android", "Android Device", "Connected")
    
    console.print(table)


@platform_app.command()
def start_macos():
    """Start macOS menu bar app."""
    console.print("[bold cyan]Starting macOS Menu Bar App[/bold cyan]")
    
    async def run():
        app = await create_macos_menubar()
        console.print(f"âœ“ Created macOS menu bar app: {app.config.node_id}")
        console.print(f"  Device: {app.config.device_name}")
        console.print(f"  Capabilities: {', '.join(app.config.capabilities)}")
        
        # Would connect to gateway here
        # await app.connect()
    
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted[/yellow]")


@platform_app.command()
def start_ios(
    device_id: str = typer.Option("ios-device-1", "--device-id", help="iOS device ID")
):
    """Start iOS node."""
    console.print(f"[bold cyan]Starting iOS Node: {device_id}[/bold cyan]")
    
    async def run():
        node = await create_ios_node(device_id=device_id)
        console.print(f"âœ“ Created iOS node: {node.config.node_id}")
        console.print(f"  Device: {node.config.device_name}")
        console.print(f"  Features: Voice Wake, Talk Mode, Canvas, Camera")
        console.print(f"  Capabilities: {', '.join(node.config.capabilities)}")
    
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted[/yellow]")


@platform_app.command()
def start_android(
    device_id: str = typer.Option("android-device-1", "--device-id", help="Android device ID")
):
    """Start Android node."""
    console.print(f"[bold cyan]Starting Android Node: {device_id}[/bold cyan]")
    
    async def run():
        node = await create_android_node(device_id=device_id)
        console.print(f"âœ“ Created Android node: {node.config.node_id}")
        console.print(f"  Device: {node.config.device_name}")
        console.print(f"  Features: Talk Mode, Canvas, Camera, SMS, Screen Recording")
        console.print(f"  Capabilities: {', '.join(node.config.capabilities)}")
    
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted[/yellow]")


@platform_app.command()
def demo():
    """Start demo with all platform nodes."""
    console.print("[bold cyan]Starting Platform Nodes Demo[/bold cyan]\n")
    
    async def run():
        console.print("[bold yellow]1. macOS Menu Bar App[/bold yellow]")
        macos = await create_macos_menubar()
        await macos.initialize()
        console.print(f"   âœ“ {macos.config.device_name}")
        console.print(f"   Capabilities: {', '.join(macos.config.capabilities)}\n")
        
        console.print("[bold yellow]2. iOS Node[/bold yellow]")
        ios = await create_ios_node()
        await ios.initialize()
        console.print(f"   âœ“ {ios.config.device_name}")
        console.print(f"   Capabilities: {', '.join(ios.config.capabilities)}\n")
        
        console.print("[bold yellow]3. Android Node[/bold yellow]")
        android = await create_android_node()
        await android.initialize()
        console.print(f"   âœ“ {android.config.device_name}")
        console.print(f"   Capabilities: {', '.join(android.config.capabilities)}\n")
        
        console.print("[bold green]All platform nodes initialized![/bold green]")
        console.print("\nTo connect to gateway, run: ultrabot gateway")
    
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted[/yellow]")

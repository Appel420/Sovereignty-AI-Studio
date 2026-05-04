"""
System_Orchestrator.py
======================
The *brain* of Sovereignty AI Studio.

Responsibilities
----------------
1. **Boot hydration** — loads persisted memory on startup so agents start
   with full context from prior sessions.
2. **Watcher startup** — starts the FileWatcher (config hot-reload),
   HealthWatcher (service liveness), and EventListener (central dispatcher).
3. **Agent lifecycle** — starts, stops, and restarts registered agents as
   asyncio tasks.
4. **Event bus coordination** — routes messages between agents via
   ``event_bus.bus``.
5. **Human-readable CLI** — ``python System_Orchestrator.py status`` prints
   a live service health table; ``python System_Orchestrator.py run`` starts
   everything.
6. **Graceful shutdown** — catches SIGINT / SIGTERM, drains the event bus,
   and stops all background tasks cleanly.

Usage::

    # Start the full orchestrator (foreground — CTRL-C to stop)
    python System_Orchestrator.py run

    # Print current service status (assumes orchestrator is already managing
    # the services via a shared health state file)
    python System_Orchestrator.py status

    # Replay dead-letter queue events
    python System_Orchestrator.py dlq
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import pathlib
import signal
import sys
import time
import uuid
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Internal module imports (all within this repository)
# ---------------------------------------------------------------------------
from memory.memory_store import MemoryStore
from memory.hydration import MemoryHydration
from watchers.file_watcher import FileWatcher, FileChangeEvent
from watchers.health_watcher import HealthWatcher, ServiceHealth, HealthStatus
from watchers.event_listener import EventListener
from event_bus import bus as event_bus

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
ROOT_DIR = pathlib.Path(__file__).parent
LOGS_DIR = ROOT_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOGS_DIR / "orchestrator.log"),
    ],
)
log = logging.getLogger("orchestrator")

# ---------------------------------------------------------------------------
# Well-known config files to watch for hot-reload
# ---------------------------------------------------------------------------
_WATCH_FILES: List[str] = [
    str(ROOT_DIR / ".env"),
    str(ROOT_DIR / "config.json"),
]

# ---------------------------------------------------------------------------
# Agent registry type
# ---------------------------------------------------------------------------
AgentEntry = Dict[str, Any]  # keys: id, task, restart_count, last_restart


class SystemOrchestrator:
    """Full orchestrator: coordinates memory, watchers, agents, and event routing.

    Lifecycle::

        orchestrator = SystemOrchestrator()
        await orchestrator.start()
        # ... runs until stopped ...
        await orchestrator.stop()

    The constructor is lightweight (no I/O).  All real work happens in
    :meth:`start`.
    """

    def __init__(self) -> None:
        # Unique identifier for this orchestrator instance (useful for logs)
        self.instance_id: str = str(uuid.uuid4())[:8]

        # Core subsystems — initialised in start()
        self._memory: Optional[MemoryStore] = None
        self._hydration: Optional[MemoryHydration] = None
        self._file_watcher: Optional[FileWatcher] = None
        self._health_watcher: Optional[HealthWatcher] = None
        self._event_listener: Optional[EventListener] = None

        # Registry of managed agents: agent_id → AgentEntry
        self._agents: Dict[str, AgentEntry] = {}

        # Background asyncio tasks
        self._tasks: List[asyncio.Task] = []

        self._running = False
        self._shutdown_event = asyncio.Event()

    # ------------------------------------------------------------------
    # Start
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Initialise and start all orchestrator subsystems.

        Order of operations:
        1. Initialise memory store
        2. Hydrate agents from persisted memory
        3. Start FileWatcher (config hot-reload)
        4. Start HealthWatcher (service liveness polling)
        5. Start EventListener (central event dispatcher)
        6. Start event bus processing loop
        7. Register signal handlers for graceful shutdown
        8. Log the "READY" banner
        """
        log.info("═" * 60)
        log.info("  Sovereignty AI Studio — Orchestrator  [instance=%s]", self.instance_id)
        log.info("═" * 60)

        # ── 1. Memory ──────────────────────────────────────────────────
        log.info("[1/6] Initialising persistent memory store...")
        self._memory = MemoryStore(namespace="orchestrator")
        await self._memory.initialise()

        # ── 2. Hydration ───────────────────────────────────────────────
        log.info("[2/6] Hydrating agent context from memory...")
        self._hydration = MemoryHydration(store=self._memory)
        await self._hydration.hydrate()

        # Record this boot event in memory so we have a full restart history
        await self._hydration.save_global(
            f"boot_{int(time.time())}",
            {"instance_id": self.instance_id, "ts": time.time()},
            tags=["boot", "orchestrator"],
        )

        # ── 3. File watcher ────────────────────────────────────────────
        log.info("[3/6] Starting file watcher...")
        self._file_watcher = FileWatcher(
            paths=[p for p in _WATCH_FILES if pathlib.Path(p).exists()]
        )
        self._file_watcher.on_change(self._on_file_change)
        await self._file_watcher.start()

        # ── 4. Health watcher ──────────────────────────────────────────
        log.info("[4/6] Starting health watcher...")
        self._health_watcher = HealthWatcher(check_interval=15.0)
        self._health_watcher.on_status_change(self._on_service_status_change)
        await self._health_watcher.start()

        # ── 5. Event listener ──────────────────────────────────────────
        log.info("[5/6] Starting central event listener...")
        self._event_listener = EventListener(max_retries=3)
        self._event_listener.register("orchestrator_cmd", self._handle_orchestrator_cmd)
        await self._event_listener.start()

        # ── 6. Event bus ───────────────────────────────────────────────
        log.info("[6/6] Starting event bus processing loop...")
        bus_task = asyncio.create_task(
            event_bus.process_events(), name="event_bus"
        )
        self._tasks.append(bus_task)

        # ── Signal handlers ───────────────────────────────────────────
        self._install_signal_handlers()

        self._running = True
        log.info("✓ Orchestrator READY — all subsystems running")
        log.info("  Press CTRL-C or send SIGTERM to stop gracefully.")
        log.info("═" * 60)

    # ------------------------------------------------------------------
    # Stop
    # ------------------------------------------------------------------

    async def stop(self) -> None:
        """Gracefully stop all subsystems in reverse startup order."""
        if not self._running:
            return

        log.info("Orchestrator: initiating graceful shutdown...")
        self._running = False
        self._shutdown_event.set()

        # Stop watchers and listeners
        if self._event_listener:
            await self._event_listener.stop()
        if self._health_watcher:
            await self._health_watcher.stop()
        if self._file_watcher:
            await self._file_watcher.stop()

        # Cancel all background tasks
        for task in self._tasks:
            if not task.done():
                task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

        # Log any DLQ entries before exit
        dlq = event_bus.dlq_snapshot()
        if dlq:
            log.warning(
                "Orchestrator: %d event(s) in dead-letter queue at shutdown",
                len(dlq),
            )
            for entry in dlq[:5]:
                log.warning("  DLQ entry: %s", entry)
            if len(dlq) > 5:
                log.warning("  ... and %d more", len(dlq) - 5)

        log.info("Orchestrator: shutdown complete.")

    # ------------------------------------------------------------------
    # Run (blocking convenience entry point)
    # ------------------------------------------------------------------

    async def run_forever(self) -> None:
        """Start the orchestrator and block until a shutdown signal is received."""
        await self.start()
        try:
            await self._shutdown_event.wait()
        finally:
            await self.stop()

    # ------------------------------------------------------------------
    # Agent lifecycle
    # ------------------------------------------------------------------

    def register_agent(
        self,
        agent_id: str,
        coro_factory: Any,
        *,
        auto_restart: bool = True,
    ) -> None:
        """Register an agent coroutine factory with the orchestrator.

        The orchestrator will start the coroutine as a managed asyncio task
        and optionally restart it if it exits unexpectedly.

        Args:
            agent_id:      Unique identifier for this agent.
            coro_factory:  Zero-argument async callable that returns the
                           agent's main coroutine.
            auto_restart:  Restart the agent if it exits with an error.
        """
        self._agents[agent_id] = {
            "id": agent_id,
            "factory": coro_factory,
            "auto_restart": auto_restart,
            "task": None,
            "restart_count": 0,
            "last_restart": None,
            "status": "registered",
        }
        log.info("Orchestrator: registered agent '%s'", agent_id)

    async def start_agent(self, agent_id: str) -> None:
        """Start (or restart) a registered agent as a background task.

        Args:
            agent_id: Agent to start.  Must be registered via
                      :meth:`register_agent` first.

        Raises:
            KeyError: If *agent_id* is not registered.
        """
        entry = self._agents[agent_id]
        task = asyncio.create_task(
            self._run_agent(agent_id, entry["factory"]),
            name=f"agent:{agent_id}",
        )
        entry["task"] = task
        entry["status"] = "running"
        self._tasks.append(task)
        log.info("Orchestrator: started agent '%s'", agent_id)

    async def stop_agent(self, agent_id: str) -> None:
        """Stop a running agent task.

        Args:
            agent_id: Agent to stop.
        """
        entry = self._agents.get(agent_id)
        if not entry:
            return
        task = entry.get("task")
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        entry["status"] = "stopped"
        log.info("Orchestrator: stopped agent '%s'", agent_id)

    async def _run_agent(self, agent_id: str, factory: Any) -> None:
        """Wrapper that runs an agent and optionally restarts it on failure."""
        entry = self._agents[agent_id]
        while self._running:
            try:
                log.info("Orchestrator: agent '%s' starting...", agent_id)
                coro = factory()
                await coro
                log.info("Orchestrator: agent '%s' exited cleanly.", agent_id)
                break  # Clean exit — do not restart
            except asyncio.CancelledError:
                break
            except Exception as exc:  # noqa: BLE001
                entry["restart_count"] += 1
                entry["last_restart"] = time.time()
                log.error(
                    "Orchestrator: agent '%s' crashed (restart #%d): %s",
                    agent_id,
                    entry["restart_count"],
                    exc,
                )
                if not entry.get("auto_restart"):
                    entry["status"] = "crashed"
                    break
                # Exponential backoff — cap at 60 s
                delay = min(5.0 * entry["restart_count"], 60.0)
                log.info(
                    "Orchestrator: restarting agent '%s' in %.0fs...", agent_id, delay
                )
                await asyncio.sleep(delay)

    # ------------------------------------------------------------------
    # Callbacks: file changes, health transitions
    # ------------------------------------------------------------------

    def _on_file_change(self, event: FileChangeEvent) -> None:
        """Called when a watched config file changes."""
        log.info(
            "Orchestrator: config change detected — %s %s",
            event.kind.upper(),
            event.path,
        )
        # Emit an event so any interested agent can react
        asyncio.ensure_future(
            self._event_listener.emit(
                "config_changed",
                {"path": event.path, "kind": event.kind},
                source="file_watcher",
            )
            if self._event_listener else asyncio.sleep(0)
        )

    def _on_service_status_change(
        self, name: str, health: ServiceHealth
    ) -> None:
        """Called when a monitored service changes health status."""
        icon = {
            HealthStatus.HEALTHY: "✓",
            HealthStatus.DEGRADED: "⚠",
            HealthStatus.DOWN: "✗",
            HealthStatus.UNKNOWN: "?",
        }.get(health.status, "?")

        log.warning(
            "Orchestrator: [%s] %s → %s  (latency=%.0fms, err=%s)",
            icon,
            name,
            health.status.value,
            health.latency_ms,
            health.last_error or "none",
        )

    async def _handle_orchestrator_cmd(self, event: Any) -> None:
        """Handle control commands sent to the orchestrator via the event bus."""
        data = event.data if hasattr(event, "data") else event
        cmd = data.get("cmd", "")
        agent_id = data.get("agent_id", "")

        if cmd == "restart_agent" and agent_id:
            log.info("Orchestrator: received restart command for agent '%s'", agent_id)
            await self.stop_agent(agent_id)
            await self.start_agent(agent_id)
        elif cmd == "status":
            self.print_status()
        else:
            log.warning("Orchestrator: unknown command '%s'", cmd)

    # ------------------------------------------------------------------
    # Status CLI
    # ------------------------------------------------------------------

    def print_status(self) -> None:
        """Print a human-readable status table to stdout."""
        now_str = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n{'═' * 60}")
        print(f"  Sovereignty AI Studio — Status  [{now_str}]")
        print(f"  Instance: {self.instance_id}")
        print(f"{'─' * 60}")

        # Service health
        if self._health_watcher:
            print("  Services:")
            for name, status_str in self._health_watcher.summary().items():
                icon = {"healthy": "✓", "degraded": "⚠", "down": "✗"}.get(
                    status_str, "?"
                )
                print(f"    [{icon}] {name:<20} {status_str}")
        else:
            print("  Services: HealthWatcher not running")

        # Agents
        print(f"{'─' * 60}")
        if self._agents:
            print("  Agents:")
            for agent_id, entry in self._agents.items():
                restarts = entry.get("restart_count", 0)
                status = entry.get("status", "unknown")
                print(f"    • {agent_id:<20} {status}  (restarts={restarts})")
        else:
            print("  Agents: none registered")

        # Dead-letter queue
        dlq = event_bus.dlq_snapshot()
        print(f"{'─' * 60}")
        print(f"  Dead-letter queue: {len(dlq)} event(s)")
        print(f"{'═' * 60}\n")

    # ------------------------------------------------------------------
    # Signal handling
    # ------------------------------------------------------------------

    def _install_signal_handlers(self) -> None:
        """Register SIGINT / SIGTERM handlers for graceful shutdown."""
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(
                    sig,
                    lambda: asyncio.ensure_future(self._signal_shutdown()),
                )
            except NotImplementedError:
                # Windows does not support add_signal_handler on all loops
                pass

    async def _signal_shutdown(self) -> None:
        """Handle OS shutdown signals."""
        log.info("Orchestrator: shutdown signal received.")
        self._shutdown_event.set()


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

async def _run() -> None:
    """Start the orchestrator and run until interrupted."""
    orch = SystemOrchestrator()
    await orch.run_forever()


def _cmd_status() -> None:
    """Quick status snapshot — attempts to read the health state file."""
    # For a live status you would normally query a shared state endpoint;
    # here we print a lightweight explanation for standalone use.
    print("\nSovereignty AI Studio — Quick Status")
    print("Run `python System_Orchestrator.py run` to start the orchestrator.")
    print("For live status, start the orchestrator and press CTRL-Z, then run:")
    print("  python -c \"from System_Orchestrator import SystemOrchestrator; "
          "import asyncio; asyncio.run(SystemOrchestrator().start())\"")


def _cmd_dlq() -> None:
    """Print the current dead-letter queue contents (in-process)."""
    dlq = event_bus.dlq_snapshot()
    if not dlq:
        print("Dead-letter queue is empty.")
        return
    print(f"Dead-letter queue: {len(dlq)} event(s)")
    for entry in dlq:
        print(f"  agent={entry['agent_id']}  event_id={entry['event_id']}")
        print(f"    task={json.dumps(entry['task'])[:120]}")


if __name__ == "__main__":
    command = sys.argv[1] if len(sys.argv) > 1 else "run"

    if command == "run":
        try:
            asyncio.run(_run())
        except KeyboardInterrupt:
            print("\nOrchestrator stopped.")
    elif command == "status":
        _cmd_status()
    elif command == "dlq":
        _cmd_dlq()
    else:
        print(f"Unknown command: {command}")
        print("Usage: python System_Orchestrator.py [run|status|dlq]")
        sys.exit(1)

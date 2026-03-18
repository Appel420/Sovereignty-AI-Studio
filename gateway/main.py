"""Gateway orchestrator — instantiates all agents and runs the async pipeline.

The gateway is the single entry point for the multi-agent system.  It:
1. Creates a shared JudgeAgent
2. Creates and wires all specialist agents (AI Router, Plugin, Platform, Voice)
3. Starts the event bus processing loop
4. Runs an example task pipeline that exercises every agent
5. Exposes a minimal HTTP API (port 9898) for external control
"""

import asyncio
import json
import logging
import os
from typing import Any, Dict

from aiohttp import web  # type: ignore

from agents.judge_agent.judge import JudgeAgent
from agents.ai_router_agent.router import AIRouterAgent
from agents.plugin_agent.plugin_manager import PluginAgent
from agents.platform_agent.platform_manager import PlatformAgent
from agents.voice_assist_agent.voice_manager import VoiceAssistAgent
from event_bus import bus as event_bus

logger = logging.getLogger(__name__)

_GATEWAY_PORT = int(os.getenv("GATEWAY_PORT", "9898"))


# ---------------------------------------------------------------------------
# HTTP handlers
# ---------------------------------------------------------------------------

async def health_handler(request: web.Request) -> web.Response:
    return web.json_response({"status": "ok", "service": "sovereignty-gateway"})


async def chat_handler(request: web.Request) -> web.Response:
    """Route an AI chat request through the AI Router Agent."""
    router: AIRouterAgent = request.app["ai_router"]
    try:
        body: Dict[str, Any] = await request.json()
    except Exception:
        raise web.HTTPBadRequest(reason="Invalid JSON body")

    success, result = await router.route(body)
    if success:
        return web.json_response({"ok": True, "result": result})
    return web.json_response({"ok": False, "error": result}, status=502)


async def voice_handler(request: web.Request) -> web.Response:
    """Handle a voice command through the Voice Assist Agent."""
    agent: VoiceAssistAgent = request.app["voice_assist"]
    try:
        body: Dict[str, Any] = await request.json()
    except Exception:
        raise web.HTTPBadRequest(reason="Invalid JSON body")

    response = await agent.handle_command(body)
    return web.json_response(response)


async def plugin_run_handler(request: web.Request) -> web.Response:
    """Run a plugin by ID."""
    plugin_agent: PluginAgent = request.app["plugin_agent"]
    plugin_id = request.match_info.get("plugin_id", "")
    try:
        body: Dict[str, Any] = await request.json()
    except Exception:
        body = {}

    success, result = await plugin_agent.run_plugin(plugin_id, body)
    if success:
        return web.json_response({"ok": True, "result": result})
    return web.json_response({"ok": False, "error": str(result)}, status=500)


async def judge_log_handler(request: web.Request) -> web.Response:
    """Return the Judge task log."""
    judge: JudgeAgent = request.app["judge"]
    return web.json_response({"log": judge.get_task_log()})


# ---------------------------------------------------------------------------
# Event bus handlers
# ---------------------------------------------------------------------------

async def _handle_ai_task(task: Dict[str, Any]) -> None:
    router: AIRouterAgent = _app["ai_router"]
    success, result = await router.route(task)
    logger.info("Event bus AI task: success=%s", success)


async def _handle_voice_task(task: Dict[str, Any]) -> None:
    agent: VoiceAssistAgent = _app["voice_assist"]
    await agent.handle_command(task)


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

_app: web.Application = web.Application()


def _create_app(judge: JudgeAgent) -> web.Application:
    app = web.Application()

    # Shared agents
    ai_router = AIRouterAgent(judge)
    plugin_agent = PluginAgent(judge)
    platform_agent = PlatformAgent(judge)
    voice_assist = VoiceAssistAgent(judge)

    app["judge"] = judge
    app["ai_router"] = ai_router
    app["plugin_agent"] = plugin_agent
    app["platform_agent"] = platform_agent
    app["voice_assist"] = voice_assist

    # Routes
    app.router.add_get("/health", health_handler)
    app.router.add_post("/api/chat", chat_handler)
    app.router.add_post("/api/voice", voice_handler)
    app.router.add_post("/api/plugins/{plugin_id}/run", plugin_run_handler)
    app.router.add_get("/api/judge/log", judge_log_handler)

    return app


# ---------------------------------------------------------------------------
# Example task pipeline
# ---------------------------------------------------------------------------

async def _example_pipeline(
    judge: JudgeAgent,
    ai_router: AIRouterAgent,
    plugin_agent: PluginAgent,
    voice_assist: VoiceAssistAgent,
) -> None:
    """Demonstrate all agents cooperating through the Judge."""
    logger.info("=== Running example pipeline ===")

    # 1. Voice wizard
    for _ in range(len(["step1", "step2", "step3"])):
        resp = await voice_assist.handle_command({"command": "wizard_step", "payload": {}})
        logger.info("Voice wizard: %s", resp["text"])

    # 2. Plugin discovery
    discovered = plugin_agent.discover()
    logger.info("Discovered plugins: %s", discovered)

    # 3. AI routing (will fail gracefully if no API keys are set)
    if os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or os.getenv("XAI_API_KEY"):
        success, result = await ai_router.route(
            {"prompt": "Hello from Sovereignty AI!", "task_type": "creative"}
        )
        logger.info("AI router result: success=%s", success)

    logger.info("=== Pipeline complete ===")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    )

    judge = JudgeAgent()
    judge.start_metrics()

    global _app
    _app = _create_app(judge)

    # Register event bus handlers
    event_bus.register_handler("ai_router", _handle_ai_task)
    event_bus.register_handler("voice_assist", _handle_voice_task)

    # Discover plugins
    plugin_agent: PluginAgent = _app["plugin_agent"]
    plugin_agent.discover()

    # Connect platforms
    platform_agent: PlatformAgent = _app["platform_agent"]
    await platform_agent.start()

    # Start event bus in background
    bus_task = asyncio.create_task(event_bus.process_events(), name="event-bus")

    # Run example pipeline
    await _example_pipeline(
        judge,
        _app["ai_router"],
        plugin_agent,
        _app["voice_assist"],
    )

    # Start HTTP server
    runner = web.AppRunner(_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", _GATEWAY_PORT)
    await site.start()
    logger.info("Gateway running on port %d", _GATEWAY_PORT)

    try:
        await asyncio.Event().wait()  # run forever
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        bus_task.cancel()
        await platform_agent.stop()
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())

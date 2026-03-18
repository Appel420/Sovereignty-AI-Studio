from fastapi import APIRouter
from app.api.v1.endpoints import (
    test, auth, users, alerts, studio,
<<<<<< copilot/integrate-production-features
    generation, media, voice, avatar, music, syntax, ble_lidar,
    organizations, audit, marketplace, telemetry,
=======
    generation, media, voice, avatar, music, syntax, ble_lidar, org,
>>>>>> main
)

api_router = APIRouter()

# Include endpoints
api_router.include_router(test.router, prefix="/test", tags=["test"])
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(alerts.router, prefix="/alerts", tags=["alerts"])
api_router.include_router(studio.router, prefix="/studio", tags=["studio"])
api_router.include_router(generation.router, prefix="/generation", tags=["generation"])
api_router.include_router(media.router, prefix="/media", tags=["media"])
api_router.include_router(voice.router, prefix="/voice", tags=["voice"])
api_router.include_router(avatar.router, prefix="/avatar", tags=["avatar"])
api_router.include_router(music.router, prefix="/music", tags=["music"])
api_router.include_router(syntax.router, prefix="/syntax", tags=["syntax"])
api_router.include_router(ble_lidar.router, prefix="/ble", tags=["ble-lidar"])
api_router.include_router(organizations.router, prefix="/org", tags=["organizations"])
api_router.include_router(audit.router, prefix="/audit", tags=["audit"])
api_router.include_router(marketplace.router, prefix="/marketplace", tags=["marketplace"])
api_router.include_router(telemetry.router, prefix="/telemetry", tags=["telemetry"])

api_router.include_router(org.router, prefix="/org", tags=["organizations"])


@api_router.get("/status")
async def api_status():
    return {"status": "API v1 is running"}

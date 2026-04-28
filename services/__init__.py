"""
Services package — SOLID-split game service layer.

Each service owns one responsibility:
  - GameQueryService    : read-only game/player/throw state queries (SRP + ISP)
  - GameLifecycleService: game creation, start, reset, deletion (SRP)
  - ThrowService        : throw recording, undo, bust handling (SRP)
  - PlayerService       : player creation and removal (SRP; stateless)
  - AnalyticsService    : per-player statistics, history queries (SRP; stateless)

The dependency-provider functions (get_*) are thin FastAPI Depends()-compatible
factories. They hand each service a reference to the GameManager singleton so
callers never import GameManager directly.
"""

from game.game_manager import GameManager
from services.game_query_service import GameQueryService
from services.game_lifecycle_service import GameLifecycleService
from services.throw_service import ThrowService
from services.player_service import PlayerService
from services.analytics_service import AnalyticsService


def get_query_service() -> GameQueryService:
    return GameQueryService(GameManager.get_instance())


def get_lifecycle_service() -> GameLifecycleService:
    return GameLifecycleService(GameManager.get_instance())


def get_throw_service() -> ThrowService:
    return ThrowService(GameManager.get_instance())


def get_player_service() -> PlayerService:
    return PlayerService()


def get_analytics_service() -> AnalyticsService:
    return AnalyticsService()


__all__ = [
    "GameQueryService",
    "GameLifecycleService",
    "ThrowService",
    "PlayerService",
    "AnalyticsService",
    "get_query_service",
    "get_lifecycle_service",
    "get_throw_service",
    "get_player_service",
    "get_analytics_service",
]

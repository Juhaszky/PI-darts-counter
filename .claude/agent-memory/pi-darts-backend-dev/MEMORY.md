# PI Darts Counter Backend - Agent Memory

## Project Overview
FastAPI-based backend for automated darts scoring system running on Raspberry Pi 5.

## Architecture Patterns

### In-Memory State Management
- `GameManager` singleton pattern (`GameManager.get_instance()`)
- Games stored in `dict[str, Game]` indexed by UUID
- Players stored per game in `dict[str, list[Player]]`
- Throw history tracked in `dict[str, list[ThrowResult]]`

### Database Layer (Phase 4 - implemented)
- ORM models in `database/models.py` (separate from Pydantic models in `models/`)
- Engine + session factory in `database/db.py`; see `database-layer.md` for design
- Repository functions in `database/repository.py`
- Public exports via `database/__init__.py`: init_db, get_db, save_game, save_throw, finish_game
- `init_db()` called from `startup_event` in `main.py`

### API Layer Separation
- REST API (`api/routes.py`): Game lifecycle, manual throws, health checks
- WebSocket API (`api/websocket.py`): Real-time game state broadcasts
- `ConnectionManager` handles WebSocket rooms per game_id
- All WebSocket messages follow `{type: string, data: dict}` format

### Data Models (Pydantic)
- Game models: `Game`, `GameCreate`, `GameMode`, `GameStatus`, `GameResponse`
- Player models: `Player`, `PlayerCreate`, `PlayerResponse`
- Throw models: `Throw`, `ThrowCreate`, `ThrowResult`, `ThrowResponse`
- Strict validation: segments (0-20, 25, 50), multipliers (1-3)
- Special cases: bull (25), bullseye (50), miss (0) are always single (multiplier=1)

### Configuration
- `pydantic-settings` with `.env` support; all settings in `config.py` via `Settings`
- `settings.database_url` = `"sqlite+aiosqlite:///./database/darts.db"`
- Camera sources: `camera_0_source`, `camera_1_source`, `camera_2_source` (str, default "0"/"1"/"2")
  - Accept numeric index strings ("0") for USB cams or HTTP MJPEG URLs for IP cams

## Key Files

### Core Application
- `main.py` — FastAPI app, CORS, router, WebSocket, calls `await init_db()` on startup
- `config.py` — Settings with env var loading

### API Layer
- `api/routes.py` — REST endpoints
- `api/websocket.py` — WebSocket handler, ConnectionManager

### Game Logic
- `game/game_manager.py` — In-memory game state
- `game/game_logic.py` — 301/501 rules, validation, bust checks
- `game/score_calculator.py` — Throw result calculation

### Models (Pydantic - do not modify)
- `models/game.py`, `models/player.py`, `models/throw.py`

### Database Layer
- `database/models.py` — SQLAlchemy ORM: GameRecord, PlayerRecord, ThrowRecord
- `database/db.py` — engine, AsyncSessionLocal, get_db(), init_db()
- `database/repository.py` — save_game, save_throw, finish_game, get_game_history, get_player_stats
- `database/__init__.py` — public exports

## Common Operations

### Create & Start Game
```python
manager = GameManager.get_instance()
game, players = manager.create_game(game_data)
manager.start_game(game_id)
```

### Persist to DB (after in-memory update)
```python
async with AsyncSessionLocal() as db:
    await save_game(db, game, players)
    await save_throw(db, game_id, throw, round, throw_num)
    await finish_game(db, game_id, winner_id, finished_at)
    await db.commit()
```

## Game Logic Rules
- Modes: 301, 501 (starting scores)
- Bust: score < 0, score == 1, or (double_out && win throw not double/bullseye)
- Turn: 3 throws max; bust restores score to turn start
- Round increments when cycling back to first player
- Segment names: "T20" (triple), "D16" (double), "5" (single), "BULL", "BULLSEYE"

## Edge Cases Handled
1. Bust: Score restored, turn ends immediately, turn_throws cleared
2. Double-out: Winner must finish with double (multiplier=2) or bullseye (segment=50)
3. Invalid throws: Segment validation (25/50/0 must be single), multiplier bounds
4. Undo: Restores score, decrements throws_this_turn
5. DB idempotency: save_game/save_throw use merge() so crash-restart never duplicates rows

## Frontend Integration Notes
- WebSocket sends `game_state` on connect (full state snapshot)
- Throw events: `throw_detected`, `bust`, `turn_complete`, `game_over`
- Client messages: `manual_score`, `undo_throw`, `next_turn`

## Dependencies
- fastapi>=0.115.0, uvicorn[standard]>=0.30.0
- pydantic>=2.0.0, pydantic-settings>=2.0.0
- websockets>=12.0, python-dotenv>=1.0.0
- sqlalchemy[asyncio]>=2.0.0, aiosqlite>=0.20.0

## Camera Module (Phase 3 - implemented)

### Key Files
- `camera/__init__.py` — exports CameraManager, DartDetector, get_segment, CameraCalibration
- `camera/camera_manager.py` — lifecycle, async capture, dart position, camera status
- `camera/detector.py` — MOG2 background subtraction pipeline, stability filter, segment mapping
- `camera/calibration.py` — checkerboard calibration, JSON persistence, undistortion
- `camera/calibration_data/` — JSON files per camera; `.gitkeep` tracks the dir

### Camera Labels
- Camera 0: "Bal" (left), Camera 1: "Jobb" (right), Camera 2: "Felső" (top)

### CV2_AVAILABLE Guard Pattern
Every camera file wraps `import cv2; import numpy as np` in try/except ImportError.
Module-level `CV2_AVAILABLE: bool` flag is set. All methods check the flag before calling
OpenCV APIs. This lets the whole module import cleanly on Windows dev machines without OpenCV.

### Async Frame Capture
- `capture_frames()` uses `asyncio.get_event_loop().run_in_executor(_CAPTURE_THREAD_POOL, ...)`.
- Thread pool is module-level `ThreadPoolExecutor(max_workers=3)` — one thread per camera.
- `_read_frame()` is the synchronous worker: read → undistort → feed to DartDetector.
- DartDetector.process_frame() is called from the executor thread (safe — no async calls inside).

### Stability Filter
- Counts consecutive frames within POSITION_TOLERANCE_PX (5 px) of each other.
- Returns stable position only after STABILITY_THRESHOLD_FRAMES (45) consecutive frames.
- Any gap or large movement resets the counter to 1 (not 0) from the new position.
- `detector.reset()` must be called after a dart is removed.

### Dart Tip Definition
"Topmost point" = minimum y-value across all contours (min y = top of image = dart tip
as viewed from above with dart pointing at board).

### Calibration JSON Format
```json
{"camera_id": 0, "camera_matrix": [[...]], "dist_coeffs": [...]}
```
NumPy arrays stored as nested lists for portability. Loaded back with np.array(..., dtype=float64).

### Calibration Minimum Images
calibrate() requires checkerboard to be detected in at least 3 of the supplied images.

### get_segment() Contract
- radius < 0.05 → (50, 1) bullseye
- radius < 0.10 → (25, 1) bull
- radius > 1.0 → (0, 1) miss
- 0.62 < radius < 0.68 → triple (×3)
- 0.95 < radius <= 1.0 → double (×2)
- segment_idx = int((angle_deg + 9) % 360 / 18) % 20

## Mobile Camera Frame Processing (implemented)

### New Files
- `camera/coordinate_mapper.py` — `CoordinateMapper` class; board position as fractions of
  frame dimensions. `pixel_to_segment(x, y, w, h)` → `(segment, multiplier)`. Calls `get_segment()`.
  Updated via `update(center_x_pct, center_y_pct, radius_pct)` at runtime.

### Config Additions (config.py)
- `board_center_x_pct`, `board_center_y_pct`, `board_radius_pct` (float, default 0.5/0.5/0.4)
- `mobile_camera_fps` (int, default 10) — stability_threshold = max(5, int(1.5 × fps))

### DartDetector Change (camera/detector.py)
- `__init__` now accepts `stability_threshold: int = STABILITY_THRESHOLD_FRAMES`
- Stored as `self._stability_threshold`; replaces the module constant in `_update_stability`

### WebSocket Additions (api/websocket.py)
- Module-level: `_mobile_detectors: dict[str, DartDetector]` (per-game), `_coordinate_mapper: CoordinateMapper` (shared)
- `handle_camera_frame(game_id, data)` — decodes base64 JPEG, runs DartDetector, maps to segment, calls `process_throw`, broadcasts identical events to `handle_manual_score`
- Message loop: `elif msg_type == "camera_frame": await handle_camera_frame(game_id, msg_data)`
- Disconnect cleanup: `del _mobile_detectors[game_id]` only when the room empties (checked via `manager.active_connections`)

### REST Addition (api/routes.py)
- `POST /api/cameras/board-config` — validates pct ranges, calls `_coordinate_mapper.update()`
- Import: `from api.websocket import _coordinate_mapper` (shared singleton)

### Key Design Decisions
- `cv2`/`numpy` imported inside `handle_camera_frame` (not at module level) — preserves the CV2_AVAILABLE guard pattern so the whole app imports cleanly without OpenCV
- `process_frame()` runs synchronously in the async handler; acceptable at ≤10 fps mobile rate
- Detector reset on confirmed dart OR on miss (segment==0) prevents ghost detections
- Detector cleanup is gated on room empty (not every disconnect) — multiple clients per game

## Background Camera Loop (Phase 6 - implemented)

### New File
- `camera/camera_loop.py` — module-level state + `setup()`, `start()`, `stop()`, `_detection_loop()`

### Integration Points
- `main.py` startup: `camera_loop.setup(camera_manager, _coordinate_mapper)` then `await camera_loop.start()`
- `main.py` shutdown: `await camera_loop.stop()` then `await camera_manager.stop()`
- `GET /api/cameras` — now returns live status from `camera_manager.get_camera_status()`
- `POST /api/cameras/sources` — hot-swaps sources: stop loop → stop manager → set new sources → restart both

### CameraManager Changes
- Constructor now `list[str]` (was `list[int]`); `camera_ids` attribute is `list[str]`
- `_open_sync(cam_source: str)` — `cam_source.isdigit()` decides int vs str for cv2.VideoCapture
- `frame_sizes: dict[int, tuple[int, int]]` — populated per-frame in `_read_frame`; reset to {} in stop()
- `get_dart_position()` now returns `tuple[float, float, int, int] | None` — adds frame_w, frame_h
- `get_camera_status()` uses positional index `i` for `_CAMERA_LABELS` lookup (not source string)
- `CameraCalibration(cam_idx)` uses `len(self.calibrations)` as the index, not the source string

### Loop Design
- Deferred imports inside `_detection_loop()` (GameManager, ws_manager) to avoid circular imports
- `camera_loop.setup()` is called before `camera_manager.start()` so dependencies are always wired
- Detector reset happens immediately after stable position read — before game/active-game checks
- `_find_active_game()` returns first `status == "in_progress"` game_id

### Circular Import Pattern
- `routes.py` and `camera_loop.py` import from `main` using lazy `from main import camera_manager`
  inside the function body — never at module level. This avoids the routes→main→routes circle.

## Next Phases
- Phase 5: Wire repository calls into routes/websocket handlers after each game event
- Phase 5: Unit tests (game_logic, score_calculator, repository, detector/get_segment, coordinate_mapper)
- Phase 7 (stretch): Multi-camera triangulation replacing single-camera position stub

## Known Issues / TODOs
- Stats calculation for `game_over` is implemented but not yet persisted to DB
- `get_game_history` and `get_player_stats` not yet exposed via API endpoints
- No rate limiting on manual throws or camera_frame messages (add in production)
- `asyncio.get_event_loop()` in capture_frames/_open_camera — replace with asyncio.get_running_loop() when Python ≥3.10 is confirmed on RPi5
- IP Webcam MJPEG stream: cv2.VideoCapture blocks on open for ~30s if URL unreachable; consider a connect-timeout wrapper in _open_sync

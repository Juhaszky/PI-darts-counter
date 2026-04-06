# PI Darts Counter Backend - Agent Memory

## Project Overview
FastAPI-based backend for automated darts scoring system running on Raspberry Pi 5.

## Architecture Patterns

### In-Memory State Management
- `GameManager` singleton pattern (`GameManager.get_instance()`)
- Games stored in `dict[str, Game]` indexed by UUID
- Players stored per game in `dict[str, list[Player]]`
- Throw history tracked in `dict[str, list[ThrowResult]]`
- No database persistence yet (Phase 1-2 focus)

### API Layer Separation
- **REST API** (`api/routes.py`): Game lifecycle, manual throws, health checks
- **WebSocket API** (`api/websocket.py`): Real-time game state broadcasts
- `ConnectionManager` handles WebSocket rooms per game_id
- All WebSocket messages follow `{type: string, data: dict}` format

### Data Models (Pydantic)
- **Game models**: `Game`, `GameCreate`, `GameState`, `GameResponse`
- **Player models**: `Player`, `PlayerCreate`, `PlayerResponse`
- **Throw models**: `Throw`, `ThrowCreate`, `ThrowResult`, `ThrowResponse`
- Strict validation: segments (0-20, 25, 50), multipliers (1-3)
- Special cases: bull (25), bullseye (50), miss (0) are always single (multiplier=1)

### Game Logic
- **Modes**: 301, 501 (starting scores)
- **Bust conditions**: score < 0, score == 1, or (double_out && final_throw != double)
- **Turn flow**: 3 throws max → bust restores score → winner check → next player
- **Round increment**: when cycling back to first player
- Segment name formatting: "T20" (triple), "D16" (double), "5" (single), "BULL", "BULLSEYE"

### Configuration
- `pydantic-settings` with `.env` support
- All settings in `config.py` via `Settings` class
- CORS origins configurable (default: ["*"])
- Camera config present but unused (Phase 3)

## Key Files

### Core Application
- `main.py` - FastAPI app, CORS, router registration, WebSocket mount
- `config.py` - Settings with env var loading

### API Layer
- `api/routes.py` - REST endpoints (/api/games, /api/health, etc.)
- `api/websocket.py` - WebSocket handler, ConnectionManager, message routing

### Game Logic
- `game/game_manager.py` - In-memory game state (create, start, reset, delete)
- `game/game_logic.py` - 301/501 rules, validation, bust checks
- `game/score_calculator.py` - Calculate throw results with bust logic

### Models
- `models/game.py` - Game, GameCreate, GameState, GameResponse
- `models/player.py` - Player, PlayerCreate, PlayerResponse
- `models/throw.py` - ThrowResult, ThrowCreate, formatting helpers

## Common Operations

### Create & Start Game
```python
manager = GameManager.get_instance()
game, players = manager.create_game(game_data)  # Returns (Game, list[Player])
manager.start_game(game_id)  # Status: waiting → in_progress
```

### Process Throw
```python
throw_result = manager.process_throw(game_id, segment, multiplier)
# Returns ThrowResult or None if invalid
# Automatically handles: score update, bust, winner, next player
```

### WebSocket Broadcast
```python
await manager.broadcast(message_dict, game_id)  # All clients in game room
await manager.send_personal_message(message_dict, websocket)  # Single client
```

## Edge Cases Handled

1. **Bust**: Score restored, turn ends immediately, turn_throws cleared
2. **Double-out**: Winner must finish with double (multiplier=2) or bullseye (segment=50)
3. **Invalid throws**: Segment validation (25/50/0 must be single), multiplier bounds
4. **Turn complete**: Max 3 throws, auto-advance to next player
5. **Undo**: Restores score, decrements throws_this_turn

## Frontend Integration Notes

- WebSocket sends `game_state` on connect (full state snapshot)
- Throw events: `throw_detected`, `bust`, `turn_complete`, `game_over`
- Client messages: `manual_score`, `undo_throw`, `next_turn`
- Error messages: `{type: "error", data: {code, message, severity}}`

## Testing Strategy (Future)

- Unit tests for `game_logic.py` (validate_throw, is_bust, check_winner)
- Unit tests for `score_calculator.py` (all bust conditions)
- Integration tests for GameManager (multi-turn scenarios, undo)
- WebSocket tests (connect, broadcast, disconnect)

## Next Phases

- **Phase 3**: Camera integration (OpenCV, dart detection, calibration)
- **Phase 4**: Database persistence (SQLite + SQLAlchemy async)
- **Phase 5**: Unit tests, performance profiling

## Dependencies

- fastapi>=0.115.0
- uvicorn[standard]>=0.30.0
- pydantic>=2.0.0
- pydantic-settings>=2.0.0
- websockets>=12.0
- python-dotenv>=1.0.0

## Known Issues / TODs

- Camera endpoints are placeholders (GET /api/cameras, POST /api/cameras/calibrate)
- Stats calculation not implemented (`game_over` message has empty stats)
- Turn throws not included in `turn_complete` broadcast
- No rate limiting on manual throws (add in production)

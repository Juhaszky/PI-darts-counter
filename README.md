# PI Darts Counter - Backend

Automated darts scoring system backend built with FastAPI.

## Features

- **REST API** - Game management, player management, manual throw input
- **WebSocket API** - Real-time game updates and communication
- **Game Logic** - 301 and 501 game modes with bust detection
- **In-memory Storage** - Fast game state management (database integration coming soon)
- **CORS Support** - Ready for React Native mobile app integration

## Tech Stack

- **Python 3.12+**
- **FastAPI 0.115+** - Web framework
- **Uvicorn 0.30+** - ASGI server
- **Pydantic 2.0+** - Data validation
- **WebSockets 12.0+** - Real-time communication

## Project Structure

```
PI-darts-counter/
├── main.py                 # FastAPI application entry point
├── config.py               # Configuration management
├── requirements.txt        # Python dependencies
├── .env.example           # Environment variables template
│
├── api/                   # API layer
│   ├── routes.py          # REST API endpoints
│   └── websocket.py       # WebSocket handlers
│
├── game/                  # Game logic
│   ├── game_manager.py    # In-memory game state manager
│   ├── game_logic.py      # 301/501 game rules
│   └── score_calculator.py # Score calculation
│
├── models/                # Pydantic data models
│   ├── game.py           # Game models
│   ├── player.py         # Player models
│   └── throw.py          # Throw models
│
├── camera/                # Camera integration (coming soon)
├── database/              # Database layer (coming soon)
└── tests/                 # Unit tests
```

## Setup

### 1. Clone the repository

```bash
git clone <repository-url>
cd PI-darts-counter
```

### 2. Create virtual environment

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/Mac
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment

```bash
cp .env.example .env
# Edit .env with your configuration
```

### 5. Run the server

```bash
# Development mode (with auto-reload)
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Production mode
uvicorn main:app --host 0.0.0.0 --port 8000
```

The API will be available at:
- **API Documentation**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc
- **WebSocket**: ws://localhost:8000/ws/{game_id}

## API Endpoints

### Games

- `POST /api/games` - Create a new game
- `GET /api/games/{game_id}` - Get game state
- `POST /api/games/{game_id}/start` - Start game
- `POST /api/games/{game_id}/reset` - Reset game
- `DELETE /api/games/{game_id}` - Delete game

### Throws

- `POST /api/games/{game_id}/throw` - Record manual throw
- `POST /api/games/{game_id}/undo` - Undo last throw

### System

- `GET /api/health` - Health check
- `GET /api/cameras` - Camera status (placeholder)
- `POST /api/cameras/calibrate` - Camera calibration (placeholder)

## WebSocket Protocol

### Server → Client Messages

- `game_state` - Full game state (sent on connect)
- `throw_detected` - Throw recorded
- `bust` - Player busted
- `turn_complete` - Turn finished
- `game_over` - Game finished
- `error` - Error message

### Client → Server Messages

- `manual_score` - Record manual throw (camera override)
- `undo_throw` - Undo last throw
- `next_turn` - Force next player turn

## Example Usage

### Create a new game

```bash
curl -X POST http://localhost:8000/api/games \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "501",
    "double_out": false,
    "players": [
      {"name": "Peter"},
      {"name": "Anna"}
    ]
  }'
```

### Connect via WebSocket

```javascript
const ws = new WebSocket('ws://localhost:8000/ws/{game_id}');

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log('Received:', message);
};

// Send manual score
ws.send(JSON.stringify({
  type: 'manual_score',
  data: { segment: 20, multiplier: 3 }
}));
```

## Development Status

**Current Phase**: Backend Infrastructure (Phase 1-2)

- ✅ Project structure
- ✅ Configuration management
- ✅ Pydantic models
- ✅ Game logic (301/501)
- ✅ Score calculator
- ✅ In-memory GameManager
- ✅ REST API endpoints
- ✅ WebSocket API
- ⏳ Camera integration (Phase 3)
- ⏳ Database persistence (Future)
- ⏳ Unit tests

## Next Steps

1. **Camera Integration** (Phase 3)
   - Camera initialization
   - Dart detection pipeline
   - Calibration system

2. **Mobile App** (Phase 4)
   - React Native project
   - WebSocket integration
   - Real-time UI updates

3. **Testing & Optimization** (Phase 5)
   - Unit tests
   - Integration tests
   - Performance tuning

## License

MIT

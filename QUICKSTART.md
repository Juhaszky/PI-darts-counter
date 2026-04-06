# Quick Start Guide

## Backend Setup & Run

### 1. Telepítés

```bash
# Lépj be a projekt könyvtárába
cd PI-darts-counter

# Hozz létre virtual environmentet
python -m venv .venv

# Aktiváld a virtual environmentet
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# Telepítsd a függőségeket
pip install -r requirements.txt
```

### 2. Konfiguráció

```bash
# Másold le a .env példát
cp .env.example .env

# Opcionális: szerkeszd a .env fájlt igény szerint
# notepad .env  # Windows
# nano .env     # Linux/Mac
```

### 3. Szerver indítása

```bash
# Fejlesztői mód (auto-reload)
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

A szerver elindul és elérhető lesz:
- API dokumentáció: http://localhost:8000/docs
- WebSocket: ws://localhost:8000/ws/{game_id}

## API Tesztelés

### 1. Új játék létrehozása

```bash
curl -X POST http://localhost:8000/api/games \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "501",
    "double_out": false,
    "players": [
      {"name": "Péter"},
      {"name": "Anna"}
    ]
  }'
```

Válasz:
```json
{
  "game_id": "550e8400-e29b-41d4-a716-446655440000",
  "mode": "501",
  "status": "waiting",
  "created_at": "2026-02-25T14:30:00Z"
}
```

### 2. Játék indítása

```bash
curl -X POST http://localhost:8000/api/games/{game_id}/start
```

### 3. Kézi dobás rögzítése

```bash
curl -X POST http://localhost:8000/api/games/{game_id}/throw \
  -H "Content-Type: application/json" \
  -d '{
    "segment": 20,
    "multiplier": 3
  }'
```

### 4. Játékállapot lekérdezése

```bash
curl http://localhost:8000/api/games/{game_id}
```

## WebSocket Tesztelés

### JavaScript példa

```javascript
const gameId = '550e8400-e29b-41d4-a716-446655440000';
const ws = new WebSocket(`ws://localhost:8000/ws/${gameId}`);

ws.onopen = () => {
  console.log('Kapcsolódva!');
};

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log('Üzenet:', message);

  if (message.type === 'game_state') {
    console.log('Játék állapot:', message.data);
  } else if (message.type === 'throw_detected') {
    console.log('Dobás:', message.data.segment_name, message.data.total_score);
  }
};

// Kézi dobás küldése
ws.send(JSON.stringify({
  type: 'manual_score',
  data: { segment: 20, multiplier: 3 }
}));
```

## Hibakeresés

### Szerver nem indul

1. Ellenőrizd, hogy a port szabad-e:
   ```bash
   # Windows
   netstat -ano | findstr :8000
   # Linux/Mac
   lsof -i :8000
   ```

2. Használj másik portot:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8001 --reload
   ```

### Import hibák

```bash
# Ellenőrizd, hogy a virtual environment aktív-e
which python  # Linux/Mac
where python  # Windows

# Újratelepítés
pip install --upgrade -r requirements.txt
```

## Következő lépések

1. **Frontend fejlesztés**: Csatlakozz a React Native alkalmazással
2. **Kamera integráció**: Valós dart detektálás hozzáadása
3. **Tesztelés**: Unit és integrációs tesztek írása

## További információ

- Teljes dokumentáció: `README.md`
- Tervezési dokumentum: `DESIGN.md`
- API dokumentáció: http://localhost:8000/docs

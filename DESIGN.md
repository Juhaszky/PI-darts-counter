# 🎯 Darts Számláló Alkalmazás – Tervdokumentum

**Projekt:** PI Darts Counter
**Verzió:** 1.0
**Dátum:** 2026-02-25
**Platform:** Raspberry Pi 5 + Natív Mobil Alkalmazás

---

## Tartalomjegyzék

1. [Rendszer áttekintés](#1-rendszer-áttekintés)
2. [Hardver specifikáció](#2-hardver-specifikáció)
3. [Kamera elrendezés és képfeldolgozás](#3-kamera-elrendezés-és-képfeldolgozás)
4. [Szerver oldal architektúra](#4-szerver-oldal-architektúra)
5. [Játék logika](#5-játék-logika)
6. [Kommunikációs protokoll – WebSocket API](#6-kommunikációs-protokoll--websocket-api)
7. [REST API végpontok](#7-rest-api-végpontok)
8. [Mobil alkalmazás](#8-mobil-alkalmazás)
9. [Adatbázis terv](#9-adatbázis-terv)
10. [Könyvtárstruktúra](#10-könyvtárstruktúra)
11. [Fejlesztési ütemterv](#11-fejlesztési-ütemterv)
12. [Technológiai stack](#12-technológiai-stack)

---

## 1. Rendszer áttekintés

### Architektúra diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    RASPBERRY PI 5                           │
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                  │
│  │ Kamera 1 │  │ Kamera 2 │  │ Kamera 3 │                  │
│  │ (bal)    │  │ (jobb)   │  │ (felső)  │                  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘                  │
│       │              │              │                        │
│       └──────────────┼──────────────┘                        │
│                      │                                       │
│              ┌───────▼────────┐                              │
│              │  Kép-         │                              │
│              │  feldolgozás  │                              │
│              │  (OpenCV +    │                              │
│              │  NumPy)       │                              │
│              └───────┬────────┘                              │
│                      │                                       │
│              ┌───────▼────────┐                              │
│              │  Játék Logika  │                              │
│              │  (301 / 501)   │                              │
│              └───────┬────────┘                              │
│                      │                                       │
│              ┌───────▼────────┐                              │
│              │  FastAPI       │                              │
│              │  Szerver       │                              │
│              │  (WebSocket +  │                              │
│              │  REST API)     │                              │
│              └───────┬────────┘                              │
└──────────────────────┼──────────────────────────────────────┘
                       │  WiFi / LAN
                       │
                    │
          ┌─────────▼──────────┐
          │   React Native App  │
          │   (TypeScript)      │
          │                     │
          │  iOS   │  Android   │
          └─────────────────────┘
```

### Működési folyamat

```
Nyíl dobás → Kamerák rögzítik → Képfeldolgozás → Pontszámítás
→ Játék logika frissítés → WebSocket üzenet küldés
→ Mobil app frissítés → Kijelző
```

---

## 2. Hardver specifikáció

### Raspberry Pi 5
- **CPU:** Broadcom BCM2712, 4-mag ARM Cortex-A76 @ 2.4GHz
- **RAM:** 8 GB LPDDR4X
- **OS:** Raspberry Pi OS (64-bit)
- **Tápellátás:** 5V / 5A USB-C
- **Hálózat:** WiFi 802.11ac / Gigabit Ethernet

### Kamerák (3 db)
| Kamera | Elhelyezés | Feladata |
|--------|-----------|---------|
| Kamera 1 | Bal oldal (~45°) | Nyíl X pozíció meghatározása |
| Kamera 2 | Jobb oldal (~45°) | Nyíl X pozíció megerősítése |
| Kamera 3 | Felülről (90°) | Nyíl Y pozíció és szegmens |

**Javasolt kameramodellek:**
- Raspberry Pi Camera Module 3 (12 MP) – legjobb kompatibilitás
- USB Webcam 1080p – alternatíva

### Darts tábla referencia koordináták
```
         0 (top)
    20      1
  18    5      12   (szegmensek óramutató járásával)
14   10   6    9    15
11   7    8   16    2
  19   3      17
    12      4
         (bottom)
```

---

## 3. Kamera elrendezés és képfeldolgozás

### 3.1 Kamera kalibrálás

Minden kamerát kalibrálni kell a szoba felvétele előtt:

```python
# Kalibrálási lépések:
# 1. Sakktábla minta segítségével belső paraméterek meghatározása
# 2. Torzítás korrekció (lens distortion)
# 3. Sztereó kalibrálás a kamerák között (3D pozíció számításhoz)
```

**Kalibrálási adatok mentése:**
```json
{
  "camera_matrix": [[fx, 0, cx], [0, fy, cy], [0, 0, 1]],
  "dist_coeffs": [k1, k2, p1, p2, k3],
  "rvecs": [...],
  "tvecs": [...]
}
```

### 3.2 Nyíl detektálás pipeline

```
Videó frame bevitel
       ↓
Háttér szubtrakció (MOG2 / KNN)
       ↓
Különbség maszk kiszámítása
       ↓
Morfológiai műveletek (zaj eltávolítás)
       ↓
Kontúr keresés
       ↓
Nyíl hegyének lokalizálása (legkisebb pontnak keresése)
       ↓
3D pozíció számítás (triangulation – 2+ kamerából)
       ↓
Darts tábla koordinátára vetítés
       ↓
Szegmens és szorzó azonosítás
       ↓
Pontszám kiadása
```

### 3.3 Szegmens azonosítás

```python
# Darts tábla körülhatárolása:
# - Belső körök: bullseye (50 pont), bull (25 pont)
# - Tripla gyűrű: szegmens × 3
# - Dupla gyűrű (külső): szegmens × 2
# - Számított szegmensek (1-20)

SEGMENTS = [20, 1, 18, 4, 13, 6, 10, 15, 2, 17, 3, 19, 7, 16, 8, 11, 14, 9, 12, 5]

def get_segment(angle_deg: float, radius: float) -> tuple[int, int]:
    """
    angle_deg: 0-360 fok (0 = felső)
    radius: normalizált távolság a középponttól (0.0 - 1.0)
    return: (szegmens_érték, szorzó)  szorzó: 1, 2, 3 | 25, 50
    """
    # Bullseye
    if radius < 0.05:
        return (50, 1)
    # Bull
    if radius < 0.10:
        return (25, 1)
    # Darts szegmens szög számítás
    segment_idx = int((angle_deg + 9) / 18) % 20
    value = SEGMENTS[segment_idx]
    # Gyűrű meghatározás
    if 0.62 < radius < 0.68:
        multiplier = 3  # tripla
    elif 0.95 < radius < 1.0:
        multiplier = 2  # dupla
    else:
        multiplier = 1
    return (value, multiplier)
```

### 3.4 Dobás stabilitás detektálás

A pontszámot csak akkor rögzítjük, ha a nyíl legalább **1.5 másodpercig** azonos pozícióban maradt (nem mozog) – ezzel kizárjuk az átmeneti detektálást.

```python
STABILITY_THRESHOLD_FRAMES = 45  # 30fps × 1.5s
POSITION_TOLERANCE_PX = 5        # pixeles eltérés tolerancia
```

---

## 4. Szerver oldal architektúra

### 4.1 Modulstruktúra

```
server/
├── main.py                 # FastAPI alkalmazás belépési pont
├── config.py               # Konfigurációk (portok, kamera ID-k)
├── camera/
│   ├── __init__.py
│   ├── camera_manager.py   # Kamerák inicializálása, frame olvasás
│   ├── detector.py         # Nyíl detektálás logika (OpenCV)
│   └── calibration.py      # Kamera kalibrálás
├── game/
│   ├── __init__.py
│   ├── game_manager.py     # Játék állapot kezelő
│   ├── game_logic.py       # 301 / 501 szabályok
│   └── score_calculator.py # Pontszám számítás
├── api/
│   ├── __init__.py
│   ├── routes.py           # REST API végpontok
│   └── websocket.py        # WebSocket kezelő
├── models/
│   ├── game.py             # Játék adatmodellek (Pydantic)
│   ├── player.py           # Játékos modell
│   └── throw.py            # Dobás modell
└── database/
    ├── db.py               # SQLite kapcsolat
    └── repository.py       # CRUD műveletek
```

### 4.2 Fő komponensek

#### CameraManager
```python
class CameraManager:
    def __init__(self, camera_ids: list[int]):
        self.cameras: list[cv2.VideoCapture] = []
        self.detectors: list[DartDetector] = []

    async def start(self): ...
    async def capture_frames(self) -> list[np.ndarray]: ...
    def get_dart_position(self) -> tuple[float, float] | None: ...
```

#### GameManager
```python
class GameManager:
    def __init__(self, mode: Literal["301", "501"]):
        self.players: list[Player] = []
        self.current_player_idx: int = 0
        self.round: int = 1
        self.throws_this_turn: int = 0  # max 3 / kör

    def add_throw(self, score: int) -> ThrowResult: ...
    def next_player(self): ...
    def check_winner(self) -> Player | None: ...
    def reset(self): ...
```

### 4.3 Szerver indítás

```bash
# Fejlesztői mód
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Raspberry Pi produkció
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1
```

---

## 5. Játék logika

### 5.1 Támogatott játékmódok

| Mód | Kezdőpontszám | Befejezés |
|-----|--------------|-----------|
| 301 | 301 pont | Pontosan 0-ra kell csökkenteni |
| 501 | 501 pont | Pontosan 0-ra kell csökkenteni |

### 5.2 Szabályok

**Közös szabályok:**
- Minden játékos körönként **3 nyilat** dob
- A pontszámot **le kell vonni** a kezdőértékből
- Ha a levonás után **negatív** lenne → **BUST** (túllövés), az egész kör törlődik
- Ha a pontszám **pontosan 0** → a játékos **NYER**

**Double Out opció (opcionális konfiguráció):**
- Az utolsó nyílnak a **dupla gyűrűn** vagy **bullseye-on** kell landolnia

### 5.3 Állapotgép

```
[WAITING_FOR_PLAYERS]
         ↓ játék indítás
    [GAME_STARTED]
         ↓
  [PLAYER_N_TURN]  ←──────────────┐
         ↓                         │
  [WAITING_THROW]  (3x)            │
         ↓                         │
  [DART_DETECTED]                  │
         ↓                         │
  [SCORE_CALCULATED]               │
         ↓                         │
  [BUST?] → igen → kör törlés      │
         ↓ nem                     │
  [SCORE_APPLIED]                  │
         ↓                         │
  [WINNER?] → igen → [GAME_OVER]   │
         ↓ nem                     │
  [NEXT_PLAYER] ───────────────────┘
```

### 5.4 Pontszám számítás

```python
@dataclass
class ThrowResult:
    raw_score: int        # pl. 20
    multiplier: int       # 1, 2, 3
    total: int            # raw_score × multiplier
    is_bust: bool
    remaining: int        # maradék pontszám
    is_winner: bool
    segment_name: str     # pl. "T20", "D16", "BULL", "BULLSEYE"

def calculate_throw(segment: int, multiplier: int, current_score: int) -> ThrowResult:
    total = segment * multiplier
    new_score = current_score - total

    is_bust = new_score < 0 or new_score == 1  # 1-re nem lehet befejezni
    is_winner = new_score == 0

    # Double out esetén: is_winner = new_score == 0 and multiplier == 2

    return ThrowResult(
        raw_score=segment,
        multiplier=multiplier,
        total=total,
        is_bust=is_bust,
        remaining=current_score if is_bust else new_score,
        is_winner=is_winner,
        segment_name=f"{'T' if multiplier==3 else 'D' if multiplier==2 else ''}{segment}"
    )
```

---

## 6. Kommunikációs protokoll – WebSocket API

### 6.1 Kapcsolat

```
WebSocket URL: ws://<raspberry_ip>:8000/ws/{game_id}
```

### 6.2 Szerver → Kliens üzenetek

#### `game_state` – Teljes játék állapot (csatlakozáskor)
```json
{
  "type": "game_state",
  "data": {
    "game_id": "uuid",
    "mode": "501",
    "status": "in_progress",
    "round": 3,
    "players": [
      {
        "id": "uuid",
        "name": "Péter",
        "score": 287,
        "throws_this_turn": 1,
        "is_current": true
      },
      {
        "id": "uuid",
        "name": "Anna",
        "score": 341,
        "throws_this_turn": 0,
        "is_current": false
      }
    ],
    "current_player_id": "uuid",
    "last_throw": null
  }
}
```

#### `throw_detected` – Dobás detektálva
```json
{
  "type": "throw_detected",
  "data": {
    "player_id": "uuid",
    "player_name": "Péter",
    "segment": 20,
    "multiplier": 3,
    "total_score": 60,
    "segment_name": "T20",
    "remaining_score": 227,
    "is_bust": false,
    "throws_left": 2,
    "throw_number": 1
  }
}
```

#### `bust` – Túllövés
```json
{
  "type": "bust",
  "data": {
    "player_id": "uuid",
    "player_name": "Péter",
    "score_before": 32,
    "attempted_throw": 60,
    "score_restored": 32
  }
}
```

#### `turn_complete` – Kör vége
```json
{
  "type": "turn_complete",
  "data": {
    "player_id": "uuid",
    "throws": [
      {"segment_name": "T20", "total": 60},
      {"segment_name": "5", "total": 5},
      {"segment_name": "D16", "total": 32}
    ],
    "turn_total": 97,
    "next_player_id": "uuid"
  }
}
```

#### `game_over` – Játék vége
```json
{
  "type": "game_over",
  "data": {
    "winner_id": "uuid",
    "winner_name": "Péter",
    "final_throw": "D16",
    "total_rounds": 7,
    "stats": {
      "Péter": {"avg_per_dart": 32.4, "highest_turn": 140},
      "Anna": {"avg_per_dart": 28.1, "highest_turn": 121}
    }
  }
}
```

#### `camera_status` – Kamera állapot
```json
{
  "type": "camera_status",
  "data": {
    "cameras": [
      {"id": 0, "label": "Bal", "active": true},
      {"id": 1, "label": "Jobb", "active": true},
      {"id": 2, "label": "Felső", "active": false}
    ]
  }
}
```

#### `error` – Hiba
```json
{
  "type": "error",
  "data": {
    "code": "CAMERA_DISCONNECTED",
    "message": "A 2. kamera lecsatlakozott",
    "severity": "warning"
  }
}
```

### 6.3 Kliens → Szerver üzenetek

#### `manual_score` – Kézi pontszám (kamera hiba esetén)
```json
{
  "type": "manual_score",
  "data": {
    "segment": 20,
    "multiplier": 1
  }
}
```

#### `undo_throw` – Utolsó dobás visszavonása
```json
{
  "type": "undo_throw"
}
```

#### `next_turn` – Következő játékos (kézi továbblépés)
```json
{
  "type": "next_turn"
}
```

---

## 7. REST API végpontok

### Játékok

| Metódus | Végpont | Leírás |
|---------|---------|--------|
| `POST` | `/api/games` | Új játék létrehozása |
| `GET` | `/api/games/{game_id}` | Játék állapot lekérdezése |
| `POST` | `/api/games/{game_id}/start` | Játék indítása |
| `POST` | `/api/games/{game_id}/reset` | Játék visszaállítása |
| `DELETE` | `/api/games/{game_id}` | Játék törlése |

### Játékosok

| Metódus | Végpont | Leírás |
|---------|---------|--------|
| `POST` | `/api/games/{game_id}/players` | Játékos hozzáadása |
| `DELETE` | `/api/games/{game_id}/players/{player_id}` | Játékos eltávolítása |

### Kézi dobás

| Metódus | Végpont | Leírás |
|---------|---------|--------|
| `POST` | `/api/games/{game_id}/throw` | Kézi dobás rögzítése |
| `POST` | `/api/games/{game_id}/undo` | Utolsó dobás visszavonása |

### Rendszer

| Metódus | Végpont | Leírás |
|---------|---------|--------|
| `GET` | `/api/health` | Szerver állapot |
| `GET` | `/api/cameras` | Kamerák állapota |
| `POST` | `/api/cameras/calibrate` | Kalibrálás indítása |

### Példa kérések

#### Új játék létrehozása (POST /api/games)
```json
// Request
{
  "mode": "501",
  "double_out": false,
  "players": [
    {"name": "Péter"},
    {"name": "Anna"}
  ]
}

// Response
{
  "game_id": "550e8400-e29b-41d4-a716-446655440000",
  "mode": "501",
  "status": "waiting",
  "created_at": "2026-02-25T14:30:00Z"
}
```

---

## 8. Mobil alkalmazás

### 8.1 Technológia választás

**React Native (TypeScript)**
- Egyetlen kódbázis iOS + Android – valódi natív renderelés
- TypeScript típusbiztonság a teljes kódbázisban
- Expo managed workflow a gyors fejlesztéshez
- Kiváló WebSocket támogatás (`react-native` beépített `WebSocket` API)
- Zustand a könnyű, boilerplate-mentes state managementhez
- React Navigation a képernyők közötti navigációhoz

**Miért nem Flutter?**
- JavaScript/TypeScript ökoszisztéma – könnyebb webfejlesztőknek
- Natív modulok szélesebb közösségi támogatása
- Expo OTA updates lehetősége (Over-The-Air frissítések)

### 8.2 Képernyők

#### Főképernyő (Home Screen)
```
┌────────────────────────────┐
│      🎯 Darts Counter      │
│                            │
│  ┌──────────────────────┐  │
│  │  IP Cím: 192.168.1.5 │  │
│  │  Port:   8000        │  │
│  └──────────────────────┘  │
│                            │
│  [   Csatlakozás    ]      │
│                            │
│  Legutóbbi játékok:        │
│  • Péter vs Anna – 501     │
│  • Gábor vs Béla – 301     │
└────────────────────────────┘
```

#### Játék setup képernyő
```
┌────────────────────────────┐
│  ← Új Játék                │
│                            │
│  Játékmód:                 │
│  [301]  [501]              │
│                            │
│  Double out:  □ Ki  ■ Be  │
│                            │
│  Játékosok:                │
│  ┌──────────────────────┐  │
│  │ 👤 Péter         [x] │  │
│  │ 👤 Anna          [x] │  │
│  └──────────────────────┘  │
│  [+ Játékos hozzáadása]    │
│                            │
│  [  Játék indítása  ]      │
└────────────────────────────┘
```

#### Játék képernyő (Game Screen)
```
┌────────────────────────────┐
│  🎯 501 – 3. kör     [⚙]  │
├────────────────────────────┤
│  ← PÉTER          ANNA → │
│   287 pt           341 pt  │
│  ████████░░░░  ██████████░ │
├────────────────────────────┤
│         PÉTER KÖRE         │
│                            │
│   ┌──────┐ ┌──────┐ ┌──┐  │
│   │  T20  │ │      │ │  │  │
│   │  60   │ │  -   │ │- │  │
│   └──────┘ └──────┘ └──┘  │
│    1. nyíl   2. nyíl  3.  │
│                            │
│   Maradék: 227 pt          │
├────────────────────────────┤
│ [Visszavon] [Kézi pont]    │
└────────────────────────────┘
```

#### Statisztika képernyő
```
┌────────────────────────────┐
│  ← Statisztikák            │
│                            │
│  Átlag/nyíl:               │
│  Péter: 32.4  Anna: 28.1   │
│                            │
│  Legjobb kör:              │
│  Péter: 140   Anna: 121    │
│                            │
│  Kiszálló szegmensek:      │
│  [T20][T20][D20]           │
│                            │
│  Összes dobás: 63          │
└────────────────────────────┘
```

### 8.3 React Native projektstruktúra

```
mobile/
├── app.json                          # Expo konfiguráció
├── package.json
├── tsconfig.json
├── babel.config.js
├── src/
│   ├── App.tsx                       # Gyökér komponens, navigáció setup
│   ├── constants/
│   │   ├── theme.ts                  # Színek, betűméretek, spacing
│   │   └── config.ts                 # Alapértelmezett IP, port
│   ├── services/
│   │   ├── websocketService.ts       # WebSocket kapcsolat és eseménykezelés
│   │   └── apiService.ts             # REST API hívások (fetch/axios)
│   ├── store/
│   │   ├── gameStore.ts              # Zustand – játék állapot
│   │   └── connectionStore.ts        # Zustand – kapcsolat állapot
│   ├── types/
│   │   ├── game.types.ts             # Game, Player, Throw interfészek
│   │   └── websocket.types.ts        # WS üzenet típusok
│   ├── hooks/
│   │   ├── useWebSocket.ts           # WebSocket logika hook
│   │   └── useGame.ts                # Játék állapot hook
│   ├── screens/
│   │   ├── HomeScreen.tsx            # Főképernyő + csatlakozás
│   │   ├── SetupScreen.tsx           # Játék beállítása
│   │   ├── GameScreen.tsx            # Aktív játék képernyő
│   │   └── StatsScreen.tsx           # Statisztika képernyő
│   └── components/
│       ├── PlayerCard.tsx            # Játékos pontszám kártya
│       ├── ThrowSlots.tsx            # 3 dobás megjelenítő
│       ├── ManualScoreModal.tsx      # Kézi pontbevitel modal
│       ├── BustOverlay.tsx           # Bust animáció
│       └── ConnectionStatus.tsx      # WiFi kapcsolat jelző
└── README.md
```

### 8.4 WebSocket kapcsolat (React Native / TypeScript)

```typescript
// src/services/websocketService.ts

type MessageHandler = (event: WsEvent) => void;

class WebSocketService {
  private ws: WebSocket | null = null;
  private handlers: Set<MessageHandler> = new Set();
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private host: string = '';
  private port: number = 8000;
  private gameId: string = '';

  connect(host: string, port: number, gameId: string): void {
    this.host = host;
    this.port = port;
    this.gameId = gameId;

    const url = `ws://${host}:${port}/ws/${gameId}`;
    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      console.log('[WS] Kapcsolódva:', url);
      if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    };

    this.ws.onmessage = (e: MessageEvent) => {
      const event: WsEvent = JSON.parse(e.data);
      this.handlers.forEach((handler) => handler(event));
    };

    this.ws.onerror = (e) => {
      console.error('[WS] Hiba:', e);
    };

    this.ws.onclose = () => {
      console.warn('[WS] Kapcsolat megszakadt – újracsatlakozás 3s múlva');
      this.scheduleReconnect();
    };
  }

  private scheduleReconnect(): void {
    this.reconnectTimer = setTimeout(() => {
      this.connect(this.host, this.port, this.gameId);
    }, 3000);
  }

  send(type: string, data?: object): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type, data }));
    }
  }

  sendManualScore(segment: number, multiplier: number): void {
    this.send('manual_score', { segment, multiplier });
  }

  sendUndo(): void {
    this.send('undo_throw');
  }

  onMessage(handler: MessageHandler): () => void {
    this.handlers.add(handler);
    return () => this.handlers.delete(handler);   // unsubscribe fn
  }

  disconnect(): void {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.ws?.close();
    this.ws = null;
  }
}

export const wsService = new WebSocketService();
```

### 8.5 Zustand store (játék állapot)

```typescript
// src/store/gameStore.ts
import { create } from 'zustand';
import type { GameState, Player, Throw } from '../types/game.types';

interface GameStore {
  gameState: GameState | null;
  lastThrow: Throw | null;
  isBust: boolean;
  setGameState: (state: GameState) => void;
  applyThrow: (t: Throw) => void;
  setBust: (value: boolean) => void;
  reset: () => void;
}

export const useGameStore = create<GameStore>((set) => ({
  gameState: null,
  lastThrow: null,
  isBust: false,

  setGameState: (state) => set({ gameState: state }),

  applyThrow: (t) =>
    set((s) => ({
      lastThrow: t,
      gameState: s.gameState
        ? {
            ...s.gameState,
            players: s.gameState.players.map((p) =>
              p.id === t.playerId ? { ...p, score: t.remainingScore } : p
            ),
          }
        : null,
    })),

  setBust: (value) => set({ isBust: value }),
  reset: () => set({ gameState: null, lastThrow: null, isBust: false }),
}));
```

### 8.6 useWebSocket hook

```typescript
// src/hooks/useWebSocket.ts
import { useEffect } from 'react';
import { wsService } from '../services/websocketService';
import { useGameStore } from '../store/gameStore';
import type { WsEvent } from '../types/websocket.types';

export function useWebSocket() {
  const { setGameState, applyThrow, setBust } = useGameStore();

  useEffect(() => {
    const unsubscribe = wsService.onMessage((event: WsEvent) => {
      switch (event.type) {
        case 'game_state':
          setGameState(event.data);
          break;
        case 'throw_detected':
          applyThrow(event.data);
          setBust(false);
          break;
        case 'bust':
          setBust(true);
          break;
        case 'game_over':
          // navigáció a stats képernyőre
          break;
      }
    });

    return unsubscribe;
  }, []);
}
```

### 8.7 TypeScript típusok

```typescript
// src/types/game.types.ts

export type GameMode = '301' | '501';
export type GameStatus = 'waiting' | 'in_progress' | 'finished';

export interface Player {
  id: string;
  name: string;
  score: number;
  throwsThisTurn: number;
  isCurrent: boolean;
}

export interface GameState {
  gameId: string;
  mode: GameMode;
  status: GameStatus;
  round: number;
  players: Player[];
  currentPlayerId: string;
}

export interface Throw {
  playerId: string;
  playerName: string;
  segment: number;
  multiplier: number;
  totalScore: number;
  segmentName: string;        // "T20", "D16", "BULL"
  remainingScore: number;
  isBust: boolean;
  throwsLeft: number;
  throwNumber: number;        // 1 | 2 | 3
}

// src/types/websocket.types.ts
export type WsEventType =
  | 'game_state'
  | 'throw_detected'
  | 'bust'
  | 'turn_complete'
  | 'game_over'
  | 'camera_status'
  | 'error';

export interface WsEvent {
  type: WsEventType;
  data: any;
}
```

---

## 9. Adatbázis terv

**Motor:** SQLite (beépített, Raspberry Pi-ra ideális)
**ORM:** SQLAlchemy (async)

### Táblák

```sql
-- Játékok
CREATE TABLE games (
    id          TEXT PRIMARY KEY,      -- UUID
    mode        TEXT NOT NULL,         -- '301' | '501'
    status      TEXT NOT NULL,         -- 'waiting' | 'in_progress' | 'finished'
    double_out  INTEGER DEFAULT 0,     -- boolean
    winner_id   TEXT,
    created_at  TEXT NOT NULL,
    finished_at TEXT,
    FOREIGN KEY (winner_id) REFERENCES players(id)
);

-- Játékosok
CREATE TABLE players (
    id         TEXT PRIMARY KEY,       -- UUID
    game_id    TEXT NOT NULL,
    name       TEXT NOT NULL,
    score      INTEGER NOT NULL,       -- jelenlegi pontszám
    order_idx  INTEGER NOT NULL,       -- dobási sorrend
    FOREIGN KEY (game_id) REFERENCES games(id)
);

-- Dobások
CREATE TABLE throws (
    id          TEXT PRIMARY KEY,      -- UUID
    game_id     TEXT NOT NULL,
    player_id   TEXT NOT NULL,
    round       INTEGER NOT NULL,
    throw_num   INTEGER NOT NULL,      -- 1, 2, 3
    segment     INTEGER NOT NULL,      -- 1-20, 25
    multiplier  INTEGER NOT NULL,      -- 1, 2, 3
    total       INTEGER NOT NULL,
    is_bust     INTEGER DEFAULT 0,
    timestamp   TEXT NOT NULL,
    FOREIGN KEY (game_id) REFERENCES games(id),
    FOREIGN KEY (player_id) REFERENCES players(id)
);
```

---

## 10. Könyvtárstruktúra

```
PI-darts-counter/
├── DESIGN.md                    # Ez a fájl
├── README.md
├── requirements.txt
├── .env.example
├── main.py                      # FastAPI belépési pont
├── config.py                    # Konfiguráció
│
├── camera/                      # Képfeldolgozás modul
│   ├── __init__.py
│   ├── camera_manager.py
│   ├── detector.py
│   ├── calibration.py
│   └── calibration_data/        # Kamera kalibrálási adatok
│       ├── camera_0.json
│       ├── camera_1.json
│       └── camera_2.json
│
├── game/                        # Játék logika
│   ├── __init__.py
│   ├── game_manager.py
│   ├── game_logic.py
│   └── score_calculator.py
│
├── api/                         # API réteg
│   ├── __init__.py
│   ├── routes.py
│   └── websocket.py
│
├── models/                      # Pydantic adatmodellek
│   ├── __init__.py
│   ├── game.py
│   ├── player.py
│   └── throw.py
│
├── database/                    # Adatbázis réteg
│   ├── __init__.py
│   ├── db.py
│   ├── repository.py
│   └── darts.db                 # SQLite fájl (gitignore)
│
├── tests/                       # Tesztek
│   ├── test_game_logic.py
│   ├── test_score_calculator.py
│   └── test_detector.py
│
└── mobile/                      # React Native (Expo) mobil app
    ├── src/
    │   ├── screens/
    │   ├── components/
    │   ├── services/
    │   ├── store/
    │   ├── hooks/
    │   └── types/
    ├── app.json
    ├── package.json
    ├── tsconfig.json
    └── README.md
```

---

## 11. Fejlesztési ütemterv

### Fázis 1 – Alapok (1-2. hét)
- [x] FastAPI projekt setup (`main.py`)
- [ ] Projekt struktúra kialakítása
- [ ] Konfigurációs rendszer (`config.py`, `.env`)
- [ ] SQLite adatbázis és modellek
- [ ] Játék logika implementálása (301 / 501 szabályok)
- [ ] Alapvető REST API végpontok
- [ ] Unit tesztek a játék logikára

### Fázis 2 – WebSocket (2-3. hét)
- [ ] WebSocket szerver implementálása
- [ ] Esemény rendszer (GameEvent, broadcast)
- [ ] Kapcsolat kezelés (reconnect, disconnect)
- [ ] Kézi pontszám bevitel API-n keresztül

### Fázis 3 – Kamera integráció (3-5. hét)
- [ ] Kamera inicializálás (3 kamera)
- [ ] Háttér szubtrakció pipeline
- [ ] Nyíl hegy detektálás
- [ ] Kamera kalibrálás script
- [ ] 3D pozíció számítás (triangulation)
- [ ] Szegmens és szorzó azonosítás
- [ ] Stabilitás szűrő (1.5s stabilizáció)

### Fázis 4 – Mobil alkalmazás (4-6. hét)
- [ ] React Native + Expo projekt setup (`npx create-expo-app`)
- [ ] TypeScript konfiguráció, ESLint, Prettier
- [ ] Zustand store struktúra (gameStore, connectionStore)
- [ ] WebSocket service implementálása (reconnect logika)
- [ ] REST API service (fetch wrapper)
- [ ] React Navigation setup (Stack Navigator)
- [ ] HomeScreen – IP/port bevitel + csatlakozás gomb
- [ ] SetupScreen – játékmód, játékosok hozzáadása
- [ ] GameScreen – real-time dobás megjelenítés, bust animáció
- [ ] ManualScoreModal – kézi pontbevitel darts tábla UI
- [ ] StatsScreen – kör összefoglaló, statisztikák
- [ ] iOS + Android tesztelés (Expo Go)

### Fázis 5 – Finomítás és tesztelés (6-8. hét)
- [ ] Valós tesztelés darts táblával
- [ ] Detektálás pontosság javítása
- [ ] Hibakezelés és reconnect logika
- [ ] UI/UX finomítás
- [ ] Raspberry Pi teljesítmény optimalizálás
- [ ] Dokumentáció

---

## 12. Technológiai stack

### Backend (Raspberry Pi 5)

| Technológia | Verzió | Feladat |
|------------|--------|---------|
| Python | 3.12+ | Programozási nyelv |
| FastAPI | 0.115+ | Web framework (REST + WebSocket) |
| Uvicorn | 0.30+ | ASGI szerver |
| OpenCV (cv2) | 4.10+ | Képfeldolgozás, kamera kezelés |
| NumPy | 2.0+ | Matematikai számítások |
| SQLAlchemy | 2.0+ | Adatbázis ORM |
| aiosqlite | 0.20+ | Async SQLite |
| Pydantic | 2.0+ | Adatvalidáció |
| python-multipart | - | Fájlfeltöltés |

### Mobil (React Native + Expo)

| Technológia | Verzió | Feladat |
|------------|--------|---------|
| React Native | 0.76+ | Natív UI framework |
| Expo | SDK 52+ | Managed workflow, build tooling |
| TypeScript | 5.x | Típusbiztos programozási nyelv |
| Zustand | 5.x | Könnyűsúlyú state management |
| React Navigation | 7.x | Képernyők közötti navigáció |
| Axios | 1.x | REST API hívások |
| `@react-native-async-storage` | 2.x | Lokális beállítás tárolás (IP, port) |
| Expo Haptics | - | Rezgés visszajelzés dobásnál |
| React Native Reanimated | 3.x | Gördülékeny animációk (bust, nyerés) |

### Fejlesztői eszközök

| Eszköz | Feladat |
|--------|---------|
| Git | Verziókövetés |
| pytest | Python tesztek |
| Docker (opcionális) | Konténerizálás |
| Raspberry Pi OS | Szerver OS |

---

## Konfigurációs példa (`.env`)

```env
# Server
HOST=0.0.0.0
PORT=8000
DEBUG=false

# Cameras
CAMERA_0_ID=0
CAMERA_1_ID=1
CAMERA_2_ID=2
CAMERA_FPS=30
STABILITY_FRAMES=45

# Game
DEFAULT_MODE=501
DOUBLE_OUT=false

# Database
DATABASE_URL=sqlite+aiosqlite:///./database/darts.db
```

---

## Ismert kihívások és megoldások

| Kihívás | Megoldás |
|---------|---------|
| Látási zavar (nyilak takarják egymást) | Több kameraszög + legjobb konfidencia alapján döntés |
| Kamera szinkronizálás | Timestamp alapú frame párosítás |
| Reflektálás / világítás | IR szűrő vagy dedikált LED megvilágítás |
| Raspberry Pi CPU terhelés | Frame rate csökkentés detektálás nélküli időszakban |
| Hálózati megszakítás | Automatikus reconnect a mobil appban (exponential backoff) |
| Pontatlan detektálás | Kézi felülírás lehetősége a mobil appban |

---

*Tervdokumentum vége – PI Darts Counter v1.0*

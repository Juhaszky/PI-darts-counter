# Database Layer Design Notes

## File Map
- `database/models.py` — SQLAlchemy ORM table definitions
- `database/db.py` — engine, session factory, get_db(), init_db()
- `database/repository.py` — all DB queries
- `database/__init__.py` — public re-exports

## ORM Model Decisions

### Boolean columns stored as Integer
SQLite has no native BOOLEAN type. `double_out` (GameRecord) and `is_bust`
(ThrowRecord) are declared as `Integer` (0/1). Conversion happens at the
repository boundary: `int(bool_val)` on write, `bool(int_val)` on read.

### Relationships declared but lazy-loaded
All `relationship()` calls use `lazy="select"` (the SQLAlchemy default).
They exist for ORM convenience but are never relied on in repository queries —
all joins are written explicitly with `select(...).join(...)`. This avoids
N+1 query surprises.

### Cascade delete
Both `PlayerRecord` and `ThrowRecord` have `ondelete="CASCADE"` on their
foreign keys. The ORM side also uses `cascade="all, delete-orphan"` on
`GameRecord.players` and `GameRecord.throws` so deleting a GameRecord via
the ORM cleans up child rows automatically.

## Engine and Session

### check_same_thread=False
Required for SQLite + aiosqlite. aiosqlite uses a background thread for I/O;
without this flag SQLite raises "SQLite objects created in a thread can only
be used in that same thread."

### expire_on_commit=False
Prevents SQLAlchemy from marking ORM objects as expired after `commit()`.
Without this, accessing any attribute on an object after the session closes
would trigger a lazy-load on a dead session and raise `DetachedInstanceError`.

### get_db() rolls back on exception
The generator always calls `rollback()` on any exception so partial writes
never leak into the database. FastAPI propagates the exception to the HTTP
layer after rollback.

## Repository Patterns

### merge() for upserts
`save_game` and `save_throw` use `session.merge()`. This issues an INSERT if
the PK does not exist, or an UPDATE if it does. This makes both functions
idempotent — safe to call again after a crash without duplicating rows.

### Deterministic throw IDs
`save_throw` generates its UUID with `uuid.uuid5(NAMESPACE_OID, ...)` from a
string combining game_id + player_id + round + throw_num. The same throw
always maps to the same UUID, so `merge()` becomes a true no-op on replay
rather than a duplicate-key error.

### finish_game uses UPDATE, not load+modify
Avoids a SELECT round-trip. One targeted `update(GameRecord).where(...).values(...)`
is all that is needed to close out a game record.

### Aggregate queries stay in the DB
`get_game_history` and `get_player_stats` use `func.count`, `func.sum`, and
`func.count(col.distinct())` via SQLAlchemy core expressions. No Python loops
over result sets — this keeps memory usage O(1) relative to history size.

## Testing Notes
- Use an in-memory SQLite URL (`sqlite+aiosqlite:///:memory:`) in tests.
- Call `init_db()` once per test session to create tables.
- Each test should use its own `AsyncSession` from a fresh `async_sessionmaker`
  bound to the test engine, so tests are isolated.
- `merge()` idempotency can be verified by calling `save_game` twice with the
  same game object and asserting the row count stays at 1.

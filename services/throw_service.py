"""
Core gameplay service for PI Darts Counter.

ThrowService is the single orchestration point for dart throw processing and
undo operations.  It coordinates the two persistence layers:

  - GameManager  — authoritative in-memory state (fast, synchronous)
  - repository   — SQLite persistence (async, session-scoped)

Isolation rationale
-------------------
Throw processing is intentionally separated from game lifecycle management
(GameService) so that game-rule changes — new modes, double-in, cricket —
can be absorbed here without touching player management or lifecycle code.
The Open/Closed principle applies directly: extend ThrowService for new rules,
leave the other services untouched.

Transaction ownership
---------------------
Every method accepts ``db: AsyncSession`` as its first argument.  The caller
(route handler or WebSocket handler) owns the transaction: ``get_db()``
auto-commits on a clean return and rolls back on any unhandled exception.
ThrowService never calls ``db.commit()`` or ``db.rollback()``.

Critical ordering in process_throw
-----------------------------------
``round_before`` and ``throw_num`` are captured from the in-memory state
*before* calling ``manager.process_throw()``.  The manager immediately
advances game state on a valid throw — it may end the turn, increment the
round, or flip status to "finished".  Capturing these values after the call
would write the wrong round/throw_num to the database row.
"""
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from database import repository as repo
from game.game_manager import GameManager
from models.player import Player
from models.throw import ThrowResult

logger = logging.getLogger(__name__)


class ThrowService:
    """
    Processes dart throws and undos.

    This is the core gameplay service.  It coordinates the in-memory state
    mutation (GameManager) with atomic DB persistence within the caller's
    transaction.

    Instantiate with a GameManager so the service is independently testable
    without starting the singleton.  In production, inject the singleton via
    ``GameManager.get_instance()``.

    Critical ordering in process_throw:
      ``round_before`` and ``throw_num`` must be captured BEFORE calling
      ``manager.process_throw()``, because the manager immediately advances
      game state (turn transition, round increment, game-over).  Capturing
      after the call would record the wrong DB row metadata.
    """

    def __init__(self, game_manager: GameManager) -> None:
        """
        Initialise the service with an injected GameManager.

        Args:
            game_manager: The shared in-memory game state manager.
        """
        self._manager = game_manager

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def process_throw(
        self,
        db: AsyncSession,
        game_id: str,
        segment: int,
        multiplier: int,
    ) -> Optional[ThrowResult]:
        """
        Apply a throw, persist it, sync the player's score, and stamp
        game-over if the throw wins the game.

        Persistence sequence (all writes share the same ``db`` session and
        are committed atomically by the caller):
          1. Persist the throw record via ``repo.save_throw``.
          2. Update the throwing player's score in the DB via
             ``repo.update_player_score`` using the post-throw in-memory
             value (which is already bust-corrected or zeroed by the manager).
          3. If the game transitioned to ``"finished"``, call
             ``repo.finish_game`` to stamp winner_id and finished_at.

        Args:
            db:         Active async database session (caller owns commit).
            game_id:    UUID string of the game.
            segment:    Dart segment value (0–20, 25 for bull, 50 for bullseye).
            multiplier: Throw multiplier (1 = single, 2 = double, 3 = triple).

        Returns:
            ThrowResult if the throw was accepted and persisted.
            None if the game was not found, not in_progress, the throw failed
            validation, or the current player has already thrown 3 times this
            turn.
        """
        # --- 1. Capture pre-throw state ----------------------------------------
        # Must happen before manager.process_throw() mutates game state.
        game = self._manager.get_game(game_id)
        current_player = self._manager.get_current_player(game_id)

        if game is None or current_player is None:
            logger.warning(
                "process_throw: game %s or current player not found.",
                game_id,
            )
            return None

        # Snapshot the round number and per-turn throw counter.  The manager
        # increments both during turn transitions and round rollovers, so
        # reading them after the call would produce wrong DB metadata.
        round_before: int = game.round
        throw_num: int = current_player.throws_this_turn + 1

        # --- 2. Apply throw to in-memory state ------------------------------------
        throw_result: Optional[ThrowResult] = self._manager.process_throw(
            game_id, segment, multiplier
        )

        if throw_result is None:
            logger.warning(
                "process_throw: manager rejected throw for game %s "
                "(segment=%d, multiplier=%d).",
                game_id,
                segment,
                multiplier,
            )
            return None

        # --- 3. Persist throw record ----------------------------------------------
        await repo.save_throw(db, game_id, throw_result, round_before, throw_num)

        # --- 4. Sync throwing player's score to DB --------------------------------
        # Re-fetch from memory after mutation so we write the post-throw value:
        #   - Bust:   score is unchanged (manager did not deduct it).
        #   - Win:    score is 0.
        #   - Normal: score is current_score − total_score.
        players_after: list[Player] = self._manager.get_players(game_id)
        throwing_player: Optional[Player] = next(
            (p for p in players_after if p.id == throw_result.player_id),
            None,
        )

        if throwing_player is not None:
            await repo.update_player_score(
                db, throwing_player.id, throwing_player.score
            )
        else:
            # This should never happen: the manager only removes players via
            # delete_game, not during throw processing.  Log as an error and
            # continue — we have already persisted the throw record, so the
            # DB is not corrupted; only the score column will be stale.
            logger.error(
                "process_throw: player %s vanished from memory after throw "
                "in game %s — score column not updated.",
                throw_result.player_id,
                game_id,
            )

        # --- 5. Stamp game-over if the throw was a winning dart -------------------
        # Re-read game state after the manager has had a chance to call
        # _end_game(); status will be "finished" only if score reached 0.
        updated_game = self._manager.get_game(game_id)
        if updated_game is not None and updated_game.status == "finished":
            # Use the timestamp set by GameManager._end_game() so the DB and
            # in-memory state share an identical finished_at value.
            finished_at: datetime = updated_game.finished_at or datetime.utcnow()
            await repo.finish_game(
                db,
                game_id,
                updated_game.winner_id,  # type: ignore[arg-type]
                finished_at,
            )
            logger.info(
                "Game %s finished via throw. Winner: %s.",
                game_id,
                updated_game.winner_id,
            )

        logger.debug(
            "Throw processed: game=%s player=%s segment=%d mult=%d "
            "round=%d throw_num=%d bust=%s remaining=%d.",
            game_id,
            throw_result.player_id,
            segment,
            multiplier,
            round_before,
            throw_num,
            throw_result.is_bust,
            throw_result.remaining_score,
        )
        return throw_result

    async def undo_throw(self, db: AsyncSession, game_id: str) -> bool:
        """
        Undo the last recorded throw for a game.

        Applies the undo to in-memory state first (score restoration and
        throw counter decrement), then removes the matching DB row and syncs
        the affected player's score so both layers stay consistent.

        The DB score written is the post-undo in-memory value — not derived
        from the undone ThrowResult — because the manager is authoritative and
        already handles bust vs. normal restoration internally.

        Args:
            db:      Active async database session (caller owns commit).
            game_id: UUID string of the game.

        Returns:
            True if a throw was successfully undone.
            False if there was nothing to undo (no throws recorded, game not
            found, or game not in_progress).
        """
        # --- 1. Apply undo to in-memory state -------------------------------------
        undone: Optional[ThrowResult] = self._manager.undo_throw(game_id)

        if undone is None:
            logger.debug("undo_throw: nothing to undo for game %s.", game_id)
            return False

        # --- 2. Remove the matching row from the database -------------------------
        await repo.delete_latest_throw(db, game_id)

        # --- 3. Sync the restored player score to DB ------------------------------
        # Read score from memory after the manager has already restored it so we
        # write the correct value regardless of whether the undone throw was a
        # bust (score unchanged by the original throw) or a normal throw.
        players: list[Player] = self._manager.get_players(game_id)
        restored_player: Optional[Player] = next(
            (p for p in players if p.id == undone.player_id),
            None,
        )

        if restored_player is not None:
            await repo.update_player_score(
                db, restored_player.id, restored_player.score
            )
        else:
            # The player disappeared between the undo call and this read.
            # The DB throw row is already deleted; log the anomaly so it
            # can be investigated, but do not re-raise — the game is still
            # playable from the in-memory state.
            logger.error(
                "undo_throw: player %s not found in memory after undo "
                "for game %s — score column not updated.",
                undone.player_id,
                game_id,
            )

        logger.info(
            "Throw undone: game=%s player=%s segment=%d mult=%d bust=%s.",
            game_id,
            undone.player_id,
            undone.segment,
            undone.multiplier,
            undone.is_bust,
        )
        return True

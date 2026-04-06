"""
In-memory game state manager for PI Darts Counter.
Handles game creation, player management, throw processing, and state transitions.
"""
import uuid
from datetime import datetime
from typing import Optional

from models import (
    Game,
    GameCreate,
    GameMode,
    GameStatus,
    Player,
    PlayerCreate,
    ThrowResult,
)
from game.game_logic import get_starting_score, validate_throw, check_winner
from game.score_calculator import calculate_throw


class GameManager:
    """
    Manages all active games in memory.
    Singleton pattern - use get_instance() to access.
    """

    _instance: Optional["GameManager"] = None

    def __init__(self):
        """Initialize the game manager."""
        self.games: dict[str, Game] = {}
        self.players: dict[str, list[Player]] = {}  # game_id -> list of players
        self.throws_history: dict[str, list[ThrowResult]] = {}  # game_id -> list of throws
        self.turn_throws: dict[str, list[ThrowResult]] = {}  # game_id -> current turn throws

    @classmethod
    def get_instance(cls) -> "GameManager":
        """Get or create the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def create_game(self, game_data: GameCreate) -> tuple[Game, list[Player]]:
        """
        Create a new game with players.

        Args:
            game_data: Game creation data

        Returns:
            Tuple of (Game, list of Players)
        """
        game_id = str(uuid.uuid4())

        # Create game
        game = Game(
            id=game_id,
            mode=game_data.mode,
            double_out=game_data.double_out,
            status="waiting",
            round=1,
            current_player_idx=0,
            winner_id=None,
            created_at=datetime.utcnow(),
            finished_at=None,
        )

        # Create players
        starting_score = get_starting_score(game_data.mode)
        players = []
        for idx, player_data in enumerate(game_data.players):
            player = Player(
                id=str(uuid.uuid4()),
                game_id=game_id,
                name=player_data.name,
                score=starting_score,
                order_idx=idx,
                throws_this_turn=0,
                is_current=(idx == 0),
            )
            players.append(player)

        # Store in memory
        self.games[game_id] = game
        self.players[game_id] = players
        self.throws_history[game_id] = []
        self.turn_throws[game_id] = []

        return game, players

    def get_game(self, game_id: str) -> Optional[Game]:
        """Get a game by ID."""
        return self.games.get(game_id)

    def get_players(self, game_id: str) -> list[Player]:
        """Get all players for a game."""
        return self.players.get(game_id, [])

    def get_current_player(self, game_id: str) -> Optional[Player]:
        """Get the current player for a game."""
        game = self.get_game(game_id)
        if not game:
            return None

        players = self.get_players(game_id)
        if not players:
            return None

        return players[game.current_player_idx]

    def start_game(self, game_id: str) -> bool:
        """
        Start a game (transition from waiting to in_progress).

        Args:
            game_id: Game ID

        Returns:
            True if started successfully, False otherwise
        """
        game = self.get_game(game_id)
        if not game or game.status != "waiting":
            return False

        game.status = "in_progress"
        return True

    def process_throw(
        self, game_id: str, segment: int, multiplier: int
    ) -> Optional[ThrowResult]:
        """
        Process a throw for the current player.

        Args:
            game_id: Game ID
            segment: Segment value (0-20, 25, 50)
            multiplier: Multiplier (1, 2, 3)

        Returns:
            ThrowResult if successful, None if invalid
        """
        game = self.get_game(game_id)
        if not game or game.status != "in_progress":
            return None

        # Validate throw
        if not validate_throw(segment, multiplier):
            return None

        current_player = self.get_current_player(game_id)
        if not current_player:
            return None

        # Check if turn is complete (already threw 3 times)
        if current_player.throws_this_turn >= 3:
            return None

        # Calculate throw result
        throw_number = current_player.throws_this_turn + 1
        throws_left = 3 - throw_number

        if throw_number == 3:
          self._next_player(game_id)

        throw_result = calculate_throw(
            segment=segment,
            multiplier=multiplier,
            current_score=current_player.score,
            player_id=current_player.id,
            player_name=current_player.name,
            throw_number=throw_number,
            throws_left=throws_left,
            double_out=game.double_out,
        )

        # Store throw in history
        self.throws_history[game_id].append(throw_result)
        self.turn_throws[game_id].append(throw_result)

        # Update player state
        if throw_result.is_bust:
            # Bust: end turn immediately, restore score
            self._end_turn_with_bust(game_id, current_player)
        else:
            # Valid throw: update score and check for winner
            current_player.score = throw_result.remaining_score
            current_player.throws_this_turn += 1

            if check_winner(current_player.score):
                self._end_game(game_id, current_player.id)
            elif current_player.throws_this_turn >= 3:
                # Turn complete, move to next player
                self._next_player(game_id)

        return throw_result

    def undo_throw(self, game_id: str) -> bool:
        """
        Undo the last throw.

        Args:
            game_id: Game ID

        Returns:
            True if undo successful, False otherwise
        """
        game = self.get_game(game_id)
        if not game or game.status != "in_progress":
            return False

        throws = self.throws_history.get(game_id, [])
        if not throws:
            return False

        # Remove last throw
        last_throw = throws.pop()

        # Restore player score
        players = self.get_players(game_id)
        for player in players:
            if player.id == last_throw.player_id:
                # Restore score to before the throw
                player.score += last_throw.total_score
                player.throws_this_turn = max(0, player.throws_this_turn - 1)
                break

        return True

    def _end_turn_with_bust(self, game_id: str, player: Player) -> None:
        """
        End turn with a bust (restore score and move to next player).

        Args:
            game_id: Game ID
            player: Player who busted
        """
        # Bust: score remains unchanged (already handled in calculate_throw)
        # Reset turn throws
        player.throws_this_turn = 0
        self.turn_throws[game_id] = []
        self._next_player(game_id)

    def _next_player(self, game_id: str) -> None:
        """
        Move to the next player.

        Args:
            game_id: Game ID
        """
        game = self.get_game(game_id)
        if not game:
            return

        players = self.get_players(game_id)
        if not players:
            return

        # Reset current player
        current_player = players[game.current_player_idx]
        current_player.is_current = False
        current_player.throws_this_turn = 0

        # Move to next player
        game.current_player_idx = (game.current_player_idx + 1) % len(players)

        # Set new current player
        next_player = players[game.current_player_idx]
        next_player.is_current = True

        # Increment round when cycling back to first player
        if game.current_player_idx == 0:
            game.round += 1

        # Clear turn throws
        self.turn_throws[game_id] = []

    def _end_game(self, game_id: str, winner_id: str) -> None:
        """
        End the game with a winner.

        Args:
            game_id: Game ID
            winner_id: ID of the winning player
        """
        game = self.get_game(game_id)
        if not game:
            return

        game.status = "finished"
        game.winner_id = winner_id
        game.finished_at = datetime.utcnow()

    def reset_game(self, game_id: str) -> bool:
        """
        Reset a game to initial state.

        Args:
            game_id: Game ID

        Returns:
            True if reset successful, False otherwise
        """
        game = self.get_game(game_id)
        if not game:
            return False

        players = self.get_players(game_id)
        starting_score = get_starting_score(game.mode)

        # Reset game state
        game.status = "waiting"
        game.round = 1
        game.current_player_idx = 0
        game.winner_id = None
        game.finished_at = None

        # Reset players
        for idx, player in enumerate(players):
            player.score = starting_score
            player.throws_this_turn = 0
            player.is_current = (idx == 0)

        # Clear history
        self.throws_history[game_id] = []
        self.turn_throws[game_id] = []

        return True

    def delete_game(self, game_id: str) -> bool:
        """
        Delete a game and all associated data.

        Args:
            game_id: Game ID

        Returns:
            True if deleted, False if not found
        """
        if game_id not in self.games:
            return False

        del self.games[game_id]
        del self.players[game_id]
        del self.throws_history[game_id]
        del self.turn_throws[game_id]

        return True

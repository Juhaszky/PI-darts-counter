from database.repository import (
    create_player,
    get_all_player_names,
)

class GameService: 
    def __init__(self, game_repository):
        self.game_repository = game_repository

    def create_game(self, game_mode, players):
        return self.game_repository.create_game(game_mode, players)

    def get_game(self, game_id):
        return self.game_repository.get_game(game_id)

    def update_game(self, game_id, game_data):
        return self.game_repository.update_game(game_id, game_data)

    def delete_game(self, game_id):
        return self.game_repository.delete_game(game_id)
    async def create_player(self, db, player_name):
        return await create_player(db, player_name)
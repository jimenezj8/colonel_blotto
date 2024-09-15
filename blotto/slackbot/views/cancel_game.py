from typing import List

from slack_sdk.models import blocks
from slack_sdk.models.views import View

from models import Game


def load(games: List[Game]):
    game_options = [
        blocks.Option(
            value=f"{game.id}",
            label=f"Game {game.id}",  # TODO: meaningful identifiers
        )
        for game in games
    ]

    return View(
        type="modal",
        callback_id="cancel_game_select_game_view",
        title="Cancel Game",
        submit="Submit",
        close="Close",
        blocks=[
            blocks.InputBlock(
                label="Your Games",
                block_id="cancel_game_select_game_block",
                element=blocks.StaticSelectElement(
                    action_id="select_game",
                    options=game_options,
                    initial_option=game_options[0],
                ),
            )
        ],
    )

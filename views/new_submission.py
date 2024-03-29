import json
from typing import Iterable

from slack_sdk.models import blocks
from slack_sdk.models.views import View

import messages
from models import Game


def load(games: Iterable[Game]):
    game_options = [
        blocks.Option(
            value=f"{game.id}",
            label=f"Game {game.id}",
        )
        for game in games
    ]

    return View(
        type="modal",
        callback_id="strategy_submission_select_game_view",
        title="Select game",
        submit="Select",
        close="Cancel",
        blocks=[
            blocks.InputBlock(
                label="Active Games",
                block_id="strategy_submission_select_game_block",
                element=blocks.StaticSelectElement(
                    action_id="select_game",
                    options=game_options,
                    initial_option=game_options[0],
                ),
            )
        ],
    )


def update(
    game_id: int,
    round_num: int,
    round_soldiers: int,
    round_fields: int,
    round_rules: str,
) -> View:
    return View(
        type="modal",
        callback_id="strategy_submission_inputs_view",
        private_metadata=json.dumps({"game_id": game_id, "round_num": round_num}),
        title="Strategy submission",
        submit="Submit",
        close="Cancel",
        blocks=(
            [
                blocks.HeaderBlock(text="General rules"),
                blocks.SectionBlock(
                    text=blocks.MarkdownTextObject(text=messages.general_rules)
                ),
                blocks.HeaderBlock(text="Round rules"),
                blocks.SectionBlock(
                    text=blocks.MarkdownTextObject(text=round_rules),
                ),
                blocks.DividerBlock(),
                blocks.SectionBlock(
                    text=(
                        f"You have {round_soldiers} soldiers "
                        f"to distribute amongst {round_fields} fields. "
                        "Good luck, Major!"
                    ),
                ),
            ]
            + [
                blocks.InputBlock(
                    label=f"Field {field_num + 1}",
                    element=blocks.PlainTextInputElement(
                        action_id=f"field-{field_num + 1}-input",
                        placeholder=blocks.PlainTextObject(
                            text="Enter a number of soldiers"
                        ),
                    ),
                    block_id=f"field-{field_num + 1}-block",
                )
                for field_num in range(round_fields)
            ]
        ),
    )

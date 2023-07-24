import json

from slack_sdk.models import blocks
from slack_sdk.models.views import View

import messages


def load(
    game_id: int,
    round_num: int,
    round_soldiers: int,
    round_fields: int,
    round_rules: str,
) -> dict[str, any]:
    return View(
        type="modal",
        callback_id="submit_strategy",
        private_metadata=json.dumps({"game_id": game_id, "round_num": round_num}),
        title="Strategy submission",
        submit="Submit",
        close="Cancel",
        blocks=[
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
                    action_id=f"field-{field_num + 1}",
                    placeholder=blocks.PlainTextObject("Enter a number of soldiers"),
                ),
                block_id=f"field-{field_num + 1}",
            )
            for field_num in range(round.fields)
        ],
    )

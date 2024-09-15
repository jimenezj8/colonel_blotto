import datetime


def load(dt: datetime.datetime):
    return {
        "type": "modal",
        "callback_id": "new_game",
        "title": {"type": "plain_text", "text": "New Blotto Game"},
        "submit": {"type": "plain_text", "text": "New Game"},
        "close": {
            "type": "plain_text",
            "text": "Cancel",
        },
        "blocks": [
            {
                "block_id": "num_rounds",
                "type": "input",
                "element": {
                    "action_id": "num_rounds",
                    "type": "number_input",
                    "is_decimal_allowed": False,
                    "initial_value": "3",
                    "min_value": "1",
                },
                "label": {
                    "type": "plain_text",
                    "text": "Number of rounds",
                },
            },
            {
                "block_id": "round_length_num",
                "type": "input",
                "element": {
                    "action_id": "round_length_num",
                    "type": "number_input",
                    "is_decimal_allowed": False,
                    "initial_value": "1",
                    "min_value": "1",
                    "max_value": "60",
                },
                "label": {
                    "type": "plain_text",
                    "text": "Round Length - Number",
                },
            },
            {
                "block_id": "round_length_unit",
                "type": "input",
                "element": {
                    "action_id": "round_length_unit",
                    "type": "static_select",
                    "options": [
                        {
                            "text": {"type": "plain_text", "text": "Minutes"},
                            "value": "minutes",
                        },
                        {
                            "text": {"type": "plain_text", "text": "Hours"},
                            "value": "hours",
                        },
                        {
                            "text": {"type": "plain_text", "text": "Days"},
                            "value": "days",
                        },
                    ],
                    "initial_option": {
                        "text": {"type": "plain_text", "text": "Hours"},
                        "value": "hours",
                    },
                },
                "label": {
                    "type": "plain_text",
                    "text": "Round Length - Unit",
                },
            },
            {"type": "divider"},
            {
                "block_id": "datetime",
                "type": "input",
                "element": {
                    "action_id": "datetime",
                    "type": "datetimepicker",
                    "initial_date_time": int(dt.timestamp()),
                },
                "label": {
                    "type": "plain_text",
                    "text": "Signup Close",
                    "emoji": True,
                },
            },
            {"type": "divider"},
            {
                "block_id": "advertise_to_channels",
                "type": "input",
                "optional": False,
                "label": {
                    "type": "plain_text",
                    "text": "Select a channel to advertise the game to",
                },
                "element": {
                    "action_id": "advertise_to_channels",
                    "type": "channels_select",
                },
            },
        ],
    }

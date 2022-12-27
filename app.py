import datetime
import logging
import os
import sys
import time

import pytz
from slack_bolt import Ack, App, BoltContext, Respond
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk.web.client import WebClient

import blotto
import db_utils
import messages

BOT_TOKEN = os.getenv("BOT_TOKEN")
BOT_MEMBER_ID = "U03LWG7NAAY"

app = App(
    token=BOT_TOKEN,
    signing_secret=os.getenv("SIGNING_SECRET"),
    ignoring_self_events_enabled=False,
)

logging.basicConfig(level=logging.DEBUG)


@app.command("/cancel_game")
def cancel_game_command_handler(
    ack: Ack, client: WebClient, command: dict, logger: logging.Logger
):
    ack()

    user_id = command["user_id"]
    response_channel = command["channel_id"]
    game_id = int(command["text"])

    game = db_utils.get_game(game_id)
    if pytz.utc.localize(datetime.datetime.utcnow()) >= game.start:
        logger.info("Game has already begun, letting user know")

        client.chat_postEphemeral(
            token=BOT_TOKEN,
            user=user_id,
            channel=response_channel,
            text="The game you've requested to cancel has already begun, sorry.",
        )

    elif game.canceled:
        logger.info("Game has already been canceled, letting user know")

        client.chat_postEphemeral(
            token=BOT_TOKEN,
            user=user_id,
            channel=response_channel,
            text="The game you've requested to cancel was already canceled.",
        )

    logger.info(f"Canceling game {game_id} by request from {user_id}")
    db_utils.cancel_game(game_id)

    logger.info("Game canceled successfully")


@app.command("/modify_submission")
def modify_submission_command_handler(ack: Ack, respond: Respond, command: dict):
    pass


@app.command("/new_game")
def serve_new_game_modal(
    ack: Ack, command: dict, client: WebClient, logger: logging.Logger
):
    """
    This function will create a new game of Blotto, which will consist of X number of rounds.
    There will be a preset of possible rules for a round, and they will be randomly selected from with no replacement.

    Several actions must be performed for recordkeeping of this new game:
    - A table containing gameIDs will update with a new entry
        - This table will look like:
            game_id (int) | round_clock (interval) | num_rounds (int)

    - A message will be posted to a channel (TBD) advertising the game for users to sign up
        - A specific emoji will be requested for users to indicate interest
        - A monitor will be created to check if users add/remove a reaction

    - A table containing user+game pairs will update with signups from users that wish to participate in a new game
        - Signups will be controlled by monitoring reactions to a published message as indicated above
        - Adding a reaction will insert a new record
        - Removing a reaction will remove an existing record

    - A table containing results for each round of the game will be created. It will be named in accordance with the gameID
    """
    ack()

    logger.info("Creating new game")

    client.views_open(
        trigger_id=command["trigger_id"],
        view={
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
                        "type": "plain_text_input",
                        "placeholder": {"type": "plain_text", "text": "[number]"},
                    },
                    "label": {
                        "type": "plain_text",
                        "text": "Number of rounds",
                        "emoji": True,
                    },
                },
                {
                    "block_id": "round_length",
                    "type": "input",
                    "element": {
                        "action_id": "round_length",
                        "type": "plain_text_input",
                        "placeholder": {
                            "type": "plain_text",
                            "text": "[number] [days/hours (default: days)]",
                        },
                    },
                    "label": {
                        "type": "plain_text",
                        "text": "Submission Window per Round",
                    },
                },
                {"type": "divider"},
                {
                    "block_id": "date",
                    "type": "input",
                    "element": {
                        "action_id": "date",
                        "type": "datepicker",
                        "initial_date": (
                            datetime.date.today() + datetime.timedelta(days=1)
                        ).strftime("%Y-%m-%d"),
                        "placeholder": {
                            "type": "plain_text",
                            "text": "Select a date",
                            "emoji": True,
                        },
                    },
                    "label": {
                        "type": "plain_text",
                        "text": "Signup Close Date",
                        "emoji": True,
                    },
                },
                {
                    "block_id": "time",
                    "type": "input",
                    "element": {
                        "action_id": "time",
                        "type": "timepicker",
                        "initial_time": datetime.time(12).strftime("%H:%M"),
                        "placeholder": {
                            "type": "plain_text",
                            "text": "Select time",
                            "emoji": True,
                        },
                    },
                    "label": {
                        "type": "plain_text",
                        "text": "Signup Close Time",
                        "emoji": True,
                    },
                },
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
            "type": "modal",
        },
    )


@app.command("/submit_round")
def serve_submission_modal(
    ack: Ack, command: dict, client: WebClient, logger: logging.Logger
):
    ack()

    user_id = command["user_id"]
    game_id = command["text"]

    if not game_id:
        games = db_utils.get_user_signups(user_id)

        if len(games) > 1:
            logger.info("User participating in multiple games, must select one")
            logger.info("Messaging user with game ids for active games")
            client.chat_postEphemeral(
                token=BOT_TOKEN,
                channel=command["channel_id"],
                user=user_id,
                text=messages.submit_round_error_multiple_active_games.format(
                    games=", ".join(games)
                ),
            )

            return

        elif not games:
            logger.info("User is not participating in any active games")
            logger.info("Messaging user about the status of their participation")
            client.chat_postEphemeral(
                token=BOT_TOKEN,
                channel=command["channel_id"],
                user=user_id,
                text=messages.submit_round_error_no_active_games,
            )

            return

        else:
            game_id = games[0]

    else:
        if not db_utils.signup_exists(user_id, game_id):
            logger.info("User is not signed up for indicated game")
            logger.info("Messaging user about the status of their participation")
            client.chat_postEphemeral(
                token=BOT_TOKEN,
                channel=command["channel_id"],
                user=user_id,
                text=messages.submit_round_error_invalid_game.format(
                    games=", ".join(games)
                ),
            )

            return

    logger.info("Serving user submission modal")

    round = (
        blotto.DecreasingSoldiers()
    )  # TODO: interaction model with Round objects and assignments to Games
    round_rules = round.rules
    round_fields = round.fields
    round_soldiers = round.soldiers

    view = {
        "type": "modal",
        "callback_id": "submit_round",
        "title": {"type": "plain_text", "text": "Strategy submission"},
        "submit": {
            "type": "plain_text",
            "text": "Submit",
        },
        "close": {
            "type": "plain_text",
            "text": "Cancel",
        },
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "General rules",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "plain_text",
                    "text": round_rules,
                },
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "plain_text",
                    "text": f"You have {round_soldiers} soldiers to distribute amongst {round_fields} fields. Good luck, Major!",
                },
            },
        ]
        + [
            {
                "type": "input",
                "element": {
                    "type": "plain_text_input",
                    "action_id": f"field-{field_num + 1}",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Enter a number of soldiers",
                    },
                },
                "label": {
                    "type": "plain_text",
                    "text": f"Field {field_num + 1}",
                },
            }
            for field_num in range(round_fields)
        ],
    }

    client.views_open(trigger_id=command["trigger_id"], view=view)


@app.event("app_home_opened")
def update_home_tab(client: WebClient, event: dict, logger: logging.Logger):
    user_id = event["user"]

    db_utils.get_user_signups(user_id)

    # views.publish is the method that your app uses to push a view to the Home tab
    client.views_publish(
        user_id=user_id,
        view={
            "type": "home",
            "callback_id": "home_view",
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*Welcome to your _App's Home_* :tada:",
                    },
                },
                {"type": "divider"},
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "This button won't do much for now but you can set up a listener for it using the `actions()` method and passing its unique `action_id`. See an example in the `examples` folder within your Bolt app.",
                    },
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Click me!"},
                        }
                    ],
                },
            ],
        },
    )


@app.event("reaction_added")
def add_participant(event: dict, client: WebClient, logger: logging.Logger):
    logger.info("Reaction registered on message")

    reacji = event["reaction"]

    if not "raising-hand" in reacji:
        logger.info("Not a valid signup reacji")
        return

    logger.info("Signup reaction detected")

    message_channel = event["item"]["channel"]
    message_ts = event["item"]["ts"]
    user_id = event["user"]

    message = client.conversations_history(
        token=BOT_TOKEN,
        channel=message_channel,
        oldest=message_ts,
        inclusive=True,
        limit=1,
        include_all_metadata=True,
    )

    # check if valid response from API
    if not message["ok"]:
        logger.info("SlackAPI did not return a valid response")
        return

    # single out message content, check that bot sent message and it's a game signup
    message = message["messages"][0]
    if (not message.get("bot_id") == client.auth_test()["bot_id"]) or (
        not "has started a new game of Blotto" in message["text"]
    ):
        logger.info("Message did not meet criteria for valid signup request")
        return

    # verify that user did not add accidental duplicate signup
    other_reactions = message.get("reactions", [])
    for reaction in other_reactions:
        if not "raising-hand" in reaction["name"] or reaction["name"] == reacji:
            continue

        if user_id in reaction["users"]:
            logger.info("User added duplicate signup request, no further action")
            return

    game_id = int(message["metadata"]["event_payload"]["game_id"])

    if db_utils.signup_exists(user_id, game_id):
        logger.info("User already signed up for game, request denied")

        client.chat_postEphemeral(
            token=BOT_TOKEN,
            channel=message_channel,
            text=messages.signup_request_error_duplicate.format(game_id=game_id),
            user=user_id,
        )
        return

    signup_close = db_utils.get_game_start(game_id)
    if signup_close < datetime.datetime.fromtimestamp(
        float(event["event_ts"]), pytz.utc
    ):
        logger.info("User signup requested after game start, request denied")

        client.chat_postEphemeral(
            token=BOT_TOKEN,
            channel=message_channel,
            text=messages.signup_request_error_game_started,
            user=user_id,
        )
        return

    logger.info("Valid user signup request")

    db_utils.add_user_to_game(user_id, game_id)

    logger.info("User signed up for game successfully")

    game_start = db_utils.get_game_start(game_id)

    client.chat_postEphemeral(
        token=BOT_TOKEN,
        channel=message_channel,
        text=messages.signup_request_success.format(
            game_id=game_id, game_start=int(game_start.timestamp())
        ),
        user=user_id,
    )


@app.event("reaction_removed")
def remove_participant(event: dict, client: WebClient, logger: logging.Logger):
    logger.info("Reaction removal registered")

    reacji = event["reaction"]

    if not "raising-hand" in reacji:
        logger.info("Not a relevant reacji, ignoring")
        return

    logger.info("Signup reaction removal detected")

    message_channel = event["item"]["channel"]
    message_ts = event["item"]["ts"]
    user_id = event["user"]

    message = client.conversations_history(
        token=BOT_TOKEN,
        channel=message_channel,
        oldest=message_ts,
        inclusive=True,
        limit=1,
        include_all_metadata=True,
    )

    # check if valid response from API
    if not message["ok"]:
        logger.info("SlackAPI did not return a valid response")
        return

    # single out message content, check that bot sent message and that it was for a game signup
    message = message["messages"][0]
    if (not message["bot_id"] == client.auth_test()["bot_id"]) or (
        not "has started a new game of Blotto" in message["text"]
    ):
        logger.info("Message did not meet criteria for valid signup withdrawal request")
        return

    # verify that user did not remove accidental duplicate signup
    other_reactions = message.get("reactions", [])
    for reaction in other_reactions:
        if not "raising-hand" in reaction["name"]:
            continue

        if user_id in reaction["users"]:
            logger.info("User removed duplicate signup request, no further action")
            return

    logger.info("Valid user signup removal request")

    game_id = int(message["metadata"]["event_payload"]["game_id"])

    if not db_utils.signup_exists(user_id, game_id):
        logger.info("Signup record not located, cannot be removed")

        client.chat_postEphemeral(
            token=BOT_TOKEN,
            channel=message_channel,
            text=messages.signup_remove_request_error_no_signup.format(game_id=game_id),
            user=user_id,
        )
        return

    db_utils.remove_user_from_game(user_id, game_id)

    logger.info("User removed from game successfully")

    client.chat_postEphemeral(
        token=BOT_TOKEN,
        channel=message_channel,
        text=messages.signup_remove_request_success.format(game_id=game_id),
        user=user_id,
    )


@app.event("message_metadata_posted")
def metadata_trigger_router(client: WebClient, payload: dict, logger: logging.Logger):
    def game_start_handler(client: WebClient, payload: dict, logger: logging.Logger):
        metadata = payload["metadata"]
        metadata_payload = metadata["event_payload"]

        game_id = metadata_payload["game_id"]

        logger.info(f"Game {game_id} starting")
        if len(db_utils.get_participants(game_id)) < 2:
            logger.info("Not enough participants, canceling game")
            db_utils.cancel_game(game_id)
            logger.info("Game canceled successfully")
            return

        logger.info("Posting game announcement")

        game = db_utils.get_game(game_id)
        client.chat_postMessage(
            token=BOT_TOKEN,
            channel=metadata_payload["channel_id"],
            text=messages.game_start_announcement.format(
                game_id=game_id, round_length=game.round_length
            ),
            metadata={
                "event_type": "round_start",
                "event_payload": {"game_id": game_id, "round_number": 1},
            },
        )

    def round_start_handler(client: WebClient, payload: dict, logger: logging.Logger):
        metadata = payload["metadata"]
        metadata_payload = metadata["event_payload"]

        game_id = metadata_payload["game_id"]
        round_num = metadata_payload["round_number"]

        logger.info(f"Round {round_num} starting, posting rules")

        round = db_utils.get_round(game_id, round_num)
        round_obj = blotto.RoundLibrary.load_round(
            round.id, round.fields, round.soldiers
        )

        client.chat_postMessage(
            token=BOT_TOKEN,
            channel=payload["channel_id"],
            text=messages.round_start_announcement.format(
                game_id=game_id,
                round_num=round.number,
                round_end=int(round.end.timestamp()),
                round_rules=round_obj.RULES,
            ),
        )
        time.sleep(1)

        logger.info(f"Round {round_num} rules posted, scheduling end of round")

        client.chat_scheduleMessage(
            token=BOT_TOKEN,
            channel=BOT_MEMBER_ID,
            post_at=int(round.end.timestamp()),
            text="next",
            metadata={
                "event_type": "round_end",
                "event_payload": {
                    "game_id": game_id,
                    "round_number": round_num,
                    "channel_id": payload["channel_id"],
                },
            },
        )

    def round_end_handler(client: WebClient, payload: dict, logger: logging.Logger):
        metadata = payload["metadata"]
        metadata_payload = metadata["event_payload"]

        game_id = metadata_payload["game_id"]
        round_num = metadata_payload["round_number"]

        logger.info(f"Round {round_num} has ended")
        logger.info("Calculating round results")

        round = db_utils.get_round(game_id, round_num)
        round_obj = blotto.RoundLibrary.load_round(
            round.id, round.fields, round.soldiers, game_id
        )

        round_obj.update_results()

        scores = db_utils.get_round_results(game_id, round_num)

        message_params = {
            "token": BOT_TOKEN,
            "channel": metadata_payload["channel_id"],
            "text": messages.round_end_announcement.format(
                game_id=game_id,
                round_num=round_num,
                first=scores[0].user_id,
                first_score=scores[0].score,
                second=scores[1].user_id,
                second_score=scores[1].score,
                third=scores[2].user_id,
                third_score=scores[2].score,
            ),
        }

        next_round = db_utils.get_round(game_id, round_num + 1)

        if not next_round:
            message_params["metadata"] = {
                "event_type": "game_end",
                "event_payload": {"game_id": game_id},
            }

        else:
            message_params["metadata"] = {
                "event_type": "round_start",
                "event_payload": {"game_id": game_id, "round_number": round_num + 1},
            }

        client.chat_postMessage(**message_params)

    def game_end_handler(client: WebClient, payload: dict, logger: logging.Logger):
        metadata = payload["metadata"]
        metadata_payload = metadata["event_payload"]

        game_id = metadata_payload["game_id"]

        logger.info(f"Game {game_id} ended")
        logger.info("Calculating game results")

        blotto.update_game_results(game_id)

        logger.info("Posting game winner announcement")

        scores = db_utils.get_game_results(game_id)
        winner = scores[0]
        client.chat_postMessage(
            token=BOT_TOKEN,
            channel=payload["channel_id"],
            text=messages.game_end_announcement.format(
                game_id=game_id, winner=winner.user_id, winner_score=winner.score
            ),
        )

    logger.info("Received metadata, passing payload to handler")

    metadata_type = payload["metadata"]["event_type"]

    match metadata_type:
        case "game_announced":
            logger.info("Game announcement, no action required")

        case "game_start":
            game_start_handler(client, payload, logger)

        case "round_start":
            round_start_handler(client, payload, logger)

        case "round_end":
            round_end_handler(client, payload, logger)

        case "game_end":
            game_end_handler(client, payload, logger)


@app.message("")
def ignore_messages(ack: Ack, logger: logging.Logger):
    ack()

    logger.info("Message posted somewhere, nobody cares")


@app.view("submit_round")
def handle_round_submission(
    ack: Ack,
    view: dict,
    client: WebClient,
    context: BoltContext,
    logger: logging.Logger,
):
    pass


@app.view("new_game")
def handle_new_game_submission(
    ack: Ack,
    view: dict,
    client: WebClient,
    context: BoltContext,
    logger: logging.Logger,
):
    ack()
    logger.info("Parsing game parameter inputs")

    inputs = view["state"]["values"]

    num_rounds = int(inputs["num_rounds"]["num_rounds"]["value"])
    round_length = inputs["round_length"]["round_length"]["value"]

    if "hour" in round_length:
        round_length = datetime.timedelta(hours=int(round_length.split(" ")[0]))

    elif "day" in round_length:
        round_length = datetime.timedelta(days=int(round_length.split(" ")[0]))

    else:
        round_length = datetime.timedelta(days=int(round_length))

    date_input = inputs["date"]["date"]["selected_date"]
    time_input = inputs["time"]["time"]["selected_time"]
    timezone_input = client.users_info(token=BOT_TOKEN, user=context["user_id"])[
        "user"
    ]["tz"]

    signup_close = (
        pytz.timezone(timezone_input)
        .localize(
            datetime.datetime.strptime(date_input + " " + time_input, "%Y-%m-%d %H:%M")
        )
        .astimezone(pytz.utc)
    )

    logger.info("Valid params, creating game instance")

    game_id = blotto.GameFactory.new_game(num_rounds, round_length, signup_close)

    logger.info("Game created, announcing")

    selected_channel = view["state"]["values"]["advertise_to_channels"][
        "advertise_to_channels"
    ]["selected_channel"]

    client.chat_postMessage(
        token=BOT_TOKEN,
        channel=selected_channel,
        text=messages.new_game_announcement.format(
            user_id=context["user_id"],
            num_rounds=num_rounds,
            round_length=round_length,
            game_id=game_id,
            game_start=int(signup_close.timestamp()),
        ),
        metadata={
            "event_type": "game_announced",
            "event_payload": {
                "game_id": game_id,
            },
        },
        unfurl_links=False,
    )
    time.sleep(1)

    logger.info("Game announced, scheduling signup close action")
    client.chat_scheduleMessage(
        token=BOT_TOKEN,
        channel=BOT_MEMBER_ID,
        post_at=int(signup_close.timestamp()),
        text="game",
        metadata={
            "event_type": "game_start",
            "event_payload": {
                "game_id": game_id,
                "channel_id": selected_channel,
            },
        },
    )

    logger.info("Success, new game flow complete")


if __name__ == "__main__":
    db_utils.MetaData.create_all()

    handler = SocketModeHandler(app, os.getenv("APP_TOKEN"))

    try:
        handler.start()
    except KeyboardInterrupt:
        print("\nExiting")
        sys.exit(0)

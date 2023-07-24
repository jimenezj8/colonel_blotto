import datetime
import json
import logging
import os
import sys
import time

import pytz
from slack_bolt import Ack, App, BoltContext, Respond
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk.web.client import WebClient
from sqlalchemy.exc import NoResultFound

import blotto
import db_utils
import enums
import messages
import views

BOT_TOKEN = os.getenv("BOT_TOKEN")
BOT_MEMBER_ID = "U03LWG7NAAY"


# if ENV == "development" validation will still allow the requested
# action to be attempted in some cases this will still result in an error
ENV = enums.Environment(os.getenv("ENV"))


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

    try:
        game = db_utils.get_game(game_id)
    except NoResultFound:
        logger.info("Game requested to cancel does not exist")

        client.chat_postEphemeral(
            token=BOT_TOKEN,
            user=user_id,
            channel=response_channel,
            text="The game you've requested to cancel doesn't exist, please double-check the ID you provided.",
        )
        if not ENV == enums.Environment.DEV:
            return

    if pytz.utc.localize(datetime.datetime.utcnow()) >= game.start:
        logger.info("Game has already begun, letting user know")

        client.chat_postEphemeral(
            token=BOT_TOKEN,
            user=user_id,
            channel=response_channel,
            text="The game you've requested to cancel has already begun, sorry.",
        )
        if not ENV == enums.Environment.DEV:
            return

    elif game.canceled:
        logger.info("Game has already been canceled, letting user know")

        client.chat_postEphemeral(
            token=BOT_TOKEN,
            user=user_id,
            channel=response_channel,
            text="The game you've requested to cancel was already canceled.",
        )
        if not ENV == enums.Environment.DEV:
            return

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

    logger.info("Serving new game modal")

    client.views_open(
        trigger_id=command["trigger_id"],
        view=views.new_game.load(
            datetime.datetime.utcnow() + datetime.timedelta(days=1)
        ),
    )


@app.command("/submit_strategy")
def serve_submission_modal(
    ack: Ack, command: dict, client: WebClient, logger: logging.Logger
):
    ack()

    user_id = command["user_id"]
    channel_id = command["channel_id"]

    if not command["text"]:
        logger.info("User did not provide a game ID")
        logger.info("Messaging user")

        client.chat_postEphemeral(
            token=BOT_TOKEN,
            channel=channel_id,
            user=user_id,
            text=messages.submit_strategy_error_no_game_id,
        )

        if not ENV == enums.Environment.DEV:
            return

    game_id = int(command["text"])

    try:
        game = db_utils.get_game(game_id)
    except NoResultFound:
        logger.info("The specified game doesn't exist")
        logger.info("Messaging user")

        client.chat_postEphemeral(
            token=BOT_TOKEN,
            channel=channel_id,
            user=user_id,
            text=messages.submit_strategy_error_game_doesnt_exist,
        )

        if not ENV == enums.Environment.DEV:
            return

    if game.canceled:
        logger.info("Game specified has been canceled, messaging user")

        client.chat_postEphemeral(
            token=BOT_TOKEN,
            channel=channel_id,
            user=user_id,
            text=messages.general_game_canceled,
        )

        if not ENV == enums.Environment.DEV:
            return

    try:
        db_utils.check_participation(user_id, game_id)
    except NoResultFound:
        logger.info(f"{user_id} is not signed up for game {game_id}")
        logger.info("Messaging user")

        client.chat_postEphemeral(
            token=BOT_TOKEN,
            channel=channel_id,
            user=user_id,
            text=messages.submit_strategy_error_user_not_in_game,
        )

        if not ENV == enums.Environment.DEV:
            return

    try:
        round = db_utils.get_active_round(
            game_id, pytz.utc.localize(datetime.datetime.utcnow())
        )
    except NoResultFound:
        logger.info("Game specified isn't currently active")
        logger.info("Messaging user")

        client.chat_postEphemeral(
            token=BOT_TOKEN,
            channel=channel_id,
            user=user_id,
            text=messages.submit_strategy_error_game_inactive,
        )

        if not ENV == enums.Environment.DEV:
            return

    logger.info("Serving user submission modal")
    round_obj = blotto.RoundLibrary.load_round(
        round.id, round.fields, round.soldiers, round.game_id
    )

    view = views.new_submission.load(
        game_id, round.number, round.soldiers, round.fields, round_obj.RULES
    )

    client.views_open(trigger_id=command["trigger_id"], view=view)


@app.event("app_home_opened")
def update_home_tab(client: WebClient, event: dict, logger: logging.Logger):
    user_id = event["user"]

    db_utils.get_user_signups(user_id)

    # views.publish is the method that your app uses to push a view to the Home tab
    client.views_publish(
        user_id=user_id,
        view=views.app_home.load(),
    )


@app.event("reaction_added")
def add_participant(event: dict, client: WebClient, logger: logging.Logger):
    logger.info("Reaction registered on message")

    reacji = event["reaction"]

    if "raising-hand" not in reacji:
        logger.info("Not a valid signup reacji")
        if not ENV == enums.Environment.DEV:
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
        if not ENV == enums.Environment.DEV:
            return

    # single out message content, check that bot sent message and it's a game signup
    message = message["messages"][0]
    if (not message.get("bot_id") == client.auth_test()["bot_id"]) or (
        "has started a new game of Blotto" not in message["text"]
    ):
        logger.info("Message did not meet criteria for valid signup request")
        if not ENV == enums.Environment.DEV:
            return

    # verify that user did not add accidental duplicate signup
    other_reactions = message.get("reactions", [])
    for reaction in other_reactions:
        if "raising-hand" not in reaction["name"] or reaction["name"] == reacji:
            continue

        if user_id in reaction["users"]:
            logger.info("User added duplicate signup request, no further action")
            if not ENV == enums.Environment.DEV:
                return

    game_id = int(message["metadata"]["event_payload"]["game_id"])

    try:
        db_utils.check_participation(user_id, game_id)

        logger.info("User already signed up for game, request denied")
        logger.info("Messaging user")

        client.chat_postEphemeral(
            token=BOT_TOKEN,
            channel=message_channel,
            text=messages.signup_request_error_duplicate.format(game_id=game_id),
            user=user_id,
        )
        if not ENV == enums.Environment.DEV:
            return
    except NoResultFound:
        logger.info("Verified user has not already signed up")

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
        if not ENV == enums.Environment.DEV:
            return

    logger.info("Valid user signup request")

    db_utils.add_user_to_game(user_id, game_id)

    logger.info("User signed up for game successfully")

    game_start = db_utils.get_game_start(game_id)

    client.chat_postEphemeral(
        token=BOT_TOKEN,
        channel=message_channel,
        text=messages.signup_request_success.format(
            game_id=game_id,
            game_start=messages.format_timestamp(int(game_start.timestamp())),
        ),
        user=user_id,
    )


@app.event("reaction_removed")
def remove_participant(event: dict, client: WebClient, logger: logging.Logger):
    logger.info("Reaction removal registered")

    reacji = event["reaction"]

    if "raising-hand" not in reacji:
        logger.info("Not a relevant reacji, ignoring")
        if not ENV == enums.Environment.DEV:
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
        if not ENV == enums.Environment.DEV:
            return

    # single out message content, check that bot sent message and that it was for a game signup
    message = message["messages"][0]
    if (not message["bot_id"] == client.auth_test()["bot_id"]) or (
        "has started a new game of Blotto" not in message["text"]
    ):
        logger.info("Message did not meet criteria for valid signup withdrawal request")
        if not ENV == enums.Environment.DEV:
            return

    # verify that user did not remove accidental duplicate signup
    other_reactions = message.get("reactions", [])
    for reaction in other_reactions:
        if "raising-hand" not in reaction["name"]:
            continue

        if user_id in reaction["users"]:
            logger.info("User removed duplicate signup request, no further action")
            if not ENV == enums.Environment.DEV:
                return

    logger.info("Valid user signup removal request")

    game_id = int(message["metadata"]["event_payload"]["game_id"])

    try:
        db_utils.check_participation(user_id, game_id)
        logger.info("Verified user has signed up")
    except NoResultFound:
        logger.info("Signup record not located, cannot be removed")
        logger.info("Messaging user")

        client.chat_postEphemeral(
            token=BOT_TOKEN,
            channel=message_channel,
            text=messages.signup_remove_request_error_no_signup.format(game_id=game_id),
            user=user_id,
        )
        if not ENV == enums.Environment.DEV:
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
        game = db_utils.get_game(game_id)

        logger.info(f"Game {game_id} starting")
        if len(db_utils.get_participants(game_id)) < 2:
            logger.info("Not enough participants, canceling game")
            db_utils.cancel_game(game_id)
            logger.info("Game canceled successfully")
            if not ENV == enums.Environment.DEV:
                return

        elif game.canceled:
            logger.info("Game was canceled, no need to announce")
            if not ENV == enums.Environment.DEV:
                return

        logger.info("Posting game announcement")

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
                round_end=messages.format_timestamp(int(round.end.timestamp())),
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


@app.view("submit_strategy")
def handle_strategy_submission(
    ack: Ack,
    view: dict,
    client: WebClient,
    context: BoltContext,
    logger: logging.Logger,
):
    user_id = context["user_id"]
    channel_id = context["user_id"]

    metadata = json.loads(view["private_metadata"])
    game_id = metadata["game_id"]
    round_num = metadata["round_num"]

    round = db_utils.get_round(game_id, round_num)

    inputs = view["state"]["values"]
    fields = [
        inputs[f"field-{i+1}"][f"field-{i+1}"]["value"] for i in range(round.fields)
    ]
    errors = {}
    for i, soldiers in enumerate(fields):
        try:
            fields[i] = int(soldiers)
        except ValueError:
            errors[f"field-{i+1}"] = "Argument must be an integer"

    if errors:
        ack(response_action="errors", errors=errors)

        if not ENV == enums.Environment.DEV:
            return

    round_obj = blotto.RoundLibrary.load_round(
        round.id, round.fields, round.soldiers, round.game_id
    )
    try:
        field_errors = round_obj.check_field_rules(fields)

    except ValueError:
        ack(
            response_action="errors",
            errors={
                f"field-{i+1}": "Total soldier count is too high"
                for i in range(round.fields)
            },
        )

        if not ENV == enums.Environment.DEV:
            return

    else:
        if field_errors:
            ack(response_action="errors", errors=field_errors)

            if not ENV == enums.Environment.DEV:
                return

    logger.info("Valid submission, accepted")
    ack()

    timestamp = pytz.utc.localize(datetime.datetime.utcnow())
    db_utils.submit_user_strategy(game_id, round_num, user_id, fields, timestamp)

    logger.info("Messaging user")

    client.chat_postEphemeral(
        token=BOT_TOKEN,
        channel=channel_id,
        user=user_id,
        text="Successfully submitted!",
    )


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
    round_length_num = int(inputs["round_length_num"]["round_length_num"]["value"])
    round_length_unit = inputs["round_length_unit"]["round_length_unit"][
        "selected_option"
    ]["value"]

    round_length = datetime.timedelta(**{round_length_unit: round_length_num})

    signup_close = int(inputs["datetime"]["datetime"]["selected_date_time"])
    timezone_input = client.users_info(token=BOT_TOKEN, user=context["user_id"])[
        "user"
    ]["tz"]

    signup_close = (
        pytz.timezone(timezone_input)
        .localize(datetime.datetime.fromtimestamp(signup_close))
        .astimezone(pytz.utc)
    )

    logger.info("Valid params, creating game instance")

    game_id = blotto.GameFactory.new_game(num_rounds, round_length, signup_close)

    logger.info("Game created, announcing")

    selected_channel = inputs["advertise_to_channels"]["advertise_to_channels"][
        "selected_channel"
    ]

    client.chat_postMessage(
        token=BOT_TOKEN,
        channel=selected_channel,
        text=messages.new_game_announcement.format(
            user_id=context["user_id"],
            num_rounds=num_rounds,
            round_length=round_length,
            game_id=game_id,
            game_start=messages.format_timestamp(int(signup_close.timestamp())),
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
        if ENV == enums.Environment.PROD:
            app.client.chat_postMessage(
                token=BOT_TOKEN, channel="testing", text="Back online"
            )
        handler.start()
    except KeyboardInterrupt:
        app.logger.info("Shutting down")
        if ENV == enums.Environment.PROD:
            app.client.chat_postMessage(
                token=BOT_TOKEN, channel="testing", text="Shutting down temporarily"
            )
        sys.exit(0)

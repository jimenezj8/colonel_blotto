import datetime
import json
import logging
import os
import time

import pytz
from psycopg2.errors import UniqueViolation
from slack_bolt import Ack, App, BoltContext
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk.errors import SlackApiError
from slack_sdk.models.views import View
from slack_sdk.web.client import WebClient
from sqlalchemy.exc import IntegrityError, NoResultFound

import blotto
import db_utils
import messages
import models
import slack_utils
import views
from enums import Environment
from exc import BlottoValidationError

BOT_TOKEN = os.getenv("BOT_TOKEN")
TEST_CHANNEL_ID = os.getenv("DEVELOPMENT_CHANNEL_ID")
USER_ID = os.getenv("DEVELOPER_MEMBER_ID")


# if ENV == "development" validation will still allow the requested
# action to be attempted in some cases this will still result in an error
ENV = Environment(os.getenv("ENV"))


app = App(
    token=BOT_TOKEN,
    signing_secret=os.getenv("SIGNING_SECRET"),
    ignoring_self_events_enabled=False,
)
BOT_ID = str(app.client.auth_test().data["bot_id"])
BOT_MEMBER_ID = str(app.client.bots_info(bot=BOT_ID).data["bot"]["user_id"])

logging.basicConfig(level=logging.DEBUG)


@app.command("/blotto_cancel")
def serve_cancel_game_modal(
    ack: Ack, client: WebClient, command: dict, logger: logging.Logger
):
    ack()

    user_id = command["user_id"]
    trigger_id = command["trigger_id"]

    logger.info(f"User {user_id} requesting to cancel a game")

    games_as_admin = db_utils.get_admin_games(user_id)
    games_as_admin = [
        game
        for game in games_as_admin
        if game.start >= datetime.datetime.utcnow().astimezone(datetime.UTC)
        and not game.canceled
    ]

    if not games_as_admin:
        logger.info("User is not admin of any pending games")

        client.chat_postEphemeral(
            user=user_id,
            channel=command["channel_id"],
            text="There aren't any games you can cancel at the moment",
        )

        return

    logger.info("Serving cancel game modal")

    client.views_open(
        trigger_id=trigger_id, view=views.cancel_game.load(games_as_admin)
    )


@app.command("/blotto_game")
def serve_new_game_modal(
    ack: Ack, command: dict, client: WebClient, logger: logging.Logger
):
    """
    This function will create a new game of Blotto, which will
    consist of X number of rounds. There will be a preset of
    possible rules for a round, and they will be randomly
    selected from with no replacement.

    Several actions must be performed for recordkeeping of this new game:
    - A table containing gameIDs will update with a new entry
        - This table will look like:
            game_id (int) | round_clock (interval) | num_rounds (int)

    - A message will be posted to a channel (TBD) advertising the game for
    users to sign up
        - A specific emoji will be requested for users to indicate interest
        - A monitor will be created to check if users add/remove a reaction

    - A table containing user+game pairs will update with signups from
    users that wish to participate in a new game
        - Signups will be controlled by monitoring reactions to a published
        message as indicated above
        - Adding a reaction will insert a new record
        - Removing a reaction will remove an existing record

    - A table containing results for each round of the game will be created.
    It will be named in accordance with the gameID
    """
    ack()

    logger.info("Serving new game modal")

    client.views_open(
        trigger_id=command["trigger_id"],
        view=views.new_game.load(
            datetime.datetime.utcnow() + datetime.timedelta(days=1)
        ),
    )


@app.command("/blotto_submission")
def serve_submission_modal(
    ack: Ack, command: dict, client: WebClient, logger: logging.Logger
):
    ack()

    user_id = command["user_id"]
    channel_id = command["channel_id"]

    logger.info(f"Querying games for user {user_id}")
    games = db_utils.get_user_active_games(user_id)

    if not games:
        logger.info(
            "User attempting to submit games while not "
            "signed up for any active ones, messaging user"
        )

        client.chat_postEphemeral(
            channel=channel_id,
            user=user_id,
            text=messages.submit_strategy_error_not_in_active_game,
        )

        return

    client.views_open(
        trigger_id=command["trigger_id"], view=views.new_submission.load(games)
    )


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
        return

    logger.info("Signup reaction detected")

    message_channel = event["item"]["channel"]
    message_ts = event["item"]["ts"]
    user_id = event["user"]

    try:
        game = db_utils.get_game_from_announcement(
            message_channel,
            datetime.datetime.fromtimestamp(float(message_ts)),
        )
    except NoResultFound:
        logger.info("Reaction added to message that is not game announcement, ignoring")

        return

    if datetime.datetime.utcnow().astimezone(pytz.utc) > game.start:
        logger.info("User signup requested after game start, request denied")

        client.chat_postEphemeral(
            token=BOT_TOKEN,
            channel=message_channel,
            text=messages.signup_request_error_game_started,
            user=user_id,
        )

        return

    try:
        db_utils.create_records([models.Participant(game_id=game.id, user_id=user_id)])

    except IntegrityError as e:
        if type(e.__cause__) is UniqueViolation:
            logger.info("User already signed up for game")

            client.chat_postEphemeral(
                token=BOT_TOKEN,
                channel=message_channel,
                text=messages.signup_request_error_duplicate.format(game_id=game.id),
                user=user_id,
            )

            return

        else:
            raise

    else:
        logger.info("Valid user signup request")
        logger.info("User signed up for game successfully")

        client.chat_postEphemeral(
            token=BOT_TOKEN,
            channel=message_channel,
            text=messages.signup_request_success.format(
                game_id=game.id,
                game_start=slack_utils.DateTimeShortPretty(game.start),
            ),
            user=user_id,
        )


@app.event("reaction_removed")
def remove_participant(event: dict, client: WebClient, logger: logging.Logger):
    logger.info("Reaction removal registered")

    reacji = event["reaction"]

    if "raising-hand" not in reacji:
        logger.info("Not a relevant reacji, ignoring")
        if not ENV == Environment.DEV:
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
        if not ENV == Environment.DEV:
            return

    # single out message content
    # check that bot sent message and that it was for a game signup
    message = message["messages"][0]
    if (not message["bot_id"] == BOT_ID) or (
        message["metadata"]["event_type"] != "game_announced"
    ):
        logger.info("Message did not meet criteria for valid signup withdrawal request")
        if not ENV == Environment.DEV:
            return

    # verify that user did not remove accidental duplicate signup
    other_reactions = message.get("reactions", [])
    for reaction in other_reactions:
        if "raising-hand" not in reaction["name"]:
            continue

        if user_id in reaction["users"]:
            logger.info("User removed duplicate signup request, no further action")
            if not ENV == Environment.DEV:
                return

    logger.info("Valid user signup removal request")

    game_id = int(message["metadata"]["event_payload"]["game_id"])

    try:
        participant = db_utils.get_participant(game_id, user_id)
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
        if not ENV == Environment.DEV:
            return

    db_utils.delete_records([participant])

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
            if not ENV == Environment.DEV:
                return

        elif game.canceled:
            logger.info("Game was canceled, no need to announce")
            if not ENV == Environment.DEV:
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
                round_end=slack_utils.DateTimeShortPretty(round.end),
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


@app.event({"type": "message", "subtype": "message_changed"})
@app.event({"type": "message", "subtype": "message_deleted"})
@app.message("")
def ignore_messages(ack: Ack, logger: logging.Logger):
    ack()

    logger.info("A message was changed or posted somewhere")


@app.view("cancel_game_select_game_view")
def cancel_game_handler(
    ack: Ack,
    client: WebClient,
    view: View,
    logger: logging.Logger,
):
    logger.info("Received cancel_game view submission")

    view_state = view["state"]["values"]
    element = view_state["cancel_game_select_game_block"]["select_game"]
    game_id = element["selected_option"]["value"]

    ack()

    game = db_utils.get_game(game_id)

    game.canceled = True

    db_utils.update_records([game])

    logger.info("Game attribute 'canceled' updated to 'True'")

    client.chat_postMessage(
        channel=game.announcement_channel,
        text="Sorry, this game has been canceled :slightly_frowning_face:",
        thread_ts=str(game.announcement_ts.timestamp()),
        mrkdwn=True,
        reply_broadcast=True,
    )
    client.reactions_add(
        channel=game.announcement_channel,
        name="x",
        timestamp=str(game.announcement_ts.timestamp()),
    )


@app.view("strategy_submission_select_game_view")
def update_strategy_submission_modal_with_field_inputs(
    ack: Ack,
    view: dict,
    logger: logging.Logger,
):
    view_state = view["state"]["values"]
    element = view_state["strategy_submission_select_game_block"]["select_game"]

    game_id = element["selected_option"]["value"]

    game_round = db_utils.get_active_round(game_id)

    if not game_round:
        logger.fatal("Failed to find the active round for the indicated game")
        logger.info("Closing all strategy submission views")
        ack(response_action="clear")
        return

    blotto_round = blotto.RoundLibrary.load_round(game_round)

    new_view = views.new_submission.update(
        game_id,
        blotto_round.number,
        blotto_round.soldiers,
        blotto_round.fields,
        blotto_round.RULES,
    )

    logger.info("Serving user new view to provide submission")

    ack(response_action="push", view=new_view)


@app.view("strategy_submission_inputs_view")
def process_strategy_submission(
    ack: Ack,
    client: WebClient,
    logger: logging.Logger,
    view: dict,
    context: dict,
):
    logger.info("User submitted strategy")

    view: View = View(**view)
    metadata = json.loads(view.private_metadata)

    blotto_round = blotto.RoundLibrary.load_round(
        game_id=metadata["game_id"], round_number=metadata["round_num"]
    )

    submission = {
        element_id.split("-")[1]: int(element_state.value)
        for block in view.state.values.values()
        for element_id, element_state in block.items()
    }
    submission = [
        item[1]
        for item in sorted(
            submission.items(),
            key=lambda item: item[0],
        )
    ]

    try:
        blotto_round.check_general_rules(submission)
    except BlottoValidationError as e:
        logger.info("Validation error in submission, update user view")
        logger.info(e)
        ack(
            response_action="errors",
            errors={f"field-{i+1}-block": str(e) for i in range(len(submission))},
        )
        return

    field_errors = blotto_round.check_field_rules(submission)
    if field_errors:
        logger.info("Validation errors in submission, update user view")
        logger.info(field_errors)
        ack(
            response_action="errors",
            errors={
                f"field-{field}-block": error for field, error in field_errors.items()
            },
        )
        return

    ack(response_action="clear")

    # TODO: persist submission to DB

    client.chat_postEphemeral(
        channel=context["user_id"],
        user=context["user_id"],
        text="Strategy accepted!",
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

    user_id = context["user_id"]
    inputs = view["state"]["values"]

    num_rounds = int(inputs["num_rounds"]["num_rounds"]["value"])
    round_length_num = int(inputs["round_length_num"]["round_length_num"]["value"])
    round_length_unit = inputs["round_length_unit"]["round_length_unit"][
        "selected_option"
    ]["value"]

    round_length = datetime.timedelta(**{round_length_unit: round_length_num})

    signup_close = int(inputs["datetime"]["datetime"]["selected_date_time"])
    timezone_input = client.users_info(token=BOT_TOKEN, user=user_id)["user"]["tz"]

    signup_close = (
        pytz.timezone(timezone_input)
        .localize(datetime.datetime.fromtimestamp(signup_close))
        .astimezone(pytz.utc)
    )

    logger.info("Valid params, creating game instance")

    game = blotto.GameFactory.new_game(user_id, num_rounds, round_length, signup_close)

    logger.info("Game created, announcing")

    selected_channel = inputs["advertise_to_channels"]["advertise_to_channels"][
        "selected_channel"
    ]

    response = client.chat_postMessage(
        token=BOT_TOKEN,
        channel=selected_channel,
        text=messages.new_game_announcement.format(
            user_id=user_id,
            num_rounds=num_rounds,
            round_length=round_length,
            game_id=game.id,
            game_start=slack_utils.DateTimeShortPretty(signup_close),
        ),
        metadata={
            "event_type": "game_announced",
            "event_payload": {
                "game_id": game.id,
            },
        },
        unfurl_links=False,
    )

    game.announcement_channel = selected_channel
    game.announcement_ts = datetime.datetime.fromtimestamp(float(response.data["ts"]))

    db_utils.update_records([game])

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
                "game_id": game.id,
                "channel_id": selected_channel,
            },
        },
    )

    logger.info("Success, new game flow complete")


if __name__ == "__main__":
    if ENV == Environment.DEV:
        models.MetaData.drop_all(db_utils.engine)

    models.MetaData.create_all(db_utils.engine)

    if ENV == Environment.DEV:
        blotto.RoundLibrary.ROUND_MAP = {0: blotto.TestRound}

        if os.getenv("CREATE_TEST_DATA").lower() == "true":
            game_start = datetime.datetime.utcnow()
            records = [
                models.Game(
                    admin=USER_ID,
                    start=game_start,
                    end=game_start + datetime.timedelta(days=1),
                    num_rounds=3,
                    round_length=datetime.timedelta(hours=8),
                    canceled=False,
                ),
                models.Game(
                    admin=USER_ID,
                    start=game_start + datetime.timedelta(hours=1),
                    end=game_start + datetime.timedelta(hours=4),
                    num_rounds=3,
                    round_length=datetime.timedelta(hours=1),
                    canceled=False,
                ),
                models.GameRound(
                    game_id=1,
                    number=1,
                    library_id=0,
                    start=game_start,
                    end=game_start + datetime.timedelta(hours=8),
                    fields=5,
                    soldiers=100,
                ),
                models.Participant(
                    game_id=1,
                    user_id=USER_ID,
                ),
            ]
            db_utils.create_records(records)

    handler = SocketModeHandler(app, os.getenv("APP_TOKEN"))

    try:
        handler.start()
    except KeyboardInterrupt:
        app.logger.info("Shutting down")
        # cleanup actions include:
        # 1. deleting all scheduled messages from the bot user
        # 2. deleting all bot messages in #testing
        if ENV == Environment.DEV:
            response = app.client.chat_scheduledMessages_list()
            scheduled_messages = response.data["scheduled_messages"]
            for message in scheduled_messages:
                if message.get("bot_id") == BOT_ID:
                    app.client.chat_deleteScheduledMessage(
                        channel=TEST_CHANNEL_ID,
                        scheduled_message_id=message["message_id"],
                    )

            response = app.client.conversations_history(channel=TEST_CHANNEL_ID)
            chat_messages = response.data["messages"]
            for message in chat_messages:
                try:
                    app.client.chat_delete(channel=TEST_CHANNEL_ID, ts=message["ts"])
                except SlackApiError:
                    pass

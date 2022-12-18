import datetime
import logging
import os
import sys

import pytz

from slack_bolt import Ack, App, BoltContext
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk.web.client import WebClient

import blotto, db_utils

app = App(
    token=os.getenv("BOT_TOKEN"),
    signing_secret=os.getenv("SIGNING_SECRET"),
    ignoring_self_events_enabled=False,
)

logging.basicConfig(level=logging.DEBUG)


@app.command("/modify_submission")
def modify_round_submission(ack, respond, command):
    pass


@app.command("/new_game")
def serve_new_game_modal(ack, command, client: WebClient, logger):
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
def serve_submission_modal(ack, command, client: WebClient, logger):
    ack()

    user_id = command["user_id"]
    game_id = command["text"]

    if not game_id:
        games = db_utils.get_user_signups(user_id)

        if len(games) > 1:
            logger.info("User participating in multiple games, must select one")
            logger.info("Messaging user with game ids for active games")
            client.chat_postEphemeral(
                token=os.getenv("BOT_TOKEN"),
                channel=command["channel_id"],
                user=user_id,
                text=(
                    "Sorry, it looks like you're participating in multiple active games currently."
                    "Before you can submit your strategy, you must select which game it will apply to.\n\n"
                    f"Choose from the following game IDs: {', '.join(games)}\n\n"
                    "When you use the command `/submit_round` next time, please include the relevant game ID."
                ),
            )

            return

        elif not games:
            logger.info("User is not participating in any active games")
            logger.info("Messaging user about the status of their participation")
            client.chat_postEphemeral(
                token=os.getenv("BOT_TOKEN"),
                channel=command["channel_id"],
                user=user_id,
                text=(
                    "Sorry, it looks like you're not participating in any active games at the moment.\n\n"
                    "Please sign up for a game before attempting to submit a strategy."
                ),
            )

            return

        else:
            game_id = games[0]

    else:
        if not db_utils.signup_exists(user_id, game_id):
            logger.info("User is not signed up for indicated game")
            logger.info("Messaging user about the status of their participation")
            client.chat_postEphemeral(
                token=os.getenv("BOT_TOKEN"),
                channel=command["channel_id"],
                user=user_id,
                text=(
                    "Sorry, I couldn't find any record of your participation in the game you indicated. "
                    "Please verify the game ID you provided before attempting to submit a strategy again.\n\n"
                    f"For your reference, the games you are signed up for include: {', '.join(games)}"
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
def update_home_tab(client, event, logger):
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
        token=os.getenv("BOT_TOKEN"),
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

    logger.info("Valid user signup request")

    game_id = int(message["metadata"]["event_payload"]["game_id"])

    if db_utils.signup_exists(user_id, game_id):
        logger.info("User already signed up for game, request denied")

        client.chat_postEphemeral(
            token=os.getenv("BOT_TOKEN"),
            channel=message_channel,
            text=f"You have already signed up for game {game_id}. Glad you're excited, though!",
            user=user_id,
        )
        return

    db_utils.add_user_to_game(user_id, game_id)

    logger.info("User signed up for game successfully")

    game_start = db_utils.get_game_start(game_id)

    client.chat_postEphemeral(
        token=os.getenv("BOT_TOKEN"),
        channel=message_channel,
        text=f'You have been signed up for Blotto game {game_id}! Round 1 will begin at {game_start.strftime("%I:%M %p %Z %b %d, %Y")}.',
        user=user_id,
    )


@app.event("reaction_removed")
def remove_participant(event, client: WebClient, logger: logging.Logger):
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
        token=os.getenv("BOT_TOKEN"),
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
            token=os.getenv("BOT_TOKEN"),
            channel=message_channel,
            text=f"I can't seem to find any record that you signed up for game {game_id}",
            user=user_id,
        )
        return

    db_utils.remove_user_from_game(user_id, game_id)

    logger.info("User removed from game successfully")

    client.chat_postEphemeral(
        token=os.getenv("BOT_TOKEN"),
        channel=message_channel,
        text=f"You have been removed from Blotto game {game_id}. Sorry to see you go :cry:",
        user=user_id,
    )


@app.event("message_metadata_posted")
def metadata_trigger_router(client: WebClient, payload: dict, logger: logging.Logger):
    def game_start_handler(client: WebClient, payload: dict, logger: logging.Logger):
        logger.info(f"Game {payload['game_id']} starting")
        logger.info("Posting rules for Round 1")
        round_id, fields, soldiers = db_utils.get_round(payload["game_id"], 1)
        logger.info(f"Round ID = {round_id}")
        round = blotto.RoundLibrary.load_round(round_id, fields, soldiers)

        client.chat_postMessage(
            token=os.getenv("BOT_TOKEN"),
            channel=payload["announcement_channel"],
            text=round.RULES,
        )

    def round_close_handler(client: WebClient, payload: dict, logger: logging.Logger):
        logger.info("Round close, posting next round start")
        logger.info("Calculating round results")
        logger.info("Updating leaderboard")

    def game_end_handler(client: WebClient, payload: dict, logger: logging.Logger):
        logger.info("Game end, posting announcement")
        logger.info("Calculating round results")
        logger.info("Calculating game results")
        logger.info("Updating leaderboard")
        logger.info("Posting game winner announcement")

    logger.info("Received metadata, passing payload to handler")

    metadata_type = payload["metadata"]["event_type"]
    metadata_payload = payload["metadata"]["event_payload"]

    match metadata_type:
        case "game_announced":
            logger.info("Game announcement, no action required")

        case "game_start":
            game_start_handler(client, metadata_payload, logger)

        case "round_close":
            round_close_handler(client, metadata_payload, logger)

        case "game_end":
            game_end_handler(client, metadata_payload, logger)


@app.view("submit_round")
def handle_round_submission(ack, view, client: WebClient, context, logger):
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

    num_rounds = int(view["state"]["values"]["num_rounds"]["num_rounds"]["value"])

    round_length = view["state"]["values"]["round_length"]["round_length"]["value"]

    if "hour" in round_length:
        round_length = datetime.timedelta(hours=int(round_length.split(" ")[0]))

    elif "day" in round_length:
        round_length = datetime.timedelta(days=int(round_length.split(" ")[0]))

    else:
        round_length = datetime.timedelta(days=int(round_length))

    date_input = view["state"]["values"]["date"]["date"]["selected_date"]
    time_input = view["state"]["values"]["time"]["time"]["selected_time"]
    timezone_input = client.users_info(
        token=os.getenv("BOT_TOKEN"), user=context["user_id"]
    )["user"]["tz"]
    signup_close = (
        pytz.timezone(timezone_input)
        .localize(
            datetime.datetime.strptime(date_input + " " + time_input, "%Y-%m-%d %H:%M")
        )
        .astimezone(pytz.utc)
    )

    logger.info("Valid params, creating game instance")

    game_id = db_utils.create_new_game(
        num_rounds, round_length, signup_close
    ).inserted_primary_key[0]
    db_utils.generate_rounds(game_id, num_rounds, round_length, signup_close)
    logger.info("Game created, announcing")

    selected_channel = view["state"]["values"]["advertise_to_channels"][
        "advertise_to_channels"
    ]["selected_channel"]

    client.chat_postMessage(
        token=os.getenv("BOT_TOKEN"),
        channel=selected_channel,
        text=(
            f"<@{context['user_id']}> has started a new game of Blotto!\n\n"
            "Raise your hands :man-raising-hand: :woman-raising-hand: "
            f"to test your grit and game theory over the course of {num_rounds} rounds "
            f"in a round-robin style tournament. Each round will have a submission window of "
            f"{round_length / datetime.timedelta(hours=1)} hour(s).\n\n"
            "Rules for each round will be announced at the start of the submission window for that round, "
            f"and the signup period for Game {game_id} will close "
            f"<!date^{int(signup_close.timestamp())}^{{date_short_pretty}} at {{time}}|{signup_close.strftime('%Y-%m-%d %H:%M %Z')}>.\n\n"
            "To learn more, read about the Colonel Blotto game <https://en.wikipedia.org/wiki/Blotto_game|here> "
            "or check out the homepage of this app. Brought to you by Jovi :smile:"
        ),
        metadata={
            "event_type": "game_announced",
            "event_payload": {
                "game_id": game_id,
                "announcement_channel": selected_channel,
            },
        },
        unfurl_links=False,
    )

    logger.info("Game announced, scheduling signup close announcement")
    client.chat_scheduleMessage(
        token=os.getenv("BOT_TOKEN"),
        channel=selected_channel,
        post_at=int(signup_close.timestamp()),
        text=(
            f"Game {game_id} has now begun!\n\n"
            f"<@{client.auth_test()['user_id']}> will post the rules for Round 1 shortly, and participants will have "
            f"{round_length / datetime.timedelta(hours=1)} hour(s) to get their submission in.\n\n"
            "Good luck! :fist:"
        ),
        metadata={
            "event_type": "game_start",
            "event_payload": {
                "game_id": game_id,
                "announcement_channel": selected_channel,
            },
        },
    )


if __name__ == "__main__":
    db_utils.MetaData.create_all()

    handler = SocketModeHandler(app, os.getenv("APP_TOKEN"))

    try:
        handler.start()
    except KeyboardInterrupt:
        print("\nExiting")
        sys.exit(0)

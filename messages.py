signup_request_error_duplicate = """
You have already signed up for game {game_id}. Glad you're excited, though!
"""

signup_request_error_game_started = """
Sorry, the game you signed up for has already begun. Try starting a new game!
"""

signup_request_success = """
You signed up for Blotto game {game_id}! Round 1 will begin {game_start}.
"""

signup_remove_request_error_no_signup = """
I can't find any record indicating you signed up for game {game_id}; if you think this is a mistake, reach out to Jovi.
"""

signup_remove_request_success = """
Your signup has been removed for Blotto game {game_id}. Sorry to see you go :cry:
"""

game_start_announcement = """
Game {game_id} has begun! As a reminder, in each round you will have {round_length} hours to submit your strategy.

Rules will only be posted at the very start of the round, and results will be calculated and updated on my app homepage, where you can also view leaderboards for your games.

Good luck! :fist:
"""

round_start_announcement = """
Game {game_id} round {round_num} has started! Participants have until {round_end} to get their strategies submitted. Please use the command `/submit_strategy` with the appropriate game ID to do so.

The rules for this round are as follows:
{round_rules}
"""

new_game_announcement = """
<@{user_id}> has started a new game of Blotto!

Raise your hands :man-raising-hand: :woman-raising-hand: to test your grit and game theory over the course of {num_rounds} battles in a round-robin style tournament. Each round will have a submission window of {round_length} hours.

Rules for each battle will be announced at the start of the submission window for that round. The signup period for Game {game_id} will close {game_start}.

To learn more, read about the Blotto game <https://en.wikipedia.org/wiki/Blotto_game|here> or check out the homepage of this app. Brought to you by Jovi :smile:
"""

round_end_announcement = """
Game {game_id} round {round_num} has ended! To see how you scored, check out the app homepage.

Here's a snapshot of the scores for this round:
1. <@{first}>: {first_score}
2. <@{second}>: {second_score}
3. <@{third}>: {third_score}

To see how you're doing in the game overall, you can also check out the app homepage.
"""

game_end_announcement = """
Game {game_id} has ended! Congratulations to <@{winner}>, you've placed first with a score of {winner_score}!

Thanks for playing everyone; if you'd like to view your scores, you can check it out on the app homepage, with detailed results about how you did on each round and in the game overall.
"""

general_rules = """
> • Soldiers must be integers
> • You can make multiple submissions, but only the last one will count
> • No collusion!
"""

submit_strategy_error_not_in_active_game = """
It looks like you're not signed up for any active games.
"""

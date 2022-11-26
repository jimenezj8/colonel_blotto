# colonel_blotto
A revival of a personally beloved game, meant for tournament-style play.

## Developers

### Code Organization

`app.py` is where the application defines listener functions and responses. It handles all interactions with the Slack workspaces.

`blotto.py` is where all the Blotto-specific code lives. The Round Library, scoring, etc.

`db_utils.py` handles all database interactions, and `models.py` defines the database structure.

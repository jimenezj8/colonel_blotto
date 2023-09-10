# colonel_blotto

A revival of a personally beloved game, meant for tournament-style play.

## Developers

### Code Organization

`app.py` is where the application defines listener functions and responses. It handles all interactions with the Slack workspaces.
`views` is the directory that stores all of the modal views that define user interactions with the app. Finally,
`messages.py` is the location where you can find most of the messages that the bot uses to communicate with users.

`blotto/` is where all the Blotto-specific code lives.

`db_utils/` handles all database interactions, and `models/` defines the database structure.

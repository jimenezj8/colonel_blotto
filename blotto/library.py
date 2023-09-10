import random


class BlottoLibrary:
    def __init__(self, members: list):
        self.MAP = {
            member.LIBRARY_ID: member for member in members if member.LIBRARY_ID > 0
        }

    def get_random(self):
        "Returns a random member of the library as a class reference"
        return random.choice(self.MAP.values())

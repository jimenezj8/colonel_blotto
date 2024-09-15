import random


class BlottoLibrary:
    """Base class for libraries of Blotto game components."""

    def __init__(self, member_type: type):
        self.MAP: dict[int, type] = {
            member.LIBRARY_ID: member
            for member in member_type.__subclasses__()
            if member.LIBRARY_ID > 0
        }

    def get_random(self) -> type:
        "Returns a random member of the library as a class reference"
        return random.choice(list(self.MAP.values()))

import pytest

from blotto.core import stage
from blotto.exc import BlottoNotDefinedError


def test_blotto_library_init():
    random_stage = stage.StageLibrary.get_random()
    assert issubclass(getattr(stage, random_stage.__name__, False), stage.Stage)


def test_blotto_library_members_all_subclasses():
    members = list(stage.StageLibrary.MAP.values())
    is_subclass = [issubclass(member, stage.Stage) for member in members]
    assert all(is_subclass)


def test_stage_init():
    with pytest.raises(BlottoNotDefinedError):
        stage.Stage(7, 100)

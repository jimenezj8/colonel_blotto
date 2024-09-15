from blotto.core import stage


def test_blotto_library_init():
    random_stage = stage.StageLibrary.get_random()
    assert isinstance(getattr(stage, random_stage.__name__, False), stage.Stage)

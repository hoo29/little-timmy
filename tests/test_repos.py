import os
import pytest

from little_timmy.var_finder import find_unused_vars
from little_timmy.config_loader import find_and_load_config

TEST_REPOS = os.path.join("tests", "repos")


def get_test_folders(path: str):
    return [name for name in os.listdir(path) if os.path.isdir(os.path.join(path, name))]


@pytest.mark.parametrize("repo", get_test_folders(TEST_REPOS))
@pytest.mark.filterwarnings("ignore:.*:DeprecationWarning")
def test_finds_unused_vars(repo):
    with open(os.path.join(TEST_REPOS, repo, "unused_vars")) as f:
        expected = f.read().splitlines()

    config = find_and_load_config(os.path.join(TEST_REPOS, repo, "repo"))
    actual = find_unused_vars(os.path.join(TEST_REPOS, repo, "repo"), config)

    assert bool(set(actual.keys()).intersection(set(expected)))

from little_timmy.var_finder import find_unused_vars

import os
import pytest

TEST_REPOS = os.path.join("tests", "repos")


def get_test_folders(path: str):
    return [name for name in os.listdir(path) if os.path.isdir(os.path.join(path, name))]


@pytest.mark.parametrize("repo", get_test_folders(TEST_REPOS))
@pytest.mark.filterwarnings("ignore:.*:DeprecationWarning")
def test_finds_unused_vars(repo):
    with open(os.path.join(TEST_REPOS, repo, "unused_vars")) as f:
        expected = f.read().splitlines()

    actual = find_unused_vars(os.path.join(TEST_REPOS, repo, "repo"))

    assert list(actual.keys()) == expected

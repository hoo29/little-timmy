from collections import defaultdict
import json
import os
import pytest

from little_timmy.config_loader import DuplicatedVarInfo, setup_run
from little_timmy.duplicated_var_finder import find_duplicated_vars
from little_timmy.unused_var_finder import find_unused_vars


TEST_REPOS = os.path.join("tests", "repos")


def get_test_folders(path: str):
    return [name for name in os.listdir(path) if os.path.isdir(os.path.join(path, name))]


def get_test_duplicate_folders(path: str):
    return [name for name in os.listdir(path) if os.path.isdir(os.path.join(path, name)) and os.path.isfile(os.path.join(path, name, "duplicated_vars"))]


@pytest.mark.parametrize("repo", get_test_folders(TEST_REPOS))
@pytest.mark.filterwarnings("ignore:.*:DeprecationWarning")
def test_finds_unused_vars(repo):
    with open(os.path.join(TEST_REPOS, repo, "unused_vars")) as f:
        expected = f.read().splitlines()
    context = setup_run(os.path.join(TEST_REPOS, repo, "repo"))
    find_unused_vars(context)
    actual = context.all_unused_vars

    _actual = list(actual.keys())
    _actual.sort()
    expected.sort()
    assert _actual == expected
    expected_len = len(expected)
    assert expected_len == len(actual.keys())
    assert len(set(expected).intersection(
        set(actual.keys()))) == expected_len


@pytest.mark.parametrize("repo", get_test_duplicate_folders(TEST_REPOS))
@pytest.mark.filterwarnings("ignore:.*:DeprecationWarning")
def test_finds_duplicated_vars(repo):
    with open(os.path.join(TEST_REPOS, repo, "duplicated_vars")) as f:
        raw_expected = f.read().splitlines()
    context = setup_run(os.path.join(TEST_REPOS, repo, "repo"))
    find_duplicated_vars(context)
    actual = context.all_duplicated_vars

    expected: dict[str, DuplicatedVarInfo] = defaultdict(DuplicatedVarInfo)
    for line in raw_expected:
        parts = line.split("#")
        key = f"localhost##{parts[0]}"
        key = key.replace(":", "##")
        expected[key].locations = set(
            json.loads(parts[1]))

    assert sorted(list(actual.keys())) == sorted(list(expected.keys()))
    for k, v in actual.items():
        rel_locs = [os.path.relpath(x, context.root_dir) for x in v.locations]
        assert not expected[k].locations.symmetric_difference(set(rel_locs))

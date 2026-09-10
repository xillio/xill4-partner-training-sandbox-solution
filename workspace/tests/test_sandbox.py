"""The naming and allocation rules two trainees' sandboxes must never share."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
import sandbox


def test_slug_reduces_an_id_to_database_safe_characters():
    assert sandbox.slug("Alice Smith") == "alice_smith"
    assert sandbox.slug("bob.o'neill@partner.example") == "bob_o_neill_partner_example"
    assert sandbox.database_name("Alice Smith") == "xill4_alice_smith"


def test_an_id_with_nothing_usable_in_it_is_refused():
    # Silently mapping this to a shared default would put two trainees in one database.
    with pytest.raises(sandbox.TraineeIdError):
        sandbox.slug("---")


def test_different_trainees_get_different_databases():
    names = {sandbox.database_name(name) for name in ("alice", "bob", "carol", "dave")}
    assert len(names) == 4


def test_port_slot_is_stable_for_a_trainee():
    assert sandbox.preferred_slot("alice") == sandbox.preferred_slot("alice")
    assert sandbox.preferred_slot("alice") != sandbox.preferred_slot("bob")


def test_a_trainee_keeps_the_slot_they_already_hold():
    # Their instance's URL has to survive a reset, so an existing allocation wins over
    # whatever the hash would now prefer.
    assert sandbox.assign_slot("alice", {"alice": 42}) == 42


def test_a_collision_moves_the_newcomer_not_the_incumbent():
    preferred = sandbox.preferred_slot("alice")
    assert sandbox.assign_slot("alice", {"bob": preferred}) == (preferred + 1) % 100


def test_allocation_gives_up_rather_than_reusing_a_port():
    taken = {f"trainee{index}": index for index in range(sandbox.PORT_SLOTS)}
    with pytest.raises(RuntimeError):
        sandbox.assign_slot("one-too-many", taken)


def test_connection_string_escapes_a_password_that_would_break_the_uri():
    uri = sandbox.connection_string("alice", "p@ss/word:1", "xill4_alice")
    assert uri == ("mongodb://alice:p%40ss%2Fword%3A1@mongo:27017/"
                   "xill4_alice?authSource=xill4_alice")


def test_connection_string_authenticates_against_the_trainees_own_database():
    # authSource must be the trainee's database: that is where their scoped user exists.
    assert "authSource=xill4_bob" in sandbox.connection_string("bob", "secret", "xill4_bob")


def test_rendered_env_carries_the_trainees_own_database_and_port(tmp_path):
    rendered = sandbox.parse_env(sandbox.render_env(
        "alice", "01-legacy-fileshare", ".workspaces/alice/01-legacy-fileshare", 5,
        {"MONGO_PASSWORD": "pw", "S3_SECRET_KEY": "s3pw"}))
    assert rendered["XILL4_PORT"] == str(sandbox.XILL4_PORT_BASE + 5)
    assert rendered["MONGO_DATABASE"] == "xill4_alice"
    assert rendered["XILL4_DATABASE_CONNECTION_STRING"].endswith("authSource=xill4_alice")


def test_allocated_slots_reads_back_what_was_written(tmp_path):
    for trainee, slot in (("alice", 3), ("bob", 7)):
        path = sandbox.env_file_for(tmp_path, trainee)
        path.write_text(sandbox.render_env(
            trainee, "01", f".workspaces/{trainee}/01", slot,
            {"MONGO_PASSWORD": "pw", "S3_SECRET_KEY": "s3"}), encoding="utf-8")
    assert sandbox.allocated_slots(tmp_path) == {"alice": 3, "bob": 7}
    # And a third trainee is placed around them rather than on top of one.
    assert sandbox.assign_slot("carol", sandbox.allocated_slots(tmp_path)) not in (3, 7)


def test_generated_passwords_are_not_reused():
    assert sandbox.generate_password() != sandbox.generate_password()


@pytest.mark.skipif(os.name != "posix", reason="POSIX permissions")
def test_preparing_a_workspace_keeps_the_answer_key_private(tmp_path):
    workspace = tmp_path / "ws"
    (workspace / "target").mkdir(parents=True)
    (workspace / ".expected").mkdir()
    (workspace / ".expected" / "facts.json").write_text("{}", encoding="utf-8")

    sandbox.prepare_workspace_permissions(workspace)

    assert Path(workspace / ".expected").stat().st_mode & 0o077 == 0
    # Nothing can be graded if the trainee's instance cannot write its output.
    assert Path(workspace / "target").stat().st_mode & 0o200

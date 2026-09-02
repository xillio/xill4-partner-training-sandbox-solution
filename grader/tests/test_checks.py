"""Unit tests for the check plugins -- these are what scenario authors build on."""

import hashlib
import json

import pytest
from grader.checks import get_check, registered_types, resolve_value
from grader.checks.jsondata import QueryError, query
from grader.context import Context, MissingVariable


@pytest.fixture
def ctx(tmp_path):
    return Context(tmp_path, {"TARGET": str(tmp_path / "target"), "NAME": "alice"})


def run_check(type_name, params, ctx):
    return get_check(type_name)(params, ctx)


def test_context_expands_nested_structures(ctx):
    assert ctx.expand({"a": ["${NAME}.csv"]}) == {"a": ["alice.csv"]}


def test_context_rejects_unknown_variable(ctx):
    with pytest.raises(MissingVariable, match="SOURCE"):
        ctx.expand("${SOURCE}/x")


def test_relative_paths_resolve_against_the_workspace(ctx, tmp_path):
    assert ctx.path("target/out.json") == tmp_path / "target" / "out.json"


def test_fs_exists_reports_missing_paths(ctx):
    outcome = run_check("fs.exists", {"path": "${TARGET}/manifest.json", "kind": "file"}, ctx)
    assert not outcome.passed and "missing" in outcome.message


def test_fs_file_count_honours_glob_and_bounds(ctx, tmp_path):
    (tmp_path / "target").mkdir()
    for name in ("a.pdf", "b.pdf", "c.txt"):
        (tmp_path / "target" / name).write_text("x")

    assert run_check("fs.file_count", {"path": "${TARGET}", "pattern": "**/*.pdf",
                                       "equals": 2}, ctx).passed
    assert not run_check("fs.file_count", {"path": "${TARGET}", "min": 5}, ctx).passed


def test_fs_file_count_requires_a_constraint(ctx, tmp_path):
    (tmp_path / "target").mkdir()
    with pytest.raises(ValueError, match="equals, min or max"):
        run_check("fs.file_count", {"path": "${TARGET}"}, ctx)


def test_fs_tree_matches_distinguishes_missing_from_altered(ctx, tmp_path):
    digest = hashlib.sha256(b"hello").hexdigest()
    (tmp_path / "target" / "a").mkdir(parents=True)
    (tmp_path / "target" / "a" / "one.txt").write_bytes(b"hello")
    (tmp_path / "target" / "a" / "two.txt").write_bytes(b"wrong")
    manifest = tmp_path / "tree.json"
    manifest.write_text(json.dumps({"a/one.txt": digest, "a/two.txt": digest,
                                    "a/three.txt": digest}))

    outcome = run_check("fs.tree_matches", {"path": "${TARGET}", "manifest": str(manifest)}, ctx)
    assert not outcome.passed
    assert outcome.evidence["missing"] == ["a/three.txt"]
    assert outcome.evidence["wrong_content"] == ["a/two.txt"]


def test_fs_tree_matches_can_ignore_content(ctx, tmp_path):
    (tmp_path / "target").mkdir()
    (tmp_path / "target" / "one.txt").write_text("anything")
    manifest = tmp_path / "tree.json"
    manifest.write_text(json.dumps({"one.txt": "0" * 64}))

    assert run_check("fs.tree_matches", {"path": "${TARGET}", "manifest": str(manifest),
                                         "compare": "paths"}, ctx).passed


@pytest.mark.parametrize("expression,expected", [
    ("documents[]", 2),
    ("documents[0].path", "a.pdf"),
    ("summary.errors", 0),
])
def test_json_query_supports_the_documented_syntax(expression, expected):
    document = {"documents": [{"path": "a.pdf"}, {"path": "b.pdf"}], "summary": {"errors": 0}}
    assert query(document, expression) == expected


def test_json_query_explains_a_bad_path():
    with pytest.raises(QueryError, match="no key 'nope'"):
        query({"a": 1}, "nope.b")


def test_json_assert_reads_expected_values_from_a_reference(ctx, tmp_path):
    (tmp_path / "target").mkdir()
    (tmp_path / "target" / "manifest.json").write_text(json.dumps({"documents": [1, 2, 3]}))
    facts = tmp_path / "facts.json"
    facts.write_text(json.dumps({"files_on_share": 3}))

    assert run_check("json.assert", {
        "path": "${TARGET}/manifest.json",
        "queries": [{"query": "documents[]",
                     "equals": {"from": str(facts), "query": "files_on_share"}}],
    }, ctx).passed


def test_json_assert_reports_invalid_json(ctx, tmp_path):
    (tmp_path / "target").mkdir()
    (tmp_path / "target" / "manifest.json").write_text("{not json")
    outcome = run_check("json.assert", {"path": "${TARGET}/manifest.json",
                                        "queries": [{"query": "a", "equals": 1}]}, ctx)
    assert not outcome.passed and "not valid JSON" in outcome.message


def test_csv_matches_ignores_row_order_but_not_values(ctx, tmp_path):
    (tmp_path / "target").mkdir()
    actual = tmp_path / "target" / "metadata.csv"
    expected = tmp_path / "expected.csv"
    expected.write_text("doc_id,department\nb,legal\na,finance\n")

    actual.write_text("doc_id,department\na,finance\nb,legal\n")
    assert run_check("csv.matches", {"path": str(actual), "expected": str(expected),
                                     "key": "doc_id"}, ctx).passed

    actual.write_text("doc_id,department\na,Finance\nb,legal\n")
    outcome = run_check("csv.matches", {"path": str(actual), "expected": str(expected),
                                        "key": "doc_id"}, ctx)
    assert not outcome.passed
    assert outcome.evidence["wrong_values"][0]["actual"] == "Finance"


def test_csv_matches_names_the_missing_column(ctx, tmp_path):
    actual, expected = tmp_path / "a.csv", tmp_path / "e.csv"
    actual.write_text("doc_id\na\n")
    expected.write_text("doc_id,department\na,finance\n")

    outcome = run_check("csv.matches", {"path": str(actual), "expected": str(expected),
                                        "key": "doc_id"}, ctx)
    assert not outcome.passed and "department" in outcome.message


def test_cmd_run_captures_exit_code_and_output(ctx):
    assert run_check("cmd.run", {"command": ["echo", "migrated 19"],
                                 "stdout_matches": r"migrated \d+"}, ctx).passed
    assert not run_check("cmd.run", {"command": ["false"]}, ctx).passed
    assert not run_check("cmd.run", {"command": ["definitely-not-a-command"]}, ctx).passed


def test_resolve_value_passes_plain_values_through(ctx):
    assert resolve_value("${NAME}", ctx) == "alice"
    assert resolve_value(7, ctx) == 7


def test_every_registered_type_is_callable():
    assert all(callable(get_check(name)) for name in registered_types())

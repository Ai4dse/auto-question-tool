"""Tests for the ``schedule_properties`` question type.

The reference values for the four exercise-3 histories are taken directly from
the task sheet's sample solution; the property implications are theorems that
must hold for *every* generated instance, which gives strong cross-checks.
"""

import pytest

from app.question_types.schedule_properties import (
    SchedulePropertiesQuestion,
    parse_history,
    PROPERTIES,
)


def props_of(history):
    """Compute the five property booleans for a raw history string."""
    q = SchedulePropertiesQuestion(seed=1)
    ops = parse_history(history)
    edges, nodes = q._conflict_edges(ops)
    return {
        "is_serial": q._is_serial(ops),
        "is_serializable": not q._has_cycle(nodes, edges),
        "is_recoverable": q._is_recoverable(ops),
        "is_aca": q._is_aca(ops),
        "is_strict": q._is_strict(ops),
    }


# (history, expected props) — the four histories from exercise 3.
EXERCISE_HISTORIES = [
    (
        "w1[x] w1[y] c1 r2[x] w2[z] c2 r3[y] a3",
        {"is_serial": True, "is_serializable": True, "is_recoverable": True,
         "is_aca": True, "is_strict": True},
    ),
    (
        "w1[x] w2[x] w2[y] w1[y] w1[z] c1 c2",
        {"is_serial": False, "is_serializable": False, "is_recoverable": True,
         "is_aca": True, "is_strict": False},
    ),
    (
        "r1[x] w1[x] r2[x] w2[y] r1[y] w1[z] c1 c2 r3[z] w3[x] c3",
        {"is_serial": False, "is_serializable": False, "is_recoverable": False,
         "is_aca": False, "is_strict": False},
    ),
    (
        "r1[x] w1[y] r2[y] w1[z] w2[z] c1 w2[x] c2",
        {"is_serial": False, "is_serializable": True, "is_recoverable": True,
         "is_aca": False, "is_strict": False},
    ),
]


@pytest.mark.parametrize("history,expected", EXERCISE_HISTORIES)
def test_exercise_histories(history, expected):
    assert props_of(history) == expected


def test_lecture_recoverability_example():
    # Slide "Recoverability": H is NOT recoverable (T2 reads x from T1, commits,
    # then T1 aborts).
    p = props_of("w1[x] r2[x] w2[y] c2 a1")
    assert p["is_recoverable"] is False
    assert p["is_aca"] is False  # reads x before c1 (which never happens)
    assert p["is_strict"] is False


def test_lecture_strictness_example():
    # Slide "Strictness": w2[x] violates strictness (writes x before T1 ends).
    p = props_of("r1[x] w1[x] w2[x] c1 c2")
    assert p["is_strict"] is False
    # No transaction reads another's write here, so RC/ACA hold vacuously.
    assert p["is_recoverable"] is True
    assert p["is_aca"] is True


def test_serial_schedule_is_everything():
    # A fully serial, all-committing schedule satisfies every property.
    p = props_of("r1[x] w1[x] c1 r2[x] w2[x] c2")
    assert all(p.values())


def test_parse_history_roundtrip():
    ops = parse_history("w1[x] r2[y] c1 a2")
    assert ops == [
        {"kind": "w", "t": 1, "obj": "x"},
        {"kind": "r", "t": 2, "obj": "y"},
        {"kind": "c", "t": 1, "obj": None},
        {"kind": "a", "t": 2, "obj": None},
    ]


def test_parse_history_rejects_garbage():
    with pytest.raises(ValueError):
        parse_history("w1[x] bogus c1")


# --------------------------------------------------------------------------- #
# Property implications — theorems that must hold for every instance.
# --------------------------------------------------------------------------- #
SEEDS = range(200)
DIFFICULTIES = ["easy", "medium", "hard"]


@pytest.mark.parametrize("difficulty", DIFFICULTIES)
@pytest.mark.parametrize("seed", SEEDS)
def test_property_implications(seed, difficulty):
    q = SchedulePropertiesQuestion(seed=seed, difficulty=difficulty)
    p = q.props
    # serial => strict => ACA => recoverable
    if p["is_serial"]:
        assert p["is_strict"], (seed, difficulty, q._history_str())
    if p["is_strict"]:
        assert p["is_aca"], (seed, difficulty, q._history_str())
    if p["is_aca"]:
        assert p["is_recoverable"], (seed, difficulty, q._history_str())
    # serial => serializable (a serial order has an acyclic precedence graph).
    # NOTE: strict does NOT imply serializable — strictness ignores read-write
    # anti-dependencies, so a strict schedule can still have a precedence cycle.
    if p["is_serial"]:
        assert p["is_serializable"], (seed, difficulty, q._history_str())


@pytest.mark.parametrize("seed", SEEDS)
def test_determinism(seed):
    a = SchedulePropertiesQuestion(seed=seed, difficulty="medium")
    b = SchedulePropertiesQuestion(seed=seed, difficulty="medium")
    assert a._history_str() == b._history_str()
    assert a.props == b.props


@pytest.mark.parametrize("seed", SEEDS)
def test_generate_evaluate_wiring(seed):
    q = SchedulePropertiesQuestion(seed=seed, difficulty="medium")
    layout = q.generate()
    assert "view1" in layout

    # Collect element ids present in the layout.
    ids = {el.get("id") for el in layout["view1"] if isinstance(el, dict) and el.get("id")}
    for fid, _label in PROPERTIES:
        assert fid in ids
    assert "graph" in ids
    assert "solution" in ids

    # Submitting the exact correct answer scores every property correct.
    correct_input = {fid: q.props[fid] for fid, _ in PROPERTIES}
    results = q.evaluate(correct_input)
    for fid, _ in PROPERTIES:
        assert results[fid]["correct"] is True

    # An all-wrong submission is graded wrong on exactly the true properties.
    wrong_input = {fid: not q.props[fid] for fid, _ in PROPERTIES}
    wrong_results = q.evaluate(wrong_input)
    for fid, _ in PROPERTIES:
        assert wrong_results[fid]["correct"] is False

    # Graph payload shape.
    graph = results["graph"]["expected"]
    assert set(graph) == {"nodes", "edges", "cycles", "serializable", "aborted"}
    assert graph["serializable"] == q.props["is_serializable"]
    # Cycle present iff not serializable.
    assert bool(graph["cycles"]) == (not q.props["is_serializable"])

    # Solution is a non-empty markdown string.
    assert isinstance(results["solution"]["expected"], str)
    assert results["solution"]["expected"].strip()


def test_empty_input_does_not_crash():
    q = SchedulePropertiesQuestion(seed=3)
    results = q.evaluate({})
    # Unchecked boxes count as "property does not hold".
    for fid, _ in PROPERTIES:
        assert results[fid]["correct"] == (q.props[fid] is False)


def test_distribution_has_variety():
    # Across seeds we should see both serializable and non-serializable, and
    # both with and without aborts.
    ser, non_ser, with_abort, no_abort = 0, 0, 0, 0
    for seed in range(60):
        q = SchedulePropertiesQuestion(seed=seed, difficulty="medium")
        if q.props["is_serializable"]:
            ser += 1
        else:
            non_ser += 1
        if q.aborted:
            with_abort += 1
        else:
            no_abort += 1
    assert ser > 0 and non_ser > 0
    assert with_abort > 0 and no_abort > 0

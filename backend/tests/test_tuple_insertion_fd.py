import pytest

from app.question_types.tuple_insertion_fd import TupleInsertionFDQuestion


DIFFICULTIES = ["easy", "medium", "hard"]
SEEDS = [1, 7, 42, 123, 999, 2024]


def _independent_violations(question, t):
    """Recompute violated FD indices independently of the question internals."""
    violated = []
    for idx, (lhs, rhs) in enumerate(question.fds):
        for s in question.instance:
            if all(s[a] == t[a] for a in lhs) and any(s[b] != t[b] for b in rhs):
                violated.append(idx)
                break
    return violated


def test_deterministic_for_fixed_seed():
    a = TupleInsertionFDQuestion(seed=42, difficulty="medium")
    b = TupleInsertionFDQuestion(seed=42, difficulty="medium")

    assert a.attributes == b.attributes
    assert [sorted(map(sorted, [lhs, rhs])) for lhs, rhs in a.fds] == \
           [sorted(map(sorted, [lhs, rhs])) for lhs, rhs in b.fds]
    assert [c["values"] for c in a.candidates] == [c["values"] for c in b.candidates]
    assert a.evaluate({}) == b.evaluate({})


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("difficulty", DIFFICULTIES)
def test_structure_and_consistency(seed, difficulty):
    q = TupleInsertionFDQuestion(seed=seed, difficulty=difficulty)

    assert len(q.candidates) == q.num_tuples
    assert len(q.instance) >= 1

    for cand in q.candidates:
        expected_violations = sorted(_independent_violations(q, cand["values"]))
        assert sorted(cand["violated"]) == expected_violations
        assert cand["insertable"] == (len(expected_violations) == 0)


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("difficulty", DIFFICULTIES)
def test_layout_field_ids(seed, difficulty):
    q = TupleInsertionFDQuestion(seed=seed, difficulty=difficulty)
    layout = q.generate()

    assert "view1" in layout
    cand_table = next(el for el in layout["view1"] if el.get("type") == "layout_table")
    # header row + one row per candidate
    assert cand_table["rows"] == q.num_tuples + 1
    assert cand_table["cols"] == len(q.attributes) + 2


def _perfect_answer(q):
    """Build the fully correct user input for a question."""
    payload = {}
    for i, cand in enumerate(q.candidates):
        if cand["insertable"]:
            payload[f"tuple_{i}_decision"] = "Ja"
            payload[f"tuple_{i}_fds"] = ""
        else:
            payload[f"tuple_{i}_decision"] = "Nein"
            payload[f"tuple_{i}_fds"] = "; ".join(
                q._format_fd(q.fds[idx]) for idx in cand["violated"]
            )
    return payload


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("difficulty", DIFFICULTIES)
def test_perfect_answer_is_all_correct(seed, difficulty):
    q = TupleInsertionFDQuestion(seed=seed, difficulty=difficulty)
    results = q.evaluate(_perfect_answer(q))
    assert all(r["correct"] for r in results.values())


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("difficulty", DIFFICULTIES)
def test_empty_answer_grades_decisions_against_default(seed, difficulty):
    q = TupleInsertionFDQuestion(seed=seed, difficulty=difficulty)
    results = q.evaluate({})

    for i, cand in enumerate(q.candidates):
        dec = results[f"tuple_{i}_decision"]
        # Blank decision never matches the expected "Ja"/"Nein".
        assert dec["correct"] is False
        assert dec["expected"] in ("Ja", "Nein")

        fd = results[f"tuple_{i}_fds"]
        # Blank FD field is correct only for insertable tuples.
        assert fd["correct"] == cand["insertable"]


def test_wrong_fd_set_is_rejected_for_non_insertable():
    # Find a seed that yields at least one non-insertable tuple.
    q = None
    for seed in range(1, 200):
        candidate = TupleInsertionFDQuestion(seed=seed, difficulty="medium")
        if any(not c["insertable"] for c in candidate.candidates):
            q = candidate
            break
    assert q is not None, "expected at least one non-insertable tuple across seeds"

    i = next(i for i, c in enumerate(q.candidates) if not c["insertable"])
    payload = _perfect_answer(q)

    # Correct decision but empty FD set -> wrong.
    payload[f"tuple_{i}_fds"] = ""
    results = q.evaluate(payload)
    assert results[f"tuple_{i}_decision"]["correct"] is True
    assert results[f"tuple_{i}_fds"]["correct"] is False


def test_fd_parser_accepts_format_variants():
    q = TupleInsertionFDQuestion(seed=42, difficulty="easy")
    a, b, c = q.attributes[0], q.attributes[1], q.attributes[2]

    canonical = {(frozenset({a, b}), frozenset({c}))}
    for text in (
        f"{a}{b}->{c}",
        f"{a},{b} -> {c}",
        f"{b}{a}->{c}",
        f"{a}{b}→{c}",
        f"{a}{b}=>{c}",
        f"  {a}{b} -> {c}  ",
    ):
        assert q._parse_fds(text) == canonical, text

    # Multiple FDs separated by ';' or newline.
    multi = {(frozenset({a}), frozenset({b})), (frozenset({b}), frozenset({c}))}
    assert q._parse_fds(f"{a}->{b}; {b}->{c}") == multi
    assert q._parse_fds(f"{a}->{b}\n{b}->{c}") == multi

    # Blank -> empty set; malformed -> None.
    assert q._parse_fds("") == set()
    assert q._parse_fds("   ") == set()
    assert q._parse_fds("garbage") is None
    assert q._parse_fds(f"{a}->") is None
    assert q._parse_fds("1->2") is None  # not valid attributes


def test_invalid_difficulty_falls_back_to_easy():
    q = TupleInsertionFDQuestion(seed=1, difficulty="impossible")
    assert q.difficulty == "easy"

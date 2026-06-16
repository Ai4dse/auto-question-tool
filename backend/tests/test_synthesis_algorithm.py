import json

import pytest

from app.question_types.synthesis_algorithm import SynthesisAlgorithmQuestion


DIFFICULTIES = ["easy", "medium", "hard"]
MODES = ["steps", "exam"]
SEEDS = [1, 7, 42, 123, 999, 2024, 31337]


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def fd(lhs, rhs):
    return (frozenset(lhs), frozenset(rhs))


def fdset(*pairs):
    return {fd(l, r) for l, r in pairs}


def _q(**kwargs):
    kwargs.setdefault("seed", 1)
    return SynthesisAlgorithmQuestion(**kwargs)


def _with_fds(attrs, fds):
    """Build a question whose schema/FDs are overridden, then recompute the
    whole synthesis chain on them. Lets us assert the lecture examples exactly."""
    q = _q(difficulty="easy")
    q.attributes = list(attrs)
    q.all_attrs = frozenset(attrs)
    q.fds = list(fds)
    q._compute_chain()
    return q


def _closure(q, attrs, fds):
    return q._closure(attrs, fds)


# --------------------------------------------------------------------------- #
# Lecture examples (Folie 49 / 54 / 57 / 63) — the source of truth
# --------------------------------------------------------------------------- #
def test_left_reduction_slide49():
    # F = {ABC->D, A->D, B->D}  =>  {A->D, B->D}
    q = _q()
    result = set(q._left_reduce(list(fdset(("ABC", "D"), ("A", "D"), ("B", "D")))))
    assert result == fdset(("A", "D"), ("B", "D"))


def test_left_reduction_irreducible_slide52():
    # F = {AB->E, A->C, B->D} cannot be left-reduced (neither A nor B alone -> E)
    q = _q()
    given = fdset(("AB", "E"), ("A", "C"), ("B", "D"))
    assert set(q._left_reduce(list(given))) == given


def test_right_reduction_slide54():
    # F = {A->BCD, B->C, A->D}  =>  {A->B, B->C, A->D}
    q = _q()
    result = set(q._right_reduce(list(fdset(("A", "BCD"), ("B", "C"), ("A", "D")))))
    assert result == fdset(("A", "B"), ("B", "C"), ("A", "D"))


def test_right_reduction_can_empty_rhs_then_step3_removes_it():
    # F = {A->B, A->C, B->C}: right reduction empties A->C (=> A->∅),
    # step 3 then drops it, leaving {A->B, B->C}.
    q = _q()
    f1 = fdset(("A", "B"), ("A", "C"), ("B", "C"))
    f2 = set(q._right_reduce(list(f1)))
    assert fd("A", "") in f2  # A -> ∅ present after right reduction
    assert set(q._remove_empty(list(f2))) == fdset(("A", "B"), ("B", "C"))


def test_canonical_cover_slide57():
    # F = {A->B, B->C, AB->C}  =>  Fc = {A->B, B->C}
    q = _with_fds(["A", "B", "C"], fdset(("A", "B"), ("B", "C"), ("AB", "C")))
    assert set(q.cover) == fdset(("A", "B"), ("B", "C"))


def test_full_synthesis_cdshop_slide63():
    # CD_Shop mapped to single letters:
    #   A=cd_id B=track C=title D=interpret E=album F=foundation G=publication
    # F = {AB->C, A->DEFG, D->F, E->G}
    q = _with_fds(
        ["A", "B", "C", "D", "E", "F", "G"],
        fdset(("AB", "C"), ("A", "DEFG"), ("D", "F"), ("E", "G")),
    )
    # canonical cover (Folie 61/63)
    assert set(q.cover) == fdset(("AB", "C"), ("A", "DE"), ("D", "F"), ("E", "G"))
    # schemas (Folie 64, step 2)
    assert q.schemas == {
        frozenset("ABC"),
        frozenset("ADE"),
        frozenset("DF"),
        frozenset("EG"),
    }
    # {A,B} is the (unique) candidate key and already contained -> no key relation
    assert q.keys == [frozenset({"A", "B"})]
    assert q.key_contained is True
    # nothing is contained in another schema -> final == schemas
    assert q.final_schemas == q.schemas


# --------------------------------------------------------------------------- #
# Determinism
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("difficulty", DIFFICULTIES)
def test_deterministic_for_fixed_seed(difficulty):
    a = SynthesisAlgorithmQuestion(seed=42, difficulty=difficulty)
    b = SynthesisAlgorithmQuestion(seed=42, difficulty=difficulty)
    assert a.attributes == b.attributes
    assert set(a.f0) == set(b.f0)
    assert set(a.cover) == set(b.cover)
    assert a.final_schemas == b.final_schemas
    assert a.generate() == b.generate()
    assert a.evaluate({}) == b.evaluate({})


# --------------------------------------------------------------------------- #
# Structural invariants of the computed chain across many instances
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("difficulty", DIFFICULTIES)
def test_chain_is_valid(seed, difficulty):
    q = SynthesisAlgorithmQuestion(seed=seed, difficulty=difficulty)

    # canonical cover: every left-hand side appears exactly once (Folie 46/47 step 4)
    lhss = [frozenset(lhs) for lhs, _ in q.cover]
    assert len(lhss) == len(set(lhss))

    # equivalence F ≡ Fc : same closure on the relevant determinants (Folie 45)
    for lhs, rhs in q.f0:
        assert set(rhs) <= _closure(q, lhs, q.cover)
    for lhs, rhs in q.cover:
        assert set(rhs) <= _closure(q, lhs, q.f0)

    # synthesis output is a real decomposition that covers every attribute
    assert len(q.final_schemas) >= 2
    covered = set().union(*q.final_schemas) if q.final_schemas else set()
    assert covered == set(q.attributes)

    # at least one candidate key, and a key relation is added iff none is contained
    assert q.keys
    if q.key_contained:
        assert q.schemas_with_key == q.schemas
    else:
        assert any(set(q.chosen_key) == s for s in (q.schemas_with_key - q.schemas))

    # final schemas contain no schema that is a subset of another
    for s in q.final_schemas:
        assert not any(s < t for t in q.final_schemas)


@pytest.mark.parametrize("seed", SEEDS)
def test_hard_exercises_both_reductions(seed):
    # Generation aims for: a left reduction AND (a right reduction or an emptied FD).
    q = SynthesisAlgorithmQuestion(seed=seed, difficulty="hard")
    left_changed = set(q.f1) != set(q.f0)
    right_changed = set(q.f2) != set(q.f1)
    empty_removed = len(q.f2) != len(q.f3)
    assert left_changed and (right_changed or empty_removed)


# --------------------------------------------------------------------------- #
# Layout
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("difficulty", DIFFICULTIES)
def test_steps_layout_has_seven_views(seed, difficulty):
    q = SynthesisAlgorithmQuestion(seed=seed, difficulty=difficulty, mode="steps")
    layout = q.generate()

    assert [f"view{i}" for i in range(1, 8)] == [k for k in layout if k.startswith("view")]
    assert "view8" not in layout

    for index, (field_id, sol_id, _title) in enumerate(q.STEP_IDS, start=1):
        view = layout[f"view{index}"]
        assert any(el.get("type") == "text_input" and el.get("id") == field_id for el in view)
        sol = next(el for el in view if el.get("type") == "solution_box")
        assert sol["id"] == sol_id
        # The worked result must NOT be embedded in the payload.
        assert "expected" not in sol


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("difficulty", DIFFICULTIES)
def test_exam_layout_is_single_view_with_all_fields(seed, difficulty):
    q = SynthesisAlgorithmQuestion(seed=seed, difficulty=difficulty, mode="exam")
    layout = q.generate()

    assert list(k for k in layout if k.startswith("view")) == ["view1"]
    ids = {el.get("id") for el in layout["view1"] if el.get("type") == "text_input"}
    assert ids == {field_id for field_id, _s, _t in q.STEP_IDS}
    sols = [el for el in layout["view1"] if el.get("type") == "solution_box"]
    assert len(sols) == 1 and sols[0]["id"] == "solution" and "expected" not in sols[0]


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("mode", MODES)
def test_generate_does_not_leak_answers(seed, mode):
    """No reduced FD set / cover / schema list may appear in the question payload
    (answers are delivered only through evaluate())."""
    q = SynthesisAlgorithmQuestion(seed=seed, difficulty="hard", mode=mode)
    blob = json.dumps(q.generate(), ensure_ascii=False)

    for field_id in ("step_union", "step_schemas", "step_final"):
        expected = q._expected_text(field_id)
        # Only meaningful to check when it differs from the given F (always true
        # for schema steps; for the cover only when a reduction happened).
        if expected and expected != q._fmt_fds(q.f0):
            assert expected not in blob, (field_id, expected)


# --------------------------------------------------------------------------- #
# Evaluation
# --------------------------------------------------------------------------- #
def _perfect_payload(q):
    return {field_id: q._expected_text(field_id) for field_id, _s, _t in q.STEP_IDS}


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("difficulty", DIFFICULTIES)
def test_perfect_answer_is_all_correct(seed, difficulty):
    q = SynthesisAlgorithmQuestion(seed=seed, difficulty=difficulty)
    results = q.evaluate(_perfect_payload(q))
    for field_id, _s, _t in q.STEP_IDS:
        assert results[field_id]["correct"] is True, field_id


@pytest.mark.parametrize("seed", SEEDS)
def test_empty_answer_is_all_wrong(seed):
    q = SynthesisAlgorithmQuestion(seed=seed, difficulty="medium")
    results = q.evaluate({})
    for field_id, _s, _t in q.STEP_IDS:
        assert results[field_id]["correct"] is False
        assert isinstance(results[field_id]["expected"], str) and results[field_id]["expected"]


@pytest.mark.parametrize("seed", SEEDS)
def test_each_step_graded_independently_against_canonical(seed):
    # Carry-forward semantics: a correct step is correct even if every other
    # step is garbage (each step is graded against the canonical chain).
    q = SynthesisAlgorithmQuestion(seed=seed, difficulty="medium")
    for field_id, _s, _t in q.STEP_IDS:
        payload = {fid: "ZZ->ZZ" for fid, _s2, _t2 in q.STEP_IDS}
        payload[field_id] = q._expected_text(field_id)
        results = q.evaluate(payload)
        assert results[field_id]["correct"] is True, field_id


def test_step_key_accepts_any_candidate_key_when_addition_needed():
    # Construct an instance where no schema contains a key, so a key relation
    # must be added. F = {A->B, B->A, A->C}: keys {A},{B}; schemas {A,B},{A,C};
    # neither contains a full key on its own? {A,B} contains key {A} and {B}.
    # Use a cleaner case: A->C, B->C over R(A,B,C): only key is {A,B} (not contained).
    q = _with_fds(["A", "B", "C"], fdset(("A", "C"), ("B", "C")))
    assert q.key_contained is False
    assert q.chosen_key == frozenset({"A", "B"})
    # schemas {A,C},{B,C}; adding key {A,B}
    base = q._fmt_schemas(q.schemas)
    res = q.evaluate({"step_key": base + "; {A,B}"})
    assert res["step_key"]["correct"] is True
    # forgetting the key relation is wrong
    res2 = q.evaluate({"step_key": base})
    assert res2["step_key"]["correct"] is False


def test_evaluate_returns_solution_payloads():
    q = SynthesisAlgorithmQuestion(seed=7, difficulty="easy")
    results = q.evaluate({})
    for _f, sol_id, _t in q.STEP_IDS:
        assert results[sol_id]["correct"] is True
        assert isinstance(results[sol_id]["expected"], str) and results[sol_id]["expected"]
    assert "Synthesealgorithmus" in results["solution"]["expected"]


# --------------------------------------------------------------------------- #
# Parsing
# --------------------------------------------------------------------------- #
def test_fd_parser_variants():
    q = _q()
    canonical = fdset(("AB", "C"))
    for text in ("AB->C", "A,B -> C", "BA->C", "AB→C", "AB=>C", "  AB -> C  "):
        assert q._parse_fds(text) == canonical, text

    multi = fdset(("A", "B"), ("B", "C"))
    assert q._parse_fds("A->B; B->C") == multi
    assert q._parse_fds("A->B\nB->C") == multi

    # empty right-hand side variants
    assert q._parse_fds("AB->") == fdset(("AB", ""))
    assert q._parse_fds("AB->∅") == fdset(("AB", ""))
    assert q._parse_fds("AB->\\empty") == fdset(("AB", ""))
    assert q._parse_fds("AB->\\leer") == fdset(("AB", ""))

    assert q._parse_fds("") == set()
    assert q._parse_fds("garbage") is None  # no arrow
    assert q._parse_fds("1->2") is None  # unknown attributes


def test_relation_set_parser_variants():
    q = _q()
    expected = {frozenset({"A", "B"}), frozenset({"C", "D"})}
    for text in ("{A,B}; {C,D}", "R1(A,B); R2(C,D)", "AB; CD", "{A, B}\n{C, D}"):
        assert q._parse_relation_set(text) == expected, text

    assert q._parse_relation_set("") == set()
    assert q._parse_relation_set("{A,9}") is None


# --------------------------------------------------------------------------- #
# Configuration fallbacks
# --------------------------------------------------------------------------- #
def test_invalid_difficulty_and_mode_fall_back():
    q = SynthesisAlgorithmQuestion(seed=1, difficulty="impossible", mode="weird")
    assert q.difficulty == "easy"
    assert q.mode == "steps"


# --------------------------------------------------------------------------- #
# Multiple valid solution paths (non-unique canonical cover)
#
# F = AC->BD; AD->B; B->D  has two valid right reductions of AC->BD:
#   AC->D (sorted default)  and  AC->B.
# The left reduction here is unique (nothing is reducible).
# --------------------------------------------------------------------------- #
NONUNIQUE_ATTRS = ["A", "B", "C", "D"]
NONUNIQUE_FDS = fdset(("AC", "BD"), ("AD", "B"), ("B", "D"))


def _nonunique_q():
    return _with_fds(NONUNIQUE_ATTRS, NONUNIQUE_FDS)


def test_all_right_reductions_enumerated():
    q = _nonunique_q()
    rights = q._all_right_reductions(q._norm_fds(q.f1))
    assert q._norm_fds(fdset(("AC", "D"), ("AD", "B"), ("B", "D"))) in rights
    assert q._norm_fds(fdset(("AC", "B"), ("AD", "B"), ("B", "D"))) in rights
    assert len(rights) == 2


def test_left_reduction_here_is_unique():
    q = _nonunique_q()
    assert len(q._all_left_reductions(q._norm_fds(q.f0))) == 1


def test_both_right_reduction_branches_accepted():
    q = _nonunique_q()
    assert q.evaluate({"step_right": "AC->D; AD->B; B->D"})["step_right"]["correct"] is True
    assert q.evaluate({"step_right": "AC->B; AD->B; B->D"})["step_right"]["correct"] is True


def test_full_alternative_path_all_correct():
    # A complete valid solution through the (non-default) AC->B branch.
    q = _nonunique_q()
    payload = {
        "step_left": "AC->BD; AD->B; B->D",     # unique: nothing reducible
        "step_right": "AC->B; AD->B; B->D",      # alternative branch
        "step_empty": "AC->B; AD->B; B->D",
        "step_union": "AC->B; AD->B; B->D",
        "step_schemas": "{A,B,C}; {A,B,D}; {B,D}",
        "step_key": "{A,B,C}; {A,B,D}; {B,D}",   # key {A,C} already in {A,B,C}
        "step_final": "{A,B,C}; {A,B,D}",
    }
    res = q.evaluate(payload)
    for field_id, _s, _t in q.STEP_IDS:
        assert res[field_id]["correct"] is True, field_id


def test_downstream_must_follow_the_selected_branch():
    # Choose the AC->B branch at step_right, then submit the OTHER branch's
    # schemas (those of AC->D): the chosen branch fixes the continuation, so the
    # inconsistent schemas must be rejected.
    q = _nonunique_q()
    res = q.evaluate({
        "step_right": "AC->B; AD->B; B->D",
        "step_schemas": "{A,C,D}; {A,B,D}; {B,D}",
    })
    assert res["step_right"]["correct"] is True
    assert res["step_schemas"]["correct"] is False


def test_solution_lists_all_options_and_highlights_submitted():
    q = _nonunique_q()
    sol = q.evaluate({"step_right": "AC->B; AD->B; B->D"})["sol_right"]["expected"]
    assert "AC → B" in sol and "AC → D" in sol      # both valid results listed
    assert "Mehrere Ergebnisse" in sol              # explanation is present
    highlighted = [ln for ln in sol.splitlines() if "✅" in ln]
    assert len(highlighted) == 1 and "AC → B" in highlighted[0]


def test_default_branch_highlighted_when_answer_missing_or_wrong():
    q = _nonunique_q()
    sol = q.evaluate({"step_right": "garbage"})["sol_right"]["expected"]
    highlighted = [ln for ln in sol.splitlines() if "✅" in ln]
    assert len(highlighted) == 1 and "AC → D" in highlighted[0]  # sorted-order default


def test_unique_step_has_no_multiple_solutions_note():
    q = _nonunique_q()
    sol_left = q.evaluate({})["sol_left"]["expected"]
    # unique step -> just the bold result, no list and no multi-solutions note
    assert "Mehrere Ergebnisse" not in sol_left
    assert "Gültige Ergebnisse" not in sol_left
    assert "AC → BD" in sol_left

import itertools

import pytest

from app.question_types.decomposition_fd import DecompositionFDQuestion


DIFFICULTIES = ["easy", "medium", "hard"]
SEEDS = [1, 2, 3, 4, 7, 42, 123, 999, 2024, 31337]


# --------------------------------------------------------------------------- #
# Independent reference implementations (intentionally written differently from
# the production code so they cross-check it rather than mirror it).
# --------------------------------------------------------------------------- #
def _closure(attrs, fds):
    closure = set(attrs)
    changed = True
    while changed:
        changed = False
        for lhs, rhs in fds:
            if set(lhs) <= closure and not set(rhs) <= closure:
                closure |= set(rhs)
                changed = True
    return closure


def _lossless_binary_reference(fragments, fds):
    """For a binary decomposition, lossless iff the shared attributes
    functionally determine one of the two fragments."""
    r1, r2 = set(fragments[0]), set(fragments[1])
    overlap = r1 & r2
    if not overlap:
        return False
    clos = _closure(overlap, fds)
    return r1 <= clos or r2 <= clos


def _project_fds(frag, fds):
    """Explicit projection of F onto a fragment: every non-trivial X -> A with
    X subset of frag and A in (X)+ ∩ frag. (Definition-level, brute force.)"""
    frag = list(frag)
    proj = []
    for size in range(1, len(frag) + 1):
        for comb in itertools.combinations(frag, size):
            x = set(comb)
            clos = _closure(x, fds) & set(frag)
            for a in clos - x:
                proj.append((frozenset(x), frozenset({a})))
    return proj


def _preserving_reference(fragments, fds):
    """Dependency preservation via G = union of projected FDs, then check that
    every original FD is implied by G (i.e. G+ covers F)."""
    g = []
    for frag in fragments:
        g.extend(_project_fds(frag, fds))
    return all(set(rhs) <= _closure(lhs, g) for lhs, rhs in fds)


# --------------------------------------------------------------------------- #
# Tests
# --------------------------------------------------------------------------- #
def test_deterministic_for_fixed_seed():
    a = DecompositionFDQuestion(seed=42, difficulty="medium")
    b = DecompositionFDQuestion(seed=42, difficulty="medium")

    assert a.attributes == b.attributes
    assert a.fds == b.fds
    assert a.fragments == b.fragments
    assert (a.lossless, a.preserving) == (b.lossless, b.preserving)
    assert a.evaluate({}) == b.evaluate({})


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("difficulty", DIFFICULTIES)
def test_decomposition_structure(seed, difficulty):
    q = DecompositionFDQuestion(seed=seed, difficulty=difficulty)
    all_attrs = set(q.attributes)
    r1, r2 = set(q.fragments[0]), set(q.fragments[1])

    assert len(q.fragments) == 2
    assert r1 | r2 == all_attrs          # union covers R
    assert r1 & r2                        # non-empty overlap
    assert r1 < all_attrs and r2 < all_attrs  # both proper subsets
    assert len(q.fds) == q.n_fd
    assert isinstance(q.lossless, bool) and isinstance(q.preserving, bool)


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("difficulty", DIFFICULTIES)
def test_lossless_matches_binary_criterion(seed, difficulty):
    q = DecompositionFDQuestion(seed=seed, difficulty=difficulty)
    assert q.lossless == _lossless_binary_reference(q.fragments, q.fds)


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("difficulty", DIFFICULTIES)
def test_preserving_matches_projection_reference(seed, difficulty):
    q = DecompositionFDQuestion(seed=seed, difficulty=difficulty)
    assert q.preserving == _preserving_reference(q.fragments, q.fds)


def test_known_lossless_not_preserving():
    # R(A,B,C), F = {AB->C, C->B}, decomposition {A,C},{B,C}.
    # Classic example: lossless join but NOT dependency preserving.
    q = DecompositionFDQuestion(seed=1, difficulty="easy")
    fds = [(frozenset("AB"), frozenset("C")), (frozenset("C"), frozenset("B"))]
    frags = [frozenset("AC"), frozenset("BC")]
    q.attributes = ["A", "B", "C"]
    assert q._lossless(frags, fds) is True
    assert q._preserving(frags, fds) is False


def test_known_lossless_and_preserving():
    # R(A,B,C), F = {A->B, B->C}, decomposition {A,B},{B,C}.
    q = DecompositionFDQuestion(seed=1, difficulty="easy")
    fds = [(frozenset("A"), frozenset("B")), (frozenset("B"), frozenset("C"))]
    frags = [frozenset("AB"), frozenset("BC")]
    q.attributes = ["A", "B", "C"]
    assert q._lossless(frags, fds) is True
    assert q._preserving(frags, fds) is True


def test_known_lossy_but_preserving():
    # R(A,B,C), F = {A->B}, decomposition {A,B},{B,C}.
    # Overlap {B} determines neither fragment -> lossy; A->B lives in {A,B} -> preserved.
    q = DecompositionFDQuestion(seed=1, difficulty="easy")
    fds = [(frozenset("A"), frozenset("B"))]
    frags = [frozenset("AB"), frozenset("BC")]
    q.attributes = ["A", "B", "C"]
    assert q._lossless(frags, fds) is False
    assert q._preserving(frags, fds) is True


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("difficulty", DIFFICULTIES)
def test_layout_field_ids(seed, difficulty):
    q = DecompositionFDQuestion(seed=seed, difficulty=difficulty)
    layout = q.generate()

    assert "view1" in layout
    mc_ids = {el["id"] for el in layout["view1"] if el.get("type") == "multiple_choice"}
    assert mc_ids == {"lossless_decision", "preserving_decision"}
    for el in layout["view1"]:
        if el.get("type") == "multiple_choice":
            assert el["options"] == ["Ja", "Nein"]


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("difficulty", DIFFICULTIES)
def test_evaluate_includes_solution(seed, difficulty):
    q = DecompositionFDQuestion(seed=seed, difficulty=difficulty)
    results = q.evaluate({})
    sol = results["solution"]["expected"]
    assert "Verlustfreiheit" in sol
    assert "Abhängigkeitsbewahrung" in sol
    # The worked solution's bolded conclusions must agree with the verdicts.
    assert ("**verlustfrei**" in sol) == q.lossless
    assert ("**verlustbehaftet**" in sol) == (not q.lossless)
    assert ("**nicht abhängigkeitsbewahrend**" in sol) == (not q.preserving)
    assert ("**abhängigkeitsbewahrend**" in sol) == q.preserving
    # One bullet per FD in the preservation breakdown.
    assert sol.count("\n- ") == len(q.fds)


def test_solution_explains_bridge_case():
    # The flagged example: R(A,B,C,D), F={A->C, C->D, D->A}, R1{A,B,C} / R2{C,D}.
    # D->A is preserved indirectly via D->C (on R2) and C->A (on R1).
    q = DecompositionFDQuestion(seed=1, difficulty="easy")
    q.attributes = ["A", "B", "C", "D"]
    q.fds = [
        (frozenset("A"), frozenset("C")),
        (frozenset("C"), frozenset("D")),
        (frozenset("D"), frozenset("A")),
    ]
    q.fragments = [frozenset("ABC"), frozenset("CD")]
    q.lossless = q._lossless(q.fragments, q.fds)
    q.preserving = q._preserving(q.fragments, q.fds)

    assert q.lossless is True
    assert q.preserving is True

    lines = q._explain_preservation()
    da_line = next(line for line in lines if line.startswith("- **D → A**"))
    assert "✓" in da_line          # preserved
    assert "R2" in da_line and "R1" in da_line  # rebuilt across both fragments

    sol = q._build_solution()
    assert "abhängigkeitsbewahrend" in sol
    assert "nicht abhängigkeitsbewahrend" not in sol


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("difficulty", DIFFICULTIES)
def test_perfect_answer_is_all_correct(seed, difficulty):
    q = DecompositionFDQuestion(seed=seed, difficulty=difficulty)
    payload = {
        "lossless_decision": "Ja" if q.lossless else "Nein",
        "preserving_decision": "Ja" if q.preserving else "Nein",
    }
    results = q.evaluate(payload)
    assert all(r["correct"] for r in results.values())
    assert results["lossless_decision"]["expected"] == ("Ja" if q.lossless else "Nein")
    assert results["preserving_decision"]["expected"] == ("Ja" if q.preserving else "Nein")


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("difficulty", DIFFICULTIES)
def test_empty_answer_is_incorrect(seed, difficulty):
    q = DecompositionFDQuestion(seed=seed, difficulty=difficulty)
    results = q.evaluate({})
    for field in ("lossless_decision", "preserving_decision"):
        assert results[field]["correct"] is False
        assert results[field]["expected"] in ("Ja", "Nein")


def test_wrong_answer_is_rejected():
    q = DecompositionFDQuestion(seed=42, difficulty="medium")
    flipped = {
        "lossless_decision": "Nein" if q.lossless else "Ja",
        "preserving_decision": "Nein" if q.preserving else "Ja",
    }
    results = q.evaluate(flipped)
    assert results["lossless_decision"]["correct"] is False
    assert results["preserving_decision"]["correct"] is False


def test_invalid_difficulty_falls_back_to_easy():
    q = DecompositionFDQuestion(seed=1, difficulty="impossible")
    assert q.difficulty == "easy"

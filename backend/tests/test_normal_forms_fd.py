import itertools

import pytest

from app.question_types.normal_forms_fd import (
    NormalFormsFDQuestion,
    NF_OPTIONS,
    NF_RANK,
    NONE_NF,
)


DIFFICULTIES = ["easy", "medium", "hard"]
SEEDS = [1, 2, 3, 4, 5, 7, 42, 123, 999, 2024, 31337]


# --------------------------------------------------------------------------- #
# Independent reference implementations.
#
# The FD-based levels (2NF/3NF) are verified straight from the *full* textbook
# definition: they quantify over every attribute subset (i.e. over F+), not just
# the given FDs. The production code uses the standard shortcut of testing only
# the given FDs (exact for 3NF) and only the maximal proper subkeys (exact for
# 2NF); cross-checking against the brute-force definition proves that correct.
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


def _powerset_nonempty(attrs):
    attrs = sorted(attrs)
    for size in range(1, len(attrs) + 1):
        for comb in itertools.combinations(attrs, size):
            yield set(comb)


def _ref_candidate_keys(attrs, fds):
    """All superkeys, then keep the minimal ones (different approach from prod)."""
    attrs = set(attrs)
    superkeys = [set(x) for x in _powerset_nonempty(attrs) if _closure(x, fds) == attrs]
    keys = []
    for sk in superkeys:
        if not any(other < sk for other in superkeys):
            keys.append(frozenset(sk))
    return keys


def _ref_prime(keys):
    prime = set()
    for k in keys:
        prime |= set(k)
    return prime


def _ref_is_3nf(attrs, fds, prime):
    """3NF iff for every X: X is a superkey, or everything X newly determines is prime."""
    attrs = set(attrs)
    for x in _powerset_nonempty(attrs):
        clos = _closure(x, fds)
        if clos == attrs:
            continue
        if not (clos - x) <= prime:
            return False
    return True


def _ref_is_2nf(attrs, fds, keys, prime):
    """2NF iff no *proper* subset of any candidate key determines a non-prime attribute."""
    nonprime = set(attrs) - prime
    for k in keys:
        k = set(k)
        for size in range(1, len(k)):  # all proper, non-empty subsets
            for comb in itertools.combinations(sorted(k), size):
                if _closure(set(comb), fds) & nonprime:
                    return False
    return True


def _ref_fd_based_nf(attrs, fds):
    """Highest FD-based normal form assuming atomicity (1NF/2NF/3NF)."""
    keys = _ref_candidate_keys(attrs, fds)
    prime = _ref_prime(keys)
    if _ref_is_3nf(attrs, fds, prime):
        return "3NF"
    if _ref_is_2nf(attrs, fds, keys, prime):
        return "2NF"
    return "1NF"


def _ref_expected(q):
    """The expected answer: Keine NF when non-atomic, else the FD-based level."""
    if not q.atomic:
        return NONE_NF
    return _ref_fd_based_nf(q.attributes, q.fds)


def _key_sets(keys):
    return {frozenset(k) for k in keys}


def _instance_violates_fds(instance, fds):
    """True if any FD is violated by a (scalar-valued) instance."""
    for lhs, rhs in fds:
        for s in instance:
            for t in instance:
                if all(s[a] == t[a] for a in lhs) and any(s[b] != t[b] for b in rhs):
                    return True
    return False


# --------------------------------------------------------------------------- #
# Determinism & structure
# --------------------------------------------------------------------------- #
def test_deterministic_for_fixed_seed():
    a = NormalFormsFDQuestion(seed=42, difficulty="medium")
    b = NormalFormsFDQuestion(seed=42, difficulty="medium")

    assert a.attributes == b.attributes
    assert a.fds == b.fds
    assert a.atomic == b.atomic
    assert a.instance == b.instance
    assert a.highest_nf == b.highest_nf
    assert _key_sets(a.candidate_keys) == _key_sets(b.candidate_keys)
    assert a.evaluate({}) == b.evaluate({})


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("difficulty", DIFFICULTIES)
def test_structure(seed, difficulty):
    q = NormalFormsFDQuestion(seed=seed, difficulty=difficulty)
    all_attrs = set(q.attributes)

    assert len(q.attributes) == q.n_attr
    assert len(q.fds) == q.n_fd
    assert q.candidate_keys, "every relation has at least one candidate key"
    for k in q.candidate_keys:
        assert q._closure(set(k), q.fds) == all_attrs
        for x in k:
            assert q._closure(set(k) - {x}, q.fds) != all_attrs
    for lhs, rhs in q.fds:
        assert not rhs <= lhs  # FDs are non-trivial
    assert q.highest_nf in NF_RANK
    assert all_attrs - q.prime_attributes  # never degenerate
    assert len(q.instance) >= 1


# --------------------------------------------------------------------------- #
# Atomicity / sample instance
# --------------------------------------------------------------------------- #
def test_non_atomic_instances_are_keine_nf():
    found = False
    for s in range(48):
        q = NormalFormsFDQuestion(seed=s, difficulty="medium")
        if not q.atomic:
            found = True
            assert q.highest_nf == NONE_NF
            assert q.nonatomic_cells, "non-atomic instance must record offending cells"
            assert any(isinstance(v, list) for t in q.instance for v in t.values())
    assert found, "expected some non-atomic instances across seeds"


def test_atomic_instances_are_scalar_and_fd_consistent():
    found = False
    for s in range(48):
        q = NormalFormsFDQuestion(seed=s, difficulty="medium")
        if q.atomic:
            found = True
            assert q.highest_nf in ("1NF", "2NF", "3NF")
            assert not q.nonatomic_cells
            assert all(not isinstance(v, list) for t in q.instance for v in t.values())
            assert not _instance_violates_fds(q.instance, q.fds)
    assert found, "expected some atomic instances across seeds"


# --------------------------------------------------------------------------- #
# Correctness: production logic must match the brute-force definition
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("difficulty", DIFFICULTIES)
def test_candidate_keys_match_reference(seed, difficulty):
    q = NormalFormsFDQuestion(seed=seed, difficulty=difficulty)
    assert _key_sets(q.candidate_keys) == _key_sets(_ref_candidate_keys(q.attributes, q.fds))


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("difficulty", DIFFICULTIES)
def test_highest_nf_matches_reference(seed, difficulty):
    q = NormalFormsFDQuestion(seed=seed, difficulty=difficulty)
    assert q.highest_nf == _ref_expected(q)


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("difficulty", DIFFICULTIES)
def test_individual_levels_match_reference(seed, difficulty):
    q = NormalFormsFDQuestion(seed=seed, difficulty=difficulty)
    attrs = set(q.attributes)
    keys = q.candidate_keys
    prime = q.prime_attributes

    assert q._is_3nf(attrs, q.fds, prime) == _ref_is_3nf(attrs, q.fds, prime)
    assert q._is_2nf(attrs, q.fds, keys, prime) == _ref_is_2nf(attrs, q.fds, keys, prime)


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("difficulty", DIFFICULTIES)
def test_hierarchy_is_monotone(seed, difficulty):
    """3NF => 2NF must always hold for the computed verdicts."""
    q = NormalFormsFDQuestion(seed=seed, difficulty=difficulty)
    attrs = set(q.attributes)
    is_3nf = q._is_3nf(attrs, q.fds, q.prime_attributes)
    is_2nf = q._is_2nf(attrs, q.fds, q.candidate_keys, q.prime_attributes)
    if is_3nf:
        assert is_2nf


# --------------------------------------------------------------------------- #
# Known textbook instances (FD-based level, ignoring atomicity)
# --------------------------------------------------------------------------- #
def _q():
    return NormalFormsFDQuestion(seed=1, difficulty="easy")


def test_known_only_1nf():
    # R(A,B,C), F = {A->C}. Only key {A,B}; {A} -> C is a partial dependency.
    fds = [(frozenset("A"), frozenset("C"))]
    assert _q()._highest_nf(set("ABC"), fds) == "1NF"


def test_known_partial_dependency_despite_given_full_fd():
    # R(A,B,C), F = {C->B, A->B, AC->B}. Only candidate key {A,C}; B is non-prime.
    # Even though AC->B is given, B already depends on the proper subset {A}
    # (A->B), so B is only *partially* dependent on {A,C} -> 2NF is violated ->
    # highest NF is 1NF. (Guards against reading "AC->B exists" as "full".)
    fds = [(frozenset("C"), frozenset("B")),
           (frozenset("A"), frozenset("B")),
           (frozenset("AC"), frozenset("B"))]
    q = _q()
    assert _key_sets(q._candidate_keys(set("ABC"), fds)) == {frozenset("AC")}
    assert q._highest_nf(set("ABC"), fds) == "1NF"


def test_known_2nf_not_3nf():
    # R(A,B,C), F = {A->B, B->C}. Key {A}; B->C is transitive.
    fds = [(frozenset("A"), frozenset("B")), (frozenset("B"), frozenset("C"))]
    assert _q()._highest_nf(set("ABC"), fds) == "2NF"


def test_known_3nf_prime_rhs():
    # R(A,B,C), F = {AB->C, C->B}. Keys {A,B},{A,C}; C->B has prime RHS -> 3NF.
    fds = [(frozenset("AB"), frozenset("C")), (frozenset("C"), frozenset("B"))]
    assert _q()._highest_nf(set("ABC"), fds) == "3NF"


def test_known_3nf_all_superkeys():
    # R(A,B,C), F = {A->B, A->C}. Key {A}; every FD has a superkey LHS -> 3NF.
    fds = [(frozenset("A"), frozenset("B")), (frozenset("A"), frozenset("C"))]
    assert _q()._highest_nf(set("ABC"), fds) == "3NF"


# --------------------------------------------------------------------------- #
# Layout & evaluation
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("difficulty", DIFFICULTIES)
def test_layout_field_ids(seed, difficulty):
    q = NormalFormsFDQuestion(seed=seed, difficulty=difficulty)
    layout = q.generate()

    assert "view1" in layout
    mc = next(el for el in layout["view1"] if el.get("type") == "multiple_choice")
    assert mc["id"] == "highest_nf"
    assert mc["options"] == [NONE_NF, "1NF", "2NF", "3NF"]

    # A sample instance table is always present so atomicity is checkable.
    table = next(el for el in layout["view1"] if el.get("type") == "table")
    assert table["columns"] == q.attributes
    assert len(table["rows"]) == len(q.instance)

    assert any(el.get("type") == "solution_box" and el.get("id") == "solution"
               for el in layout["view1"])


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("difficulty", DIFFICULTIES)
def test_evaluate_includes_consistent_solution(seed, difficulty):
    q = NormalFormsFDQuestion(seed=seed, difficulty=difficulty)
    results = q.evaluate({})

    sol = results["solution"]["expected"]
    assert results["solution"]["correct"] is True
    assert f"Die höchste erfüllte Normalform ist **{q.highest_nf}**." in sol

    if q.highest_nf == NONE_NF:
        assert "nicht in 1. Normalform" in sol
    else:
        for heading in ("1. Normalform", "2. Normalform", "3. Normalform"):
            assert heading in sol
        assert "**1NF erfüllt**" in sol
        if q.highest_nf == "1NF":
            assert "**2NF verletzt.**" in sol
        if q.highest_nf == "2NF":
            assert "**2NF erfüllt.**" in sol and "**3NF verletzt.**" in sol
        if q.highest_nf == "3NF":
            assert "**3NF erfüllt.**" in sol


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("difficulty", DIFFICULTIES)
def test_perfect_answer_is_all_correct(seed, difficulty):
    q = NormalFormsFDQuestion(seed=seed, difficulty=difficulty)
    results = q.evaluate({"highest_nf": q.highest_nf})
    assert results["highest_nf"]["correct"] is True
    assert results["highest_nf"]["expected"] == q.highest_nf
    assert all(r["correct"] for r in results.values())


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("difficulty", DIFFICULTIES)
def test_empty_answer_is_incorrect(seed, difficulty):
    q = NormalFormsFDQuestion(seed=seed, difficulty=difficulty)
    results = q.evaluate({})
    assert results["highest_nf"]["correct"] is False
    assert results["highest_nf"]["expected"] in NF_RANK


def test_wrong_answer_is_rejected():
    q = NormalFormsFDQuestion(seed=42, difficulty="medium")
    wrong = next(nf for nf in NF_OPTIONS if nf != q.highest_nf)
    results = q.evaluate({"highest_nf": wrong})
    assert results["highest_nf"]["correct"] is False


def test_invalid_difficulty_falls_back_to_easy():
    q = NormalFormsFDQuestion(seed=1, difficulty="impossible")
    assert q.difficulty == "easy"


def test_no_bcnf_anywhere():
    """BCNF was removed: it must not appear as an option, answer or in solutions."""
    assert "BCNF" not in NF_OPTIONS
    for s in range(20):
        q = NormalFormsFDQuestion(seed=s, difficulty="hard")
        assert q.highest_nf != "BCNF"
        assert "BCNF" not in q.evaluate({})["solution"]["expected"]
        assert not hasattr(q, "_is_bcnf")


# --------------------------------------------------------------------------- #
# Distribution: across seeds the targeting should surface every answer
# --------------------------------------------------------------------------- #
def test_distribution_covers_all_levels():
    seen = {NormalFormsFDQuestion(seed=s, difficulty="medium").highest_nf
            for s in range(60)}
    assert seen == {NONE_NF, "1NF", "2NF", "3NF"}, f"got {seen}"

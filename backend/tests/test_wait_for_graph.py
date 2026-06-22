import json

import pytest

from app.question_types.wait_for_graph import (
    WaitForGraphQuestion,
    ROLLBACK_NONE,
    TARGET_DEADLOCK,
)


DIFFICULTIES = ["easy", "medium", "hard"]
SEEDS = [1, 2, 3, 4, 7, 42, 123, 999, 2024, 31337]


# --------------------------------------------------------------------------- #
# Independent reference implementation (intentionally written differently from
# production so it cross-checks rather than mirrors).
# --------------------------------------------------------------------------- #
def _ref_edges(held, requests, txs):
    """Re-derive wait-for edges, indexed element -> holders (production indexes
    request -> all transactions)."""
    holders = {}  # elem -> list of (tx, held_mode)
    for t in txs:
        for e, mode in held[t].items():
            holders.setdefault(e, []).append((t, mode))

    edges = set()
    for ti in txs:
        for mode, e in requests.get(ti, []):
            for tj, hm in holders.get(e, []):
                if tj == ti:
                    continue
                if mode == "X" or hm == "x":  # X req conflicts with anything; S req with x
                    edges.add((ti, tj))
    return edges


def _ref_has_cycle(edges, txs):
    """Cycle detection via Kahn's algorithm (production uses DFS colouring)."""
    indeg = {t: 0 for t in txs}
    adj = {t: [] for t in txs}
    for a, b in edges:
        if a in adj and b in indeg:
            adj[a].append(b)
            indeg[b] += 1
    queue = [t for t in txs if indeg[t] == 0]
    removed = 0
    while queue:
        node = queue.pop()
        removed += 1
        for m in adj[node]:
            indeg[m] -= 1
            if indeg[m] == 0:
                queue.append(m)
    return removed != len(txs)


def _ref_valid_rollback(edges, txs):
    if not _ref_has_cycle(edges, txs):
        return set()
    out = set()
    for v in txs:
        sub = {(a, b) for (a, b) in edges if a != v and b != v}
        rest = [t for t in txs if t != v]
        if not _ref_has_cycle(sub, rest):
            out.add(v)
    return out


def _perfect_payload(q):
    return {
        "wait_for": json.dumps(q._edges_as_pairs()),
        "deadlock_decision": "Ja" if q.deadlock else "Nein",
        "rollback_choice": (sorted(q.valid_rollback)[0] if q.deadlock else ROLLBACK_NONE),
    }


def _find(predicate, difficulty="medium", max_seed=300):
    for s in range(1, max_seed + 1):
        q = WaitForGraphQuestion(seed=s, difficulty=difficulty)
        if predicate(q):
            return q
    return None


# --------------------------------------------------------------------------- #
# Determinism
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("difficulty", DIFFICULTIES)
def test_deterministic_for_fixed_seed(difficulty):
    a = WaitForGraphQuestion(seed=42, difficulty=difficulty)
    b = WaitForGraphQuestion(seed=42, difficulty=difficulty)
    assert a.transactions == b.transactions
    assert a.elements == b.elements
    assert a.held == b.held
    assert a.requests == b.requests
    assert a.edges == b.edges
    assert a.deadlock == b.deadlock
    assert a.valid_rollback == b.valid_rollback
    assert a.generate() == b.generate()
    assert a.evaluate({}) == b.evaluate({})


# --------------------------------------------------------------------------- #
# Correctness vs. the independent reference
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("difficulty", DIFFICULTIES)
def test_edges_match_reference(seed, difficulty):
    q = WaitForGraphQuestion(seed=seed, difficulty=difficulty)
    assert set(q.edges) == _ref_edges(q.held, q.requests, q.transactions)


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("difficulty", DIFFICULTIES)
def test_verdict_and_rollback_match_reference(seed, difficulty):
    q = WaitForGraphQuestion(seed=seed, difficulty=difficulty)
    assert q.deadlock == _ref_has_cycle(q.edges, q.transactions)
    assert q.valid_rollback == _ref_valid_rollback(q.edges, q.transactions)


# --------------------------------------------------------------------------- #
# Generation invariants
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("difficulty", DIFFICULTIES)
def test_held_lock_state_is_consistent(seed, difficulty):
    q = WaitForGraphQuestion(seed=seed, difficulty=difficulty)
    for e in q.elements:
        holders = {t: q.held[t][e] for t in q.transactions if e in q.held[t]}
        modes = set(holders.values())
        # either no element-X among multiple holders: X => exactly one holder, no S.
        if "x" in modes:
            assert len(holders) == 1, (seed, difficulty, e, holders)
    # requests are a list; each is on an element the requester does not hold,
    # and no element is requested twice by the same transaction.
    for t in q.transactions:
        assert isinstance(q.requests[t], list)
        seen = set()
        for mode, e in q.requests[t]:
            assert mode in ("S", "X")
            assert e not in q.held[t]
            assert e not in seen
            seen.add(e)


def test_multiple_requests_occur_across_seeds():
    # With MULTI_REQUEST_PROB > 0, some transactions ask for more than one lock.
    found = False
    for s in range(1, 400):
        q = WaitForGraphQuestion(seed=s, difficulty="hard")
        if any(len(q.requests[t]) >= 2 for t in q.transactions):
            found = True
            break
    assert found, "expected at least one instance with a multi-lock request"


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("difficulty", DIFFICULTIES)
def test_deadlock_instances_are_resolvable(seed, difficulty):
    q = WaitForGraphQuestion(seed=seed, difficulty=difficulty)
    if q.deadlock:
        assert q.valid_rollback, "deadlock instance must be resolvable by one rollback"


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("difficulty", DIFFICULTIES)
def test_acyclic_instances_are_nontrivial(seed, difficulty):
    q = WaitForGraphQuestion(seed=seed, difficulty=difficulty)
    if not q.deadlock:
        assert len(q.edges) >= q.min_edges


def test_distribution_covers_deadlock_and_acyclic():
    outcomes = {WaitForGraphQuestion(seed=s, difficulty="medium").deadlock for s in SEEDS}
    assert True in outcomes and False in outcomes


def test_target_rotation_is_seed_parity():
    # The steering target is purely a function of seed parity.
    assert TARGET_DEADLOCK[0] != TARGET_DEADLOCK[1]


# --------------------------------------------------------------------------- #
# The exam-PDF fallback instance
# --------------------------------------------------------------------------- #
def test_pdf_fallback_reproduces_exam_instance():
    q = WaitForGraphQuestion(seed=2, difficulty="hard")
    held, requests = q._fallback_deadlock()
    q.held, q.requests = held, requests
    q.edges = q._derive_edges(held, requests)
    q.cycles = q._find_cycles(q.edges)
    q.deadlock = bool(q.cycles)
    q.valid_rollback = q._valid_rollbacks(q.edges)

    expected = {
        ("T1", "T3"), ("T1", "T4"),
        ("T2", "T5"),
        ("T3", "T1"), ("T3", "T2"),
        ("T4", "T1"),
        ("T5", "T4"),
    }
    assert q.edges == expected
    assert q.deadlock is True
    assert "T1" in q.valid_rollback  # T1 lies on every cycle


# --------------------------------------------------------------------------- #
# Layout
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("difficulty", DIFFICULTIES)
def test_layout_field_ids_and_options(seed, difficulty):
    q = WaitForGraphQuestion(seed=seed, difficulty=difficulty)
    layout = q.generate()
    assert "view1" in layout

    by_type = {}
    for el in layout["view1"]:
        by_type.setdefault(el.get("type"), []).append(el)

    builder = by_type["wait_for_graph_builder"][0]
    assert builder["id"] == "wait_for"
    assert builder["transactions"] == q.transactions

    mc = by_type["multiple_choice"][0]
    assert mc["id"] == "deadlock_decision"
    assert mc["options"] == ["Ja", "Nein"]

    dd = by_type["dropdown_input"][0]
    assert dd["id"] == "rollback_choice"
    assert dd["options"] == q.transactions + [ROLLBACK_NONE]

    assert by_type["solution_box"][0]["id"] == "solution"


@pytest.mark.parametrize("seed", SEEDS)
def test_generate_does_not_leak_answers(seed):
    q = WaitForGraphQuestion(seed=seed, difficulty="hard")
    layout = q.generate()
    blob = json.dumps(layout, ensure_ascii=False)

    # solution markdown markers / rollback text must not be in the payload
    assert "#### Verklemmung" not in blob
    assert "#### Wartegraph ableiten" not in blob
    assert "Konfliktregel" not in blob
    assert "eine genügt" not in blob

    for el in layout["view1"]:
        if el.get("type") == "solution_box":
            assert "expected" not in el


# --------------------------------------------------------------------------- #
# Evaluation
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("difficulty", DIFFICULTIES)
def test_perfect_answer_is_all_correct(seed, difficulty):
    q = WaitForGraphQuestion(seed=seed, difficulty=difficulty)
    results = q.evaluate(_perfect_payload(q))
    assert all(r["correct"] for r in results.values())


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("difficulty", DIFFICULTIES)
def test_empty_answer_is_incorrect(seed, difficulty):
    q = WaitForGraphQuestion(seed=seed, difficulty=difficulty)
    results = q.evaluate({})
    assert results["wait_for"]["correct"] is False
    assert results["deadlock_decision"]["correct"] is False
    assert results["rollback_choice"]["correct"] is False
    # expected values stay populated
    assert results["deadlock_decision"]["expected"] in ("Ja", "Nein")
    assert str(results["rollback_choice"]["expected"]).strip() != ""
    assert results["solution"]["correct"] is True
    assert isinstance(results["solution"]["expected"], str) and results["solution"]["expected"]


def test_wrong_answer_is_rejected():
    q = WaitForGraphQuestion(seed=4, difficulty="medium")
    payload = {
        "wait_for": json.dumps([["T1", "T2"], ["T2", "T1"]] if not q.edges else []),
        "deadlock_decision": "Nein" if q.deadlock else "Ja",
        "rollback_choice": "Nein",
    }
    results = q.evaluate(payload)
    assert results["deadlock_decision"]["correct"] is False
    # an empty / bogus edge set should not match a non-empty expected set
    if q.edges:
        assert results["wait_for"]["correct"] is False


def test_any_valid_rollback_is_accepted():
    q = _find(lambda x: x.deadlock and len(x.valid_rollback) >= 1)
    assert q is not None
    base = _perfect_payload(q)
    for v in sorted(q.valid_rollback):
        payload = dict(base, rollback_choice=v)
        assert q.evaluate(payload)["rollback_choice"]["correct"] is True

    invalid = [t for t in q.transactions if t not in q.valid_rollback]
    if invalid:
        payload = dict(base, rollback_choice=invalid[0])
        assert q.evaluate(payload)["rollback_choice"]["correct"] is False


def test_no_deadlock_requires_keine_transaktion():
    q = _find(lambda x: not x.deadlock)
    assert q is not None
    ok = q.evaluate(dict(_perfect_payload(q), rollback_choice=ROLLBACK_NONE))
    assert ok["rollback_choice"]["correct"] is True
    wrong = q.evaluate(dict(_perfect_payload(q), rollback_choice=q.transactions[0]))
    assert wrong["rollback_choice"]["correct"] is False


def test_structured_expected_for_wait_for():
    q = WaitForGraphQuestion(seed=7, difficulty="medium")
    exp = q.evaluate({})["wait_for"]["expected"]
    assert isinstance(exp, dict)
    assert set(exp.keys()) == {"edges", "deadlock", "cycles", "rollback"}
    assert all(isinstance(e, list) and len(e) == 2 for e in exp["edges"])
    assert exp["deadlock"] == q.deadlock
    assert exp["rollback"] == sorted(q.valid_rollback)
    assert isinstance(exp["cycles"], list)


@pytest.mark.parametrize("seed", SEEDS)
@pytest.mark.parametrize("difficulty", DIFFICULTIES)
def test_solution_conclusion_matches_verdict(seed, difficulty):
    q = WaitForGraphQuestion(seed=seed, difficulty=difficulty)
    sol = q.evaluate({})["solution"]["expected"]
    assert ("**Verklemmung (Deadlock)**" in sol) == q.deadlock
    assert ("**keine Verklemmung**" in sol) == (not q.deadlock)


# --------------------------------------------------------------------------- #
# Defensive edge parsing
# --------------------------------------------------------------------------- #
def test_parse_edges_variants():
    q = WaitForGraphQuestion(seed=1, difficulty="easy")
    t0, t1 = q.transactions[0], q.transactions[1]
    assert q._parse_edges(json.dumps([[t0, t1]])) == {(t0, t1)}
    assert q._parse_edges([[t0, t1], [t0, t1]]) == {(t0, t1)}  # dedupe, accepts list too
    assert q._parse_edges("") == set()
    assert q._parse_edges(None) == set()
    assert q._parse_edges("garbage") == set()
    assert q._parse_edges("{}") == set()
    assert q._parse_edges(json.dumps([[t0]])) == set()          # malformed pair
    assert q._parse_edges(json.dumps([[t0, "T99"]])) == set()   # unknown transaction
    assert q._parse_edges(json.dumps([[t0, t0]])) == set()      # self-loop


# --------------------------------------------------------------------------- #
# Config fallbacks
# --------------------------------------------------------------------------- #
def test_invalid_difficulty_falls_back_to_easy():
    q = WaitForGraphQuestion(seed=1, difficulty="impossible")
    assert q.difficulty == "easy"

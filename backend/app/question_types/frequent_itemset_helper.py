import math
import re
from itertools import combinations


def format_itemset(itemset):
    return "{" + ",".join(itemset) + "}"


def format_probability(value):
    return f"{value:.3f}".rstrip("0").rstrip(".")


def support_probability(count, total_transactions):
    if total_transactions <= 0:
        return 0.0
    return count / total_transactions


def support_count(transactions, itemset):
    target = set(itemset)
    return sum(1 for transaction in transactions if target.issubset(transaction))


def parse_itemset_text(text):
    tokens = re.findall(r"[A-Za-z0-9]+", str(text or "").upper())
    return tuple(sorted(set(tokens)))


def parse_probability(text):
    raw = str(text or "").strip().replace(",", ".")
    if not raw:
        return None
    is_percent = "%" in raw
    raw = raw.replace("%", "")
    try:
        value = float(raw)
    except ValueError:
        return None
    if is_percent or value > 1.0:
        value = value / 100.0
    return value


def generate_candidates(previous_frequents, k):
    if k <= 1:
        return []
    previous = sorted(set(previous_frequents))
    previous_set = set(previous)
    candidates = set()

    for i, left in enumerate(previous):
        for right in previous[i + 1 :]:
            if left[: k - 2] != right[: k - 2]:
                continue
            merged = tuple(sorted(set(left) | set(right)))
            if len(merged) != k:
                continue
            all_subsets_frequent = all(
                tuple(sorted(subset)) in previous_set
                for subset in combinations(merged, k - 1)
            )
            if all_subsets_frequent:
                candidates.add(merged)

    return sorted(candidates)


def run_apriori_levels(transactions, base_items, minsup):
    total = len(transactions)
    threshold = max(1, math.ceil(float(minsup) * total))
    levels = []

    k = 1
    candidates = [(item,) for item in sorted(base_items)]

    while True:
        counted_candidates = []
        for itemset in candidates:
            count = support_count(transactions, itemset)
            counted_candidates.append(
                {
                    "itemset": itemset,
                    "count": count,
                    "probability": support_probability(count, total),
                }
            )

        frequents = [c for c in counted_candidates if c["count"] >= threshold]

        levels.append(
            {
                "k": k,
                "candidates": counted_candidates,
                "frequents": frequents,
                "terminate": len(frequents) == 0,
            }
        )

        if not frequents:
            break

        k += 1
        previous = [tuple(f["itemset"]) for f in frequents]
        candidates = generate_candidates(previous, k)
        if not candidates:
            # Terminate at current level: no C(k+1) can be generated.
            levels[-1]["terminate"] = True
            break

    return levels, threshold


def generate_transaction_dataset(
    rng,
    num_items,
    num_transactions,
    min_items_per_transaction,
    max_items_per_transaction,
):
    base_items = [chr(ord("A") + i) for i in range(num_items)]

    # Weighted occurrence probabilities make non-trivial frequent sets more likely.
    item_probabilities = {
        item: rng.uniform(0.30, 0.85)
        for item in base_items
    }

    transactions = []
    for _ in range(num_transactions):
        picked = [
            item
            for item in base_items
            if rng.random() <= item_probabilities[item]
        ]

        if len(picked) < min_items_per_transaction:
            missing = min_items_per_transaction - len(picked)
            remaining = [x for x in base_items if x not in picked]
            if remaining:
                picked.extend(rng.sample(remaining, k=min(missing, len(remaining))))

        if len(picked) > max_items_per_transaction:
            picked = rng.sample(picked, k=max_items_per_transaction)

        transactions.append(tuple(sorted(set(picked))))

    # Ensure every base item appears at least once.
    seen = set().union(*transactions) if transactions else set()
    missing_items = [item for item in base_items if item not in seen]
    if missing_items and transactions:
        for idx, item in enumerate(missing_items):
            tx = set(transactions[idx % len(transactions)])
            tx.add(item)
            if len(tx) > max_items_per_transaction:
                tx = set(sorted(tx)[:max_items_per_transaction])
            transactions[idx % len(transactions)] = tuple(sorted(tx))

    return base_items, [set(tx) for tx in transactions]

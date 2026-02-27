from itertools import permutations

import pytest

from app.question_types.hungarian_method import HungarianMethodQuestion


def _assignment_input(prefix, question, assignment_tuple):
    return {
        f"{prefix}{row}": question.schema_b[col]
        for row, col in enumerate(assignment_tuple)
    }


def _matrix_input(matrix_id, matrix_tuple):
    return {
        f"{matrix_id}:cell:{r},{c}": str(float(matrix_tuple[r][c]))
        for r in range(len(matrix_tuple))
        for c in range(len(matrix_tuple[r]))
    }


def _cover_input(matrix_id, cover_tuple, n):
    rows, cols = cover_tuple
    payload = {}
    for r in range(n):
        payload[f"{matrix_id}:row:{r}"] = r in rows
    for c in range(n):
        payload[f"{matrix_id}:col:{c}"] = c in cols
    return payload


def _find_question_with_multiple_optima(max_seed=700):
    for seed in range(1, max_seed + 1):
        q = HungarianMethodQuestion(seed=seed, difficulty="easy", mode="exam")
        if len(q.valid_assignment_tuples) > 1:
            return q
    return None


def _find_steps_question_with_branching_cover(max_seed=900):
    for seed in range(1, max_seed + 1):
        q = HungarianMethodQuestion(seed=seed, difficulty="medium", mode="steps")
        if q.steps == 0:
            continue
        first_step_cover_options = {r["step3_covers"][0] for r in q.step_routes}
        if len(first_step_cover_options) > 1:
            return q
    return None


def test_steps_layout_contains_progressive_views():
    question = HungarianMethodQuestion(seed=25, difficulty="medium", mode="steps")
    layout = question.generate()

    assert "view1" in layout
    assert "view2" in layout

    terminal_view = 2 * question.steps + 3
    final_view = terminal_view + 1
    assert f"view{terminal_view}" in layout
    assert f"view{final_view}" in layout

    step2_matrix_inputs = [el for el in layout["view2"] if el.get("type") == "MatrixInput"]
    assert step2_matrix_inputs
    assert step2_matrix_inputs[0].get("values") == question._as_values(question.step1_matrix)

    first_step3_elements = layout["view3"]
    first_step3_matrix = [el for el in first_step3_elements if el.get("type") == "MatrixInput"][0]
    assert first_step3_matrix.get("id") == ("hm_step3_display_1" if question.steps > 0 else "hm_step3_terminal_display")
    expected_checkbox_id = "hm_cover_1" if question.steps > 0 else "hm_cover_terminal"
    assert first_step3_matrix.get("checkboxId") == expected_checkbox_id


def test_steps_evaluation_accepts_complete_valid_route():
    question = HungarianMethodQuestion(seed=25, difficulty="medium", mode="steps")
    route = question.step_routes[0]

    user_input = {}
    user_input.update(_matrix_input("hm_step1", route["step1_matrix"]))
    user_input.update(_matrix_input("hm_step2", route["step2_matrix"]))

    for i in range(1, question.steps + 1):
        cover_id = f"hm_cover_{i}"
        user_input.update(_cover_input(cover_id, route["step3_covers"][i - 1], question.matrix_size))
        user_input.update(_matrix_input(f"hm_step4_{i}", route["step4_matrices"][i - 1]))

    terminal_cover_id = "hm_cover_terminal"
    user_input.update(_cover_input(terminal_cover_id, route["terminal_cover"], question.matrix_size))
    user_input.update(_assignment_input("hm_final_assign_", question, route["assignment_tuples"][0]))

    results = question.evaluate(user_input)
    assert all(item["correct"] for item in results.values())


def test_steps_accepts_alternative_correct_cover_choice():
    question = _find_steps_question_with_branching_cover()
    if question is None:
        pytest.skip("No medium instance with branching cover choices found in seed range")
    assert question is not None

    first_options = sorted({r["step3_covers"][0] for r in question.step_routes})
    chosen_first = first_options[1]

    chosen_route = None
    for route in question.step_routes:
        if route["step3_covers"][0] == chosen_first:
            chosen_route = route
            break

    assert chosen_route is not None

    user_input = {}
    user_input.update(_matrix_input("hm_step1", chosen_route["step1_matrix"]))
    user_input.update(_matrix_input("hm_step2", chosen_route["step2_matrix"]))
    user_input.update(_cover_input("hm_cover_1", chosen_first, question.matrix_size))
    user_input.update(_matrix_input("hm_step4_1", chosen_route["step4_matrices"][0]))

    results = question.evaluate(user_input)

    for r in range(question.matrix_size):
        assert results[f"hm_cover_1:row:{r}"]["correct"]
    for c in range(question.matrix_size):
        assert results[f"hm_cover_1:col:{c}"]["correct"]


def test_steps_rejects_mixed_cover_across_different_valid_options():
    question = _find_steps_question_with_branching_cover()
    if question is None:
        pytest.skip("No medium instance with branching cover choices found in seed range")
    assert question is not None

    first_options = sorted({r["step3_covers"][0] for r in question.step_routes})
    option_set = set(first_options)

    row_sets = sorted({rows for rows, _ in option_set})
    col_sets = sorted({cols for _, cols in option_set})

    mixed_cover = None
    for rows in row_sets:
        for cols in col_sets:
            candidate = (rows, cols)
            if candidate not in option_set:
                mixed_cover = candidate
                break
        if mixed_cover is not None:
            break

    if mixed_cover is None:
        pytest.skip("Could not construct a mixed invalid cover from available branching options")

    user_input = _cover_input("hm_cover_1", mixed_cover, question.matrix_size)
    results = question.evaluate(user_input)

    for r in range(question.matrix_size):
        assert not results[f"hm_cover_1:row:{r}"]["correct"]
    for c in range(question.matrix_size):
        assert not results[f"hm_cover_1:col:{c}"]["correct"]


def test_step2_expected_is_not_blank_when_answer_is_wrong():
    question = HungarianMethodQuestion(seed=25, difficulty="medium", mode="steps")

    user_input = _matrix_input("hm_step1", question.step1_matrix)
    user_input["hm_step2:cell:0,0"] = "99999"

    results = question.evaluate(user_input)
    assert results["hm_step2:cell:0,0"]["correct"] is False
    assert str(results["hm_step2:cell:0,0"]["expected"]).strip() != ""


def test_generate_exam_layout_contains_final_assignment_inputs():
    question = HungarianMethodQuestion(seed=21, difficulty="easy", mode="exam")
    layout = question.generate()

    assert "view1" in layout
    assert any(el.get("type") == "MatrixInput" and el.get("id") == "hm_exam_work" for el in layout["view1"])
    layout_tables = [el for el in layout["view1"] if el.get("type") == "layout_table"]
    assert layout_tables

    cells = layout_tables[0].get("cells", [])
    assert len(cells) == 2
    assert all(cell.get("type") == "DropdownInput" for cell in cells[1])


def test_exam_accepts_any_valid_optimal_assignment():
    question = _find_question_with_multiple_optima()
    if question is None:
        pytest.skip("No multi-optimal easy seed found in search range")
    assert question is not None

    first = question.valid_assignment_tuples[0]
    second = question.valid_assignment_tuples[1]

    results_first = question.evaluate(_assignment_input("exam_assign_", question, first))
    results_second = question.evaluate(_assignment_input("exam_assign_", question, second))

    assert all(item["correct"] for item in results_first.values())
    assert all(item["correct"] for item in results_second.values())


def test_exam_rejects_non_optimal_assignment():
    question = HungarianMethodQuestion(seed=33, difficulty="easy", mode="exam")
    valid = set(question.valid_assignment_tuples)

    wrong_tuple = None
    for perm in permutations(range(question.matrix_size)):
        if perm not in valid:
            wrong_tuple = perm
            break

    assert wrong_tuple is not None

    results = question.evaluate(_assignment_input("exam_assign_", question, wrong_tuple))
    assert any(not item["correct"] for item in results.values())


def test_steps_final_assignment_is_graded_per_field():
    question = HungarianMethodQuestion(seed=25, difficulty="medium", mode="steps")
    route = question.step_routes[0]

    user_input = {}
    user_input.update(_matrix_input("hm_step1", route["step1_matrix"]))
    user_input.update(_matrix_input("hm_step2", route["step2_matrix"]))

    for i in range(1, question.steps + 1):
        cover_id = f"hm_cover_{i}"
        user_input.update(_cover_input(cover_id, route["step3_covers"][i - 1], question.matrix_size))
        user_input.update(_matrix_input(f"hm_step4_{i}", route["step4_matrices"][i - 1]))

    user_input.update(_cover_input("hm_cover_terminal", route["terminal_cover"], question.matrix_size))

    valid = set(question.valid_assignment_tuples)
    base = question.valid_assignment_tuples[0]
    candidate = list(base)

    changed_row = None
    for row in range(question.matrix_size):
        allowed = {t[row] for t in valid}
        for col in range(question.matrix_size):
            if col not in allowed:
                candidate[row] = col
                changed_row = row
                break
        if changed_row is not None:
            break

    if changed_row is None:
        pytest.skip("No row-specific partial-wrong case available for this instance")

    user_input.update(_assignment_input("hm_final_assign_", question, tuple(candidate)))

    results = question.evaluate(user_input)
    final_keys = [f"hm_final_assign_{i}" for i in range(question.matrix_size)]
    assert any(results[k]["correct"] for k in final_keys)
    assert any(not results[k]["correct"] for k in final_keys)

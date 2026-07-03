import React, { useEffect, useMemo, useRef, useState } from "react";

const STYLE_ID = "association-rule-formula-builder-styles";

function ensureStyles() {
  if (typeof document === "undefined" || document.getElementById(STYLE_ID)) return;

  const style = document.createElement("style");
  style.id = STYLE_ID;
  style.textContent = `
    .arfb-shell {
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }

    .arfb-header,
    .arfb-support-panel,
    .arfb-target-card {
      border: 1px solid #e5e7eb;
      border-radius: 16px;
      background: #ffffff;
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    }

    .arfb-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 1rem;
      padding: 1rem;
    }

    .arfb-title {
      margin: 0;
      font-size: 1.05rem;
      font-weight: 750;
      color: #111827;
    }

    .arfb-subtitle {
      margin: 0.25rem 0 0;
      color: #6b7280;
      line-height: 1.35;
    }

    .arfb-formula-badge {
      flex: 0 0 auto;
      padding: 0.65rem 0.9rem;
      border-radius: 14px;
      background: #f3f4f6;
      color: #111827;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
      font-size: 0.9rem;
      white-space: nowrap;
      line-height: 1.45;
    }

    .arfb-formula-note {
      display: block;
      margin-top: 0.15rem;
      color: #6b7280;
      font-size: 0.78rem;
    }

    .arfb-support-panel {
      padding: 1rem;
    }

    .arfb-panel-title {
      margin: 0 0 0.75rem;
      font-size: 0.95rem;
      font-weight: 750;
      color: #111827;
    }

    .arfb-support-levels {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 0.75rem;
    }

    .arfb-support-level {
      padding: 0.75rem;
      border-radius: 14px;
      background: #f9fafb;
      min-height: 4rem;
    }

    .arfb-level-title {
      margin-bottom: 0.45rem;
      font-weight: 750;
      color: #374151;
      font-size: 0.9rem;
    }

    .arfb-chip-list {
      display: flex;
      flex-wrap: wrap;
      gap: 0.4rem;
    }

    .arfb-chip {
      display: inline-flex;
      align-items: center;
      gap: 0.3rem;
      padding: 0.32rem 0.55rem;
      border-radius: 999px;
      background: #eef2ff;
      color: #1f2937;
      font-size: 0.88rem;
      font-weight: 650;
    }

    .arfb-chip-support {
      color: #6b7280;
      font-weight: 600;
    }

    .arfb-target-card {
      padding: 1rem;
    }

    .arfb-target-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 1rem;
      margin-bottom: 0.85rem;
    }

    .arfb-target-title {
      margin: 0;
      font-size: 1rem;
      font-weight: 750;
      color: #111827;
    }

    .arfb-target-subtitle {
      margin: 0.2rem 0 0;
      color: #6b7280;
      font-size: 0.9rem;
    }

    .arfb-add-btn {
      border: 1px solid #d1d5db;
      border-radius: 999px;
      background: #ffffff;
      padding: 0.45rem 0.75rem;
      cursor: pointer;
      color: #111827;
      font-weight: 650;
    }

    .arfb-add-btn:hover {
      background: #f9fafb;
    }

    .arfb-rule-list {
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
    }

    .arfb-rule-card {
      padding: 0.85rem;
      border: 1px solid #e5e7eb;
      border-radius: 14px;
      background: #f9fafb;
    }

    .arfb-rule-card.arfb-correct {
      border-color: #86efac;
      background: #f0fdf4;
    }

    .arfb-rule-card.arfb-wrong {
      border-color: #fca5a5;
      background: #fff1f2;
    }

    .arfb-rule-topline {
      display: grid;
      grid-template-columns: minmax(96px, 1fr) auto minmax(96px, 1fr) auto;
      align-items: center;
      gap: 0.5rem;
      margin-bottom: 0.75rem;
    }

    .arfb-side-chip {
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 2.35rem;
      padding: 0.45rem 0.7rem;
      border: 1px solid #dbeafe;
      border-radius: 12px;
      background: #eff6ff;
      font-weight: 750;
      color: #1e3a8a;
    }

    .arfb-side-chip.arfb-correct {
      border-color: #86efac;
      background: #dcfce7;
      color: #166534;
    }

    .arfb-side-chip.arfb-wrong {
      border-color: #fca5a5;
      background: #fee2e2;
      color: #991b1b;
    }

    .arfb-arrow {
      font-size: 1.25rem;
      font-weight: 800;
      color: #111827;
    }

    .arfb-input {
      width: 100%;
      box-sizing: border-box;
      padding: 0.55rem 0.65rem;
      border: 1px solid #d1d5db;
      border-radius: 10px;
      background: #ffffff;
      color: #111827;
    }

    .arfb-input:focus {
      outline: 2px solid #bfdbfe;
      border-color: #93c5fd;
    }

    .arfb-number-input {
      width: 5.1rem;
      text-align: center;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
    }

    .arfb-input.arfb-correct {
      border-color: #86efac;
      background: #f0fdf4;
    }

    .arfb-input.arfb-wrong {
      border-color: #fca5a5;
      background: #fff1f2;
    }

    .arfb-remove-btn {
      width: 2rem;
      height: 2rem;
      border: 0;
      border-radius: 999px;
      background: transparent;
      color: #6b7280;
      font-size: 1.35rem;
      cursor: pointer;
    }

    .arfb-remove-btn:hover {
      background: #fee2e2;
      color: #991b1b;
    }

    .arfb-rendered-formula {
      display: flex;
      align-items: center;
      flex-wrap: wrap;
      gap: 0.45rem;
      padding: 0.75rem;
      border-radius: 12px;
      background: #ffffff;
      border: 1px solid #eef2f7;
      color: #111827;
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
      line-height: 2.3rem;
    }

    .arfb-formula-label {
      font-weight: 700;
    }

    .arfb-decision-row {
      display: flex;
      align-items: center;
      gap: 0.55rem;
      margin-top: 0.7rem;
      color: #374151;
      font-weight: 600;
      border: 1px solid transparent;
      border-radius: 10px;
      padding: 0.35rem 0.45rem;
      width: fit-content;
    }

    .arfb-checkbox-wrap {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 1.15rem;
      height: 1.15rem;
      border-radius: 0.35rem;
      border: 1px solid transparent;
    }

    .arfb-checkbox-wrap.arfb-correct,
    .arfb-decision-row.arfb-correct {
      border-color: #86efac;
      background: #dcfce7;
      color: #166534;
    }

    .arfb-checkbox-wrap.arfb-wrong,
    .arfb-decision-row.arfb-wrong {
      border-color: #fca5a5;
      background: #fee2e2;
      color: #991b1b;
    }

    .arfb-field-block {
      display: inline-flex;
      flex-direction: column;
      gap: 0.25rem;
      vertical-align: middle;
    }

    .arfb-expected {
      color: #b91c1c;
      font-size: 0.78rem;
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.2;
    }

    .arfb-summary {
      padding: 0.75rem 1rem;
      border: 1px solid #fecaca;
      border-radius: 14px;
      background: #fff1f2;
      color: #991b1b;
      font-weight: 650;
    }

    .arfb-empty {
      color: #9ca3af;
      font-style: italic;
      font-size: 0.9rem;
    }

    @media (max-width: 900px) {
      .arfb-header,
      .arfb-target-header {
        flex-direction: column;
      }

      .arfb-formula-badge {
        white-space: normal;
      }

      .arfb-support-levels {
        grid-template-columns: 1fr;
      }
    }

    @media (max-width: 650px) {
      .arfb-rule-topline {
        grid-template-columns: 1fr auto 1fr auto;
      }

      .arfb-rendered-formula {
        align-items: flex-start;
      }
    }
  `;
  document.head.appendChild(style);
}

function parseItems(value) {
  const raw = String(value || "").trim().toUpperCase();
  if (!raw) return [];

  if (/[,;\s/|]+/.test(raw)) {
    return raw
      .split(/[,;\s/|]+/)
      .map((x) => x.trim())
      .filter(Boolean)
      .sort();
  }

  return raw
    .split("")
    .map((x) => x.trim())
    .filter(Boolean)
    .sort();
}

function uniqueSorted(items) {
  return [...new Set((items || []).map((x) => String(x).trim().toUpperCase()).filter(Boolean))].sort();
}

function itemsetKey(items) {
  return uniqueSorted(Array.isArray(items) ? items : parseItems(items)).join("");
}

function itemsetDisplay(items) {
  const key = itemsetKey(items);
  return key || "?";
}

function nonEmptyProperSubsets(items) {
  const normalized = uniqueSorted(items);
  const result = [];
  const n = normalized.length;

  for (let mask = 1; mask < (1 << n) - 1; mask += 1) {
    const subset = [];
    for (let i = 0; i < n; i += 1) {
      if (mask & (1 << i)) subset.push(normalized[i]);
    }
    result.push(subset);
  }

  return result;
}

function difference(items, removeItems) {
  const remove = new Set(uniqueSorted(removeItems));
  return uniqueSorted(items).filter((item) => !remove.has(item));
}

function buildRowsForTarget(targetItems, prefillRuleSides, initialRowsPerTarget) {
  const target = itemsetKey(targetItems);

  if (prefillRuleSides) {
    return nonEmptyProperSubsets(targetItems).map((lhs) => ({
      lhs: itemsetKey(lhs),
      rhs: itemsetKey(difference(targetItems, lhs)),
      numerator: "",
      denominator: "",
      confidence: "",
      accepted: false,
    }));
  }

  const count = Math.max(1, Number(initialRowsPerTarget || 2));
  return Array.from({ length: count }, () => ({
    lhs: "",
    rhs: "",
    numerator: "",
    denominator: "",
    confidence: "",
    accepted: false,
    target,
  }));
}

function parseInitialGroups(el) {
  const raw = el?.value ?? el?.answer ?? el?.initialValue;
  if (raw) {
    try {
      const parsed = typeof raw === "string" ? JSON.parse(raw) : raw;
      if (Array.isArray(parsed?.groups)) return parsed.groups;
    } catch {
      // Ignore invalid saved state and rebuild from layout data.
    }
  }

  const targets = Array.isArray(el?.targetItemsets) ? el.targetItemsets : [];
  const prefillRuleSides = el?.prefillRuleSides !== false;

  return targets.map((target) => ({
    target: itemsetKey(target.items),
    rows: buildRowsForTarget(target.items, prefillRuleSides, el?.initialRowsPerTarget),
  }));
}

function groupedSupportItemsets(supportItemsets) {
  const groups = { 1: [], 2: [], 3: [] };

  for (const entry of supportItemsets || []) {
    const level = Number(entry.level || entry.items?.length || 0);
    if (!groups[level]) groups[level] = [];
    groups[level].push(entry);
  }

  for (const level of Object.keys(groups)) {
    groups[level].sort((a, b) => itemsetKey(a.items).localeCompare(itemsetKey(b.items)));
  }

  return groups;
}

function formatExpected(expected) {
  if (expected == null) return "";
  if (typeof expected === "string" || typeof expected === "number" || typeof expected === "boolean") {
    return String(expected);
  }
  if (typeof expected === "object" && expected.message) {
    return String(expected.message);
  }
  return JSON.stringify(expected);
}

function statusClass(result) {
  if (!result) return "";
  return result.correct ? "arfb-correct" : "arfb-wrong";
}

export default function AssociationRuleFormulaBuilder({
  el,
  idx,
  onChange,
  evaluationResults = {},
  showExpected = false,
  registerFieldId,
}) {
  useEffect(() => {
    ensureStyles();
  }, []);

  const id = el?.id || `association_rule_formula_${idx ?? 0}`;
  const label = el?.label || "Assoziationsregeln mit Konfidenz";
  const minConfidence = Number(el?.minConfidence ?? 0);
  const supportItemsets = Array.isArray(el?.supportItemsets) ? el.supportItemsets : [];
  const targetItemsets = Array.isArray(el?.targetItemsets) ? el.targetItemsets : [];
  const showFormula = el?.showFormula !== false;
  const showDecisionInput = el?.showDecisionInput !== false;
  const allowRuleEditing = el?.allowRuleEditing !== false;
  const allowAddRows = el?.allowAddRows !== false;
  const formulaText = el?.formulaText || "conf(A ⇒ B) = P(A∩B) / P(A)";
  const probabilityDefinition = el?.probabilityDefinition || "P(A) = σ(A) / |Transactions|";

  const [groups, setGroups] = useState(() => parseInitialGroups(el));
  const onChangeRef = useRef(onChange);
  const registerFieldIdRef = useRef(registerFieldId);
  const registeredIdsRef = useRef(new Set());

  useEffect(() => {
    onChangeRef.current = onChange;
  }, [onChange]);

  useEffect(() => {
    registerFieldIdRef.current = registerFieldId;
  }, [registerFieldId]);

  const supportGroups = useMemo(() => groupedSupportItemsets(supportItemsets), [supportItemsets]);

  useEffect(() => {
    const serialized = JSON.stringify({ groups });
    onChangeRef.current?.(id, serialized);
  }, [groups, id]);

  useEffect(() => {
    const register = registerFieldIdRef.current;
    if (!register) return;

    const ids = [id];
    groups.forEach((group, groupIndex) => {
      (group.rows || []).forEach((_, rowIndex) => {
        const base = `${id}_g${groupIndex}_r${rowIndex}`;
        ids.push(base);
        ids.push(`${base}_lhs`);
        ids.push(`${base}_rhs`);
        ids.push(`${base}_numerator`);
        ids.push(`${base}_denominator`);
        ids.push(`${base}_confidence`);
        ids.push(`${base}_accepted`);
      });
    });

    ids.forEach((fieldId) => {
      if (registeredIdsRef.current.has(fieldId)) return;
      registeredIdsRef.current.add(fieldId);
      register(fieldId);
    });
  }, [groups, id]);

  function resultFor(fieldId) {
    const direct = evaluationResults?.[fieldId];
    if (direct) return direct;

    const elementResult = evaluationResults?.[id];
    return (
      elementResult?.field_results?.[fieldId] ||
      elementResult?.fields?.[fieldId] ||
      elementResult?.rule_results?.[fieldId] ||
      null
    );
  }

  function classFor(fieldId, base = "arfb-input") {
    const state = statusClass(resultFor(fieldId));
    return state ? `${base} ${state}` : base;
  }

  function expectedHint(fieldId) {
    const result = resultFor(fieldId);
    if (!showExpected || !result || result.correct) return null;
    return <div className="arfb-expected">Expected: {formatExpected(result.expected)}</div>;
  }

  function updateRow(groupIndex, rowIndex, patch) {
    setGroups((previous) =>
      previous.map((group, gi) => {
        if (gi !== groupIndex) return group;
        const rows = Array.isArray(group.rows) ? group.rows : [];
        return {
          ...group,
          rows: rows.map((row, ri) => (ri === rowIndex ? { ...row, ...patch } : row)),
        };
      })
    );
  }

  function addRow(groupIndex) {
    setGroups((previous) =>
      previous.map((group, gi) => {
        if (gi !== groupIndex) return group;
        return {
          ...group,
          rows: [
            ...(Array.isArray(group.rows) ? group.rows : []),
            {
              lhs: "",
              rhs: "",
              numerator: "",
              denominator: "",
              confidence: "",
              accepted: false,
              target: group.target,
            },
          ],
        };
      })
    );
  }

  function removeRow(groupIndex, rowIndex) {
    setGroups((previous) =>
      previous.map((group, gi) => {
        if (gi !== groupIndex) return group;
        return {
          ...group,
          rows: (Array.isArray(group.rows) ? group.rows : []).filter((_, ri) => ri !== rowIndex),
        };
      })
    );
  }

  const mainResult = resultFor(id);
  const mainMessage = mainResult && !mainResult.correct ? formatExpected(mainResult.expected) : "";

  return (
    <div className="arfb-shell" data-field-id={id}>
      {showExpected && mainResult && !mainResult.correct && mainMessage && (
        <div className="arfb-summary">{mainMessage}</div>
      )}

      <div className="arfb-header">
        <div>
          <h3 className="arfb-title">{label}</h3>
          <p className="arfb-subtitle">
            Erzeuge Regel-Blöcke, trage die Itemsets links/rechts des Pfeils ein und fülle die Formelwerte aus.
          </p>
        </div>
        {showFormula && (
          <div className="arfb-formula-badge">
            {formulaText}
            <span className="arfb-formula-note">{probabilityDefinition}</span>
          </div>
        )}
      </div>

      <div className="arfb-support-panel">
        <h4 className="arfb-panel-title">Gegebene frequent itemsets (FIS)</h4>
        <div className="arfb-support-levels">
          {[1, 2, 3].map((level) => (
            <div key={level} className="arfb-support-level">
              <div className="arfb-level-title">L{level}</div>
              <div className="arfb-chip-list">
                {(supportGroups[level] || []).length ? (
                  (supportGroups[level] || []).map((entry) => (
                    <span key={`${level}_${itemsetKey(entry.items)}`} className="arfb-chip">
                      {itemsetDisplay(entry.items)}
                      <span className="arfb-chip-support">
                        σ={entry.support}{entry.probability != null ? `, P=${Number(entry.probability).toFixed(3)}` : ""}
                      </span>
                    </span>
                  ))
                ) : (
                  <span className="arfb-empty">keine</span>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {groups.map((group, groupIndex) => {
        const targetFromLayout = targetItemsets[groupIndex]?.items;
        const targetLabel = group.target || itemsetDisplay(targetFromLayout);
        const rows = Array.isArray(group.rows) ? group.rows : [];

        return (
          <div key={`${targetLabel}_${groupIndex}`} className="arfb-target-card">
            <div className="arfb-target-header">
              <div>
                <h4 className="arfb-target-title">Regeln aus FIS {targetLabel}</h4>
                <p className="arfb-target-subtitle">
                  Für jede Regel muss A ∪ B = {targetLabel} gelten. Die Richtung A ⇒ B ist relevant.
                </p>
              </div>
              {allowAddRows && (
                <button type="button" className="arfb-add-btn" onClick={() => addRow(groupIndex)}>
                  + Regel-Block
                </button>
              )}
            </div>

            <div className="arfb-rule-list">
              {rows.map((row, rowIndex) => {
                const base = `${id}_g${groupIndex}_r${rowIndex}`;
                const lhsField = `${base}_lhs`;
                const rhsField = `${base}_rhs`;
                const numeratorField = `${base}_numerator`;
                const denominatorField = `${base}_denominator`;
                const confidenceField = `${base}_confidence`;
                const acceptedField = `${base}_accepted`;
                const lhsLabel = itemsetDisplay(row.lhs);
                const rhsLabel = itemsetDisplay(row.rhs);
                const xLabel = itemsetKey(row.lhs) || "?";
                const probabilityBothLabel = lhsLabel !== "?" && rhsLabel !== "?" ? `${lhsLabel}∩${rhsLabel}` : "A∩B";
                const probabilityLeftLabel = xLabel !== "?" ? xLabel : "A";

                return (
                  <div key={rowIndex} className={classFor(base, "arfb-rule-card")}>
                    <div className="arfb-rule-topline">
                      {allowRuleEditing ? (
                        <div className="arfb-field-block">
                          <input
                            className={classFor(lhsField)}
                            value={row.lhs || ""}
                            placeholder="A, z. B. A oder AB"
                            onChange={(event) => updateRow(groupIndex, rowIndex, { lhs: event.target.value })}
                          />
                          {expectedHint(lhsField)}
                        </div>
                      ) : (
                        <div className="arfb-field-block">
                          <span className={classFor(lhsField, "arfb-side-chip")}>{lhsLabel}</span>
                          {expectedHint(lhsField)}
                        </div>
                      )}

                      <span className="arfb-arrow">⇒</span>

                      {allowRuleEditing ? (
                        <div className="arfb-field-block">
                          <input
                            className={classFor(rhsField)}
                            value={row.rhs || ""}
                            placeholder="B, z. B. B oder CD"
                            onChange={(event) => updateRow(groupIndex, rowIndex, { rhs: event.target.value })}
                          />
                          {expectedHint(rhsField)}
                        </div>
                      ) : (
                        <div className="arfb-field-block">
                          <span className={classFor(rhsField, "arfb-side-chip")}>{rhsLabel}</span>
                          {expectedHint(rhsField)}
                        </div>
                      )}

                      {allowAddRows ? (
                        <button
                          type="button"
                          className="arfb-remove-btn"
                          aria-label="Remove rule"
                          onClick={() => removeRow(groupIndex, rowIndex)}
                        >
                          ×
                        </button>
                      ) : (
                        <span />
                      )}
                    </div>

                    <div className="arfb-rendered-formula">
                      <span className="arfb-formula-label">conf({lhsLabel} ⇒ {rhsLabel})</span>
                      <span>=</span>
                      <span>P({probabilityBothLabel}) / P({probabilityLeftLabel})</span>
                      <span>=</span>

                      <span className="arfb-field-block">
                        <input
                          className={classFor(numeratorField, "arfb-input arfb-number-input")}
                          value={row.numerator || ""}
                          placeholder="P(A∩B)"
                          inputMode="decimal"
                          onChange={(event) => updateRow(groupIndex, rowIndex, { numerator: event.target.value })}
                        />
                        {expectedHint(numeratorField)}
                      </span>

                      <span>/</span>

                      <span className="arfb-field-block">
                        <input
                          className={classFor(denominatorField, "arfb-input arfb-number-input")}
                          value={row.denominator || ""}
                          placeholder="P(A)"
                          inputMode="decimal"
                          onChange={(event) => updateRow(groupIndex, rowIndex, { denominator: event.target.value })}
                        />
                        {expectedHint(denominatorField)}
                      </span>

                      <span>=</span>

                      <span className="arfb-field-block">
                        <input
                          className={classFor(confidenceField, "arfb-input arfb-number-input")}
                          value={row.confidence || ""}
                          placeholder="conf"
                          inputMode="decimal"
                          onChange={(event) => updateRow(groupIndex, rowIndex, { confidence: event.target.value })}
                        />
                        {expectedHint(confidenceField)}
                      </span>
                    </div>

                    {showDecisionInput && (
                      <label className={classFor(acceptedField, "arfb-decision-row")}>
                        <span className={classFor(acceptedField, "arfb-checkbox-wrap")}>
                          <input
                            type="checkbox"
                            checked={Boolean(row.accepted)}
                            onChange={(event) => updateRow(groupIndex, rowIndex, { accepted: event.target.checked })}
                          />
                        </span>
                        <span>conf ≥ d = {minConfidence.toFixed(2)}</span>
                        {expectedHint(acceptedField)}
                      </label>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}

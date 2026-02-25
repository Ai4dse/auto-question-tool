import React, { useEffect, useState } from "react";
import Plot from "react-plotly.js";
import Tree from "react-d3-tree";
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import "bootstrap/dist/css/bootstrap.min.css";

const replaceOps = (value) => {
  return value
    .replace(/\\join/g, "⋈{}")
    .replace(/\\proj/g, "π{}")     
    .replace(/\\sel/g, "σ{}")
    .replace(/\\diff/g, "−{}")           
    .replace(/\\rename/g, "ρ{}")   
};

const NODE_OP_META = {
  join: {
    color: "#1f77b4",
    symbol: "⋈",
    label: "JOIN",
  },
  projection: {
    color: "#2ca02c",
    symbol: "π",
    label: "PROJECTION",
  },
  selection: {
    color: "#d62728",
    symbol: "σ",
    label: "SELECTION",
  },
  diff: {
    color: "#9467bd",
    symbol: "−",
    label: "DIFFERENCE",
  },
  rename_attribute: {
    color: "#ff7f0e",
    symbol: "ρ",
    label: "RENAME ATTRIBUTE",
  },
  rename_relation: {
    color: "#ffde08ff",
    symbol: "ρ",
    label: "RENAME RELATION",
  },
};

const OP_SYMBOL_COLORS = {
  "⋈": NODE_OP_META.join.color,
  "π": NODE_OP_META.projection.color,
  "σ": NODE_OP_META.selection.color,
  "−": NODE_OP_META.diff.color,
  "ρ": NODE_OP_META.rename_attribute.color,
};


const NODE_RELATION_COLOR = "#555555"; // grey for relations like hoeren, Studierende, etc.

function ColoredNode({ nodeDatum }) {
  const rawName = String(nodeDatum?.name ?? "");

  // detect operator keyword from first token, e.g. "join" from "join (A=B)"
  const lower = rawName.toLowerCase();
  const match = lower.match(/^[a-z_]+/);
  const opKey = match && NODE_OP_META[match[0]] ? match[0] : null;

  const isOp = !!opKey;
  const meta = opKey ? NODE_OP_META[opKey] : null;

  const fill = isOp ? meta.color : NODE_RELATION_COLOR;
  const radius = isOp ? 58 : 42;

  // split "join (Studierende.MatrNr=hoeren.MatrNr)" into title + detail
  let title = rawName;
  let detail = "";

  const openIdx = rawName.indexOf("(");
  const closeIdx = rawName.lastIndexOf(")");

  if (openIdx !== -1 && closeIdx !== -1 && closeIdx > openIdx) {
    title = rawName.slice(0, openIdx).trim();             // "join"
    detail = rawName.slice(openIdx + 1, closeIdx).trim(); // "Studierende.MatrNr=hoeren.MatrNr"
  }

  const fontBase = {
    fontFamily: '"Helvetica Neue", Arial, sans-serif',
    letterSpacing: "0.4px",
    stroke: "none",
    fill: "#000",
  };

  return (
    <g>
      {/* Circle */}
      <circle r={radius} fill={fill} stroke="#181717ff" strokeWidth={2.1} />

      {isOp ? (
        <>
          {/* math-style symbol INSIDE the circle (⋈, π, σ, …) */}
          <text
            dy={17}
            textAnchor="middle"
            style={{ ...fontBase, fontSize: 64, }}
          >
            {meta.symbol}
          </text>

          {/* operator label below, e.g. JOIN / PROJECTION */}
          <text
            dy={radius + 36}
            textAnchor="middle"
            style={{ ...fontBase, fontSize: 30 }}
          >
            {meta.label}
          </text>

          {/* condition / detail below that, smaller */}
          {detail && (
            <text
              dy={radius + 74}
              textAnchor="middle"
              style={{ ...fontBase, fontSize: 38 }}
            >
              {detail}
            </text>
          )}
        </>
      ) : (
        // relations: name below the circle
        <text
          dy={radius + 44}
          textAnchor="middle"
          style={{ ...fontBase, fontSize: 40}}
        >
          {rawName}
        </text>
      )}
    </g>
  );
}

function renderMathLike(text) {
  const parts = [];
  const regex = /{([^}]*)}/g; // findet {...}
  let lastIdx = 0;
  let match;
  let key = 0;

  // Operatoren, die hervorgehoben werden sollen
  const opRegex = /([⋈πσρ−])/g;

  // Plain-Text-Abschnitt mit farbigen Operatoren rendern
  const renderPlainSegment = (segment) => {
    if (!segment) return null;

    const subParts = [];
    let last = 0;
    let m;
    let subKey = 0;

    while ((m = opRegex.exec(segment)) !== null) {
      // Text vor dem Operator
      if (m.index > last) {
        subParts.push(
          <span key={`plain-${key}-${subKey++}`}>
            {segment.slice(last, m.index)}
          </span>
        );
      }

      const symbol = m[1];
      const color = OP_SYMBOL_COLORS[symbol] || "#000";

      // Der Operator selbst – groß, fett, farbig
      subParts.push(
        <span
          key={`op-${key}-${subKey++}`}
          style={{
            fontSize: "1.35em",
            marginRight: "2px",
            color,
          }}
        >
          {symbol}
        </span>
      );

      last = opRegex.lastIndex;
    }

    // Rest hinter dem letzten Operator
    if (last < segment.length) {
      subParts.push(
        <span key={`plain-tail-${key}-${subKey++}`}>
          {segment.slice(last)}
        </span>
      );
    }

    return subParts;
  };

  // Haupt-Loop: Text in Plain-Parts + {…}-Parts zerlegen
  while ((match = regex.exec(text)) !== null) {
    // Plain-Text vor {…}
    if (match.index > lastIdx) {
      const segment = text.slice(lastIdx, match.index);
      parts.push(
        <React.Fragment key={key++}>
          {renderPlainSegment(segment)}
        </React.Fragment>
      );
    }

    // Inhalt in {…} als graues, kleineres Subscript
    parts.push(
      <sub
        key={key++}
        style={{
          fontSize: "0.75em",
          color: "#666",
          verticalAlign: "sub",
          fontWeight: 400,
        }}
      >
        {match[1]}
      </sub>
    );

    lastIdx = regex.lastIndex;
  }

  // Rest nach dem letzten {…}
  if (lastIdx < text.length) {
    const segment = text.slice(lastIdx);
    parts.push(
      <React.Fragment key={key++}>
        {renderPlainSegment(segment)}
      </React.Fragment>
    );
  }

  return parts;
}

/**
 * LayoutRenderer
 * ---------------
 * - Renders layout-defined elements (text, tables, inputs, plots)
 * - Includes evaluation color feedback
 * - Uses Bootstrap for styling
 */
const normLabel = (x) => (Array.isArray(x) ? String(x[0] ?? "") : String(x ?? ""));

function MatrixInputGrid({
  el,
  idx,
  userInput,
  onChange,
  renderEvaluatedInput,
  registerFieldId,
  evaluationResults,
  showExpected,
}) {
  const id = el.id || `matrix_${idx}`;
  const checkboxId = el.checkboxId || id;
  const rows = el.rows || [];
  const cols = el.cols || [];
  const placeholders = el.values || [];

  const registerField = (fieldId) => {
    if (typeof registerFieldId === "function") registerFieldId(String(fieldId));
  };

  const isRowStruck = (r) => !!userInput?.[`${checkboxId}:row:${r}`];
  const isColStruck = (c) => !!userInput?.[`${checkboxId}:col:${c}`];
  const cellKey = (r, c) => `${id}:cell:${r},${c}`;

  const renderCheckboxFeedback = (fieldId) => {
    const evalResult = evaluationResults?.[fieldId];
    const isCorrect = evalResult?.correct;
    const expected = evalResult?.expected;
    const feedbackClass = evalResult === undefined ? "" : isCorrect ? "is-valid" : "is-invalid";

    return {
      feedbackClass,
      feedbackEl:
        showExpected && evalResult !== undefined && !isCorrect && expected !== undefined ? (
          <small className="text-muted fst-italic d-block">Correct: {String(expected)}</small>
        ) : null,
    };
  };

  // Seed userInput with placeholder values once per matrix identity/size
  useEffect(() => {
    for (let r = 0; r < rows.length; r++) {
      for (let c = 0; c < cols.length; c++) {
        const key = cellKey(r, c);
        const hasValue = userInput && Object.prototype.hasOwnProperty.call(userInput, key);
        if (!hasValue) {
          const v = placeholders?.[r]?.[c];
          if (v !== undefined) onChange(key, String(v));
        }
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, rows.length, cols.length]);

  return (
    <div className="card mb-4 shadow-sm">
      <div className="card-body">
        <h5 className="card-title mb-3">{el.title || "Matrix"}</h5>

        <div className="table-responsive">
          <table className="table table-bordered table-sm align-middle">
            <thead className="table-light">
              <tr>
                <th className="text-center">x</th>
                {cols.map((cLabel, cIdx) => {
                  const colStruck = isColStruck(cIdx);
                  return (
                    <th
                      key={`c-head-${cIdx}`}
                      className={colStruck ? "text-decoration-line-through text-muted" : ""}
                    >
                      {normLabel(cLabel)}
                    </th>
                  );
                })}
                <th className="text-center small text-muted">Strike row</th>
              </tr>
            </thead>

            <tbody>
                {rows.map((rLabel, rIdx) => {
                  const rowStruck = isRowStruck(rIdx);
                  const rowStrikeKey = `${checkboxId}:row:${rIdx}`;
                  const rowFeedback = renderCheckboxFeedback(rowStrikeKey);
                  registerField(rowStrikeKey);

                  return (
                  <tr
                    key={`r-${rIdx}`}
                    className={rowStruck ? "text-decoration-line-through text-muted" : ""}
                  >
                    <th className="text-center fw-semibold">{normLabel(rLabel)}</th>

                    {cols.map((_, cIdx) => {
                      const colStruck = isColStruck(cIdx);
                      const strike = rowStruck || colStruck ? "text-decoration-line-through text-muted" : "";
                      const key = cellKey(rIdx, cIdx);
                      const seeded = placeholders?.[rIdx]?.[cIdx];
                      const value = userInput?.[key] ?? (seeded !== undefined ? String(seeded) : "");

                      return (
                        <td key={`cell-${rIdx}-${cIdx}`} className={strike}>
                          {/* pass fieldId + current value to your wrapper */}
                          {renderEvaluatedInput(key, value)}
                        </td>
                      );
                    })}

                    <td className="text-center">
                      <input
                        type="checkbox"
                        className={`form-check-input ${rowFeedback.feedbackClass}`}
                          checked={!!userInput?.[rowStrikeKey]}
                          onChange={(e) => onChange(rowStrikeKey, e.target.checked)}
                        aria-label={`Strike row ${normLabel(rLabel)}`}
                      />
                      {rowFeedback.feedbackEl}
                    </td>
                  </tr>
                );
              })}
            </tbody>

            <tfoot>
              <tr>
                <th className="small text-muted text-center">Strike col</th>
                {cols.map((_, cIdx) => {
                  const colStrikeKey = `${checkboxId}:col:${cIdx}`;
                  const colFeedback = renderCheckboxFeedback(colStrikeKey);
                  registerField(colStrikeKey);
                  return (
                    <td key={`c-foot-${cIdx}`} className="text-center">
                      <input
                        type="checkbox"
                        className={`form-check-input ${colFeedback.feedbackClass}`}
                        checked={!!userInput?.[colStrikeKey]}
                        onChange={(e) => onChange(colStrikeKey, e.target.checked)}
                        aria-label={`Strike column ${normLabel(cols[cIdx])}`}
                      />
                      {colFeedback.feedbackEl}
                    </td>
                  );
                })}
                <td />
              </tr>
            </tfoot>
          </table>
        </div>
      </div>
    </div>
  );
}
function DendrogramBuilder({ el, idx, userInput, onChange, renderEvaluatedInput }) {

  const id = el.id || `dendro_${idx}`;

  const pointLabels = (Array.isArray(el.points) ? el.points : []).map((p) => String(p));
  const leafRefs = pointLabels.map((_, i) => `L:${i}`);

  const MERGE_CHILD_PREFIX = `${id}:merge:`;
  const MERGE_DIST_PREFIX = `${id}:merge_dist:`;

  const distKey = (k) => `${MERGE_DIST_PREFIX}${k}`;
  const childrenKey = (k) => `${id}:merge:${k}:children`;

  const parseMerges = () => {
    const out = [];
    for (const key of Object.keys(userInput || {})) {
      if (!key.startsWith(MERGE_CHILD_PREFIX)) continue;
      const m = key.match(new RegExp(`^${id}:merge:(\\d+):children$`));
      if (!m) continue;

      const k = Number(m[1]);
      const raw = String(userInput?.[key] ?? "");
      const [a, b] = raw.split("|");
      if (!a || !b) continue;

      out.push({ k, a, b });
    }
    out.sort((x, y) => x.k - y.k);
    return out;
  };

  const merges = parseMerges();
  const mergeRefs = merges.map((m) => `M:${m.k}`);

  const nextMergeId = () => {
    let max = -1;
    for (const m of merges) max = Math.max(max, m.k);
    return max + 1;
  };

  const [selected, setSelected] = useState(null);
  const [msg, setMsg] = useState("");

  const isLeaf = (ref) => ref.startsWith("L:");
  const leafIndex = (ref) => Number(ref.split(":")[1]);
  const mergeId = (ref) => Number(ref.split(":")[1]);

  // parent map: childRef -> parentRef (used to enforce "only roots selectable")
  const parentOf = new Map();
  for (const m of merges) {
    const p = `M:${m.k}`;
    parentOf.set(m.a, p);
    parentOf.set(m.b, p);
  }
  const isRoot = (ref) => !parentOf.has(ref);

  const maxMerges = Math.max(0, pointLabels.length - 1);
  const remainingMerges = Math.max(0, maxMerges - merges.length);
  const isComplete = merges.length === maxMerges;

  const createMerge = (aRef, bRef) => {
    setMsg("");

    if (aRef === bRef) return;

    if (!isRoot(aRef) || !isRoot(bRef)) {
      setMsg("You can only merge top-most clusters / unused points.");
      return;
    }

    if (merges.length >= maxMerges) {
      setMsg("Max merges reached (a dendrogram on n leaves has n−1 merges).");
      return;
    }

    const k = nextMergeId();

    onChange(childrenKey(k), `${aRef}|${bRef}`);

    if (!Object.prototype.hasOwnProperty.call(userInput || {}, distKey(k))) {
      onChange(distKey(k), "");
    }
  };

  const onSelectRef = (ref) => {
    setMsg("");
    if (!isRoot(ref)) return;

    if (selected === null) return setSelected(ref);
    if (selected === ref) return setSelected(null);

    createMerge(selected, ref);
    setSelected(null);
  };

  // ---------- CASCADE DELETE ----------
  const computeCascadeDelete = (k0) => {
    // Build reverse dependency: childRef -> Set(parentMergeK)
    // If a merge uses child "M:7", then deleting 7 should delete that merge too.
    const rev = new Map(); // ref -> Set<number>
    for (const m of merges) {
      const parentK = m.k;
      for (const childRef of [m.a, m.b]) {
        if (!rev.has(childRef)) rev.set(childRef, new Set());
        rev.get(childRef).add(parentK);
      }
    }

    const startRef = `M:${k0}`;
    const toDelete = new Set([k0]);
    const queue = [startRef];

    while (queue.length) {
      const ref = queue.shift(); // "M:<k>"
      const parents = rev.get(ref);
      if (!parents) continue;

      for (const pk of parents) {
        if (!toDelete.has(pk)) {
          toDelete.add(pk);
          queue.push(`M:${pk}`);
        }
      }
    }

    // delete deeper merges first (higher k is usually "later"; but safest is descending)
    return Array.from(toDelete).sort((a, b) => b - a);
  };

  // parse "M:7" -> 7
  const mergeNumFromRef = (ref) => Number(String(ref).split(":")[1]);

  // rewrite a child ref if it is a merge ref and exists in map
  const remapRef = (ref, oldToNew) => {
    if (!String(ref).startsWith("M:")) return ref;
    const oldK = mergeNumFromRef(ref);
    const newK = oldToNew.get(oldK);
    return Number.isFinite(newK) ? `M:${newK}` : ref; // should always exist after cascade
  };

  // Compact all merges in userInput to 0..(k-1) based on current merges list,
  // excluding the ones in deleteSet.
  const compactMergesAfterDelete = (deleteSet) => {
    // merges that remain
    const kept = merges.filter((m) => !deleteSet.has(m.k)).sort((a, b) => a.k - b.k);

    // oldK -> newK mapping
    const oldToNew = new Map();
    kept.forEach((m, i) => oldToNew.set(m.k, i));

    // 1) Clear ALL existing merge keys (both kept and deleted) so we don't leave stale ids behind.
    for (const m of merges) {
      onChange(childrenKey(m.k), "");
      onChange(distKey(m.k), "");
    }

    // 2) Re-create kept merges under new compact ids
    for (const m of kept) {
      const newK = oldToNew.get(m.k);

      const newA = remapRef(m.a, oldToNew);
      const newB = remapRef(m.b, oldToNew);

      onChange(childrenKey(newK), `${newA}|${newB}`);

      // carry over the old height value to the new id
      const oldHeight = userInput?.[distKey(m.k)] ?? "";
      onChange(distKey(newK), oldHeight);
    }
  };

  const removeMergeCascade = (k0) => {
    const ks = computeCascadeDelete(k0);
    const deleteSet = new Set(ks);

    compactMergesAfterDelete(deleteSet);

    setSelected(null);
    setMsg("");
  };


  const clearAll = () => {
    // remove everything by deleting all merges (descending)
    const allKs = merges.map((m) => m.k).sort((a, b) => b - a);
    for (const k of allKs) {
      onChange(childrenKey(k), "");
      onChange(distKey(k), "");
    }
    setSelected(null);
    setMsg("");
  };
  // ---------- END CASCADE DELETE ----------

  // ----- Layout computation -----
  const W = Number(el.width ?? 900);

  const padX = Number(el.padX ?? 60);
  const bottomPad = Number(el.bottomPad ?? 60);
  const topPad = Number(el.topPad ?? 30);
  const levelStep = Number(el.levelStep ?? 70);
  const firstLevelOffset = Number(el.firstLevelOffset ?? 90);

  const levels = merges.length;
  const neededHeight =
    topPad + bottomPad + firstLevelOffset + Math.max(0, levels - 1) * levelStep;
  const H = Math.max(Number(el.height ?? 360), neededHeight);

  const baseY = H - bottomPad;
  const levelY = (level) => baseY - firstLevelOffset - level * levelStep;

  const xForLeaf = (i) => {
    if (pointLabels.length <= 1) return W / 2;
    const span = W - 2 * padX;
    return padX + (span * i) / (pointLabels.length - 1);
  };

  const nodePos = new Map();
  for (let i = 0; i < pointLabels.length; i++) {
    nodePos.set(`L:${i}`, { x: xForLeaf(i), y: baseY });
  }

  for (let level = 0; level < merges.length; level++) {
    const m = merges[level];
    const pRef = `M:${m.k}`;
    const a = nodePos.get(m.a);
    const b = nodePos.get(m.b);
    if (!a || !b) continue;
    nodePos.set(pRef, { x: (a.x + b.x) / 2, y: levelY(level) });
  }

  const refLabel = (ref) => {
    if (ref.startsWith("L:")) return pointLabels[leafIndex(ref)] ?? ref;
    return `C${mergeId(ref)}`;
  };


  const nodeR = 16;
  const allRefs = [...leafRefs, ...mergeRefs];

  return (
    <div className="card mb-4 shadow-sm">
      <div className="card-body">
        <div className="d-flex justify-content-between align-items-center mb-2">
          <h5 className="card-title mb-0">{el.title || "Dendrogram Builder"}</h5>
          <div className="d-flex gap-2">
            <button
              type="button"
              className="btn btn-sm btn-outline-danger"
              onClick={clearAll}
              disabled={merges.length === 0}
            >
              Clear all
            </button>
          </div>
        </div>

        <div className="text-muted small mb-2">
          Click any two <b>root</b> items (unused points or top-most clusters) to merge them.
        </div>
        <div className="d-flex align-items-center gap-2 mb-2">
          <span className={`badge ${isComplete ? "bg-success" : "bg-warning text-dark"}`}>
            {isComplete
              ? "Dendrogram complete"
              : `Incomplete: ${remainingMerges} merge${remainingMerges === 1 ? "" : "s"} missing`}
          </span>
          {!isComplete && (
            <span className="text-muted small">
              Merge until you reach {maxMerges} total merges.
            </span>
          )}
        </div>

        {msg && <div className="alert alert-warning py-2">{msg}</div>}

        <div className="mb-3 d-flex flex-wrap gap-2">
          {leafRefs.map((ref) => {
            const isSel = selected === ref;
            const disabled = !isRoot(ref);
            return (
              <button
                key={`${id}-${ref}`}
                type="button"
                disabled={disabled}
                className={`btn btn-sm ${isSel ? "btn-primary" : "btn-outline-primary"} ${
                  disabled ? "opacity-50" : ""
                }`}
                onClick={() => onSelectRef(ref)}
                title={disabled ? "Already part of a cluster" : ""}
              >
                {refLabel(ref)}
              </button>
            );
          })}

          {mergeRefs.length > 0 && (
            <>
              <span className="mx-2 text-muted small align-self-center">Clusters:</span>
              {mergeRefs.map((ref) => {
                const isSel = selected === ref;
                const disabled = !isRoot(ref);
                return (
                  <button
                    key={`${id}-${ref}`}
                    type="button"
                    disabled={disabled}
                    className={`btn btn-sm ${isSel ? "btn-success" : "btn-outline-success"} ${
                      disabled ? "opacity-50" : ""
                    }`}
                    onClick={() => onSelectRef(ref)}
                    title={disabled ? "Not top-most cluster" : ""}
                  >
                    {refLabel(ref)}
                  </button>
                );
              })}
            </>
          )}
        </div>

        <div
          className="border rounded p-2 bg-light"
          style={{ overflowX: "auto", overflowY: "auto", maxHeight: "600px" }}
        >
          <svg width={W} height={H} style={{ display: "block" }}>
            <line x1={padX} y1={baseY} x2={W - padX} y2={baseY} stroke="#999" strokeWidth="2" />

            {merges.map((m) => {
              const pRef = `M:${m.k}`;
              const p = nodePos.get(pRef);
              const a = nodePos.get(m.a);
              const b = nodePos.get(m.b);
              if (!p || !a || !b) return null;

              const heightValRaw = userInput?.[distKey(m.k)];
              const heightVal = heightValRaw !== undefined && heightValRaw !== null ? String(heightValRaw) : "";

              const btnSize = 18;

              // vertical layout above the node
              const valueY = p.y + 32;                 // value text y
              const btnYTop = p.y - 42;
              const btnXLeft = p.x - btnSize / 2;      // centered

              //background pill for readability
              const showPill = !!heightVal;


              return (
                <g key={`${id}-merge-${m.k}`}>
                  {/* edges */}
                  <line x1={a.x} y1={a.y} x2={p.x} y2={p.y} stroke="#333" strokeWidth="3" />
                  <line x1={b.x} y1={b.y} x2={p.x} y2={p.y} stroke="#333" strokeWidth="3" />

                  {/* show current height value near merge node */}
                  {heightVal && (
                    <g>
                      {/* "pill" behind text */}
                      {showPill && (
                        <rect
                          x={p.x - 24}
                          y={valueY - 14}
                          width={48}
                          height={20}
                          rx={8}
                          ry={8}
                          fill="#fff"
                          stroke="#bbb"
                          strokeWidth="1"
                          opacity="0.95"
                        />
                      )}

                      <text
                        x={p.x}
                        y={valueY}
                        textAnchor="middle"
                        style={{
                          fontFamily: "monospace",
                          fontSize: 14,
                          fill: "#111",
                          userSelect: "none",
                          pointerEvents: "none",
                        }}
                      >
                        {heightVal}
                      </text>
                    </g>
)}

                  {/* SVG-native delete button */}
                  <g
                    transform={`translate(${btnXLeft}, ${btnYTop})`}
                    style={{ cursor: "pointer" }}
                    onClick={(e) => {
                      e.stopPropagation();
                      removeMergeCascade(m.k);
                    }}
                  >
                    <rect
                      x={0}
                      y={0}
                      width={btnSize}
                      height={btnSize}
                      rx={4}
                      ry={4}
                      fill="#fff"
                      stroke="#dc3545"
                      strokeWidth={2}
                    />
                    <text
                      x={btnSize / 2}
                      y={btnSize / 2 + 5}
                      textAnchor="middle"
                      style={{
                        fontFamily: "monospace",
                        fontSize: 16,
                        fill: "#dc3545",
                        userSelect: "none",
                        pointerEvents: "none",
                      }}
                    >
                      ×
                    </text>

                    {/* slightly larger hit target */}
                    <rect x={-6} y={-6} width={btnSize + 12} height={btnSize + 12} fill="transparent" />
                  </g>

                </g>
              );
            })}


            {allRefs.map((ref) => {
              const pos = nodePos.get(ref);
              if (!pos) return null;

              const root = isRoot(ref);
              const isSel = selected === ref;
              const isCluster = ref.startsWith("M:");

              return (
                <g
                  key={`${id}-node-${ref}`}
                  style={{ cursor: root ? "pointer" : "not-allowed", opacity: root ? 1 : 0.35 }}
                  onClick={() => root && onSelectRef(ref)}
                >
                  <circle
                    cx={pos.x}
                    cy={pos.y}
                    r={nodeR}
                    fill={isSel ? (isCluster ? "#198754" : "#0d6efd") : "#fff"}
                    stroke={isCluster ? "#198754" : "#0d6efd"}
                    strokeWidth="3"
                  />
                  <text
                    x={pos.x}
                    y={pos.y + 5}
                    textAnchor="middle"
                    style={{ fontFamily: "monospace", fontSize: 12, fill: "#111" }}
                  >
                    {isCluster ? `C${mergeId(ref)}` : (pointLabels[leafIndex(ref)] ?? "")}
                  </text>

                </g>
              );
            })}
          </svg>
        </div>

        <div className="mt-3">
          <div className="fw-semibold mb-2">Stored fields</div>

          {merges.length === 0 ? (
            <div className="text-muted small">No merges yet.</div>
          ) : (
            <div className="d-flex flex-column gap-2">
              {merges.map((m) => {
                const fieldId = distKey(m.k);
                const prettyChild = (ref) => {
                  if (ref.startsWith("L:")) return pointLabels[Number(ref.split(":")[1])] ?? ref;
                  if (ref.startsWith("M:")) return `C${Number(ref.split(":")[1])}`;
                  return ref;
                };

                const label = `Merge C${m.k}: ${prettyChild(m.a)} + ${prettyChild(m.b)} → height`;

                return (
                  <div key={`${id}-merge-field-${m.k}`} className="mb-2">
                    <label className="form-label fw-semibold">{label}</label>
                    {renderEvaluatedInput(fieldId, userInput?.[fieldId] ?? "")}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function DropdownSection({ title, children, defaultOpen = false }) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  const toggle = () => setIsOpen((o) => !o);

  return (
    <div className="card mb-3 shadow-sm">
      {/* Header-Zeile mit Titel + Pfeil */}
      <button
        type="button"
        className="btn btn-link w-100 text-start d-flex justify-content-between align-items-center px-3 py-2"
        onClick={toggle}
        style={{ textDecoration: "none" }}
      >
        <span className="fw-semibold">{title}</span>
        <span className="ms-2">
          {isOpen ? "▾" : "▸"}
        </span>
      </button>

      {/* Inhalt nur zeigen, wenn isOpen */}
      {isOpen && (
        <div className="card-body pt-2">
          {children}
        </div>
      )}
    </div>
  );
}

export default function LayoutRenderer({
  layout,
  activeView = "view1",
  onChange = () => {},
  evaluationResults = {},
  userInput = {},
  showExpected = false,
  reactiveTables = {},
  registerFieldId = null,
}) {
  if (!layout) return null;

  const viewElements = layout[activeView] || [];
  const header = layout.header;

  /** 🔹 Evaluated text input with color feedback */
  const renderEvaluatedInput = (fieldId, value = "", options = {}) => {
    if (typeof registerFieldId === "function") registerFieldId(String(fieldId));
    const {
      asTextarea = false,
      rows = 4,
      variant = "text",          // "text" | "select"
      selectOptions = [],
      placeholder = "Please select...",
    } = options;

    const evalResult = evaluationResults?.[fieldId];
    const isCorrect = evalResult?.correct;
    const expected = evalResult?.expected;

    // better tooltip condition: don't rely on truthiness
    const hasExpected = expected !== undefined && expected !== null;

    const feedbackClass =
      evalResult === undefined ? "" : isCorrect ? "is-valid" : "is-invalid";

    const title =
      evalResult !== undefined && !isCorrect && hasExpected ? `Expected: ${expected}` : "";

    // For text/textarea we apply replaceOps; for select we don't.
    const handleChange = (e) => {
      const raw = e.target.value;
      const next = variant === "select" ? raw : replaceOps(raw);
      onChange(fieldId, next);
    };

    // shared styling
    const baseStyle = { fontFamily: "monospace", whiteSpace: "pre" };
    const bgStyle =
      evalResult === undefined
        ? {}
        : isCorrect
        ? { backgroundColor: "var(--bs-success-bg-subtle)" }
        : { backgroundColor: "var(--bs-danger-bg-subtle)" };
    const controlledValue = userInput?.[fieldId] ?? (value ?? "");
    return (
      <div className="mb-2">
        {variant === "select" ? (
          <select
            name={fieldId}
            className={`form-select form-select-sm ${feedbackClass}`}
            style={bgStyle}
            onChange={handleChange}
            value={controlledValue}
            title={title}
          >
            <option value="" disabled hidden>
              {placeholder}
            </option>
            {selectOptions.map((opt, i) => (
              <option key={i} value={opt}>
                {String(opt)}
              </option>
            ))}
          </select>

        ) : asTextarea ? (
          <textarea
            name={fieldId}
            className={`form-control form-control-sm ${feedbackClass}`}
            onChange={handleChange}
            value={controlledValue}
            title={title}
            style={baseStyle}
            rows={rows}
          />
        ) : (
          <input
            type="text"
            name={fieldId}
            className={`form-control form-control-sm ${feedbackClass}`}
            onChange={handleChange}
            value={controlledValue}
            title={title}
            style={baseStyle}
          />
        )}

        {showExpected && !isCorrect && expected !== undefined && (
          <small className="text-muted fst-italic">Correct: {expected}</small>
        )}
      </div>
    );
  };


  /** 🔹 General renderer for all element types */
  const renderElement = (el, idx) => {
    switch (el.type) {
      case "DendrogramBuilder":
      case "dendrogram_builder":
        return (
          <DendrogramBuilder
            key={el.id ?? idx}
            el={el}
            idx={idx}
            userInput={userInput}
            onChange={onChange}
            renderEvaluatedInput={renderEvaluatedInput}
          />
        );
      case "Text":
      case "text":
        return (
          <p key={idx} className="mb-3" style={{ whiteSpace: "pre-line" }}>
            {el.value || el.content}
          </p>
        );
      case "Table":
      case "table":
        return (
          <div key={idx} className="card mb-4 shadow-sm">
            <div className="card-body">
              <h5 className="card-title mb-3">
                {el.title || el.label || "Table"}
              </h5>
              <div className="table-responsive">
                <table className="table table-bordered table-sm align-middle">
                  <thead className="table-light">
                    <tr>
                      {el.columns.map((col, i) => (
                        <th key={i}>{col}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {el.rows.map((row, rIdx) => (
                      <tr key={rIdx}>
                        {row.map((cell, cIdx) => (
                          <td key={cIdx}>{cell}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        );
      case "Dropdown":
      case "dropdown": {
        const childrenEls = Array.isArray(el.children) ? el.children : [];
        const title = el.title || el.label || "Details";
        const key = el.id ?? idx;

        return (
          <DropdownSection key={key} title={title} defaultOpen={!!el.defaultOpen}>
            {childrenEls.map((child, cIdx) =>
              renderElement(child, child.id ?? `${key}-${cIdx}`)
            )}
          </DropdownSection>
        );
      }
      case "SchemaGrid":
      case "schema_grid": {
        const tables = el.tables || [];

        return (
          <div
            key={idx}
            className="row row-cols-1 row-cols-md-2 row-cols-lg-2 g-3 mb-4"
          >
            {tables.map((tbl, tIdx) => (
              <div className="col" key={tIdx}>
                <div className="card h-100 shadow-sm">
                  <div className="card-body">
                    <h5 className="card-title mb-3">
                      {tbl.title || tbl.label || "Table"}
                    </h5>

                    <div className="table-responsive">
                      <table className="table table-bordered table-sm align-middle mb-0">
                        <thead className="table-light">
                          <tr>
                            {tbl.columns.map((col, i) => (
                              <th key={i} className="small">
                                {col}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {tbl.rows.map((row, rIdx) => (
                            <tr key={rIdx}>
                              {row.map((cell, cIdx) => (
                                <td key={cIdx} className="small">
                                  {String(cell)}
                                </td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>

                    {/* Optional: Hinweis, dass gekürzt wurde */}
                    <p className="text-muted small mt-2 mb-0">
                      (nur Beispiel-Tupel angezeigt)
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        );
      }
      case "ReactiveTree":
      case "reactive_tree": {
        const listenId = el.listenTo;
        const data = reactiveTables?.[listenId] || {};
        const { tree, error, status } = data;

        console.log("REACTIVE TREE DATA", listenId, data);

        return (
          <div key={idx} className="card mb-4 shadow-sm">
            <div className="card-body">
              <h5 className="card-title mb-3">{el.label || "Execution Tree"}</h5>

              {status === "loading" && <p className="text-muted">Parsing...</p>}
              {error && <p className="text-danger">{error}</p>}

              {tree && (
                <div style={{ width: "200%", height: "600px" }}>
                  <Tree
                    data={[tree]}
                    orientation="vertical"
                    nodeSize={{ x: 750, y: 220 }}
                    translate={{ x: 600, y: 50 }}
                    zoom={0.4}
                    renderCustomNodeElement={(rdProps) => <ColoredNode {...rdProps} />}
                  />
                </div>
              )}

              {!tree && !error && status !== "loading" && (
                <p className="text-muted">No expression yet.</p>
              )}
            </div>
          </div>
        );
      }
      case "ReactiveTable":
      case "reactive_table": {
        const listenId = el.listenTo; // e.g. "0"
        const data = reactiveTables?.[listenId] || {};
        const { columns = [], rows = [], error, status } = data;

        return (
          <div key={idx} className="card mb-4 shadow-sm">
            <div className="card-body">
              <h5 className="card-title mb-3">
                {el.label || el.title || "Result"}
              </h5>

              {status === "loading" && (
                <p className="text-muted small mb-2">Evaluating...</p>
              )}

              {error && (
                <p className="text-danger small mb-2">
                  {error}
                </p>
              )}

              {!error && rows.length === 0 && status !== "loading" && (
                <p className="text-muted small">
                  No tuples yet (expression incomplete or empty result).
                </p>
              )}

              {rows.length > 0 && (
                <div className="table-responsive">
                  <table className="table table-bordered table-sm align-middle">
                    <thead className="table-light">
                      <tr>
                        {columns.map((c, i) => (
                          <th key={i}>{c}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {rows.map((row, rIdx) => (
                        <tr key={rIdx}>
                          {row.map((cell, cIdx) => (
                            <td key={cIdx}>{String(cell)}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        );
      }
      case "TableInput":
      case "table_input":
        return (
          <div key={idx} className="card mb-4 shadow-sm">
            <div className="card-body">
              <h5 className="card-title mb-3">{el.label}</h5>
              <div className="table-responsive">
                <table className="table table-bordered table-sm align-middle">
                  <thead className="table-light">
                    <tr>
                      {el.columns.map((col, i) => (
                        <th key={i}>{col}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {el.rows.map((row, rIdx) => (
                      <tr key={rIdx}>
                        {row.fields.map((field, fIdx) => {
                          const fieldId = `${row.id}_${fIdx}`;
                          return (
                            <td key={fIdx} className={fIdx === 0 ? "fw-bold text-center" : ""}>
                              {fIdx === 0 ? field : renderEvaluatedInput(fieldId, field)}
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        );
      case "LayoutTable":
      case "layout_table": {
        const rows = Number(el.rows ?? 0);
        const cols = Number(el.cols ?? 0);
        const cells = Array.isArray(el.cells) ? el.cells : [];
        const tableKey = el.id ?? idx;

        const getCell = (r, c) => {
          const row = Array.isArray(cells[r]) ? cells[r] : null;
          return row && row[c] ? row[c] : null;
        };

        return (
          <div key={tableKey} className="card mb-4 shadow-sm">
            <div className="card-body">
              <h5 className="card-title mb-3">{el.title || el.label || "Layout Table"}</h5>

              <div className="table-responsive">
                <table className="table table-bordered table-sm align-middle">
                  <tbody>
                    {Array.from({ length: rows }).map((_, r) => (
                      <tr key={`r-${tableKey}-${r}`}>
                        {Array.from({ length: cols }).map((__, c) => {
                          const cellEl = getCell(r, c);
                          return (
                            <td key={`c-${tableKey}-${r}-${c}`} style={{ verticalAlign: "top" }}>
                              {cellEl ? renderElement(cellEl, `${tableKey}-${r}-${c}`) : null}
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        );
      };
      case "MatrixInput":
      case "matrix_input":
        return (
          <MatrixInputGrid
            key={idx}
            el={el}
            idx={idx}
            userInput={userInput}
            onChange={onChange}
            renderEvaluatedInput={renderEvaluatedInput}
            registerFieldId={registerFieldId}
            evaluationResults={evaluationResults}
            showExpected={showExpected}
          />
        );
      case "ExpressionInput":
      case "expression_input": {
        const fieldId = el.id;
        const value = userInput?.[fieldId] ?? el.default ?? "";
        const evalResult = evaluationResults?.[fieldId];
        const isCorrect = evalResult?.correct;
        const expected = evalResult?.expected;

        const bgClass =
          evalResult === undefined
            ? ""
            : isCorrect
            ? "bg-success-subtle"
            : "bg-danger-subtle";

        const handleChange = (e) => {
          const raw = e.target.value;
          const withUnicode = replaceOps(raw);
          onChange(fieldId, withUnicode);
        };

        return (
          <div key={idx} className="mb-3">
            <label className="form-label fw-semibold">{el.label}</label>

            {/* Mehrzeiliges Eingabefeld */}
            <textarea
              rows={el.rows || 5}
              className={`form-control ${bgClass}`}
              value={value}
              onChange={handleChange}
              style={{
                fontFamily: "monospace",
                whiteSpace: "pre-wrap",
              }}
            />

            {/* Überschrift über der gerenderten Ansicht */}
            <p className="mt-2 mb-1 fw-semibold">
              Relationaler Algebra Ausdruck (gerendert):
            </p>

            {/* Math-Style Preview */}
            <div
              className="p-2 border rounded bg-light"
              style={{
                fontSize: "1.2em",       // alles etwas größer
                whiteSpace: "pre-wrap",
              }}
            >
              {renderMathLike(value)}
            </div>

            {showExpected && !isCorrect && expected !== undefined && (
              <small className="text-muted fst-italic">Correct: {expected}</small>
            )}
          </div>
        );
      }
      case "MultipleChoice":
      case "multiple_choice":
        return (
          <div key={idx} className="mb-4">
            <h5>{el.label}</h5>
            <div>
              {el.options.map((opt, i) => (
                <div className="form-check form-check-inline" key={i}>
                  <input
                    className="form-check-input"
                    type="radio"
                    name={el.id}
                    value={opt}
                    checked={userInput?.[el.id] === opt}
                    onChange={(e) => onChange(el.id, e.target.value)}
                  />
                  <label className="form-check-label">{opt}</label>
                </div>
              ))}
            </div>
          </div>
        );

      case "TextInput":
      case "text_input":
        return (
          <div key={idx} className="mb-3">
            <label className="form-label fw-semibold">{el.label}</label>
            {renderEvaluatedInput(el.id, userInput?.[el.id])}
          </div>
        );
        case "DropdownInput":
        case "dropdown_input":
          return (
            <div key={idx} className="mb-3">
              <label className="form-label fw-semibold">{el.label}</label>

              {renderEvaluatedInput(el.id, userInput?.[el.id] ?? "", {
                variant: "select",
                selectOptions: Array.isArray(el.options) ? el.options : [],
                placeholder: el.placeholder ?? "Please select...",
              })}
            </div>
          );
      case "VarCoordinatePlot":
      case "var_coordinates_plot": {
        const toXY = (arr = []) =>
          Array.isArray(arr)
            ? arr
                .map((p) => {
                  if (Array.isArray(p) && p.length >= 3) {
                    return { label: String(p[0]), x: Number(p[1]), y: Number(p[2]) };
                  } else if (typeof p === "object" && p !== null && "x" in p && "y" in p) {
                    return {
                      label: String(p.label || ""),
                      x: Number(p.x),
                      y: Number(p.y),
                    };
                  } else {
                    console.warn("Invalid point:", p);
                    return null;
                  }
                })
                .filter(Boolean)
            : [];

        // Convert "points_blue", "points_green", etc into series entries (legacy support)
        const legacySeriesFromEl = (el) => {
          const out = [];
          const colorKeys = Object.keys(el || {}).filter((k) => k.startsWith("points_"));

          for (const key of colorKeys) {
            const color = key.replace("points_", ""); // "blue", "green", ...
            const value = el[key];

            // New-ish per-color format: { points: [...], name: "..." }
            if (value && typeof value === "object" && !Array.isArray(value)) {
              out.push({
                name: value.name || color,
                color,
                points: toXY(value.points),
                symbol: value.symbol,
                size: value.size,
              });
            } else {
              // Old format: points_blue: [...]
              out.push({
                name: color,
                color,
                points: toXY(value),
              });
            }
          }
          return out;
        };

        // Prefer new API el.series, otherwise fall back to legacy points_* fields
        const seriesRaw = Array.isArray(el.series) ? el.series : legacySeriesFromEl(el);

        // Normalize the series
        const series = seriesRaw
          .map((s, idx) => {
            // Allow passing points directly as an array, too
            const points = toXY(s?.points ?? s);
            return {
              name: typeof s?.name === "string" && s.name.length ? s.name : `Series ${idx + 1}`,
              color: typeof s?.color === "string" && s.color.length ? s.color : undefined,
              symbol: typeof s?.symbol === "string" && s.symbol.length ? s.symbol : "circle",
              size: Number.isFinite(s?.size) ? s.size : 8,
              points,
            };
          })
          .filter((s) => s.points.length > 0);

        const traces = series.map((s) => ({
          x: s.points.map((p) => p.x),
          y: s.points.map((p) => p.y),
          text: s.points.map((p) => p.label),
          mode: "markers+text",
          type: "scatter",
          name: s.name,
          textposition: "top right",
          marker: {
            // plotly will accept undefined color (it will auto-pick),
            // or you can default it if you want.
            color: s.color,
            symbol: s.symbol,
            size: s.size,
          },
        }));

        return (
          <div key={idx} className="card mb-4 shadow-sm">
            <div className="card-body">
              <h5 className="card-title mb-3">{el.title || "Coordinate Plot"}</h5>
              <Plot
                data={traces}
                layout={{
                  xaxis: { title: "X" },
                  yaxis: { title: "Y" },
                  margin: { t: 20, r: 20, b: 40, l: 40 },
                  autosize: true,
                  legend: { orientation: "h" },
                }}
                style={{ width: "100%", height: "350px" }}
                useResizeHandler
                config={{ responsive: true, displayModeBar: false }}
              />
            </div>
          </div>
        );
      }



      case "CoordinatePlot":
      case "coordinates_plot": {
        const toXY = (arr = []) =>
          Array.isArray(arr)
            ? arr
                .map((p) => {
                  if (Array.isArray(p) && p.length >= 3) {
                    return { label: String(p[0]), x: Number(p[1]), y: Number(p[2]) };
                  } else if (
                    typeof p === "object" &&
                    p !== null &&
                    "x" in p &&
                    "y" in p
                  ) {
                    return {
                      label: String(p.label || ""),
                      x: Number(p.x),
                      y: Number(p.y),
                    };
                  } else {
                    console.warn("Invalid point:", p);
                    return null;
                  }
                })
                .filter(Boolean)
            : [];

        const pointsBlue = toXY(el.points_blue);
        const pointsGreen = toXY(el.points_green);

        return (
          <div key={idx} className="card mb-4 shadow-sm">
            <div className="card-body">
              <h5 className="card-title mb-3">{el.title || "Coordinate Plot"}</h5>
              <Plot
                data={[
                  {
                    x: pointsBlue.map((p) => p.x),
                    y: pointsBlue.map((p) => p.y),
                    text: pointsBlue.map((p) => p.label),
                    mode: "markers+text",
                    type: "scatter",
                    name: "Points",
                    textposition: "top right",
                    marker: { color: "blue", size: 8 },
                  },
                  {
                    x: pointsGreen.map((p) => p.x),
                    y: pointsGreen.map((p) => p.y),
                    text: pointsGreen.map((p) => p.label),
                    mode: "markers+text",
                    type: "scatter",
                    name: "Centroids",
                    textposition: "top right",
                    marker: { color: "green", symbol: "triangle-up", size: 10 },
                  },
                ]}
                layout={{
                  xaxis: { title: "X" },
                  yaxis: { title: "Y" },
                  margin: { t: 20, r: 20, b: 40, l: 40 },
                  autosize: true,
                }}
                style={{ width: "100%", height: "350px" }}
                useResizeHandler
                config={{ responsive: true, displayModeBar: false }}
              />
            </div>
          </div>
        );
      }
      default:
        return (
          <div key={idx} className="text-muted fst-italic">
            Unknown element type: {el.type}
          </div>
        );
    }
  };

  return (
    <div className="my-4">
      {header && (
        <h2 className="mb-4 fw-bold">
          {header.value || header.content || "Untitled Layout"}
        </h2>
      )}
      <div>{viewElements.map((el, idx) => renderElement(el, idx))}</div>
    </div>
  );
}

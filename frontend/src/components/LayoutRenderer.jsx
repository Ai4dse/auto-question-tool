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
    .replace(/\\sele/g, "σ{}")
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

function MatrixInputGrid({ el, idx, userInput, onChange, renderEvaluatedInput }) {
  const id = el.id || `matrix_${idx}`;
  const rows = el.rows || [];
  const cols = el.cols || [];
  const placeholders = el.values || [];

  const isRowStruck = (r) => !!userInput?.[`${id}:row:${r}`];
  const isColStruck = (c) => !!userInput?.[`${id}:col:${c}`];
  const cellKey = (r, c) => `${id}:cell:${r},${c}`;

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
                        className="form-check-input"
                        checked={!!userInput?.[`${id}:row:${rIdx}`]}
                        onChange={(e) => onChange(`${id}:row:${rIdx}`, e.target.checked)}
                        aria-label={`Strike row ${normLabel(rLabel)}`}
                      />
                    </td>
                  </tr>
                );
              })}
            </tbody>

            <tfoot>
              <tr>
                <th className="small text-muted text-center">Strike col</th>
                {cols.map((_, cIdx) => (
                  <td key={`c-foot-${cIdx}`} className="text-center">
                    <input
                      type="checkbox"
                      className="form-check-input"
                      checked={!!userInput?.[`${id}:col:${cIdx}`]}
                      onChange={(e) => onChange(`${id}:col:${cIdx}`, e.target.checked)}
                      aria-label={`Strike column ${normLabel(cols[cIdx])}`}
                    />
                  </td>
                ))}
                <td />
              </tr>
            </tfoot>
          </table>
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
}) {
  if (!layout) return null;

  const viewElements = layout[activeView] || [];
  const header = layout.header;

  /** 🔹 Evaluated text input with color feedback */
  const renderEvaluatedInput = (fieldId, value = "", options = {}) => {
  const { asTextarea = false, rows = 4 } = options;

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
    const withUnicode = replaceOps(raw); // \\join -> ⋈{} etc., auch über Zeilenumbrüche
    onChange(fieldId, withUnicode);
  };

  const commonProps = {
    name: fieldId,
    className: `form-control form-control-sm ${bgClass}`,
    onChange: handleChange,
    value: userInput?.[fieldId] ?? "",
    title: !isCorrect && expected ? `Expected: ${expected}` : "",
    style: { fontFamily: "monospace", whiteSpace: "pre" },
  };

  return (
    <div className="mb-2">
      {asTextarea ? (
        <textarea {...commonProps} rows={rows} />
      ) : (
        <input type="text" {...commonProps} />
      )}

      {showExpected && !isCorrect && expected !== undefined && (
        <small className="text-muted fst-italic">
          Correct: {expected}
        </small>
      )}
    </div>
  );
};

  /** 🔹 General renderer for all element types */
  const renderElement = (el, idx) => {
    switch (el.type) {
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
        // el.children ist ein Array von "normalen" Layout-Elementen
        const childrenEls = el.children || [];

        return (
          <DropdownSection
            key={idx}
            title={el.title || el.label || "Details"}
            defaultOpen={!!el.defaultOpen}
          >
            {Array.isArray(childrenEls)
              ? childrenEls.map((child, cIdx) =>
                  renderElement(child, `${idx}-${cIdx}`)
                )
              : null}
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

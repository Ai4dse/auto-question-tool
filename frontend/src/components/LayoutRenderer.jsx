import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  Panel,
  Handle,
  Position,
  BaseEdge,
  EdgeLabelRenderer,
  getStraightPath,
  addEdge,
  reconnectEdge,
  useNodesState,
  useEdgesState,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

import Plot from "react-plotly.js";
import Tree from "react-d3-tree";
import ReactMarkdown from "react-markdown";
import remarkMath from "remark-math";
import '@xyflow/react/dist/style.css';
import rehypeKatex from "rehype-katex";
import "katex/dist/katex.min.css";
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
import { API_URL } from "../api";

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
function ERDiagram({ el }) {
  const {
    entities = [],
    relations = [],
    hidden_cardinalities = false,
    card_type = "min_max",
  } = el ?? {};

  const entityNames = entities.map((e) => e.name);

  const width = 1280;
  const height = Math.max(620, Math.ceil(entityNames.length / 2) * 190 + 120);

  const entityWidth = 190;
  const entityHeight = 76;
  const relationWidth = 132;
  const relationHeight = 78;

  const entityPositions = {};
  entityNames.forEach((name, i) => {
    entityPositions[name] = {
      x: 90 + (i % 2) * 820,
      y: 70 + Math.floor(i / 2) * 180,
    };
  });

  const getRelationValue = (relation, entityName) => {
    if (card_type === "cardinality") {
      return relation?.cardinality?.[entityName] ?? "";
    }
    return relation?.min_max?.[entityName] ?? "";
  };

  const wrapLabel = (text, maxCharsPerLine = 12, maxLines = 3) => {
    const source = String(text ?? "").trim();
    if (!source) return [""];

    const words = source.split(/\s+/);
    const lines = [];
    let current = "";

    for (const word of words) {
      const next = current ? `${current} ${word}` : word;
      if (next.length <= maxCharsPerLine) {
        current = next;
      } else {
        if (current) lines.push(current);
        if (word.length > maxCharsPerLine) {
          lines.push(word.slice(0, maxCharsPerLine));
          current = word.slice(maxCharsPerLine);
        } else {
          current = word;
        }
      }
    }
    if (current) lines.push(current);

    if (lines.length > maxLines) {
      const trimmed = lines.slice(0, maxLines);
      const last = trimmed[maxLines - 1];
      trimmed[maxLines - 1] =
        last.length > maxCharsPerLine - 1
          ? `${last.slice(0, maxCharsPerLine - 1)}…`
          : `${last}…`;
      return trimmed;
    }

    return lines;
  };

  const getLabelFontSize = (lines, base = 20, min = 12) => {
    const longest = Math.max(...lines.map((l) => l.length), 1);
    if (longest <= 10) return base;
    if (longest <= 14) return Math.max(base - 2, min);
    if (longest <= 18) return Math.max(base - 4, min);
    return min;
  };

  const getEntityAnchor = (entityName, targetX, targetY) => {
    const pos = entityPositions[entityName] ?? { x: 0, y: 0 };
    const cx = pos.x + entityWidth / 2;
    const cy = pos.y + entityHeight / 2;
    const dx = targetX - cx;
    const dy = targetY - cy;

    if (Math.abs(dx) > Math.abs(dy)) {
      return dx >= 0
        ? { x: pos.x + entityWidth, y: cy }
        : { x: pos.x, y: cy };
    }

    return dy >= 0
      ? { x: cx, y: pos.y + entityHeight }
      : { x: cx, y: pos.y };
  };

  let relationLayouts = relations.map((relation, idx) => {
    const [leftEntity, rightEntity] = relation.entities ?? ["", ""];
    const leftPos = entityPositions[leftEntity] ?? { x: 0, y: 0 };
    const rightPos = entityPositions[rightEntity] ?? { x: 0, y: 0 };

    const leftCenterX = leftPos.x + entityWidth / 2;
    const leftCenterY = leftPos.y + entityHeight / 2;
    const rightCenterX = rightPos.x + entityWidth / 2;
    const rightCenterY = rightPos.y + entityHeight / 2;

    return {
      relation,
      leftEntity,
      rightEntity,
      x:
        (leftCenterX + rightCenterX) / 2 - relationWidth / 2 + ((idx % 3) - 1) * 10,
      y:
        (leftCenterY + rightCenterY) / 2 -
        relationHeight / 2 +
        ((idx % 4) - 1.5) * 10,
      homeX: (leftCenterX + rightCenterX) / 2 - relationWidth / 2,
      homeY: (leftCenterY + rightCenterY) / 2 - relationHeight / 2,
    };
  });

  const intersects = (a, b, padding = 18) => {
    return !(
      a.x + relationWidth + padding < b.x ||
      b.x + relationWidth + padding < a.x ||
      a.y + relationHeight + padding < b.y ||
      b.y + relationHeight + padding < a.y
    );
  };

  for (let pass = 0; pass < 80; pass++) {
    for (let i = 0; i < relationLayouts.length; i++) {
      for (let j = i + 1; j < relationLayouts.length; j++) {
        const a = relationLayouts[i];
        const b = relationLayouts[j];

        if (!intersects(a, b)) continue;

        const ax = a.x + relationWidth / 2;
        const ay = a.y + relationHeight / 2;
        const bx = b.x + relationWidth / 2;
        const by = b.y + relationHeight / 2;

        let dx = ax - bx;
        let dy = ay - by;

        if (dx === 0 && dy === 0) {
          dx = 1;
          dy = 1;
        }

        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const push = 8;

        const px = (dx / dist) * push;
        const py = (dy / dist) * push;

        a.x += px;
        a.y += py;
        b.x -= px;
        b.y -= py;
      }
    }

    relationLayouts = relationLayouts.map((r) => {
      const spring = 0.06;
      const nx = r.x + (r.homeX - r.x) * spring;
      const ny = r.y + (r.homeY - r.y) * spring;

      return {
        ...r,
        x: Math.max(250, Math.min(width - 250, nx)),
        y: Math.max(25, Math.min(height - 25 - relationHeight, ny)),
      };
    });
  }

  relationLayouts = relationLayouts.map((item) => {
    const diamondCenter = {
      x: item.x + relationWidth / 2,
      y: item.y + relationHeight / 2,
    };

    const start = getEntityAnchor(
      item.leftEntity,
      diamondCenter.x,
      diamondCenter.y
    );
    const end = getEntityAnchor(
      item.rightEntity,
      diamondCenter.x,
      diamondCenter.y
    );

    return {
      ...item,
      start,
      end,
      diamondCenter,
      leftCard: getRelationValue(item.relation, item.leftEntity),
      rightCard: getRelationValue(item.relation, item.rightEntity),
    };
  });

  return (
    <div className="mb-4 border rounded p-2 bg-light overflow-auto">
      <svg width={width} height={height} style={{ minWidth: width }}>
        {relationLayouts.map((item, idx) => {
          const {
            relation,
            start,
            end,
            diamondCenter,
            x,
            y,
            leftCard,
            rightCard,
          } = item;

          const diamondPoints = [
            `${x + relationWidth / 2},${y}`,
            `${x + relationWidth},${y + relationHeight / 2}`,
            `${x + relationWidth / 2},${y + relationHeight}`,
            `${x},${y + relationHeight / 2}`,
          ].join(" ");

          const relationLines = wrapLabel(relation.name, 12, 2);
          const relationFontSize = getLabelFontSize(relationLines, 19, 12);

          return (
            <g key={`${relation.name}-${idx}`}>
              <line
                x1={start.x}
                y1={start.y}
                x2={diamondCenter.x}
                y2={diamondCenter.y}
                stroke="#5b4636"
                strokeWidth="2"
              />
              <line
                x1={diamondCenter.x}
                y1={diamondCenter.y}
                x2={end.x}
                y2={end.y}
                stroke="#5b4636"
                strokeWidth="2"
              />

              {!hidden_cardinalities && (
                <>
                  <text
                    x={start.x + (diamondCenter.x - start.x) * 0.34}
                    y={start.y + (diamondCenter.y - start.y) * 0.34 - 6}
                    textAnchor="middle"
                    fill="#d9534f"
                    fontWeight="bold"
                    fontSize="18"
                  >
                    {leftCard}
                  </text>
                  <text
                    x={end.x + (diamondCenter.x - end.x) * 0.34}
                    y={end.y + (diamondCenter.y - end.y) * 0.34 - 6}
                    textAnchor="middle"
                    fill="#d9534f"
                    fontWeight="bold"
                    fontSize="18"
                  >
                    {rightCard}
                  </text>
                </>
              )}

              <polygon
                points={diamondPoints}
                fill="#f6a623"
                stroke="#333"
                strokeWidth="2"
              />

              <text
                x={diamondCenter.x}
                y={
                  diamondCenter.y -
                  ((relationLines.length - 1) * relationFontSize * 0.6)
                }
                textAnchor="middle"
                fontWeight="bold"
                fontSize={relationFontSize}
              >
                {relationLines.map((line, lineIdx) => (
                  <tspan
                    key={lineIdx}
                    x={diamondCenter.x}
                    dy={lineIdx === 0 ? 0 : relationFontSize + 1}
                  >
                    {line}
                  </tspan>
                ))}
              </text>
            </g>
          );
        })}

        {entityNames.map((name, idx) => {
          const pos = entityPositions[name];
          const entityLines = wrapLabel(name, 14, 2);
          const entityFontSize = getLabelFontSize(entityLines, 20, 12);

          return (
            <g key={`${name}-${idx}`}>
              <rect
                x={pos.x}
                y={pos.y}
                rx="4"
                ry="4"
                width={entityWidth}
                height={entityHeight}
                fill="#97c95c"
                stroke="#333"
                strokeWidth="2"
              />
              <text
                x={pos.x + entityWidth / 2}
                y={
                  pos.y +
                  entityHeight / 2 -
                  ((entityLines.length - 1) * entityFontSize * 0.6)
                }
                textAnchor="middle"
                fontStyle="italic"
                fontWeight="bold"
                fontSize={entityFontSize}
              >
                {entityLines.map((line, lineIdx) => (
                  <tspan
                    key={lineIdx}
                    x={pos.x + entityWidth / 2}
                    dy={lineIdx === 0 ? 0 : entityFontSize + 1}
                  >
                    {line}
                  </tspan>
                ))}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

function ERDiagramInput({ el, renderEvaluatedInput }) {
  const {
    entities = [],
    relations = [],
    card_type = "min_max",
  } = el ?? {};

  const entityNames = entities.map((e) => e.name);

  const width = 1200;
  const height = Math.max(500, entityNames.length * 90);

  const entityWidth = 170;
  const entityHeight = 70;
  const relationWidth = 110;
  const relationHeight = 70;

  const selectOptions =
    card_type === "cardinality"
      ? ["1", "n", "m"]
      : ["0..1", "1..1", "0..*", "1..*"];

  const entityPositions = {};
  entityNames.forEach((name, i) => {
    entityPositions[name] = {
      x: 80 + (i % 2) * 760,
      y: 60 + Math.floor(i / 2) * 160,
    };
  });

  const makeFieldId = (relationName, leftEntity, rightEntity, entityName) =>
    `${relationName}__${leftEntity}__${rightEntity}__${entityName}`;

  const getEntityAnchor = (entityName, sideHint = "right") => {
    const pos = entityPositions[entityName] ?? { x: 0, y: 0 };
    if (sideHint === "left") {
      return {
        x: pos.x,
        y: pos.y + entityHeight / 2,
      };
    }
    return {
      x: pos.x + entityWidth,
      y: pos.y + entityHeight / 2,
    };
  };

  const relationLayouts = relations.map((relation, idx) => {
    const [leftEntity, rightEntity] = relation.entities ?? ["", ""];
    const leftPos = entityPositions[leftEntity] ?? { x: 0, y: 0 };
    const rightPos = entityPositions[rightEntity] ?? { x: 0, y: 0 };

    const leftCenterX = leftPos.x + entityWidth / 2;
    const leftCenterY = leftPos.y + entityHeight / 2;
    const rightCenterX = rightPos.x + entityWidth / 2;
    const rightCenterY = rightPos.y + entityHeight / 2;

    const relX = (leftCenterX + rightCenterX) / 2 - relationWidth / 2;
    const relY = (leftCenterY + rightCenterY) / 2 - relationHeight / 2 + (idx % 2) * 12;

    const leftSide = leftCenterX < rightCenterX ? "right" : "left";
    const rightSide = leftCenterX < rightCenterX ? "left" : "right";

    const start = getEntityAnchor(leftEntity, leftSide);
    const end = getEntityAnchor(rightEntity, rightSide);

    const diamondCenter = {
      x: relX + relationWidth / 2,
      y: relY + relationHeight / 2,
    };

    return {
      relation,
      leftEntity,
      rightEntity,
      relX,
      relY,
      start,
      end,
      diamondCenter,
      leftFieldId: makeFieldId(relation.name, leftEntity, rightEntity, leftEntity),
      rightFieldId: makeFieldId(relation.name, leftEntity, rightEntity, rightEntity),
      leftInputX: (start.x + diamondCenter.x) / 2 - 55,
      leftInputY: (start.y + diamondCenter.y) / 2 - 18,
      rightInputX: (end.x + diamondCenter.x) / 2 - 55,
      rightInputY: (end.y + diamondCenter.y) / 2 - 18,
    };
  });

  return (
    <div
      className="mb-4 border rounded p-2 bg-light overflow-auto position-relative"
      style={{ minHeight: height + 20 }}
    >
      <svg
        width={width}
        height={height}
        style={{ minWidth: width, display: "block" }}
      >
        {relationLayouts.map((item, idx) => {
          const {
            relation,
            start,
            end,
            diamondCenter,
            relX,
            relY,
          } = item;

          const diamondPoints = [
            `${relX + relationWidth / 2},${relY}`,
            `${relX + relationWidth},${relY + relationHeight / 2}`,
            `${relX + relationWidth / 2},${relY + relationHeight}`,
            `${relX},${relY + relationHeight / 2}`,
          ].join(" ");

          return (
            <g key={`${relation.name}-${idx}`}>
              <line
                x1={start.x}
                y1={start.y}
                x2={diamondCenter.x}
                y2={diamondCenter.y}
                stroke="#5b4636"
                strokeWidth="2"
              />
              <line
                x1={diamondCenter.x}
                y1={diamondCenter.y}
                x2={end.x}
                y2={end.y}
                stroke="#5b4636"
                strokeWidth="2"
              />

              <polygon
                points={diamondPoints}
                fill="#f6a623"
                stroke="#333"
                strokeWidth="2"
              />
              <text
                x={diamondCenter.x}
                y={diamondCenter.y + 6}
                textAnchor="middle"
                fontWeight="bold"
                fontSize="20"
              >
                {relation.name}
              </text>
            </g>
          );
        })}

        {entityNames.map((name, idx) => {
          const pos = entityPositions[name];
          return (
            <g key={`${name}-${idx}`}>
              <rect
                x={pos.x}
                y={pos.y}
                width={entityWidth}
                height={entityHeight}
                fill="#97c95c"
                stroke="#333"
                strokeWidth="2"
              />
              <text
                x={pos.x + entityWidth / 2}
                y={pos.y + entityHeight / 2 + 7}
                textAnchor="middle"
                fontStyle="italic"
                fontWeight="bold"
                fontSize="20"
              >
                {name}
              </text>
            </g>
          );
        })}
      </svg>

      {relationLayouts.map((item, idx) => (
        <div key={`inputs-${idx}`}>
          <div
            style={{
              position: "absolute",
              left: item.leftInputX,
              top: item.leftInputY,
              width: 110,
            }}
          >
            {renderEvaluatedInput(item.leftFieldId, "", {
              variant: "select",
              selectOptions,
              placeholder: card_type === "cardinality" ? "1/n/m" : "min-max",
            })}
          </div>

          <div
            style={{
              position: "absolute",
              left: item.rightInputX,
              top: item.rightInputY,
              width: 110,
            }}
          >
            {renderEvaluatedInput(item.rightFieldId, "", {
              variant: "select",
              selectOptions,
              placeholder: card_type === "cardinality" ? "1/n/m" : "min-max",
            })}
          </div>
        </div>
      ))}
    </div>
  );
}
/* ---------------- NODE COMPONENTS ---------------- */

function EntityNode({ id, data }) {
  return (
    <div
      style={{
        minWidth: 190,
        border: "2px solid #333",
        borderRadius: 6,
        background: "#97c95c",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        position: "relative",
        padding: "20px 12px",
      }}
    >
      {/* relation targets: always visible, yellow */}
      <Handle
        id="relation-left"
        type="target"
        position={Position.Left}
        isConnectableStart={false}
        isConnectableEnd={true}
        style={{
          width: 14,
          height: 14,
          borderRadius: "50%",
          background: "#f6a623",
          border: "1px solid #333",
          left: -10,
          top: "50%",
          transform: "translateY(-50%)",
          zIndex: 5,
        }}
      />

      <Handle
        id="relation-right"
        type="target"
        position={Position.Right}
        isConnectableStart={false}
        isConnectableEnd={true}
        style={{
          width: 14,
          height: 14,
          borderRadius: "50%",
          background: "#f6a623",
          border: "1px solid #333",
          right: -10,
          top: "50%",
          transform: "translateY(-50%)",
          zIndex: 5,
        }}
      />

      {/* single attribute target on top, blue */}
      <Handle
        id="attribute-top"
        type="target"
        position={Position.Top}
        isConnectableStart={false}
        isConnectableEnd={true}
        style={{
          width: 14,
          height: 14,
          borderRadius: "50%",
          background: "#cfe2ff",
          border: "1px solid #333",
          top: -10,
          left: "50%",
          transform: "translateX(-50%)",
          zIndex: 5,
        }}
      />

      <input
        value={data.label}
        onChange={(e) => data.onLabelChange(id, e.target.value)}
        onKeyDown={(e) => e.stopPropagation()}
        onPointerDown={(e) => e.stopPropagation()}
        style={{
          border: "none",
          background: "transparent",
          textAlign: "center",
          fontWeight: "bold",
          width: "100%",
          outline: "none",
        }}
      />
    </div>
  );
}

function RelationNode({ id, data }) {
  return (
    <div
      style={{
        width: 140,
        height: 120,
        position: "relative",
      }}
    >
      <Handle
        id="left"
        type="source"
        position={Position.Left}
        isConnectableStart={true}
        isConnectableEnd={false}
        style={{
          width: 14,
          height: 14,
          borderRadius: "50%",
          background: "#f6a623",
          border: "1px solid #333",
          left: -10,
          top: 48,
          transform: "none",
          zIndex: 5,
        }}
      />

      <Handle
        id="right"
        type="source"
        position={Position.Right}
        isConnectableStart={true}
        isConnectableEnd={false}
        style={{
          width: 14,
          height: 14,
          borderRadius: "50%",
          background: "#f6a623",
          border: "1px solid #333",
          right: -10,
          top: 48,
          transform: "none",
          zIndex: 5,
        }}
      />

      {/* attribute target on top */}
      <Handle
        id="attribute-top"
        type="target"
        position={Position.Top}
        isConnectableStart={false}
        isConnectableEnd={true}
        style={{
          width: 14,
          height: 14,
          borderRadius: "50%",
          background: "#cfe2ff",
          border: "1px solid #333",
          top: -25,
          left: "50%",
          transform: "translateX(-50%)",
          zIndex: 5,
        }}
      />

      <div
        style={{
          width: 110,
          height: 110,
          margin: "0 auto",
          transform: "rotate(45deg)",
          background: "#f6a623",
          border: "2px solid #333",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <div style={{ transform: "rotate(-45deg)" }}>
          <input
            value={data.label}
            onChange={(e) => data.onLabelChange(id, e.target.value)}
            onKeyDown={(e) => e.stopPropagation()}
            onPointerDown={(e) => e.stopPropagation()}
            style={{
              border: "none",
              background: "transparent",
              textAlign: "center",
              fontWeight: "bold",
              outline: "none",
            }}
          />
        </div>
      </div>
    </div>
  );
}

function AttributeNode({ id, data }) {
  return (
    <div
      onDoubleClick={(e) => {
        e.stopPropagation();
        data.onToggleKey(id);
      }}
      style={{
        minWidth: 150,
        minHeight: 70,
        border: "2px solid #333",
        borderRadius: "50%",
        background: "#cfe2ff",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        position: "relative",
        padding: "14px 18px",
        cursor: "default",
        userSelect: "none",
      }}
    >
      <Handle
        id="attribute-source"
        type="source"
        position={Position.Bottom}
        isConnectableStart={true}
        isConnectableEnd={false}
        style={{
          width: 14,
          height: 14,
          borderRadius: "50%",
          background: "#cfe2ff",
          border: "1px solid #333",
          bottom: -10,
          left: "50%",
          transform: "translateX(-50%)",
          zIndex: 5,
        }}
      />

      <input
        value={data.label}
        onChange={(e) => data.onLabelChange(id, e.target.value)}
        onDoubleClick={(e) => {
          e.stopPropagation();
          data.onToggleKey(id);
        }}
        onKeyDown={(e) => e.stopPropagation()}
        onPointerDown={(e) => e.stopPropagation()}
        style={{
          border: "none",
          background: "transparent",
          textAlign: "center",
          outline: "none",
          width: "100%",
          fontWeight: data.isKey ? "bold" : "normal",
          textDecoration: data.isKey ? "underline" : "none",
        }}
      />
    </div>
  );
}

/* ---------------- EDGE COMPONENT ---------------- */

function ERValueEdge(props) {
  const { id, sourceX, sourceY, targetX, targetY, data } = props;
  const [path] = getStraightPath({ sourceX, sourceY, targetX, targetY });

  const dx = sourceX - targetX;
  const dy = sourceY - targetY;
  const dist = Math.sqrt(dx * dx + dy * dy) || 1;
  const px = -dy / dist;
  const py = dx / dist;

  const ratioFromTarget = 0.55;
  const offset = 12;

  const labelX = targetX + (sourceX - targetX) * ratioFromTarget + px * offset;
  const labelY = targetY + (sourceY - targetY) * ratioFromTarget + py * offset;

  return (
    <>
      <BaseEdge path={path} style={{ stroke: "#555", strokeWidth: 2 }} />

      {data?.showLabel && (
        <EdgeLabelRenderer>
          <div
            style={{
              position: "absolute",
              transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
              pointerEvents: "all",
              zIndex: 1000,
              background: "#fff",
              padding: "2px 4px",
              border: "1px solid #ccc",
              borderRadius: 6,
              minWidth: 0,
            }}
          >
            <input
              type="text"
              value={data.value ?? ""}
              placeholder="1..n"
              maxLength={10}
              onChange={(e) => data.onValueChange(id, e.target.value)}
              onKeyDown={(e) => e.stopPropagation()}
              onPointerDown={(e) => e.stopPropagation()}
              style={{
                width: 56,
                minWidth: 56,
                height: 24,
                border: "1px solid #ccc",
                borderRadius: 4,
                fontSize: 12,
                padding: "1px 4px",
                textAlign: "center",
                outline: "none",
              }}
            />
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  );
}

/* ---------------- MAIN COMPONENT ---------------- */

function ERDiagramBuilder({ el, idx, onChange }) {
  const id = el.id || `er_builder_${idx}`;
  const relationFieldId = `${id}:relations`;
  const lastExport = useRef("");

  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  const getNode = useCallback(
    (nodeId) => nodes.find((n) => n.id === nodeId),
    [nodes]
  );
  const toggleAttributeKey = useCallback((nodeId) => {
    setNodes((nds) =>
      nds.map((n) =>
        n.id === nodeId && n.type === "attribute"
          ? {
              ...n,
              data: {
                ...n.data,
                isKey: !n.data?.isKey,
              },
            }
          : n
      )
    );
  }, [setNodes]);
  const updateNodeLabel = useCallback((nodeId, value) => {
    setNodes((nds) =>
      nds.map((n) =>
        n.id === nodeId ? { ...n, data: { ...n.data, label: value } } : n
      )
    );
  }, [setNodes]);

  const updateEdgeValue = useCallback((edgeId, value) => {
    setEdges((eds) =>
      eds.map((e) =>
        e.id === edgeId
          ? { ...e, data: { ...e.data, value } }
          : e
      )
    );
  }, [setEdges]);

  const removeSelected = useCallback(() => {
    const selectedNodeIds = new Set(
      nodes.filter((n) => n.selected).map((n) => n.id)
    );
    const selectedEdgeIds = new Set(
      edges.filter((e) => e.selected).map((e) => e.id)
    );

    setEdges((eds) =>
      eds.filter(
        (e) =>
          !selectedEdgeIds.has(e.id) &&
          !selectedNodeIds.has(e.source) &&
          !selectedNodeIds.has(e.target)
      )
    );

    setNodes((nds) => nds.filter((n) => !selectedNodeIds.has(n.id)));
  }, [nodes, edges, setEdges, setNodes]);

  useEffect(() => {
    const isTypingElement = (target) => {
      if (!target) return false;
      const tag = target.tagName?.toLowerCase();
      return (
        tag === "input" ||
        tag === "textarea" ||
        tag === "select" ||
        target.isContentEditable
      );
    };

    const onKeyDown = (e) => {
      if (e.key !== "Backspace" && e.key !== "Delete") return;
      if (isTypingElement(document.activeElement)) return;
      e.preventDefault();
      removeSelected();
    };

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [removeSelected]);

  const validateConnection = useCallback(
    (connection, ignoreEdgeId = null) => {
      const { source, target, sourceHandle, targetHandle } = connection;
      const s = getNode(source);
      const t = getNode(target);

      if (!s || !t) return false;
      if (s.id === t.id) return false;

      const relevantEdges = edges.filter((e) => e.id !== ignoreEdgeId);

      // relation -> entity
      if (s.type === "relation" && t.type === "entity") {
        if (!["left", "right"].includes(sourceHandle)) return false;
        if (!["relation-left", "relation-right"].includes(targetHandle)) {
          return false;
        }

        const relationEdges = relevantEdges.filter((e) => e.source === source);

        if (relationEdges.some((e) => e.sourceHandle === sourceHandle)) {
          return false;
        }

        // intentionally allow both sides of one relation to connect
        // to the same entity, as requested
        return true;
      }

      // attribute -> entity or relation
      if (s.type === "attribute" && (t.type === "entity" || t.type === "relation")) {
        if (sourceHandle !== "attribute-source") return false;
        if (targetHandle !== "attribute-top") return false;

        const attributeEdges = relevantEdges.filter((e) => e.source === source);
        if (attributeEdges.length >= 1) return false;

        return true;
      }

      return false;
    },
    [edges, getNode]
  );

  const onConnect = useCallback(
    (connection) => {
      if (!validateConnection(connection)) return;

      const sourceNode = getNode(connection.source);
      const showLabel = sourceNode?.type === "relation";

      setEdges((eds) =>
        addEdge(
          {
            ...connection,
            type: "erValueEdge",
            data: {
              value: "",
              showLabel,
              onValueChange: updateEdgeValue,
            },
          },
          eds
        )
      );
    },
    [validateConnection, getNode, updateEdgeValue, setEdges]
  );

  const onReconnect = useCallback(
    (oldEdge, newConnection) => {
      if (!validateConnection(newConnection, oldEdge.id)) return;

      setEdges((eds) =>
        reconnectEdge(
          oldEdge,
          {
            ...newConnection,
            type: oldEdge.type,
            data: oldEdge.data,
          },
          eds
        )
      );
    },
    [validateConnection, setEdges]
  );

  const addEntity = useCallback(() => {
    setNodes((nds) => {
      const count = nds.filter((n) => n.type === "entity").length + 1;
      return [
        ...nds,
        {
          id: `entity_${crypto.randomUUID()}`,
          type: "entity",
          position: { x: 100 + count * 40, y: 80 + count * 30 },
          data: {
            label: `ENTITY_${count}`,
            onLabelChange: updateNodeLabel,
          },
        },
      ];
    });
  }, [setNodes, updateNodeLabel]);

  const addRelation = useCallback(() => {
    setNodes((nds) => {
      const count = nds.filter((n) => n.type === "relation").length + 1;
      return [
        ...nds,
        {
          id: `relation_${crypto.randomUUID()}`,
          type: "relation",
          position: { x: 350 + count * 40, y: 220 + count * 30 },
          data: {
            label: `relation_${count}`,
            onLabelChange: updateNodeLabel,
          },
        },
      ];
    });
  }, [setNodes, updateNodeLabel]);

  const addAttribute = useCallback(() => {
    setNodes((nds) => {
      const count = nds.filter((n) => n.type === "attribute").length + 1;
      return [
        ...nds,
        {
          id: `attribute_${crypto.randomUUID()}`,
          type: "attribute",
          position: { x: 180 + count * 35, y: 420 + count * 25 },
          data: {
            label: `attribute_${count}`,
            isKey: false,
            onLabelChange: updateNodeLabel,
            onToggleKey: toggleAttributeKey,
          },
        },
      ];
    });
  }, [setNodes, updateNodeLabel, toggleAttributeKey]);

  useEffect(() => {
    setNodes((nds) =>
      nds.map((n) => ({
        ...n,
        data: {
          ...n.data,
          onLabelChange: updateNodeLabel,
          ...(n.type === "attribute" ? { onToggleKey: toggleAttributeKey } : {}),
        },
      }))
    );

    setEdges((eds) =>
      eds.map((e) => ({
        ...e,
        data: {
          ...e.data,
          onValueChange: updateEdgeValue,
        },
      }))
    );
  }, [updateNodeLabel, updateEdgeValue, toggleAttributeKey, setNodes, setEdges]);

  useEffect(() => {
    const relations = nodes
      .filter((n) => n.type === "relation")
      .map((rel) => {
        const rEdges = edges.filter((e) => e.source === rel.id);

        return {
          id: rel.id,
          name: rel.data.label,
          connections: rEdges.map((e) => {
            const entity = getNode(e.target);
            return {
              entity_id: e.target,
              entity_name: entity?.data?.label || e.target,
              relation_handle: e.sourceHandle,
              entity_handle: e.targetHandle,
              value: e.data?.value ?? "",
            };
          }),
        };
      });

    const attributes = nodes
      .filter((n) => n.type === "attribute")
      .map((attr) => {
        const edge = edges.find((e) => e.source === attr.id);
        const owner = edge ? getNode(edge.target) : null;

        return {
          id: attr.id,
          name: attr.data.label,
          is_key: !!attr.data.isKey,
          owner_id: edge?.target ?? null,
          owner_name: owner?.data?.label ?? null,
          owner_type: owner?.type ?? null,
        };
      });
    const json = JSON.stringify({
      relations,
      attributes,
    });

    if (json === lastExport.current) return;
    lastExport.current = json;
    onChange(relationFieldId, json);
  }, [nodes, edges, getNode, onChange, relationFieldId]);

  const nodeTypes = useMemo(
    () => ({
      entity: EntityNode,
      relation: RelationNode,
      attribute: AttributeNode,
    }),
    []
  );

  const edgeTypes = useMemo(
    () => ({
      erValueEdge: ERValueEdge,
    }),
    []
  );

  return (
    <div className="card mb-4 shadow-sm">
      <div className="card-body">
        <div
          className="border rounded"
          style={{ width: "100%", height: 700, background: "#fafafa" }}
        >
          <ReactFlow
            nodes={nodes}
            edges={edges}
            nodeTypes={nodeTypes}
            edgeTypes={edgeTypes}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onReconnect={onReconnect}
            fitView
            deleteKeyCode={null}
          >
            <Background />
            <Controls />
            <MiniMap />

            <Panel position="top-left">
              <div className="d-flex flex-column gap-2">
                <button className="btn btn-sm btn-primary" onClick={addEntity}>
                  Add Entity
                </button>

                <button className="btn btn-sm btn-warning" onClick={addRelation}>
                  Add Relation
                </button>

                <button className="btn btn-sm btn-info" onClick={addAttribute}>
                  Add Attribute
                </button>

                <button
                  className="btn btn-sm btn-outline-danger"
                  onClick={removeSelected}
                >
                  Delete Selected
                </button>
              </div>
            </Panel>
          </ReactFlow>
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

function PdfViewerSection({ title, src, height = 700, defaultOpen = false }) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className="card mb-4 shadow-sm">
      <button
        type="button"
        className="btn btn-link w-100 text-start d-flex justify-content-between align-items-center px-3 py-2"
        onClick={() => setIsOpen((v) => !v)}
        style={{ textDecoration: "none" }}
      >
        <span className="fw-semibold">{title || "Schema (PDF)"}</span>
        <span className="ms-2">{isOpen ? "▾" : "▸"}</span>
      </button>

      {isOpen && (
        <div className="card-body pt-2">
          <iframe
            src={src}
            title={title || "Schema PDF"}
            style={{ width: "100%", height: `${height}px`, border: "1px solid #dee2e6", borderRadius: "0.375rem" }}
          />
          <div className="mt-2">
            <a href={src} target="_blank" rel="noreferrer">PDF in neuem Tab öffnen</a>
          </div>
        </div>
      )}
    </div>
  );
}

function AprioriBuilderCore({
  title,
  description,
  fieldId,
  userInput,
  onChange,
  evaluationResults,
  showExpected,
  registerFieldId,
  singleLevel = false,
  initialRows = 1,
  baseLevel = 1,
}) {
  const emptyRow = () => ({ itemset: "", support: "", probability: "", belowMinsup: false });
  const makeLevel = () => ({ rows: Array.from({ length: initialRows }, emptyRow), terminate: false });

  const parseStored = (raw) => {
    try {
      const parsed = raw ? (typeof raw === "string" ? JSON.parse(raw) : raw) : null;
      if (singleLevel && parsed && Array.isArray(parsed.rows)) return parsed;
      if (!singleLevel && parsed && Array.isArray(parsed.levels) && parsed.levels.length > 0) return parsed;
    } catch (_err) {
      // fallback below
    }
    return singleLevel ? makeLevel() : { levels: [makeLevel()] };
  };

  const [builder, setBuilder] = useState(() => parseStored(userInput?.[fieldId]));

  useEffect(() => {
    onChange(fieldId, JSON.stringify(builder));
  }, [builder, fieldId, onChange]);

  const levels = singleLevel ? [builder] : (builder.levels || []);

  const setLevels = (nextLevels) => {
    if (singleLevel) {
      setBuilder(nextLevels[0] || makeLevel());
    } else {
      setBuilder((prev) => ({ ...prev, levels: nextLevels }));
    }
  };

  const updateLevel = (levelIdx, updater) => {
    const nextLevels = [...levels];
    const current = { ...(nextLevels[levelIdx] || makeLevel()) };
    updater(current);
    nextLevels[levelIdx] = current;
    setLevels(nextLevels);
  };

  const addLevel = () => setLevels([...levels, makeLevel()]);

  const removeLevel = (levelIdx) => {
    const remaining = levels.filter((_, i) => i !== levelIdx);
    setLevels(remaining.length > 0 ? remaining : [makeLevel()]);
  };

  const addRow = (levelIdx) => updateLevel(levelIdx, (level) => {
    level.rows = [...(level.rows || []), emptyRow()];
  });

  const removeRow = (levelIdx, rowIdx) => updateLevel(levelIdx, (level) => {
    level.rows = [...(level.rows || [])].filter((_, i) => i !== rowIdx);
  });

  const updateRowField = (levelIdx, rowIdx, key, value) => updateLevel(levelIdx, (level) => {
    const rows = [...(level.rows || [])];
    rows[rowIdx] = { ...(rows[rowIdx] || {}), [key]: value };
    level.rows = rows;
  });

  const updateTerminate = (levelIdx, checked) => updateLevel(levelIdx, (level) => {
    level.terminate = checked;
  });

  const evalResult = evaluationResults?.[fieldId] ?? evaluationResults?.[`${fieldId}_solution`];
  const isCorrect = evalResult?.correct;
  const expected = evalResult?.expected;
  const feedbackClass = evalResult === undefined ? "" : isCorrect ? "alert alert-success" : "alert alert-danger";
  const solutionExpected =
    expected && typeof expected === "object" && !Array.isArray(expected)
      ? expected
      : (() => {
          const fallback = evaluationResults?.[`${fieldId}_solution`]?.expected;
          return fallback && typeof fallback === "object" && !Array.isArray(fallback) ? fallback : null;
        })();
  const hasStructuredExpected = !!solutionExpected;

  const rowFieldId = (levelIdx, rowIdx, key) =>
    singleLevel ? `${fieldId}_r${rowIdx}_${key}` : `${fieldId}_l${levelIdx}_r${rowIdx}_${key}`;

  const registerLocalField = (id) => {
    if (typeof registerFieldId === "function") registerFieldId(String(id));
  };

  registerLocalField(fieldId);
  registerLocalField(`${fieldId}_solution`);

  const getCellEval = (id) => {
    registerLocalField(id);
    return evaluationResults?.[id];
  };

  const evalClass = (id) => {
    const r = getCellEval(id);
    if (r === undefined) return "";
    return r.correct ? "is-valid" : "is-invalid";
  };

  const evalTitle = (id) => {
    const r = getCellEval(id);
    if (!r || r.correct || r.expected === undefined) return "";
    return `Expected: ${r.expected}`;
  };

  const renderExpectedHint = (id) => {
    const r = getCellEval(id);
    if (!showExpected || !r || r.correct || r.expected === undefined) return null;
    return <small className="text-muted fst-italic d-block mt-1">Correct: {r.expected}</small>;
  };

  return (
    <div className="card mb-4 shadow-sm">
      <div className="card-body">
        <h5 className="card-title mb-3">{title}</h5>
        <p className="text-muted mb-3">{description}</p>

        {levels.map((level, levelIdx) => {
          const rows = level?.rows || [];
          const shownLevel = singleLevel ? Number(baseLevel || 1) : levelIdx + 1;
          return (
            <div key={`apr-level-${fieldId}-${levelIdx}`} className="border rounded p-3 mb-3 bg-light-subtle">
              {!singleLevel && (
                <div className="d-flex justify-content-between align-items-center mb-2">
                  <h6 className="mb-0">Level {shownLevel}</h6>
                  <button type="button" className="btn btn-sm btn-outline-danger" onClick={() => removeLevel(levelIdx)}>
                    Level entfernen
                  </button>
                </div>
              )}

              <div className="row g-3">
                <div className="col-12 col-lg-6">
                  <div className="fw-semibold mb-2">C{shownLevel}</div>
                  <div className="table-responsive">
                    <table className="table table-bordered table-sm align-middle mb-2">
                      <thead className="table-light">
                        <tr>
                          <th>Itemset</th>
                          <th>Support</th>
                          <th style={{ width: 48 }} />
                        </tr>
                      </thead>
                      <tbody>
                        {rows.map((row, rowIdx) => (
                          <tr key={`c-${fieldId}-${levelIdx}-${rowIdx}`}>
                            <td>
                              {(() => {
                                const id = rowFieldId(levelIdx, rowIdx, "itemset");
                                return (
                                  <>
                                    <input
                                      type="text"
                                      className={`form-control form-control-sm ${evalClass(id)}`}
                                      value={row?.itemset || ""}
                                      onChange={(e) => updateRowField(levelIdx, rowIdx, "itemset", e.target.value)}
                                      title={evalTitle(id)}
                                    />
                                    {renderExpectedHint(id)}
                                  </>
                                );
                              })()}
                            </td>
                            <td>
                              {(() => {
                                const id = rowFieldId(levelIdx, rowIdx, "support");
                                return (
                                  <>
                                    <input
                                      type="text"
                                      className={`form-control form-control-sm ${evalClass(id)}`}
                                      value={row?.support || ""}
                                      onChange={(e) => updateRowField(levelIdx, rowIdx, "support", e.target.value)}
                                      title={evalTitle(id)}
                                    />
                                    {renderExpectedHint(id)}
                                  </>
                                );
                              })()}
                            </td>
                            <td>
                              <button
                                type="button"
                                className="btn btn-sm btn-outline-danger"
                                onClick={() => removeRow(levelIdx, rowIdx)}
                              >
                                x
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <button type="button" className="btn btn-sm btn-outline-primary" onClick={() => addRow(levelIdx)}>
                    + Zeile in C{shownLevel}
                  </button>
                </div>

                <div className="col-12 col-lg-6">
                  <div className="fw-semibold mb-2">L{shownLevel}</div>
                  <div className="table-responsive">
                    <table className="table table-bordered table-sm align-middle mb-2">
                      <thead className="table-light">
                        <tr>
                          <th>Itemset</th>
                          <th>Support</th>
                          <th>P</th>
                          <th>fällt unter minsup?</th>
                        </tr>
                      </thead>
                      <tbody>
                        {rows.map((row, rowIdx) => (
                          <tr key={`l-${fieldId}-${levelIdx}-${rowIdx}`}>
                            <td>
                              {(() => {
                                const id = rowFieldId(levelIdx, rowIdx, "itemset");
                                return (
                                  <input
                                    type="text"
                                    className={`form-control form-control-sm ${evalClass(id)}`}
                                    value={row?.itemset || ""}
                                    readOnly
                                    title={evalTitle(id)}
                                  />
                                );
                              })()}
                            </td>
                            <td>
                              {(() => {
                                const id = rowFieldId(levelIdx, rowIdx, "support");
                                return (
                                  <input
                                    type="text"
                                    className={`form-control form-control-sm ${evalClass(id)}`}
                                    value={row?.support || ""}
                                    readOnly
                                    title={evalTitle(id)}
                                  />
                                );
                              })()}
                            </td>
                            <td>
                              {(() => {
                                const id = rowFieldId(levelIdx, rowIdx, "probability");
                                return (
                                  <>
                                    <input
                                      type="text"
                                      className={`form-control form-control-sm ${evalClass(id)}`}
                                      value={row?.probability || ""}
                                      onChange={(e) => updateRowField(levelIdx, rowIdx, "probability", e.target.value)}
                                      title={evalTitle(id)}
                                    />
                                    {renderExpectedHint(id)}
                                  </>
                                );
                              })()}
                            </td>
                            <td className="text-center">
                              {(() => {
                                const id = rowFieldId(levelIdx, rowIdx, "belowMinsup");
                                return (
                                <input
                                  className={`form-check-input ${evalClass(id)}`}
                                  type="checkbox"
                                  checked={!!row?.belowMinsup}
                                  onChange={(e) => updateRowField(levelIdx, rowIdx, "belowMinsup", e.target.checked)}
                                  title={evalTitle(id)}
                                />
                                );
                              })()}
                              {renderExpectedHint(rowFieldId(levelIdx, rowIdx, "belowMinsup"))}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>

              {!singleLevel && (
                <div className="form-check mt-3">
                  {(() => {
                    const termFieldId = `${fieldId}_l${levelIdx}_terminate`;
                    return (
                      <>
                  <input
                    className={`form-check-input ${evalClass(termFieldId)}`}
                    type="checkbox"
                    id={`terminate-${fieldId}-${levelIdx}`}
                    checked={!!level.terminate}
                    onChange={(e) => updateTerminate(levelIdx, e.target.checked)}
                    title={evalTitle(termFieldId)}
                  />
                      {renderExpectedHint(termFieldId)}
                      </>
                    );
                  })()}
                  <label className="form-check-label" htmlFor={`terminate-${fieldId}-${levelIdx}`}>
                    Algorithmus terminiert nach Level {shownLevel}
                  </label>
                </div>
              )}
            </div>
          );
        })}

        {!singleLevel && (
          <button type="button" className="btn btn-outline-success" onClick={addLevel}>
            + Level hinzufügen
          </button>
        )}

        {evalResult !== undefined && (
          <div className={`mt-3 py-2 px-3 rounded ${feedbackClass}`}>
            {isCorrect ? "Eingabe korrekt." : "Eingabe nicht korrekt."}
          </div>
        )}
        {showExpected && evalResult !== undefined && !isCorrect && expected !== undefined && !hasStructuredExpected && (
          <small className="text-muted fst-italic d-block mt-1">Correct: {expected}</small>
        )}

        {showExpected && evalResult !== undefined && hasStructuredExpected && singleLevel && (
          <div className="mt-3">
            {solutionExpected?.message && <div className="mb-2 text-muted">{solutionExpected.message}</div>}
            {Array.isArray(solutionExpected?.rows) && solutionExpected.rows.length > 0 && (
              <div className="table-responsive">
                <table className="table table-bordered table-sm align-middle mb-2">
                  <thead className="table-light">
                    <tr>
                      <th>Itemset</th>
                      <th>Support</th>
                      <th>P</th>
                      <th>fällt unter minsup?</th>
                    </tr>
                  </thead>
                  <tbody>
                    {solutionExpected.rows.map((row, i) => (
                      <tr key={`expected-row-${i}`}>
                        <td>{row.itemset}</td>
                        <td>{row.support}</td>
                        <td>{row.probability}</td>
                        <td>{row.below}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            {solutionExpected?.terminate !== undefined && (
              <small className="text-muted fst-italic d-block">
                Correct termination: {String(solutionExpected.terminate)}
              </small>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function AprioriExamBuilder(props) {
  const { el, ...rest } = props;
  const fieldId = el.id || "apriori_exam";
  return (
    <AprioriBuilderCore
      title={el.label || "Apriori Exam Builder"}
      description=""
      fieldId={fieldId}
      singleLevel={false}
      initialRows={1}
      {...rest}
    />
  );
}

function AprioriLevelBuilder(props) {
  const { el, ...rest } = props;
  const fieldId = el.id || "apriori_level_builder";
  return (
    <AprioriBuilderCore
      title={el.label || "Apriori Level Builder"}
      description=""
      fieldId={fieldId}
      singleLevel={true}
      initialRows={Number(el.initialRows || 3)}
      baseLevel={Number(el.level || 1)}
      {...rest}
    />
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
  openLinksInNewTab = false,
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

  const renderEvaluatedCheckbox = (fieldId, checked = false) => {
    if (typeof registerFieldId === "function") registerFieldId(String(fieldId));
    const evalResult = evaluationResults?.[fieldId];
    const isCorrect = evalResult?.correct;
    const expected = evalResult?.expected;
    const feedbackClass = evalResult === undefined ? "" : isCorrect ? "is-valid" : "is-invalid";
    const hasUserValue = Object.prototype.hasOwnProperty.call(userInput || {}, fieldId);
    const controlledChecked = hasUserValue ? !!userInput?.[fieldId] : !!checked;

    return (
      <div className="d-flex flex-column align-items-center">
        <input
          id={fieldId}
          className={`form-check-input ${feedbackClass}`}
          type="checkbox"
          checked={controlledChecked}
          onChange={(e) => onChange(fieldId, e.target.checked)}
        />
        {showExpected && evalResult !== undefined && !isCorrect && expected !== undefined && (
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
      case "AprioriExamBuilder":
      case "apriori_exam_builder":
        return (
          <AprioriExamBuilder
            key={el.id ?? idx}
            el={el}
            userInput={userInput}
            onChange={onChange}
            evaluationResults={evaluationResults}
            showExpected={showExpected}
            registerFieldId={registerFieldId}
          />
        );
      case "AprioriLevelBuilder":
      case "apriori_level_builder":
        return (
          <AprioriLevelBuilder
            key={el.id ?? idx}
            el={el}
            userInput={userInput}
            onChange={onChange}
            evaluationResults={evaluationResults}
            showExpected={showExpected}
            registerFieldId={registerFieldId}
          />
        );
      case "ER_Diagram":
      case "er_diagram":
        return (
          <ERDiagram
            key={el.id ?? idx}
            el={el}
          />
        );

      case "ER_Diagram_input":
      case "er_diagram_input":
        return (
          <ERDiagramInput
            key={el.id ?? idx}
            el={el}
            renderEvaluatedInput={renderEvaluatedInput}
          />
        );
      case "ER_Diagram_Builder":
      case "er_diagram_builder":
        return (
          <ERDiagramBuilder
            key={el.id ?? idx}
            el={el}
            idx={idx}
            userInput={userInput}
            onChange={onChange}
          />
        );
      case "Text":
      case "text": {
        const rawMarkdown = el.value ?? el.content ?? "";
        const markdownText =
          typeof rawMarkdown === "string"
            ? rawMarkdown
            : Array.isArray(rawMarkdown)
            ? rawMarkdown.map((part) => String(part ?? "")).join("\n")
            : String(rawMarkdown);

        const markdownComponents = openLinksInNewTab
          ? {
              a: ({ ...props }) => (
                <a {...props} target="_blank" rel="noopener noreferrer" />
              ),
            }
          : undefined;

        return (
          <div key={idx} className="mb-3" style={{ whiteSpace: "pre-line" }}>
            <ReactMarkdown
              remarkPlugins={[remarkMath]}
              rehypePlugins={[rehypeKatex]}
              components={markdownComponents}
            >
              {markdownText}
            </ReactMarkdown>
          </div>
        );
      }
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
      case "PdfViewer":
      case "pdf_viewer": {
        const rawSrc = String(el.src || "").trim();
        const src = rawSrc.startsWith("http://") || rawSrc.startsWith("https://")
          ? rawSrc
          : `${API_URL}${rawSrc}`;
        const height = Number(el.height || 700);

        return (
          <PdfViewerSection
            key={idx}
            title={el.title || "Schema (PDF)"}
            src={src}
            height={height}
            defaultOpen={false}
          />
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
        const { columns = [], rows = [], total_rows = rows.length, error, status } = data;

        return (
          <div key={idx} className="card mb-4 shadow-sm">
            <div className="card-body">
              <h5 className="card-title mb-3">
                {el.label || el.title || "Result"}
              </h5>

              {!error && status === "ready" && el.id === "sql_preview" && (
                <p className="text-muted small mb-2">Anzahl Zeilen: {total_rows}</p>
              )}

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
                <div className="table-responsive" style={el.id === "sql_preview" ? { maxHeight: "360px", overflowY: "auto" } : {}}>
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
                          const fallbackId = `${row.id}_${fIdx}`;

                          const renderTableCell = () => {
                            if (fIdx === 0 && (typeof field === "string" || typeof field === "number")) {
                              return field;
                            }

                            if (field && typeof field === "object") {
                              if (field.kind === "checkbox") {
                                return renderEvaluatedCheckbox(field.id || fallbackId, !!field.value);
                              }
                              if (field.kind === "input") {
                                return renderEvaluatedInput(field.id || fallbackId, field.value || "");
                              }
                              if (field.kind === "text") {
                                return String(field.value || "");
                              }
                            }

                            return fIdx === 0 ? field : renderEvaluatedInput(fallbackId, field);
                          };

                          return (
                            <td key={fIdx} className={fIdx === 0 ? "fw-bold text-center" : ""}>
                              {renderTableCell()}
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
        const alignment = el.alignment ?? "middle";

        const verticalClass =
          alignment === "top"
            ? "align-top"
            : alignment === "bottom"
            ? "align-bottom"
            : "align-middle"; // default


        const getCell = (r, c) => {
          const row = Array.isArray(cells[r]) ? cells[r] : null;
          return row && row[c] ? row[c] : null;
        };

        return (
          <div key={tableKey} className="card mb-4 shadow-sm">
            <div className="card-body">
              <h5 className="card-title mb-3">{el.title || el.label}</h5>

              <div className="table-responsive">
                <table className="table table-bordered table-sm align-middle">
                  <tbody>
                    {Array.from({ length: rows }).map((_, r) => (
                      <tr key={`r-${tableKey}-${r}`}>
                        {Array.from({ length: cols }).map((__, c) => {
                          const cellEl = getCell(r, c);
                          return (
                            <td
                              key={`c-${tableKey}-${r}-${c}`}
                              className={`text-center ${verticalClass}`}
                            >
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
        if (typeof registerFieldId === "function") registerFieldId(String(fieldId));
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
            {el.label && (
              <label className="form-label fw-semibold">
                {el.label}
              </label>
            )}

            {renderEvaluatedInput(el.id, userInput?.[el.id], {
              asTextarea: Number(el.rows || 0) > 1,
              rows: Number(el.rows || 4),
            })}
          </div>
        );
      case "CheckboxInput":
      case "checkbox_input": {
        const fieldId = el.id;
        if (typeof registerFieldId === "function") registerFieldId(String(fieldId));
        const evalResult = evaluationResults?.[fieldId];
        const isCorrect = evalResult?.correct;
        const expected = evalResult?.expected;
        const feedbackClass = evalResult === undefined ? "" : isCorrect ? "is-valid" : "is-invalid";
        const checked = !!userInput?.[fieldId];

        return (
          <div key={idx} className="mb-3">
            <div className="form-check">
              <input
                className={`form-check-input ${feedbackClass}`}
                type="checkbox"
                id={fieldId}
                checked={checked}
                onChange={(e) => onChange(fieldId, e.target.checked)}
              />
              <label className="form-check-label fw-semibold" htmlFor={fieldId}>
                {el.label || "Checkbox"}
              </label>
            </div>
            {showExpected && evalResult !== undefined && !isCorrect && expected !== undefined && (
              <small className="text-muted fst-italic">Correct: {expected}</small>
            )}
          </div>
        );
      }
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

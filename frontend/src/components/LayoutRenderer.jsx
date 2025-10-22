import React from "react";
import Plot from "react-plotly.js";
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

/**
 * LayoutRenderer
 * ---------------
 * - Renders layout-defined elements (text, tables, inputs, plots)
 * - Includes evaluation color feedback
 * - Uses Bootstrap for styling
 */
export default function LayoutRenderer({
  layout,
  activeView = "view1",
  onChange = () => {},
  evaluationResults = {},
  userInput = {},
  showExpected = false,
}) {
  if (!layout) return null;

  const viewElements = layout[activeView] || [];
  const header = layout.header;

  /** 🔹 Evaluated text input with color feedback */
  const renderEvaluatedInput = (fieldId, value = "") => {
    const evalResult = evaluationResults?.[fieldId];
    const isCorrect = evalResult?.correct;
    const expected = evalResult?.expected;

    const bgClass =
      evalResult === undefined
        ? ""
        : isCorrect
        ? "bg-success-subtle"
        : "bg-danger-subtle";

    return (
      <div className="mb-2">
        <input
          type="text"
          name={fieldId}
          className={`form-control form-control-sm ${bgClass}`}
          onChange={(e) => onChange(fieldId, e.target.value)}
          value={userInput?.[fieldId] ?? ""}
          title={!isCorrect && expected ? `Expected: ${expected}` : ""}
        />
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
          <p key={idx} className="mb-3">
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

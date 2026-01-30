// frontend/src/pages/QuestionPage.jsx
import { useEffect, useMemo, useState } from "react";
import { useLocation, useParams } from "react-router-dom";
import LayoutRenderer from "../components/LayoutRenderer";
import { API_URL } from "../api";

export default function QuestionPage() {
  const { type } = useParams();
  const { search } = useLocation();

  const [question, setQuestion] = useState(null);
  const [formData, setFormData] = useState({});
  const [visibleViews, setVisibleViews] = useState(["view1"]);
  const [viewResults, setViewResults] = useState({});
  const [viewStatus, setViewStatus] = useState({});
  const [finished, setFinished] = useState(false);
  const [reactiveTables, setReactiveTables] = useState({});

  // ✅ collect ALL url params (no hardcoded settings)
  const queryString = useMemo(() => {
    const sp = new URLSearchParams(search);

    // light sanitation: drop seed if invalid (optional)
    const seed = sp.get("seed");
    if (seed != null && seed !== "" && !/^\d+$/.test(seed)) {
      sp.delete("seed");
    }

    const s = sp.toString();
    return s ? `?${s}` : "";
  }, [search]);

  useEffect(() => {
    if (!type) return;

    fetch(`${API_URL}/question/${type}${queryString}`)
      .then((res) => res.json())
      .then((data) => {
        setQuestion(data);
        setFormData({});
        setVisibleViews(["view1"]);
        setViewResults({});
        setViewStatus({ view1: "idle" });
        setFinished(false);
        setReactiveTables({});
      })
      .catch((err) => console.error("Error loading question:", err));
  }, [type, queryString]);

  useEffect(() => {
    if (!question) return;
    if (type !== "relational_algebra") return;

    const stmt = formData["0"] ?? "";

    if (!stmt.trim()) {
      setReactiveTables((prev) => ({
        ...prev,
        "0": { columns: [], rows: [], tree: null, error: null, status: "idle" },
      }));
      return;
    }

    let cancelled = false;

    const timeoutId = setTimeout(() => {
      setReactiveTables((prev) => ({
        ...prev,
        "0": { ...(prev["0"] || {}), status: "loading" },
      }));

      fetch(`${API_URL}/question/${type}/preview${queryString}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ statement: stmt }),
      })
        .then((res) => res.json())
        .then((data) => {
          if (cancelled) return;

          setReactiveTables((prev) => ({
            ...prev,
            "0": {
              columns: data.columns || [],
              rows: data.rows || [],
              tree: data.tree || null,
              error: data.error || null,
              status: "ready",
            },
          }));
        })
        .catch((err) => {
          if (cancelled) return;
          console.error("Preview error:", err);
          setReactiveTables((prev) => ({
            ...prev,
            "0": {
              columns: [],
              rows: [],
              tree: null,
              error: "Preview request failed.",
              status: "error",
            },
          }));
        });
    }, 600);

    return () => {
      cancelled = true;
      clearTimeout(timeoutId);
    };
  }, [formData["0"], question, type, queryString]);

  const handleChange = (id, value) => setFormData((prev) => ({ ...prev, [id]: value }));

  // filterResultsForView unchanged...
  const filterResultsForView = (allResults, view) => {
    if (!allResults || !view) return {};

    const normalizedResults = {};
    for (const [k, v] of Object.entries(allResults)) normalizedResults[String(k)] = v;

    const fieldIds = new Set();
    const walk = (el) => {
      if (!el || typeof el !== "object") return;
      const t = String(el.type || "").toLowerCase();

      if ((t === "tableinput" || t === "table_input") && Array.isArray(el.rows)) {
        el.rows.forEach((row) => {
          if (!row) return;
          const rowId = row.id;
          const fields = Array.isArray(row.fields) ? row.fields : [];
          fields.forEach((_, fIdx) => fieldIds.add(String(`${rowId}_${fIdx}`)));
        });
        return;
      }

      if (t === "layouttable" || t === "layout_table") {
        const cells = Array.isArray(el.cells) ? el.cells : [];
        for (const row of cells) {
          if (!Array.isArray(row)) continue;
          for (const cell of row) walk(cell);
        }
        return;
      }

      if (el.id !== undefined && el.id !== null && el.id !== "") fieldIds.add(String(el.id));
    };
    view.forEach(walk);

    const filtered = {};
    for (const id of fieldIds) {
      if (normalizedResults[id] !== undefined) filtered[id] = normalizedResults[id];
    }
    return filtered;
  };

  const handleSubmitView = (viewName) => {
    if (!question) return;

    fetch(`${API_URL}/question/${type}/evaluate${queryString}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(formData),
    })
      .then((res) => res.json())
      .then((data) => {
        const filteredResults = filterResultsForView(data.results, question.layout[viewName]);
        setViewResults((prev) => ({ ...prev, [viewName]: filteredResults }));
        setViewStatus((prev) => ({ ...prev, [viewName]: "evaluated" }));
      })
      .catch((err) => console.error("Evaluation error:", err));
  };

  const handleShowResults = (viewName) =>
    setViewStatus((prev) => ({ ...prev, [viewName]: "showingResults" }));

  const handleNextStep = (viewName) => {
    const nextIndex = visibleViews.length + 1;
    const nextViewName = `view${nextIndex}`;
    if (question.layout[nextViewName]) {
      setVisibleViews((prev) => [...prev, nextViewName]);
      setViewStatus((prev) => ({ ...prev, [nextViewName]: "idle" }));
    } else setFinished(true);
  };

  if (!question) return <div>Loading...</div>;

  // ✅ header: show difficulty only if present in URL (or returned by backend)
  const sp = new URLSearchParams(search);
  const difficultyLabel = sp.get("difficulty") || question.difficulty;
  const displayHeader = `${type?.replace(/_/g, " ")}${difficultyLabel ? ` (${difficultyLabel})` : ""}`;

  return (
    <div className="container py-4">
      <h2 className="mb-4 text-capitalize">{displayHeader}</h2>

      {visibleViews.map((viewName, index) => {
        const status = viewStatus[viewName] || "idle";
        const results = viewResults[viewName] || {};
        const isLastVisible = index === visibleViews.length - 1;
        const nextExists = question.layout[`view${visibleViews.length + 1}`];

        return (
          <div key={viewName} className="card mb-4 shadow-sm">
            <div className="card-body">
              <LayoutRenderer
                layout={question.layout}
                activeView={viewName}
                onChange={handleChange}
                evaluationResults={results}
                userInput={formData}
                showExpected={status === "showingResults"}
                reactiveTables={reactiveTables}
              />

              <button
                type="button"
                onClick={() => handleSubmitView(viewName)}
                className="btn btn-primary mt-3 me-2"
              >
                Submit
              </button>

              {status === "evaluated" && (
                <button
                  type="button"
                  onClick={() => handleShowResults(viewName)}
                  className="btn btn-warning mt-3 me-2"
                >
                  Show Results
                </button>
              )}

              {status === "showingResults" && isLastVisible && (
                <button
                  type="button"
                  onClick={() => handleNextStep(viewName)}
                  className="btn btn-success mt-3"
                >
                  {nextExists ? "Next Step →" : "Show Final Results"}
                </button>
              )}
            </div>
          </div>
        );
      })}

      {finished && (
        <div className="mt-4">
          {question.layout.lastView ? (
            <div className="card shadow-sm">
              <div className="card-body">
                <LayoutRenderer
                  layout={question.layout}
                  activeView="lastView"
                  onChange={() => {}}
                  evaluationResults={{}}
                  userInput={{}}
                  showExpected={true}
                />
              </div>
            </div>
          ) : (
            <>
              <h3>Final Results:</h3>
              <pre className="bg-light p-3 rounded border overflow-auto">
                {JSON.stringify(viewResults, null, 2)}
              </pre>
            </>
          )}
        </div>
      )}
    </div>
  );
}

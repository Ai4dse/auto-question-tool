// frontend/src/pages/QuestionPage.jsx
import { useEffect, useMemo, useRef, useState } from "react";
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

  const viewFieldIdsRef = useRef({}); // { [viewName]: Set<string> }

  const registerFieldIdForView = (viewName, fieldId) => {
    const v = String(viewName);
    const id = String(fieldId);
    if (!viewFieldIdsRef.current[v]) viewFieldIdsRef.current[v] = new Set();
      viewFieldIdsRef.current[v].add(id);
    };

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

  const filterResultsForView = (allResults, viewName) => {
    const ids = viewFieldIdsRef.current?.[viewName];
    if (!allResults || !ids || ids.size === 0) return {};
    const filtered = {};
    for (const id of ids) {
      const key = String(id);
      if (allResults[key] !== undefined) filtered[key] = allResults[key];
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
        const filteredResults = filterResultsForView(data.results, viewName);
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
        viewFieldIdsRef.current[viewName] = new Set();
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
                registerFieldId={(fieldId) => registerFieldIdForView(viewName, fieldId)}
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

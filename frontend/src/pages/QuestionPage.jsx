// frontend/src/pages/QuestionPage.jsx
import { useEffect, useMemo, useRef, useState } from "react";
import { useLocation, useParams } from "react-router-dom";
import LayoutRenderer from "../components/LayoutRenderer";
import { API_URL, getRateLimitMessage } from "../api";

export default function QuestionPage({ onSessionExpired }) {
  const { type } = useParams();
  const { search } = useLocation();
  const isExternalExercise = type === "regex" || type === "xpath_xquery";

  const [question, setQuestion] = useState(null);
  const [formData, setFormData] = useState({});
  const [visibleViews, setVisibleViews] = useState(["view1"]);
  const [viewResults, setViewResults] = useState({});
  const [viewStatus, setViewStatus] = useState({});
  const [finished, setFinished] = useState(false);
  const [reactiveTables, setReactiveTables] = useState({});
  const [resolvedSeed, setResolvedSeed] = useState(null);
  const [resolvedExerciseName, setResolvedExerciseName] = useState(null);
  const [loadError, setLoadError] = useState("");
  const [requestError, setRequestError] = useState("");

  const viewFieldIdsRef = useRef({}); // { [viewName]: Set<string> }

  const registerFieldIdForView = (viewName, fieldId) => {
    const v = String(viewName);
    const id = String(fieldId);
    if (!viewFieldIdsRef.current[v]) viewFieldIdsRef.current[v] = new Set();
      viewFieldIdsRef.current[v].add(id);
    };

  const baseQueryString = useMemo(() => {
    const sp = new URLSearchParams(search);

    // light sanitation: drop seed if invalid (optional)
    const seed = sp.get("seed");
    if (seed != null && seed !== "" && !/^\d+$/.test(seed)) {
      sp.delete("seed");
    }

    const s = sp.toString();
    return s ? `?${s}` : "";
  }, [search]);

  const requestQueryString = useMemo(() => {
    const sp = new URLSearchParams(search);
    const seed = sp.get("seed");
    if (seed != null && seed !== "" && !/^\d+$/.test(seed)) {
      sp.delete("seed");
    }
    if (!sp.get("seed") && resolvedSeed != null) {
      sp.set("seed", String(resolvedSeed));
    }
    if (!sp.get("exercise_name") && resolvedExerciseName) {
      sp.set("exercise_name", String(resolvedExerciseName));
    }

    const s = sp.toString();
    return s ? `?${s}` : "";
  }, [search, resolvedSeed, resolvedExerciseName]);

  useEffect(() => {
    if (!type) return;
    setResolvedSeed(null);
    setResolvedExerciseName(null);

    fetch(`${API_URL}/question/${type}${baseQueryString}`, {
      credentials: "include",
    })
      .then(async (res) => {
        if (!res.ok) {
          if (res.status === 401) {
            onSessionExpired?.();
            throw new Error("Session expired. Please sign in again.");
          }
          if (res.status === 429) {
            throw new Error(getRateLimitMessage(res));
          }
          let message = `HTTP ${res.status}`;
          try {
            const err = await res.json();
            message = err?.detail || err?.error || message;
          } catch {
            // ignore JSON parse errors for error payloads
          }
          throw new Error(message);
        }
        return res.json();
      })
      .then((data) => {
        if (data?.error) throw new Error(data.error);
        setQuestion(data);
        setLoadError("");
        setRequestError("");
        setResolvedSeed(data?.seed ?? null);
        setResolvedExerciseName(data?.exercise_name ?? null);
        viewFieldIdsRef.current = {};
        setFormData({});
        setVisibleViews(["view1"]);
        setViewResults({});
        setViewStatus({ view1: "idle" });
        setFinished(false);
        setReactiveTables({});
      })
      .catch((err) => {
        console.error("Error loading question:", err);
        setQuestion(null);
        setLoadError(err?.message || "Question not available.");
      });
  }, [type, baseQueryString]);

  useEffect(() => {
    if (!question) return;
    if (type !== "relational_algebra" && type !== "sql_query") return;

    const stmt = formData["0"] ?? "";

    if (!stmt.trim()) {
      setReactiveTables((prev) => ({
        ...prev,
        "0": { columns: [], rows: [], total_rows: 0, tree: null, error: null, status: "idle" },
      }));
      return;
    }

    let cancelled = false;

    const timeoutId = setTimeout(() => {
      setRequestError("");
      setReactiveTables((prev) => ({
        ...prev,
        "0": { ...(prev["0"] || {}), status: "loading" },
      }));

      fetch(`${API_URL}/question/${type}/preview${requestQueryString}`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ statement: stmt }),
      })
        .then(async (res) => {
          if (!res.ok) {
            if (res.status === 401) {
              onSessionExpired?.();
              throw new Error("Session expired. Please sign in again.");
            }
            if (res.status === 429) {
              throw new Error(getRateLimitMessage(res));
            }
            const data = await res.json().catch(() => ({}));
            throw new Error(data?.detail || `HTTP ${res.status}`);
          }
          return res.json();
        })
        .then((data) => {
          if (cancelled) return;
          setRequestError("");

          setReactiveTables((prev) => ({
            ...prev,
            "0": {
              columns: data.columns || [],
              rows: data.rows || [],
              total_rows: Number.isFinite(data.total_rows) ? data.total_rows : (data.rows || []).length,
              tree: data.tree || null,
              error: data.error || null,
              status: "ready",
            },
          }));
        })
        .catch((err) => {
          if (cancelled) return;
          console.error("Preview error:", err);
          setRequestError(err?.message || "Vorschau fehlgeschlagen.");
          setReactiveTables((prev) => ({
            ...prev,
            "0": {
              columns: [],
              rows: [],
              total_rows: 0,
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
  }, [formData["0"], question, type, requestQueryString]);

  const handleChange = (id, value) => {
    setRequestError("");
    setFormData((prev) => ({ ...prev, [id]: value }));
  };

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

    if (isExternalExercise) {
      setFinished(true);
      return;
    }

    setRequestError("");

    fetch(`${API_URL}/question/${type}/evaluate${requestQueryString}`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(formData),
    })
      .then(async (res) => {
        if (!res.ok) {
          if (res.status === 401) {
            onSessionExpired?.();
            throw new Error("Session expired. Please sign in again.");
          }
          if (res.status === 429) {
            throw new Error(getRateLimitMessage(res));
          }
          const data = await res.json().catch(() => ({}));
          throw new Error(data?.detail || `HTTP ${res.status}`);
        }
        return res.json();
      })
      .then((data) => {
        setRequestError("");
        const filteredResults = filterResultsForView(data.results, viewName);
        const isEmpty =
          !filteredResults || Object.keys(filteredResults).length === 0;

        setViewResults((prev) => ({ ...prev, [viewName]: filteredResults }));

        setViewStatus((prev) => ({
          ...prev,
          [viewName]: isEmpty ? "showingResults" : "evaluated",
        }));
      })
      .catch((err) => {
        console.error("Evaluation error:", err);
        setRequestError(err?.message || "Abgabe fehlgeschlagen.");
      });
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

  if (loadError) return <div className="alert alert-danger">{loadError}</div>;
  if (!question) return <div>Lade...</div>;

  const sp = new URLSearchParams(search);
  const difficultyLabel = sp.get("difficulty") || question.difficulty;
  const displayType = type === "sql_query" ? "SQL-Abfrage" : type?.replace(/_/g, " ");
  const displayHeader = `${displayType}${difficultyLabel ? ` (${difficultyLabel})` : ""}`;

  return (
    <div className="container py-4">
      <h2 className="mb-4 text-capitalize">{displayHeader}</h2>
      {requestError && <div className="alert alert-warning">{requestError}</div>}

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
                registerFieldId={(fieldId) => registerFieldIdForView(viewName, fieldId)}
                openLinksInNewTab={isExternalExercise}
              />

              <button
                type="button"
                onClick={() => handleSubmitView(viewName)}
                className="btn btn-primary mt-3 me-2"
              >
                Abgeben
              </button>

              {status === "evaluated" && (
                <button
                  type="button"
                  onClick={() => handleShowResults(viewName)}
                  className="btn btn-warning mt-3 me-2"
                >
                  Ergebnisse anzeigen
                </button>
              )}

              {status === "showingResults" && isLastVisible && (
                <button
                  type="button"
                  onClick={() => handleNextStep(viewName)}
                  className="btn btn-success mt-3"
                >
                  {nextExists ? "Naechster Schritt ->" : "Endergebnisse anzeigen"}
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
                  openLinksInNewTab={isExternalExercise}
                />
              </div>
            </div>
          ) : (
            <>
              <h3>Endergebnisse:</h3>
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

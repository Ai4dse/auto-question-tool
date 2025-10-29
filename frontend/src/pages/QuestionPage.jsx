// frontend/src/pages/QuestionPage.jsx
import { useEffect, useState } from "react";
import { useLocation, useParams } from "react-router-dom";
import LayoutRenderer from "../components/LayoutRenderer";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function QuestionPage() {
  const { type } = useParams();
  const { search } = useLocation();
  const searchParams = new URLSearchParams(search);
  const rawSeed = searchParams.get("seed");
  const seed = /^\d+$/.test(rawSeed) ? rawSeed : undefined;
  const difficulty = searchParams.get("difficulty") || "medium";

  const [question, setQuestion] = useState(null);
  const [formData, setFormData] = useState({});
  const [visibleViews, setVisibleViews] = useState(["view1"]);
  const [viewResults, setViewResults] = useState({});
  const [viewStatus, setViewStatus] = useState({});
  const [finished, setFinished] = useState(false);

  useEffect(() => {
    if (!type) return;
    fetch(`${API_URL}/question/${type}?seed=${seed || "1234"}&difficulty=${difficulty}`)
      .then((res) => res.json())
      .then((data) => {
        setQuestion(data);
        setFormData({});
        setVisibleViews(["view1"]);
        setViewResults({});
        setViewStatus({ view1: "idle" });
        setFinished(false);
      })
      .catch((err) => console.error("Error loading question:", err));
  }, [type, seed, difficulty]);

  const handleChange = (id, value) => setFormData((prev) => ({ ...prev, [id]: value }));

  const filterResultsForView = (allResults, view) => {
    if (!allResults || !view) return {};
    const fieldIds = [];
    view.forEach((el) => {
      if (el.type === "TableInput" && el.rows) {
        el.rows.forEach((row) => row.fields.forEach((_, fIdx) => fieldIds.push(`${row.id}_${fIdx}`)));
      } else if (el.id) fieldIds.push(el.id);
    });
    const filtered = {};
    for (const [key, val] of Object.entries(allResults)) {
      if (fieldIds.includes(key)) filtered[key] = val;
    }
    return filtered;
  };

  const handleSubmitView = (viewName) => {
    if (!question) return;
    const seedToUse = question.seed || seed || "1234";
    const difficultyToUse = question.difficulty || difficulty || "medium";

    fetch(`${API_URL}/question/${type}/evaluate?seed=${seedToUse}&difficulty=${difficultyToUse}`, {
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

  const displayHeader = `${type?.replace(/_/g, " ")} (${difficulty})`;

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

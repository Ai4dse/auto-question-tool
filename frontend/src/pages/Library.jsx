// frontend/src/pages/Library.jsx
import { useState, useRef, useEffect } from "react";
import { Link } from "react-router-dom";
import QuestionControls from "../components/QuestionControls";
import "bootstrap/dist/css/bootstrap.min.css";
import { API_URL } from "../api";

export default function Library() {
  const [hoveredConfig, setHoveredConfig] = useState(null);
  const [questionSettings, setQuestionSettings] = useState({});
  const hoverTimeout = useRef(null);

  const [questions, setQuestions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const generateRandomSeed = () => Math.floor(Math.random() * 1_000_000).toString();

  // Helpers for hover control
  const handleEnter = (id) => {
    if (hoverTimeout.current) clearTimeout(hoverTimeout.current);
    setHoveredConfig(id);
  };

  const handleLeave = () => {
    hoverTimeout.current = setTimeout(() => setHoveredConfig(null), 150);
  };

  //fetch questions once on mount
  useEffect(() => {
    let cancelled = false;

    async function loadQuestions() {
      try {
        setLoading(true);
        setError("");

        const res = await fetch(`${API_URL}/questions`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        const data = await res.json();
        if (cancelled) return;

        const normalized = (Array.isArray(data) ? data : []).map((q) => ({
          id: q.id,
          title: q.title || q.id,
          desc: q.desc || "",
          difficulty: Array.isArray(q.difficulty) ? q.difficulty : ["easy", "medium", "hard"],
          mode: Array.isArray(q.mode) ? q.mode : ["steps", "exam"],
          tags: Array.isArray(q.tags) ? q.tags : [],
        }));

        normalized.sort((a, b) => a.title.localeCompare(b.title));
        setQuestions(normalized);
      } catch (e) {
        setError(e?.message || "Failed to load questions");
      } finally {
        setLoading(false);
      }
    }

    loadQuestions();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="container py-4">
      <h1 className="mb-4 text-center">Question Library</h1>

      {loading && <div className="text-center text-muted">Loading…</div>}
      {error && <div className="alert alert-danger">Could not load: {error}</div>}

      <div className="row">
        {questions.map((q) => {
          const availableDifficulties =
            Array.isArray(q.difficulty) && q.difficulty.length ? q.difficulty : ["easy", "medium", "hard"];

          const settings = questionSettings[q.id] || {
            seed: "",
            difficulty: availableDifficulties.includes("medium")
              ? "medium"
              : availableDifficulties[0],
          };

          const seedToUse = settings.seed?.length ? settings.seed : generateRandomSeed();
          const difficulty = settings.difficulty;
          const questionUrl = `/question/${q.id}?seed=${seedToUse}&difficulty=${difficulty}`;

          return (
            <div key={q.id} className="col-md-4 mb-4">
              <div className="card shadow-sm h-100 position-relative">
                <div className="card-body">
                  <div className="d-flex justify-content-between align-items-start">
                    <div>
                      <h5 className="card-title">{q.title}</h5>
                      <p className="card-text text-muted">{q.desc}</p>
                    </div>

                    {/* ⚙️ Options Icon + hover container */}
                    <div
                      className="position-relative"
                      onMouseEnter={() => handleEnter(q.id)}
                      onMouseLeave={handleLeave}
                    >
                      <button className="btn btn-sm btn-outline-secondary">⚙️</button>

                      {hoveredConfig === q.id && (
                        <div
                          className="position-absolute top-100 end-0 mt-2 z-3"
                          onMouseEnter={() => handleEnter(q.id)}
                          onMouseLeave={handleLeave}
                        >
                          <QuestionControls
                            initialSeed={settings.seed}
                            onSeedChange={(seed) =>
                              setQuestionSettings((prev) => ({
                                ...prev,
                                [q.id]: { ...prev[q.id], seed },
                              }))
                            }
                          />
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Difficulty Dropdown */}
                  <div className="mt-3 mb-3">
                    <label className="fw-semibold me-2">Difficulty:</label>
                    <select
                      value={difficulty}
                      onChange={(e) =>
                        setQuestionSettings((prev) => ({
                          ...prev,
                          [q.id]: { ...prev[q.id], difficulty: e.target.value },
                        }))
                      }
                      className="form-select form-select-sm w-auto d-inline-block"
                    >
                      {availableDifficulties.map((level) => (
                        <option key={level} value={level}>
                          {level}
                        </option>
                      ))}
                    </select>
                  </div>

                  <Link to={questionUrl} className="btn btn-primary w-100">
                    Open
                  </Link>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

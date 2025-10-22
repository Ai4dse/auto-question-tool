// frontend/src/pages/Library.jsx
import { useState, useRef } from "react";
import { Link } from "react-router-dom";
import QuestionControls from "../components/QuestionControls";
import "bootstrap/dist/css/bootstrap.min.css";

const difficultyLevels = ["easy", "medium", "hard"];

export default function Library() {
  const [hoveredConfig, setHoveredConfig] = useState(null); // which ⚙️ menu is open
  const [questionSettings, setQuestionSettings] = useState({}); // { [id]: { seed, difficulty } }
  const hoverTimeout = useRef(null);

  const questions = [
    { id: "kmeans", title: "K-Means Clustering", desc: "Cluster data points into groups." },
    { id: "addition", title: "Simple Addition", desc: "Practice simple arithmetic." },
  ];

  const generateRandomSeed = () => Math.floor(Math.random() * 1_000_000).toString();

  // Helpers for hover control
  const handleEnter = (id) => {
    if (hoverTimeout.current) clearTimeout(hoverTimeout.current);
    setHoveredConfig(id);
  };

  const handleLeave = () => {
    hoverTimeout.current = setTimeout(() => setHoveredConfig(null), 150);
  };

  return (
    <div className="container py-4">
      <h1 className="mb-4 text-center">Question Library</h1>

      <div className="row">
        {questions.map((q) => {
          const settings = questionSettings[q.id] || { seed: "", difficulty: "medium" };
          const seedToUse =
            settings.seed && settings.seed.length > 0 ? settings.seed : generateRandomSeed();
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
                      {difficultyLevels.map((level) => (
                        <option key={level} value={level}>
                          {level}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Open Button */}
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

// frontend/src/pages/Library.jsx
import { useState, useRef, useEffect } from "react";
import { Link } from "react-router-dom";
import "bootstrap/dist/css/bootstrap.min.css";
import { API_URL } from "../api";

import SettingField from "../components/settings/SettingField";
import {
  getDefaultsFromSchema,
  buildQueryFromSettings,
  ensureSeedValue,
} from "../components/settings/settingUtils";

export default function Library() {
  const [hoveredConfig, setHoveredConfig] = useState(null);
  const [questionSettings, setQuestionSettings] = useState({});
  const hoverTimeout = useRef(null);

  // stable random seed per question card (until user edits it)
  const seedCache = useRef({});

  const [questions, setQuestions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const handleEnter = (id) => {
    if (hoverTimeout.current) clearTimeout(hoverTimeout.current);
    setHoveredConfig(id);
  };

  const handleLeave = () => {
    hoverTimeout.current = setTimeout(() => setHoveredConfig(null), 150);
  };

  const updateSetting = (qid, name, value) => {
    setQuestionSettings((prev) => ({
      ...prev,
      [qid]: { ...(prev[qid] || {}), [name]: value },
    }));
  };

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

        const normalized = (Array.isArray(data) ? data : []).map((q) => {
          // Expect schema from backend: q.settings
          // Backcompat: minimal schema if missing
          const settings =
            (q.settings && typeof q.settings === "object" ? q.settings : null) ||
            {
              difficulty: {
                kind: "select",
                visibility: "open",
                options: Array.isArray(q.difficulty) && q.difficulty.length ? q.difficulty : ["easy", "medium", "hard"],
                default: "medium",
              },
              seed: { kind: "number", visibility: "hidden" },
            };

          return {
            id: q.id,
            title: q.title || q.id,
            desc: q.desc || "",
            mode: Array.isArray(q.mode) ? q.mode : ["steps", "exam"],
            tags: Array.isArray(q.tags) ? q.tags : [],
            settings,
          };
        });

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
          const schema = q.settings || {};
          const defaults = getDefaultsFromSchema(schema);
          const local = questionSettings[q.id] || {};

          // Effective = defaults + local overrides
          let effective = { ...defaults, ...local };

          // ✅ crucial: if schema has seed and user hasn't set it -> stable random seed
          effective = ensureSeedValue({
            schema,
            effectiveValues: effective,
            seedCache,
            questionId: q.id,
          });

          const params = buildQueryFromSettings(schema, effective);
          const questionUrl = `/question/${q.id}?${params.toString()}`;

          const openEntries = Object.entries(schema).filter(([, def]) => def?.visibility === "open");
          const hiddenEntries = Object.entries(schema).filter(([, def]) => def?.visibility === "hidden");

          return (
            <div key={q.id} className="col-md-4 mb-4">
              <div className="card shadow-sm h-100 position-relative">
                <div className="card-body">
                  <div className="d-flex justify-content-between align-items-start">
                    <div>
                      <h5 className="card-title">{q.title}</h5>
                      <p className="card-text text-muted">{q.desc}</p>
                    </div>

                    {/* ⚙️ Hidden settings */}
                    <div
                      className="position-relative"
                      onMouseEnter={() => handleEnter(q.id)}
                      onMouseLeave={handleLeave}
                    >
                      <button className="btn btn-sm btn-outline-secondary">⚙️</button>

                      {hoveredConfig === q.id && hiddenEntries.length > 0 && (
                        <div
                          className="position-absolute top-100 end-0 mt-2 z-3 bg-white border rounded p-3 shadow-sm"
                          style={{ minWidth: 260 }}
                          onMouseEnter={() => handleEnter(q.id)}
                          onMouseLeave={handleLeave}
                        >
                          <div className="fw-semibold mb-2">Settings</div>

                          {hiddenEntries.map(([name, def]) => (
                            <SettingField
                              key={name}
                              name={name}
                              def={def}
                              value={effective[name]}
                              onChange={(n, v) => updateSetting(q.id, n, v)}
                            />
                          ))}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Open settings area */}
                  {openEntries.length > 0 && (
                    <div className="mt-3 mb-3">
                      {openEntries.map(([name, def]) => (
                        <SettingField
                          key={name}
                          name={name}
                          def={def}
                          value={effective[name]}
                          onChange={(n, v) => updateSetting(q.id, n, v)}
                        />
                      ))}
                    </div>
                  )}

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

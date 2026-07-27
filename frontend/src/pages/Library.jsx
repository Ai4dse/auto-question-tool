// frontend/src/pages/Library.jsx
import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import "bootstrap/dist/css/bootstrap.min.css";
import { API_URL, getRateLimitMessage } from "../api";

import SettingField from "../components/settings/SettingField";

import {
  getDefaultsFromSchema,
  buildQueryFromSettings,
} from "../components/settings/settingUtils";

const LIBRARY_SESSION_KEY = "question-library-state-v1";

function readLibrarySessionState() {
  if (typeof window === "undefined") {
    return {
      questionSettings: {},
      randomDefaults: {},
      scrollY: 0,
    };
  }

  try {
    const stored = JSON.parse(
      window.sessionStorage.getItem(LIBRARY_SESSION_KEY) || "{}"
    );

    return {
      questionSettings:
        stored.questionSettings && typeof stored.questionSettings === "object"
          ? stored.questionSettings
          : {},
      randomDefaults:
        stored.randomDefaults && typeof stored.randomDefaults === "object"
          ? stored.randomDefaults
          : {},
      scrollY: Number.isFinite(Number(stored.scrollY))
        ? Number(stored.scrollY)
        : 0,
    };
  } catch {
    return {
      questionSettings: {},
      randomDefaults: {},
      scrollY: 0,
    };
  }
}

export default function Library({ onSessionExpired }) {
  const initialSessionStateRef = useRef(null);
  if (initialSessionStateRef.current === null) {
    initialSessionStateRef.current = readLibrarySessionState();
  }

  const [hoveredConfig, setHoveredConfig] = useState(null);
  const [questionSettings, setQuestionSettings] = useState(
    initialSessionStateRef.current.questionSettings
  );
  const hoverTimeout = useRef(null);

  // This also keeps randomly generated defaults such as a seed stable when
  // the user returns from a question page during the same browser-tab session.
  const randomDefaultsCache = useRef(
    initialSessionStateRef.current.randomDefaults
  );
  const questionSettingsRef = useRef(questionSettings);
  const restoredScrollRef = useRef(false);
  const [isScrollReady, setIsScrollReady] = useState(
    initialSessionStateRef.current.scrollY <= 0
  );
  const lastScrollYRef = useRef(initialSessionStateRef.current.scrollY);
  const isLeavingLibraryRef = useRef(false);

  const [questions, setQuestions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const saveLibrarySessionState = useCallback((scrollY) => {
    if (typeof window === "undefined") return;

    const storedScrollY = Number.isFinite(Number(scrollY))
      ? Number(scrollY)
      : lastScrollYRef.current;

    try {
      window.sessionStorage.setItem(
        LIBRARY_SESSION_KEY,
        JSON.stringify({
          questionSettings: questionSettingsRef.current,
          randomDefaults: randomDefaultsCache.current,
          scrollY: storedScrollY,
        })
      );
    } catch {
      // Ignore unavailable/full storage and keep the page functional.
    }
  }, []);

  const handleEnter = (id) => {
    if (hoverTimeout.current) clearTimeout(hoverTimeout.current);
    setHoveredConfig(id);
  };

  const handleLeave = () => {
    hoverTimeout.current = setTimeout(() => setHoveredConfig(null), 150);
  };

  const updateSetting = (qid, name, value) => {
    setQuestionSettings((prev) => {
      const next = {
        ...prev,
        [qid]: { ...(prev[qid] || {}), [name]: value },
      };
      questionSettingsRef.current = next;
      return next;
    });
  };

  const handleOpenQuestion = () => {
    isLeavingLibraryRef.current = true;
    lastScrollYRef.current = window.scrollY;
    saveLibrarySessionState(lastScrollYRef.current);
  };

  // Save the current position while scrolling and immediately before this
  // route unmounts. sessionStorage is automatically scoped to the current tab.
  useEffect(() => {
    if (typeof window === "undefined") return undefined;

    const previousScrollRestoration = window.history.scrollRestoration;
    window.history.scrollRestoration = "manual";

    let animationFrameId = null;

    const handleScroll = () => {
      if (isLeavingLibraryRef.current || animationFrameId !== null) return;

      animationFrameId = window.requestAnimationFrame(() => {
        animationFrameId = null;
        if (isLeavingLibraryRef.current) return;

        lastScrollYRef.current = window.scrollY;
        saveLibrarySessionState(lastScrollYRef.current);
      });
    };

    window.addEventListener("scroll", handleScroll, { passive: true });

    return () => {
      window.removeEventListener("scroll", handleScroll);
      if (animationFrameId !== null) {
        window.cancelAnimationFrame(animationFrameId);
      }
      saveLibrarySessionState(lastScrollYRef.current);
      window.history.scrollRestoration = previousScrollRestoration;
    };
  }, [saveLibrarySessionState]);

  useEffect(() => {
    let cancelled = false;

    async function loadQuestions() {
      try {
        setLoading(true);
        setError("");

        const res = await fetch(`${API_URL}/questions`, {
          credentials: "include",
        });
        if (!res.ok) {
          if (res.status === 401) {
            onSessionExpired?.();
            return;
          }
          if (res.status === 429) {
            throw new Error(getRateLimitMessage(res));
          }
          if (res.status === 403) {
            throw new Error("Please change your password to continue.");
          }
          throw new Error(`HTTP ${res.status}`);
        }

        const data = await res.json();
        if (cancelled) return;

        const normalized = (Array.isArray(data) ? data : []).map((q) => {
          const settings =
            (q.settings && typeof q.settings === "object" ? q.settings : null) ||
            {
              difficulty: {
                kind: "select",
                visibility: "open",
                options:
                  Array.isArray(q.difficulty) && q.difficulty.length
                    ? q.difficulty
                    : ["easy", "medium", "hard"],
                default: "medium",
              },
              seed: { kind: "number", visibility: "hidden" },
            };

          return {
            id: q.id,
            title: q.title || q.id,
            desc: q.desc || "",
            week: Number.isFinite(Number(q.week)) ? Number(q.week) : 1,
            weekTitle: q.week_title || null,
            weekStartDate: q.week_start_date || null,
            mode: Array.isArray(q.mode) ? q.mode : ["steps", "exam"],
            tags: Array.isArray(q.tags) ? q.tags : [],
            settings,
          };
        });

        normalized.sort((a, b) => {
          const startDateCompare = (a.weekStartDate || "").localeCompare(
            b.weekStartDate || ""
          );
          if (startDateCompare !== 0) return startDateCompare;
          if (a.week !== b.week) return a.week - b.week;
          return a.title.localeCompare(b.title);
        });
        setQuestions(normalized);
      } catch (e) {
        setError(e?.message || "Failed to load questions");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    loadQuestions();
    return () => {
      cancelled = true;
    };
  }, [onSessionExpired]);

  // Restore before the browser paints the loaded library. Keeping the page
  // hidden until this layout effect runs prevents a visible jump from the top.
  useLayoutEffect(() => {
    if (loading || restoredScrollRef.current) return;

    restoredScrollRef.current = true;
    const savedScrollY = initialSessionStateRef.current.scrollY;
    lastScrollYRef.current = savedScrollY;

    // A global `html { scroll-behavior: smooth; }` also affects `behavior: auto`.
    // Temporarily disabling it guarantees that restoration is instantaneous.
    const root = document.documentElement;
    const previousScrollBehavior = root.style.scrollBehavior;
    root.style.scrollBehavior = "auto";
    window.scrollTo(0, savedScrollY);
    root.style.scrollBehavior = previousScrollBehavior;

    setIsScrollReady(true);
  }, [loading, questions.length]);

  return (
    <div
      className="container py-4"
      style={{ visibility: isScrollReady ? "visible" : "hidden" }}
    >
      <h1 className="mb-4 text-center">Question Library</h1>

      {loading && <div className="text-center text-muted">Loading…</div>}
      {error && <div className="alert alert-danger">Could not load: {error}</div>}

      {Object.entries(
        questions.reduce((acc, q) => {
          const weekKey = String(q.week || 1);
          if (!acc[weekKey]) acc[weekKey] = [];
          acc[weekKey].push(q);
          return acc;
        }, {})
      ).map(([week, weekQuestions]) => (
        <div key={week} className="mb-4">
          <h4 className="mb-3">
            {weekQuestions[0]?.weekTitle || `Woche ${week}`}
          </h4>
          <div className="row">
            {weekQuestions.map((q) => {
              const schema = q.settings || {};
              const defaults = getDefaultsFromSchema({
                schema,
                randomCache: randomDefaultsCache,
                questionId: q.id,
              });
              const local = questionSettings[q.id] || {};
              const effective = { ...defaults, ...local };

              const params = buildQueryFromSettings(schema, effective);
              const queryString = params.toString();
              const questionUrl = `/question/${q.id}${
                queryString ? `?${queryString}` : ""
              }`;

              const openEntries = Object.entries(schema).filter(
                ([, def]) => def?.visibility === "open"
              );
              const hiddenEntries = Object.entries(schema).filter(
                ([, def]) => def?.visibility === "hidden"
              );

              return (
                <div key={q.id} className="col-md-4 mb-4">
                  <div className="card shadow-sm h-100 position-relative">
                    <div className="card-body d-flex flex-column h-100">
                      <div className="d-flex justify-content-between align-items-start">
                        <div>
                          <h5 className="card-title">{q.title}</h5>
                          <p className="card-text text-muted">{q.desc}</p>
                        </div>

                        {/* Hidden settings */}
                        <div
                          className="position-relative"
                          onMouseEnter={() => handleEnter(q.id)}
                          onMouseLeave={handleLeave}
                        >
                          <button className="btn btn-sm btn-outline-secondary">
                            ⚙️
                          </button>

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

                      {/* Open settings */}
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

                      <Link
                        to={questionUrl}
                        onClick={handleOpenQuestion}
                        className="btn btn-primary w-100 mt-auto"
                      >
                        Open
                      </Link>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}

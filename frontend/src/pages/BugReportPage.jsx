import { useState } from "react";
import { API_URL, getRateLimitMessage } from "../api";

export default function BugReportPage({ onSessionExpired }) {
  const [text, setText] = useState("");
  const [message, setMessage] = useState("");
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setMessage("");
    setSuccess(false);
    setLoading(true);

    try {
      const res = await fetch(`${API_URL}/bug-report`, {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ text }),
      });

      if (!res.ok) {
        if (res.status === 401) {
          onSessionExpired?.();
          return;
        }
        if (res.status === 429) {
          throw new Error(getRateLimitMessage(res));
        }

        const data = await res.json().catch(() => ({}));
        throw new Error(data?.detail || `HTTP ${res.status}`);
      }

      setSuccess(true);
      setMessage("Danke! Dein Feedback wurde gespeichert.");
      setText("");
    } catch (error) {
      setSuccess(false);
      setMessage(error?.message || "Feedback konnte nicht gesendet werden.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container py-4" style={{ maxWidth: "720px" }}>
      <h1 className="mb-3">Problem melden</h1>
      <p className="text-muted mb-4">Teile uns mit, was nicht funktioniert hat.</p>

      {message && (
        <div className={`alert ${success ? "alert-success" : "alert-danger"}`} role="alert">
          {message}
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <div className="mb-3">
          <label htmlFor="bug-report-text" className="form-label fw-semibold">
            Beschreibung
          </label>
          <textarea
            id="bug-report-text"
            className="form-control"
            rows={6}
            value={text}
            onChange={(event) => setText(event.target.value)}
            required
          />
        </div>

        <button type="submit" className="btn btn-primary" disabled={loading}>
          {loading ? "Senden..." : "Absenden"}
        </button>
      </form>
    </div>
  );
}

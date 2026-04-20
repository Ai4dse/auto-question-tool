import { useEffect, useState } from "react";
import { Routes, Route } from "react-router-dom";
import Library from "./pages/Library";
import QuestionPage from "./pages/QuestionPage";
import BugReportPage from "./pages/BugReportPage";
import Navbar from "./components/Navbar";
import AuthForm from "./components/AuthForm";
import ChangePassword from "./components/ChangePassword";
import { API_URL, getRateLimitMessage } from "./api";

function App() {
  const [user, setUser] = useState(null);
  const [mustChange, setMustChange] = useState(false);
  const [authLoading, setAuthLoading] = useState(true);
  const [globalMessage, setGlobalMessage] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function loadSession() {
      try {
        const res = await fetch(`${API_URL}/auth/me`, {
          credentials: "include",
        });

        if (!res.ok) {
          if (res.status === 429) {
            setGlobalMessage(getRateLimitMessage(res));
          }
          if (!cancelled) {
            setUser(null);
            setMustChange(false);
          }
          return;
        }

        const data = await res.json();
        if (!cancelled) {
          setGlobalMessage("");
          setUser(data.username || null);
          setMustChange(Boolean(data.must_change));
        }
      } catch {
        if (!cancelled) {
          setUser(null);
          setMustChange(false);
        }
      } finally {
        if (!cancelled) {
          setAuthLoading(false);
        }
      }
    }

    loadSession();
    return () => {
      cancelled = true;
    };
  }, []);

  const handleLogin = (username, needsChange) => {
    setUser(username);
    setMustChange(needsChange);
  };

  const handlePasswordChanged = () => {
    setMustChange(false);
  };

  const handleLogout = async () => {
    try {
      const res = await fetch(`${API_URL}/auth/logout`, {
        method: "POST",
        credentials: "include",
      });
      if (res.status === 429) {
        setGlobalMessage(getRateLimitMessage(res));
      }
    } catch {
      // local state reset still logs user out from UI
    }

    setUser(null);
    setMustChange(false);
  };

  const handleSessionExpired = () => {
    setUser(null);
    setMustChange(false);
  };

  if (authLoading) {
    return <div className="container py-4 text-center text-muted">Checking session...</div>;
  }

  return (
    <div className="container py-4">
      {globalMessage && <div className="alert alert-warning">{globalMessage}</div>}
      {!user ? (
        <AuthForm onLogin={handleLogin} />
      ) : mustChange ? (
        <ChangePassword username={user} onPasswordChanged={handlePasswordChanged} />
      ) : (
        <>
          <Navbar user={user} onLogout={handleLogout} />
          <Routes>
            <Route path="/" element={<Library onSessionExpired={handleSessionExpired} />} />
            <Route path="/question/:type" element={<QuestionPage onSessionExpired={handleSessionExpired} />} />
            <Route path="/bug-report" element={<BugReportPage onSessionExpired={handleSessionExpired} />} />
          </Routes>
        </>
      )}
    </div>
  );
}

export default App;

import { useEffect, useState } from "react";
import { Routes, Route } from "react-router-dom";
import Library from "./pages/Library";
import QuestionPage from "./pages/QuestionPage";
import Navbar from "./components/Navbar";
import AuthForm from "./components/AuthForm";
import ChangePassword from "./components/ChangePassword";
import { API_URL } from "./api";

function App() {
  const [user, setUser] = useState(null);
  const [mustChange, setMustChange] = useState(false);
  const [authLoading, setAuthLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function loadSession() {
      try {
        const res = await fetch(`${API_URL}/auth/me`, {
          credentials: "include",
        });

        if (!res.ok) {
          if (!cancelled) {
            setUser(null);
            setMustChange(false);
          }
          return;
        }

        const data = await res.json();
        if (!cancelled) {
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
      await fetch(`${API_URL}/auth/logout`, {
        method: "POST",
        credentials: "include",
      });
    } catch {
      // local state reset still logs user out from UI
    }

    setUser(null);
    setMustChange(false);
  };

  if (authLoading) {
    return <div className="container py-4 text-center text-muted">Checking session...</div>;
  }

  return (
    <div className="container py-4">
      {!user ? (
        <AuthForm onLogin={handleLogin} />
      ) : mustChange ? (
        <ChangePassword username={user} onPasswordChanged={handlePasswordChanged} />
      ) : (
        <>
          <Navbar user={user} onLogout={handleLogout} />
          <Routes>
            <Route path="/" element={<Library />} />
            <Route path="/question/:type" element={<QuestionPage />} />
          </Routes>
        </>
      )}
    </div>
  );
}

export default App;

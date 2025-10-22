import { useState } from "react";
import { Routes, Route, useLocation } from "react-router-dom";
import Library from "./pages/Library";
import QuestionPage from "./pages/QuestionPage";
import Navbar from "./components/Navbar";
import AuthForm from "./components/AuthForm";
import ChangePassword from "./components/ChangePassword";

function App() {
  const [user, setUser] = useState(localStorage.getItem("username"));
  const [mustChange, setMustChange] = useState(false);

  const handleLogin = (username, needsChange) => {
    setUser(username);
    setMustChange(needsChange);
    localStorage.setItem("username", username);
  };

  const handlePasswordChanged = () => {
    setMustChange(false);
  };

  const handleLogout = () => {
    localStorage.removeItem("username");
    setUser(null);
  };

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

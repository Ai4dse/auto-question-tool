import { Link, useLocation } from "react-router-dom";
import "bootstrap/dist/css/bootstrap.min.css";

export default function Navbar({ user, onLogout }) {
  const location = useLocation();
  const isLibrary = location.pathname === "/";

  return (
    <nav className="navbar navbar-expand-lg navbar-light bg-light mb-4 shadow-sm rounded">
      <div className="container-fluid">
        <span className="navbar-brand fw-bold">DBE</span>

        <div className="d-flex align-items-center ms-auto">
          {!isLibrary && (
            <Link to="/" className="btn btn-outline-primary me-2">
              ⬅️ Back to Library
            </Link>
          )}

          <span className="me-3 text-muted">
            <small>Signed in as: <strong>{user}</strong></small>
          </span>

          <button className="btn btn-danger" onClick={onLogout}>
            Logout
          </button>
        </div>
      </div>
    </nav>
  );
}

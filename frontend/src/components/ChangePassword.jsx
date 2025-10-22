import { useState } from "react";
import "bootstrap/dist/css/bootstrap.min.css";

export default function ChangePassword({ username, onPasswordChanged }) {
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [message, setMessage] = useState("");
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);

  const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

  const handleSubmit = async (e) => {
    e.preventDefault();
    setMessage("");
    setSuccess(false);
    setLoading(true);

    try {
      const res = await fetch(
        `${API_URL}/auth/change_password?username=${username}&old_password=${oldPassword}&new_password=${newPassword}`,
        { method: "POST" }
      );
      const data = await res.json();

      if (res.ok) {
        setMessage("✅ Password updated successfully!");
        setSuccess(true);
        setOldPassword("");
        setNewPassword("");
        setTimeout(() => onPasswordChanged(), 1500);
      } else {
        setMessage("❌ Error: " + (data.detail || "Password change failed"));
      }
    } catch (err) {
      setMessage("⚠️ Network error: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="d-flex justify-content-center align-items-center vh-100 bg-light">
      <div className="card shadow-sm p-4" style={{ width: "100%", maxWidth: "400px" }}>
        <h3 className="text-center mb-4 fw-bold">🔒 Change Password</h3>

        <div className="text-center text-muted mb-3">
          <small>Signed in as: <strong>{username}</strong></small>
        </div>

        {message && (
          <div
            className={`alert ${
              success ? "alert-success" : "alert-warning"
            } text-center py-2`}
            role="alert"
          >
            {message}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="mb-3">
            <label className="form-label fw-semibold">Old Password</label>
            <input
              type="password"
              className="form-control"
              placeholder="Enter your old password"
              value={oldPassword}
              onChange={(e) => setOldPassword(e.target.value)}
              required
            />
          </div>

          <div className="mb-4">
            <label className="form-label fw-semibold">New Password</label>
            <input
              type="password"
              className="form-control"
              placeholder="Enter a new password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              required
            />
          </div>

          <button
            type="submit"
            className="btn btn-success w-100"
            disabled={loading}
          >
            {loading ? "Updating..." : "Change Password"}
          </button>
        </form>
      </div>
    </div>
  );
}

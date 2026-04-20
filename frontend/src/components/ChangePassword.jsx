import { useState } from "react";
import "bootstrap/dist/css/bootstrap.min.css";
import { API_URL, getRateLimitMessage } from "../api";

export default function ChangePassword({ username, onPasswordChanged }) {
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [message, setMessage] = useState("");
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);

  function getFriendlyErrorMessage(data, res) {
    if (res.status === 401) {
      if (data?.detail === "Invalid credentials") {
        return "The old password is incorrect.";
      }
      return "Your credentials are invalid.";
    }

    if (res.status === 422 && Array.isArray(data?.detail)) {
      for (const err of data.detail) {
        const field = err?.loc?.[1];
        const msg = err?.msg || "";

        if (field === "new_password") {
          if (msg.toLowerCase().includes("at least")) {
            return "The new password must be at least 8 characters long.";
          }
          return "Please enter a valid new password.";
        }

        if (field === "old_password") {
          return "Please enter your old password.";
        }

        if (field === "username") {
          return "Your session seems invalid. Please sign in again.";
        }
      }

      return "Please check your input and try again.";
    }

    if (typeof data?.detail === "string") {
      return data.detail;
    }

    return "Password change failed. Please try again.";
  }

  async function reconcileAfterNetworkError() {
    try {
      const meRes = await fetch(`${API_URL}/auth/me`, {
        credentials: "include",
      });

      if (meRes.status === 429) {
        setMessage(getRateLimitMessage(meRes));
        setSuccess(false);
        return false;
      }

      if (!meRes.ok) {
        return false;
      }

      const meData = await meRes.json();
      if (meData?.must_change === false) {
        setMessage("✅ Password seems updated. Connection was lost, but your account is now active.");
        setSuccess(true);
        setOldPassword("");
        setNewPassword("");
        setTimeout(() => onPasswordChanged(), 1500);
        return true;
      }
    } catch {
      return false;
    }

    return false;
  }

  const handleSubmit = async (e) => {
    e.preventDefault();
    setMessage("");
    setSuccess(false);
    setLoading(true);

    try {
      const res = await fetch(`${API_URL}/auth/change_password`, {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          old_password: oldPassword,
          new_password: newPassword,
        }),
      });

      if (res.status === 429) {
        setMessage(getRateLimitMessage(res));
        return;
      }

      const data = await res.json();

      if (res.ok) {
        setMessage("✅ Password updated successfully!");
        setSuccess(true);
        setOldPassword("");
        setNewPassword("");
        setTimeout(() => onPasswordChanged(), 1500);
      } else {
        setMessage("❌ " + getFriendlyErrorMessage(data, res));
      }
    } catch (err) {
      const resolved = await reconcileAfterNetworkError();
      if (!resolved) {
        setMessage(
          "⚠️ Network error: Could not confirm password status. Please retry, or try logging in with your new password."
        );
      }
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

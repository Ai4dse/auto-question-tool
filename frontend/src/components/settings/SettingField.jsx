// frontend/src/components/settings/SettingField.jsx
import React from "react";

export default function SettingField({ name, def, value, onChange }) {
  const label = def?.label || name.charAt(0).toUpperCase() + name.slice(1);
  const kind = def?.kind || "text";

  if (kind === "select") {
    const options = Array.isArray(def?.options) ? def.options : [];
    const safeValue = options.includes(String(value)) ? String(value) : (options[0] || "");

    return (
      <div className="mb-2">
        <label className="fw-semibold me-2">{label}:</label>
        <select
          value={safeValue}
          onChange={(e) => onChange(name, e.target.value)}
          className="form-select form-select-sm w-auto d-inline-block"
        >
          {options.map((opt) => (
            <option key={opt} value={opt}>
              {opt}
            </option>
          ))}
        </select>
      </div>
    );
  }

  if (kind === "number") {
    const str = value === undefined || value === null ? "" : String(value);
    const placeholder = def?.placeholder || (name === "seed" ? "random" : "");

    return (
      <div className="mb-2">
        <label className="fw-semibold me-2">{label}:</label>
        <input
          type="number"
          value={str}
          onChange={(e) => onChange(name, e.target.value)}
          className="form-control form-control-sm d-inline-block"
          style={{ width: 140 }}
          placeholder={placeholder}
        />
      </div>
    );
  }

  // fallback: text
  const str = value === undefined || value === null ? "" : String(value);
  return (
    <div className="mb-2">
      <label className="fw-semibold me-2">{label}:</label>
      <input
        type="text"
        value={str}
        onChange={(e) => onChange(name, e.target.value)}
        className="form-control form-control-sm d-inline-block"
        style={{ width: 180 }}
      />
    </div>
  );
}

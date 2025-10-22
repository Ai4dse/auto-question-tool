// frontend/src/components/QuestionControls.jsx
import { useState } from "react";

export default function QuestionControls({ initialSeed = "", onSeedChange }) {
  const [seedInput, setSeedInput] = useState(initialSeed);

  const handleChange = (e) => {
    const val = e.target.value;
    if (/^\d{0,6}$/.test(val)) {
      setSeedInput(val);
      onSeedChange?.(val);
    }
  };

  return (
    <div className="p-3 bg-light border rounded shadow-sm" style={{ width: "200px" }}>
      <label className="form-label mb-1 fw-semibold">Seed:</label>
      <input
        type="text"
        value={seedInput}
        onChange={handleChange}
        inputMode="numeric"
        maxLength={6}
        placeholder="(random)"
        className="form-control form-control-sm"
      />
    </div>
  );
}

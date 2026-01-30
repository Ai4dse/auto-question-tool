// frontend/src/components/settings/settingUtils.js

export const isDigits = (v) => typeof v === "string" && /^\d+$/.test(v);

export function generateRandomSeed() {
  return Math.floor(Math.random() * 1_000_000).toString();
}

export function getDefaultsFromSchema(schema) {
  const defaults = {};
  for (const [key, def] of Object.entries(schema || {})) {
    if (def?.default !== undefined) defaults[key] = def.default;
    else if (def?.kind === "select" && Array.isArray(def.options) && def.options.length) defaults[key] = def.options[0];
    else defaults[key] = "";
  }
  return defaults;
}

export function coerceForUrl(def, value) {
  if (value == null) return undefined;

  if (def?.kind === "number") {
    const s = String(value);
    return isDigits(s) ? s : undefined;
  }

  // select/text/unknown -> string
  return String(value);
}

export function buildQueryFromSettings(schema, values) {
  const params = new URLSearchParams();

  for (const [key, def] of Object.entries(schema || {})) {
    const raw = values?.[key];

    // omit empty -> backend default
    if (raw === "" || raw === undefined || raw === null) continue;

    const coerced = coerceForUrl(def, raw);
    if (coerced === undefined || coerced === "") continue;

    // validate selects
    if (def?.kind === "select" && Array.isArray(def.options) && def.options.length) {
      if (!def.options.includes(coerced)) continue;
    }

    params.set(key, coerced);
  }

  return params;
}

export function ensureSeedValue({ schema, effectiveValues, seedCache, questionId }) {
  const seedDef = schema?.seed;
  if (!seedDef) return effectiveValues;

  const next = { ...effectiveValues };
  const raw = next.seed === undefined || next.seed === null ? "" : String(next.seed);

  if (/^\d+$/.test(raw)) {
    seedCache.current[questionId] = raw;
    next.seed = raw;
    return next;
  }

  if (!seedCache.current[questionId]) {
    seedCache.current[questionId] = Math.floor(Math.random() * 1_000_000).toString();
  }

  next.seed = seedCache.current[questionId];
  return next;
}

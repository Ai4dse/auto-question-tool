// frontend/src/components/settings/settingUtils.js

export const isDigits = (v) => typeof v === "string" && /^\d+$/.test(v);

export function generateRandomSeed() {
  return Math.floor(Math.random() * 1_000_000).toString();
}

export function getDefaultsFromSchema({ schema, randomCache, questionId }) {
  const defaults = {};

  if (!randomCache.current[questionId]) {
    randomCache.current[questionId] = {};
  }
  const cache = randomCache.current[questionId];

  for (const [key, def] of Object.entries(schema || {})) {
    // explicit default wins
    if (def?.default !== undefined) {
      defaults[key] = def.default;
      continue;
    }

    // no default => randomized per kind (cached)
    if (def?.kind === "select" && Array.isArray(def.options) && def.options.length) {
      if (cache[key] === undefined) {
        const idx = Math.floor(Math.random() * def.options.length);
        cache[key] = def.options[idx];
      }
      defaults[key] = cache[key];
      continue;
    }

    if (def?.kind === "number") {
      if (cache[key] === undefined) {
        cache[key] = generateRandomSeed();
      }
      defaults[key] = cache[key];
      continue;
    }

    defaults[key] = "";
  }

  return defaults;
}

export function coerceForUrl(def, value) {
  if (value == null) return undefined;

  if (def?.kind === "number") {
    const s = String(value);
    return isDigits(s) ? s : undefined;
  }

  return String(value);
}

export function buildQueryFromSettings(schema, values) {
  const params = new URLSearchParams();

  for (const [key, def] of Object.entries(schema || {})) {
    const raw = values?.[key];

    if (raw === "" || raw === undefined || raw === null) continue;

    const coerced = coerceForUrl(def, raw);
    if (coerced === undefined || coerced === "") continue;

    if (def?.kind === "select" && Array.isArray(def.options) && def.options.length) {
      if (!def.options.includes(coerced)) continue;
    }

    params.set(key, coerced);
  }

  return params;
}

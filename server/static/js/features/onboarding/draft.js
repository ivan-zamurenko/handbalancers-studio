// Only non-sensitive choices. A draft never supplies identity, revision or paid access.
const guestKey = 'studio:guest:onboarding-draft';
const accountKey = id => `studio:account:${id}:onboarding-draft`;
const ttl = 24 * 60 * 60 * 1000;
const fields = ['goal_codes', 'self_reported_level', 'session_minutes', 'weekdays', 'time_of_day'];

export function cleanChoices(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null;
  if (Object.keys(value).some(key => !fields.includes(key))) return null;
  const distinct = (items, min, max, allowed) => Array.isArray(items) && items.length >= min && items.length <= max
    && new Set(items).size === items.length && items.every(item => allowed.includes(item));
  if (!distinct(value.goal_codes, 1, 4, ['handstand','strength','mobility','fitness'])
    || !distinct(value.weekdays, 1, 3, [1,2,3,4,5,6,7])
    || ![1,2,3].includes(value.self_reported_level)
    || ![30,45,60,90].includes(value.session_minutes)
    || ![null,'morning','afternoon','evening'].includes(value.time_of_day ?? null)) return null;
  return Object.fromEntries(fields.map(key => [key, value[key] ?? null]));
}

function read(key) {
  try {
    const raw = sessionStorage.getItem(key);
    if (!raw) return null;
    if (raw.length > 2048) throw new Error('Oversized draft');
    const saved = JSON.parse(raw);
    const data = cleanChoices(saved.data);
    if (saved.version !== 1 || !data || !Number.isFinite(saved.expiresAt)
      || saved.expiresAt <= Date.now() || saved.expiresAt > Date.now() + ttl) throw new Error('Invalid draft');
    return {...saved, data};
  } catch {
    try { sessionStorage.removeItem(key); } catch { /* Storage is optional. */ }
    return null;
  }
}

export const readGuestDraft = () => read(guestKey);
export const readAccountDraft = id => id ? read(accountKey(id)) : null;

export function saveGuestDraft(data) {
  const choices = cleanChoices(data);
  if (!choices) throw new Error('Invalid draft');
  sessionStorage.setItem(guestKey, JSON.stringify({version:1, expiresAt:Date.now() + ttl, data:choices}));
}

export function claimGuestDraft(id) {
  if (!id) return null;
  const guest = readGuestDraft();
  if (guest) {
    try {
      sessionStorage.setItem(accountKey(id), JSON.stringify(guest));
      sessionStorage.removeItem(guestKey);
    } catch { return null; }
  }
  return readAccountDraft(id);
}

export function clearAccountDraft(id) {
  try { if (id) sessionStorage.removeItem(accountKey(id)); } catch { /* Never block saving/logout. */ }
}

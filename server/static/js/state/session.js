// Private draft/cache writers must use studio:account:<profile-id>:<key>.
// Guest theme and public preferences are intentionally outside this namespace.
export function clearAccountState(accountId) {
  if (typeof accountId !== 'string' || !accountId) return;
  const prefix = `studio:account:${accountId}:`;
  for (const area of ['localStorage', 'sessionStorage']) {
    try {
      const storage = globalThis[area];
      for (let index = storage.length - 1; index >= 0; index--) {
        const key = storage.key(index);
        if (key?.startsWith(prefix)) storage.removeItem(key);
      }
    } catch {
      // Storage may be disabled; that must not prevent server logout or navigation.
    }
  }
}

const TOKEN_KEY = 'sentinel_token';
const USER_KEY = 'sentinel_user';

export function getToken() {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setAuth(token, user) {
  try {
    localStorage.setItem(TOKEN_KEY, token);
    if (user) {
      localStorage.setItem(USER_KEY, JSON.stringify(user));
    }
  } catch {}
}

export function clearAuth() {
  try {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  } catch {}
}

export function getUser() {
  try {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

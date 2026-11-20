async function request(path, options = {}) {
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers ?? {}),
  };
  const token = typeof window !== 'undefined' ? localStorage.getItem('sentinel_token') : null;
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  const response = await fetch(path, { ...options, headers });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const issue = body.issues?.[0];
    const message = issue
      ? `${issue.path ? `${issue.path}: ` : ''}${issue.message}`
      : body.error || `Request failed (${response.status})`;
    throw new Error(message);
  }
  return body;
}

function commandHeaders(operator) {
  return operator ? { 'X-Operator-Name': operator } : {};
}

export const api = {
  dashboard: () => request('/api/dashboard'),
  nodeHistory: (nodeId, hours = 6) => request(`/api/nodes/${nodeId}/history?hours=${hours}`),
  alerts: (status = 'all') => request(`/api/alerts?status=${status}&limit=100`),
  incidents: (params = {}) => {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '' && value !== 'all') {
        query.set(key, value);
      }
    });
    return request(`/api/incidents?${query.toString()}`);
  },
  acknowledge: (alertId, operator) =>
    request(`/api/alerts/${alertId}/acknowledge`, {
      method: 'POST',
      headers: commandHeaders(operator),
      body: JSON.stringify({ operator }),
    }),
  acknowledgeAll: (operator) =>
    request('/api/alerts/acknowledge-all', {
      method: 'POST',
      headers: commandHeaders(operator),
      body: JSON.stringify({ operator }),
    }),
  issueEvacuation: (payload, operator) =>
    request('/api/commands/evacuation', {
      method: 'POST',
      headers: commandHeaders(operator),
      body: JSON.stringify({ ...payload, operator }),
    }),
  allClear: (operator) =>
    request('/api/commands/all-clear', {
      method: 'POST',
      headers: commandHeaders(operator),
      body: JSON.stringify({ operator }),
    }),
  override: (payload, operator) =>
    request('/api/commands/override', {
      method: 'POST',
      headers: commandHeaders(operator),
      body: JSON.stringify({ ...payload, operator }),
    }),
  clearOverride: (nodeId, operator) =>
    request(`/api/nodes/${nodeId}/override`, {
      method: 'DELETE',
      headers: commandHeaders(operator),
    }),
  testSos: (nodeId, operator) =>
    request('/api/commands/test-sos', {
      method: 'POST',
      headers: commandHeaders(operator),
      body: JSON.stringify({ nodeId, operator }),
    }),
  setSiren: (enabled, operator) =>
    request('/api/commands/siren', {
      method: 'POST',
      headers: commandHeaders(operator),
      body: JSON.stringify({ enabled, operator }),
    }),
};

export function incidentExportUrl(params = {}) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '' && value !== 'all') {
      query.set(key, value);
    }
  });
  return `/api/incidents/export.csv?${query.toString()}`;
}

export async function login(username, password) {
  const response = await request('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  });
  return response;
}

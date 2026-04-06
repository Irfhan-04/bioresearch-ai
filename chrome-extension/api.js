/**
 * api.js — API client. Reads config from chrome.storage.local.
 */
const DEFAULT_BASE = "http://localhost:8000";

async function getConfig() {
  return new Promise((resolve) => {
    chrome.storage.local.get(["api_base", "auth_token"], (items) => {
      resolve({
        base: items.api_base || DEFAULT_BASE,
        token: items.auth_token || null,
      });
    });
  });
}

async function apiFetch(path, options = {}) {
  const { base, token } = await getConfig();
  if (!token) {
    return {
      ok: false,
      error: "Not signed in. Open popup to authenticate.",
    };
  }

  try {
    const response = await fetch(`${base}/api/v1${path}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
        ...(options.headers || {}),
      },
    });
    const data = await response.json().catch(() => ({}));
    return { ok: response.ok, data, status: response.status };
  } catch (error) {
    return { ok: false, error: error.message };
  }
}

const API = {
  getMe: () => apiFetch("/users/me"),
  createLead: (payload) =>
    apiFetch("/leads", { method: "POST", body: JSON.stringify(payload) }),
  rescoreLead: (id) =>
    apiFetch(`/scoring/leads/${id}/recalculate`, {
      method: "POST",
      body: "{}",
    }),
};

if (typeof globalThis !== "undefined") {
  globalThis.API = API;
}

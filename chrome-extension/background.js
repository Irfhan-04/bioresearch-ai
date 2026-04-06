/**
 * background.js — Service worker. Handles API calls from content script.
 */
const DEFAULT_BASE = "http://localhost:8000";

function getConfig() {
  return new Promise((resolve) => {
    chrome.storage.local.get(["api_base", "auth_token"], (items) => {
      resolve({
        base: items.api_base || DEFAULT_BASE,
        token: items.auth_token || null,
      });
    });
  });
}

async function apiFetch(path, method = "GET", body = null) {
  const { base, token } = await getConfig();
  if (!token) {
    return { ok: false, error: "Not signed in" };
  }

  const options = {
    method,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
  };

  if (body) {
    options.body = JSON.stringify(body);
  }

  try {
    const response = await fetch(`${base}/api/v1${path}`, options);
    const data = await response.json().catch(() => ({}));
    return { ok: response.ok, data, status: response.status };
  } catch (error) {
    return { ok: false, error: error.message };
  }
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action !== "addLead") {
    return undefined;
  }

  (async () => {
    const create = await apiFetch("/leads", "POST", message.payload);
    if (!create.ok) {
      sendResponse({ ok: false, error: create.data?.detail || create.error });
      return;
    }

    const rescore = await apiFetch(
      `/scoring/leads/${create.data.id}/recalculate`,
      "POST",
      {}
    );
    const score = rescore.data?.new_score ?? create.data.propensity_score;
    sendResponse({ ok: true, data: { ...create.data, score } });
  })();

  return true;
});

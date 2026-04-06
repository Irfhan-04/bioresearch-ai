const $ = (id) => document.getElementById(id);

async function checkAuth() {
  chrome.storage.local.get(["auth_token", "api_base", "user_email"], (items) => {
    if (items.auth_token) {
      $("signed-in").style.display = "block";
      $("sign-in").style.display = "none";
      $("user-email").textContent = items.user_email || "Authenticated";
    } else {
      $("signed-in").style.display = "none";
      $("sign-in").style.display = "block";
      if (items.api_base) {
        $("api-base").value = items.api_base;
      }
    }
  });
}

$("sign-in-btn").addEventListener("click", async () => {
  const base = $("api-base").value.trim() || "http://localhost:8000";
  const token = $("token").value.trim();

  if (!token) {
    $("sign-in-msg").textContent = "Paste a JWT token";
    return;
  }

  $("sign-in-msg").textContent = "Verifying…";
  try {
    const response = await fetch(`${base}/api/v1/users/me`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const user = await response.json();
    chrome.storage.local.set(
      { auth_token: token, api_base: base, user_email: user.email },
      () => {
        $("sign-in-msg").className = "status ok";
        $("sign-in-msg").textContent = "✅ Signed in!";
        setTimeout(checkAuth, 800);
      }
    );
  } catch (error) {
    $("sign-in-msg").className = "status err";
    $("sign-in-msg").textContent = `❌ ${error.message}`;
  }
});

$("sign-out-btn").addEventListener("click", () => {
  chrome.storage.local.remove(["auth_token", "user_email"], checkAuth);
});

checkAuth();

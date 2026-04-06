/**
 * content.js — Injected into linkedin.com/in/* pages.
 * Scrapes profile data and renders a floating "Add Lead" button.
 */
(function initializeLeadButton() {
  if (document.getElementById("btlg-btn")) {
    return;
  }

  function extractProfile() {
    const selectText = (selector) =>
      document.querySelector(selector)?.innerText?.trim() || "";

    return {
      name:
        selectText("h1.text-heading-xlarge") ||
        selectText(".pv-text-details__left-panel h1"),
      title: selectText(".text-body-medium.break-words"),
      company: selectText(".pv-text-details__right-panel .hoverable-link-text"),
      location: selectText(
        ".pv-text-details__left-panel .text-body-small.inline.t-black--light"
      ),
      linkedin_url: window.location.href.split("?")[0].replace(/\/$/, ""),
    };
  }

  function toast(message, type) {
    const toastElement = document.createElement("div");
    const background =
      type === "success" ? "#16a34a" : type === "error" ? "#dc2626" : "#667eea";

    toastElement.textContent = message;
    Object.assign(toastElement.style, {
      position: "fixed",
      bottom: "80px",
      right: "24px",
      zIndex: "99999",
      background,
      color: "#fff",
      padding: "10px 16px",
      borderRadius: "8px",
      fontSize: "13px",
    });
    document.body.appendChild(toastElement);
    setTimeout(() => toastElement.remove(), 4000);
  }

  const button = document.createElement("button");
  button.id = "btlg-btn";
  button.textContent = "🎯 Add Lead";
  Object.assign(button.style, {
    position: "fixed",
    bottom: "24px",
    right: "24px",
    zIndex: "99999",
    background: "#667eea",
    color: "#fff",
    border: "none",
    borderRadius: "8px",
    padding: "10px 18px",
    fontSize: "14px",
    fontWeight: "600",
    cursor: "pointer",
    boxShadow: "0 4px 12px rgba(0,0,0,.2)",
  });

  button.onclick = async () => {
    const profile = extractProfile();
    if (!profile.name) {
      toast("Could not read profile — scroll down and retry", "error");
      return;
    }

    button.textContent = "⏳ Adding…";
    button.disabled = true;

    const response = await chrome.runtime.sendMessage({
      action: "addLead",
      payload: { ...profile, data_sources: ["linkedin_extension"] },
    });

    if (response?.ok) {
      const score = response.data?.score || "—";
      toast(`✅ Added! Score: ${score}`, "success");
      button.textContent = `✅ Added (${score})`;
    } else {
      toast(`❌ ${response?.error || "Failed"}`, "error");
      button.textContent = "🎯 Add Lead";
    }

    button.disabled = false;
  };

  document.body.appendChild(button);
})();

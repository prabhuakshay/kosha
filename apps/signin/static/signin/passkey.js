// A `data-passkey` button runs a Passkey ceremony against the server's JSON
// views: "register" adds one and goes to `data-next`; "sign-in" uses one and
// goes where the server says. The browser's own JSON helpers translate the
// server's options and the authenticator's answer.
async function post(button, url, body = {}) {
  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": button.dataset.csrfToken,
    },
    body: JSON.stringify(body),
  });
  // A stale CSRF token or an expired sign-in answers with HTML, not JSON.
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail);
  return data;
}

async function register(button) {
  const options = await post(button, button.dataset.begin);
  const credential = await navigator.credentials.create({
    publicKey: PublicKeyCredential.parseCreationOptionsFromJSON(options),
  });
  await post(button, button.dataset.complete, credential.toJSON());
  return button.dataset.next;
}

async function signIn(button) {
  const options = await post(button, button.dataset.begin);
  const credential = await navigator.credentials.get({
    publicKey: PublicKeyCredential.parseRequestOptionsFromJSON(options),
  });
  const result = await post(button, button.dataset.complete, credential.toJSON());
  return result.redirect_url;
}

// Loaded once for every page: htmx swaps pages in without running their
// scripts, so it listens on the document rather than on each button.
document.addEventListener("click", async (event) => {
  const button = event.target.closest("[data-passkey]");
  if (!button) return;
  const status = document.getElementById(button.getAttribute("aria-describedby"));
  button.disabled = true;
  status.textContent = "";
  try {
    const ceremony = button.dataset.passkey === "register" ? register : signIn;
    location.assign(await ceremony(button));
  } catch (error) {
    button.disabled = false;
    status.textContent =
      error.name === "NotAllowedError"
        ? "Cancelled. Try again when you're ready."
        : error.message || "That didn't work. Try again.";
  }
});

function refuseWithoutPasskeys(root) {
  if (window.PublicKeyCredential?.parseCreationOptionsFromJSON) return;
  for (const button of root.querySelectorAll("[data-passkey]")) {
    button.disabled = true;
    document.getElementById(button.getAttribute("aria-describedby")).textContent =
      "This browser can't use passkeys.";
  }
}

refuseWithoutPasskeys(document);
document.addEventListener("htmx:load", (event) => refuseWithoutPasskeys(event.target));

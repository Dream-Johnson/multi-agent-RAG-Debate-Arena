// app.js — no framework, no build step: just DOM references and fetch().
// This file owns three things: the password gate, kicking off a debate
// (with a staged loading experience), and rendering the result.

// ----- DOM references, grabbed once up front ------------------------------
const loginScreen = document.getElementById("login-screen");
const loginForm = document.getElementById("login-form");
const passwordInput = document.getElementById("password-input");
const loginError = document.getElementById("login-error");

const appScreen = document.getElementById("app-screen");
const topicForm = document.getElementById("topic-form");
const topicInput = document.getElementById("topic-input");
const topicError = document.getElementById("topic-error");
const submitButton = document.getElementById("submit-button");

const loadingState = document.getElementById("loading-state");
const loadingLabel = document.getElementById("loading-label");
const loadingFill = document.getElementById("loading-fill");

const results = document.getElementById("results");
const resultsTopic = document.getElementById("results-topic");
const forArgument = document.getElementById("for-argument");
const againstArgument = document.getElementById("against-argument");
const verdictText = document.getElementById("verdict-text");
const newDebateButton = document.getElementById("new-debate-button");

// ----- Password storage ----------------------------------------------------
// sessionStorage (not localStorage): cleared when the tab closes, so the
// password isn't cached on disk indefinitely. The REAL protection is
// always the server-side header check on every API call — this is just
// "don't make the user retype it on every request in the same tab."
const PASSWORD_KEY = "debatePassword";

function getSavedPassword() {
  return sessionStorage.getItem(PASSWORD_KEY);
}

function savePassword(password) {
  sessionStorage.setItem(PASSWORD_KEY, password);
}

function clearSavedPassword() {
  sessionStorage.removeItem(PASSWORD_KEY);
}

// ----- Screen switching -----------------------------------------------------
function showApp() {
  loginScreen.classList.add("hidden");
  appScreen.classList.remove("hidden");
}

function showLogin(message) {
  appScreen.classList.add("hidden");
  loginScreen.classList.remove("hidden");
  loginError.textContent = message || "";
}

// If we already have a password from earlier in this tab session, skip
// straight to the app. If it's actually stale (revoked/changed), the
// first real API call below will 401 and bounce us back to login.
if (getSavedPassword()) {
  showApp();
}

// ----- Login form -----------------------------------------------------------
loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  loginError.textContent = "";
  const password = passwordInput.value;

  try {
    const response = await fetch("/api/login", {
      method: "POST",
      headers: { "X-App-Password": password },
    });

    if (response.status === 401) {
      loginError.textContent = "Incorrect password.";
      return;
    }
    if (!response.ok) {
      loginError.textContent = "Something went wrong. Please try again.";
      return;
    }

    savePassword(password);
    passwordInput.value = "";
    showApp();
  } catch {
    loginError.textContent = "Couldn't reach the server. Check your connection.";
  }
});

// ----- Staged loading experience --------------------------------------------
// The real backend call is ONE blocking request — there's no live
// progress feed. These stages are illustrative, timed to roughly match
// the real pipeline's order (Wikipedia -> chunk/embed -> store -> agents
// -> judge), so the wait feels like *something is happening* instead of
// a frozen spinner. The moment the real fetch() resolves, we jump
// straight to results regardless of which stage this is on.
const LOADING_STAGES = [
  { label: "Researching the topic on Wikipedia…", progress: 0.15 },
  { label: "Chunking and embedding the article…", progress: 0.40 },
  { label: "Storing context in the vector database…", progress: 0.55 },
  { label: "Agents are building their arguments…", progress: 0.85 },
  { label: "The judge is weighing both sides…", progress: 0.97 },
];

let stageTimers = [];

function startLoadingAnimation() {
  loadingFill.style.setProperty("--progress", "0");
  let elapsed = 0;
  for (const stage of LOADING_STAGES) {
    elapsed += 2200; // roughly spaced; real completion can interrupt at any point
    const timer = setTimeout(() => {
      loadingLabel.textContent = stage.label;
      loadingFill.style.setProperty("--progress", String(stage.progress));
    }, elapsed);
    stageTimers.push(timer);
  }
}

function stopLoadingAnimation() {
  stageTimers.forEach(clearTimeout);
  stageTimers = [];
}

// ----- Topic form: kick off a debate ----------------------------------------
topicForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  topicError.textContent = "";
  const topic = topicInput.value.trim();
  if (!topic) return;

  topicForm.classList.add("hidden");
  results.classList.add("hidden");
  loadingState.classList.remove("hidden");
  loadingLabel.textContent = LOADING_STAGES[0].label;
  loadingFill.style.setProperty("--progress", "0.05");
  startLoadingAnimation();
  submitButton.disabled = true;

  try {
    const response = await fetch("/api/debate", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-App-Password": getSavedPassword() || "",
      },
      body: JSON.stringify({ topic }),
    });

    if (response.status === 401) {
      clearSavedPassword();
      showLogin("Your session expired. Please log in again.");
      return;
    }

    if (response.status === 404) {
      const body = await response.json();
      topicError.textContent = body.detail || "Couldn't find a Wikipedia article for that topic.";
      return;
    }

    if (!response.ok) {
      topicError.textContent = "Something went wrong generating the debate. Please try again.";
      return;
    }

    const debate = await response.json();
    resultsTopic.textContent = debate.topic;
    forArgument.textContent = debate.for_argument;
    againstArgument.textContent = debate.against_argument;
    verdictText.textContent = debate.verdict;
    results.classList.remove("hidden");
  } catch {
    topicError.textContent = "Couldn't reach the server. Check your connection.";
  } finally {
    stopLoadingAnimation();
    loadingState.classList.add("hidden");
    submitButton.disabled = false;
    if (results.classList.contains("hidden")) {
      // Only re-show the topic form if we didn't succeed (on success,
      // the "start a new debate" button is the way back to it).
      topicForm.classList.remove("hidden");
    }
  }
});

// ----- Reset to a fresh debate -----------------------------------------------
newDebateButton.addEventListener("click", () => {
  results.classList.add("hidden");
  topicForm.classList.remove("hidden");
  topicInput.value = "";
  topicInput.focus();
});

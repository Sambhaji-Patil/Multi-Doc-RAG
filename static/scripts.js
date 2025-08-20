// Full application script extracted from templates/index.html
// All globals, initialization, and UI logic live here.
let currentUser = null;
let currentSession = null;
let currentDocId = null;
let sessions = [];
let currentBlobUrl = null;
let webviewerInstance = null;
let currentHighlights = [];
let documentTextCache = new Map();
let currentReferences = [];
let pendingUploadData = null;

const SkyBlue = { r: 179, g: 229, b: 252, a: 0.35 };
const LightCyan = { r: 224, g: 247, b: 250, a: 0.35 };
const MintGreen1 = { r: 167, g: 243, b: 208, a: 0.35 };
const MintGreen2 = { r: 208, g: 251, b: 228, a: 0.35 };
const Lavender1 = { r: 237, g: 231, b: 246, a: 0.35 };
const Lavender2 = { r: 209, g: 196, b: 233, a: 0.35 };
const Pink1 = { r: 252, g: 228, b: 236, a: 0.35 };
const Pink2 = { r: 248, g: 187, b: 208, a: 0.35 };
const Gray1 = { r: 245, g: 245, b: 245, a: 0.35 };
const Gray2 = { r: 238, g: 238, b: 238, a: 0.35 };
const Teal = { r: 204, g: 251, b: 241, a: 0.35 };
const SoftLavender = { r: 233, g: 213, b: 255, a: 0.35 };
var highlightColor = SoftLavender;

let speechRecognition = null;
let isMicEnabled = false;
let isRecording = false;
let isPushToTalkActive = false;
let wakeWord = "hello shastra";
let isSpeechOutputEnabled = true;
let currentSpokenReferenceIndex = -1;
let micPressTimer = null;
const longPressThreshold = 250;
let silenceTimer = null;
const silenceTimeoutDuration = 1500;

const PORT = 7860;
const API_BASE = `http://localhost:${PORT}`;

// --- APPLICATION INITIALIZATION ---
document.addEventListener("DOMContentLoaded", function () {
  waitForWebViewer();
});

function waitForWebViewer() {
  if (window.WebViewer) {
    initializeApplication();
  } else {
    setTimeout(waitForWebViewer, 100);
  }
}

function initializeApplication() {
  console.log("DOM loaded, initializing application...");
  initializeWebViewer();
  registerServiceWorker();
}

function registerServiceWorker() {
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker
      .register("/service-worker.js")
      .then((registration) =>
        console.log(
          "Service Worker registered with scope:",
          registration.scope
        )
      )
      .catch((error) =>
        console.error("Service Worker registration failed:", error)
      );
  }
}

function initializeWebViewer() {
  const apryseViewerDiv = document.getElementById("apryseViewer");
  if (!apryseViewerDiv) {
    console.error(
      "Cannot initialize WebViewer: #apryseViewer not found."
    );
    document.getElementById("loadingText").textContent =
      "Initialization Error!";
    return;
  }
  WebViewer(
    {
      path: "/static/lib/apryse",
      fullAPI: true,
      ui: "beta",
      theme: "dark",
    },
    apryseViewerDiv
  )
    .then((instance) => {
      webviewerInstance = instance;
      console.log("Apryse WebViewer initialized successfully.");
      const { UI } = instance;
      UI.setTheme("dark");
      UI.setLanguage("en");
      apryseViewerDiv.style.display = "none";
      startApp();
    })
    .catch((error) => {
      console.error("Apryse WebViewer failed to initialize:", error);
      document.getElementById("loadingText").textContent =
        "Failed to load document viewer. Please refresh.";
    });
}

function startApp() {
  const loadingTexts = [
    "Initializing Quantum Core...",
    "Syncing Neural Interface...",
    "Reticulating Splines...",
  ];
  let textIndex = 0;
  const loadingTextEl = document.getElementById("loadingText");
  const loadingInterval = setInterval(() => {
    textIndex = (textIndex + 1) % loadingTexts.length;
    loadingTextEl.style.opacity = 0;
    setTimeout(() => {
      loadingTextEl.textContent = loadingTexts[textIndex];
      loadingTextEl.style.opacity = 1;
    }, 300);
  }, 2000);

  const loadingOverlay = document.getElementById("loadingOverlay");
  loadingOverlay.style.opacity = "0";
  setTimeout(() => {
    loadingOverlay.style.display = "none";
    clearInterval(loadingInterval);
  }, 500);

  checkAuthStatus();
  setupEventListeners();
  initializeSpeechServices();
  testApiConnection();
  initCustomCursor(); // MODIFICATION: Initialize the new particle cursor
}

function initCustomCursor() {
  const cursor = document.getElementById("custom-cursor");
  const particleColors = ["#00ffff", "#ff00ff", "#8A2BE2"]; // Cyan, Magenta, BlueViolet

  window.addEventListener("mousemove", (e) => {
    // Move the main cursor glow
    cursor.style.left = `${e.clientX}px`;
    cursor.style.top = `${e.clientY}px`;

    // Create a particle
    const particle = document.createElement("div");
    particle.className = "particle";
    document.body.appendChild(particle);

    const size = Math.floor(Math.random() * 8 + 4);
    const x = e.clientX + (Math.random() * 20 - 10);
    const y = e.clientY + (Math.random() * 20 - 10);
    const dx = (Math.random() - 0.5) * 50 + "px";
    const dy = (Math.random() - 0.5) * 50 + "px";

    particle.style.width = `${size}px`;
    particle.style.height = `${size}px`;
    particle.style.left = `${x}px`;
    particle.style.top = `${y}px`;
    particle.style.background =
      particleColors[Math.floor(Math.random() * particleColors.length)];
    particle.style.setProperty("--dx", dx);
    particle.style.setProperty("--dy", dy);

    // Remove particle from DOM after animation
    particle.addEventListener("animationend", () => {
      particle.remove();
    });
  });
}

// --- AUTH AND UI LOGIC ---
function checkAuthStatus() {
  const savedUserId = localStorage.getItem("userId");
  if (savedUserId) {
    currentUser = savedUserId;
    showApp();
    loadSessions();
  } else {
    showAuth();
  }
}

function showApp() {
  document.getElementById("authScreen").style.display = "none";
  document.getElementById("appContainer").style.display = "block";
  const animatedElements = document.querySelectorAll("[data-cool-fx]");
  animatedElements.forEach((el, index) => {
    setTimeout(() => {
      el.classList.add("in-view");
    }, 150 * (index + 1));
  });
}

function showAuth() {
  document.getElementById("authScreen").style.display = "flex";
  document.getElementById("appContainer").style.display = "none";
  setTimeout(() => {
    document
      .querySelector("#authScreen [data-cool-fx]")
      .classList.add("in-view");
  }, 100);
}

// --- MODIFICATION: highlightTextInDocument function ---
async function highlightTextInDocument(matchResult) {
  if (
    !webviewerInstance ||
    !matchResult ||
    !matchResult.quads ||
    matchResult.quads.length === 0
  ) {
    console.error(
      "Cannot highlight: Invalid matchResult or missing quads.",
      matchResult
    );
    return null;
  }
  const { annotationManager, documentViewer, Annotations } =
    webviewerInstance.Core;
  try {
    await documentViewer.setCurrentPage(matchResult.pageNumber);
    const highlight = new Annotations.TextHighlightAnnotation({
      PageNumber: matchResult.pageNumber,
      Quads: matchResult.quads,
    });

    // Apply custom color from the global constant
    const { Color } = Annotations;
    highlight.Color = new Color(
      highlightColor.r,
      highlightColor.g,
      highlightColor.b,
      highlightColor.a
    );
    highlight.StrokeColor = new Color(
      highlightColor.r,
      highlightColor.g,
      highlightColor.b,
      1
    );

    await annotationManager.addAnnotation(highlight);
    annotationManager.redrawAnnotation(highlight);
    currentHighlights.push(highlight.Id);
    return highlight.Id;
  } catch (error) {
    console.error(
      "Error creating or adding highlight annotation:",
      error
    );
    return null;
  }
}

// Remove all created highlights from the document
function clearAllHighlights() {
  try {
    if (!webviewerInstance) return;
    const { annotationManager } = webviewerInstance.Core;
    if (!annotationManager) return;
    currentHighlights.forEach((id) => {
      try {
        const ann = annotationManager.getAnnotationById(id);
        if (ann) annotationManager.deleteAnnotation(ann);
      } catch (e) {
        // ignore individual failures
      }
    });
    currentHighlights = [];
  } catch (e) {
    console.error("clearAllHighlights error:", e);
  }
}

// Show a small status box when searching/highlighting references
function showHighlightStatus(text, type = "info", timeout = 3000) {
  try {
    let el = document.getElementById("highlightStatus");
    if (!el) {
      el = document.createElement("div");
      el.id = "highlightStatus";
      el.className = "highlight-status";
      document.body.appendChild(el);
    }

    el.textContent = text;
    el.className = "highlight-status"; // reset
    if (type) el.classList.add(type);

    // show
    el.style.display = "block";

    if (timeout > 0) {
      setTimeout(() => {
        if (el) {
          el.style.display = "none";   
        }
      }, timeout);
    }
  } catch (e) {
    console.error("showHighlightStatus error:", e);
  }
}


// Find a reference snippet inside the currently loaded document using WebViewer's text search
// Returns { pageNumber, quads } or null
function findReferenceInDocument(snippet, docId, pageNumber = null, timeoutMs = 10000) {
  return new Promise(async (resolve) => {
    try {
      if (!webviewerInstance || !snippet) return resolve(null);
      const docViewer = webviewerInstance.Core.documentViewer;
      if (!docViewer) return resolve(null);

      console.log(`🔍 Searching for reference on page ${pageNumber}:`, snippet);

      // If pageNumber provided, jump to that page first
      if (pageNumber) {
        try {
          docViewer.setCurrentPage(pageNumber);
          await new Promise(resolve => setTimeout(resolve, 500)); // Wait for page to render
        } catch (e) {
          console.warn("Could not navigate to page:", pageNumber);
        }
      }

      // Strategy 1: Use Fuzzysort for robust matching
      const fuzzyMatch = await searchWithFuzzysort(snippet, pageNumber);
      if (fuzzyMatch) {
        console.log("✅ Found match with Fuzzysort");
        return resolve(fuzzyMatch);
      }

      // Fallback Strategy 2: Use WebViewer's native search as a backup
      console.log("⚠️ Fuzzysort found no match, falling back to native search...");
      const nativeMatch = await searchWithNativeApi(snippet, pageNumber);
      if (nativeMatch) {
        console.log("✅ Found match with native search API");
        return resolve(nativeMatch);
      }

      console.warn("❌ All search strategies failed for reference");
      return resolve(null);

    } catch (e) {
      console.error("findReferenceInDocument error:", e);
      return resolve(null);
    }
  });
}

// New function using Fuzzysort
async function searchWithFuzzysort(snippet, pageNumber) {
  if (typeof fuzzysort === 'undefined') {
    console.error("Fuzzysort library is not loaded.");
    return null;
  }

  const docViewer = webviewerInstance.Core.documentViewer;
  const doc = docViewer.getDocument();
  if (!doc) return null;

  const targetPage = pageNumber || docViewer.getCurrentPage();
  
  // Check cache first
  let pageText = documentTextCache.get(targetPage);
  if (!pageText) {
    console.log(`📝 Caching text for page ${targetPage}`);
    pageText = await doc.loadPageText(targetPage);
    documentTextCache.set(targetPage, pageText);
  }

  // Fuzzysort works best on an array of targets
  const lines = pageText.split('\n').map(line => line.trim()).filter(Boolean);
  const results = fuzzysort.go(snippet, lines, {
    threshold: -1000, // Lower is more permissive
    limit: 5
  });

  if (results.length > 0) {
    const bestMatch = results[0];
    console.log(`✅ Fuzzy match found with score ${bestMatch.score}: "${bestMatch.target}"`);
    
    // Now, use native search to get the quads for the best match
    return await searchWithNativeApi(bestMatch.target, targetPage, true);
  }
  
  return null;
}

// Refactored native search logic
async function searchWithNativeApi(searchText, pageNumber, exact = false) {
  return new Promise((resolve) => {
    const docViewer = webviewerInstance.Core.documentViewer;
    let resolved = false;

    const options = {
      fullSearch: true,
      onResult: (result) => {
        if (resolved || !result || !result.quads || result.quads.length === 0) return;
        
        if (pageNumber && result.pageNumber !== pageNumber) {
          console.log(`⚠️ Native search found match on page ${result.pageNumber}, but expected ${pageNumber}`);
          return;
        }
        
        resolved = true;
        resolve({ pageNumber: result.pageNumber, quads: result.quads });
      },
      onDocumentEnd: () => !resolved && resolve(null),
      onError: () => !resolved && resolve(null),
    };

    if (exact) {
      options.caseSensitive = false;
      options.wholeWord = true;
    }

    docViewer.clearSearchResults();
    docViewer.textSearchInit(searchText, null, options);

    setTimeout(() => !resolved && resolve(null), 3000); // 3-second timeout
  });
}

/* ================================================================== */
/* --- THE REST OF THE JAVASCRIPT LOGIC IS UNCHANGED. --- */
/* ================================================================== */
async function testApiConnection() {
  try {
    const response = await fetch(`${API_BASE}/hello`);
    if (!response.ok) {
      showNotification("Cannot connect to backend server.", "error");
    }
  } catch (error) {
    console.error("API connection test failed:", error);
    showNotification(
      `Cannot connect to backend. Make sure it's running on port ${PORT}`,
      "error"
    );
  }
}
function setupEventListeners() {
  document.getElementById("showSignup").addEventListener("click", () => {
    document.getElementById("loginForm").style.display = "none";
    document.getElementById("signupForm").style.display = "block";
  });
  document.getElementById("showLogin").addEventListener("click", () => {
    document.getElementById("signupForm").style.display = "none";
    document.getElementById("loginForm").style.display = "block";
  });
  document
    .getElementById("loginBtn")
    .addEventListener("click", handleLogin);
  document
    .getElementById("signupBtn")
    .addEventListener("click", handleSignup);
  document
    .getElementById("logoutBtn")
    .addEventListener("click", handleLogout);
  document
    .getElementById("loginPassword")
    .addEventListener("keypress", (e) => {
      if (e.key === "Enter") handleLogin();
    });
  document
    .getElementById("signupPassword")
    .addEventListener("keypress", (e) => {
      if (e.key === "Enter") handleSignup();
    });
  document
    .getElementById("sidebarToggleBtn")
    .addEventListener("click", () => {
      const sidebar = document.getElementById("sidebar");
      const toggleBtn = document.getElementById("sidebarToggleBtn");
      sidebar.classList.toggle("collapsed");
      toggleBtn.classList.toggle("collapsed");
    });
  document
    .getElementById("newSessionBtn")
    .addEventListener("click", () => createNewSession());
  document.getElementById("addDocsBtn").addEventListener("click", () => {
    if (!currentSession) {
      return showNotification("Please select a session first.", "error");
    }
    document.getElementById("addDocsModal").style.display = "flex";
  });
  document
    .getElementById("fileInput")
    .addEventListener("change", (e) => handleFileUpload(e.target.files));
  document
    .getElementById("uploadUrlBtn")
    .addEventListener("click", () =>
      uploadFromUrl(document.getElementById("urlInput").value.trim())
    );
  document
    .getElementById("urlInput")
    .addEventListener("keypress", (e) => {
      if (e.key === "Enter")
        uploadFromUrl(document.getElementById("urlInput").value.trim());
    });
  const addDocsModal = document.getElementById("addDocsModal");
  document
    .getElementById("closeModalBtn")
    .addEventListener("click", () => {
      addDocsModal.style.display = "none";
    });
  document.getElementById("modalFileInput").addEventListener("change", (e) => {
    handleFileUpload(e.target.files);
    addDocsModal.style.display = "none";
  });
  document.getElementById("modalUploadUrlBtn").addEventListener("click", () => {
    uploadFromUrl(document.getElementById("modalUrlInput").value.trim());
    addDocsModal.style.display = "none";
  });
  addDocsModal.addEventListener("click", (e) => {
    if (e.target === addDocsModal) {
      addDocsModal.style.display = "none";
    }
  });
  document
    .getElementById("signupBtn")
    .addEventListener("click", handleSignup);
  document
    .getElementById("sendBtn")
    .addEventListener("click", sendMessage);
  document
    .getElementById("closeChatBtn")
    .addEventListener("click", () => {
      document.getElementById("chatPanel").style.display = "none";
    });
  const chatInput = document.getElementById("chatInput");
  chatInput.addEventListener("keypress", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });
  chatInput.addEventListener("input", function () {
    this.style.height = "auto";
    this.style.height = Math.min(this.scrollHeight, 120) + "px";
  });
  document
    .getElementById("toggleSpeechBtn")
    .addEventListener("click", toggleSpeechOutput);
  document
    .getElementById("settingsBtn")
    .addEventListener("click", setWakeWord);
  const micBtn = document.getElementById("micBtn");
  micBtn.addEventListener("mousedown", handleMicButtonPress);
  document.addEventListener("mouseup", handleMicButtonRelease);
  document.addEventListener("keydown", (e) => {
    const activeEl = document.activeElement;
    const isTyping =
      activeEl.tagName === "INPUT" || activeEl.tagName === "TEXTAREA";
    if (e.code === "Space" && !e.repeat && !isTyping) {
      e.preventDefault();
      startPushToTalk();
    }
    if (e.key === "Escape") {
      if (isRecording) {
        e.preventDefault();
        console.log("Voice input canceled by Escape key.");
        document.getElementById("chatInput").value = "";
        stopVoiceServices();
      }
    }
  });
  document.addEventListener("keyup", (e) => {
    if (e.code === "Space") {
      stopPushToTalk();
    }
  });
  initChatPanelInteractions();
}
function initChatPanelInteractions() {
  const chatPanel = document.getElementById("chatPanel");
  const chatHeader = chatPanel.querySelector(".chat-header");
  const minimizeBtn = document.getElementById("minimizeChatBtn");
  const restoreBtn = document.getElementById("restoreChatBtn");
  const container = document.querySelector(".viewer-container");
  let isDragging = false;
  let offset = { x: 0, y: 0 };
  let lastPosition = { top: "20px", left: "", right: "20px" };
  chatHeader.addEventListener("mousedown", (e) => {
    if (e.target.tagName === "BUTTON") return;
    isDragging = true;
    offset.x = e.clientX - chatPanel.offsetLeft;
    offset.y = e.clientY - chatPanel.offsetTop;
    chatPanel.style.transition = "none";
  });
  document.addEventListener("mousemove", (e) => {
    if (!isDragging) return;
    e.preventDefault();
    let newX = e.clientX - offset.x;
    let newY = e.clientY - offset.y;
    const containerRect = container.getBoundingClientRect();
    const panelRect = chatPanel.getBoundingClientRect();
    newX = Math.max(
      0,
      Math.min(newX, containerRect.width - panelRect.width)
    );
    newY = Math.max(
      0,
      Math.min(newY, containerRect.height - panelRect.height)
    );
    chatPanel.style.left = `${newX}px`;
    chatPanel.style.top = `${newY}px`;
    chatPanel.style.right = "auto";
  });
  document.addEventListener("mouseup", () => {
    if (isDragging) {
      isDragging = false;
      chatPanel.style.transition =
        "width 0.3s ease, height 0.3s ease, opacity 0.3s ease";
      if (!chatPanel.classList.contains("minimized")) {
        lastPosition = {
          top: chatPanel.style.top,
          left: chatPanel.style.left,
          right: "auto",
        };
      }
    }
  });
  const toggleMinimize = () => {
    const isMinimized = chatPanel.classList.toggle("minimized");
    if (isMinimized) {
      lastPosition = {
        top: chatPanel.style.top || "20px",
        left: chatPanel.style.left || "",
        right: chatPanel.style.right || "20px",
      };
    } else {
      chatPanel.style.top = lastPosition.top;
      chatPanel.style.left = lastPosition.left;
      chatPanel.style.right = lastPosition.right;
    }
  };
  minimizeBtn.addEventListener("click", toggleMinimize);
  restoreBtn.addEventListener("click", toggleMinimize);
}
async function handleLogin() {
  const email = document.getElementById("loginEmail").value;
  const password = document.getElementById("loginPassword").value;
  if (!email || !password)
    return showNotification("Please fill in all fields", "error");
  try {
    const response = await fetch(`${API_BASE}/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    const data = await response.json();
    if (response.ok && data.user_id) {
      currentUser = data.user_id;
      localStorage.setItem("userId", currentUser);
      showApp();
      loadSessions();
      showNotification("Login successful!", "success");
    } else {
      showNotification(data.error || "Login failed", "error");
    }
  } catch (error) {
    showNotification("Login failed. Please try again.", "error");
  }
}
async function handleSignup() {
  const email = document.getElementById("signupEmail").value;
  const password = document.getElementById("signupPassword").value;
  if (!email || !password)
    return showNotification("Please fill in all fields", "error");
  try {
    const response = await fetch(`${API_BASE}/signup`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    const data = await response.json();
    if (response.ok && data.user_id) {
      showNotification("Account created! Please login.", "success");
      document.getElementById("signupForm").style.display = "none";
      document.getElementById("loginForm").style.display = "block";
      document.getElementById("loginEmail").value = email;
    } else {
      showNotification(data.error || "Signup failed", "error");
    }
  } catch (error) {
    showNotification("Signup failed. Please try again.", "error");
  }
}
function handleLogout() {
  currentUser = null;
  currentSession = null;
  currentDocId = null;
  sessions = [];
  localStorage.removeItem("userId");
  cleanupBlobUrl();
  document.getElementById("chatMessages").innerHTML = "";
  document.getElementById("sessionsList").innerHTML = "";
  stopVoiceServices();
  isMicEnabled = false;
  isSpeechOutputEnabled = true;
  updateMicButtonState();
  updateSpeechButtonState();
  showUploadArea();
  showAuth();
}
async function loadSessions() {
  if (!currentUser) return;
  try {
    const response = await fetch(
      `${API_BASE}/my_sessions/${currentUser}`
    );
    const data = await response.json();
    if (response.ok) {
      sessions = data.sessions;
      renderSessions();
      if (sessions.length === 0) {
        showUploadArea();
      }
    } else {
      console.error("Failed to load sessions");
    }
  } catch (error) {
    console.error("Error loading sessions:", error);
  }
}
function renderSessions() {
  const sessionsList = document.getElementById("sessionsList");
  sessionsList.innerHTML = "";
  sessions.forEach((session) => {
    const sessionElement = document.createElement("div");
    sessionElement.className = `session-item ${
      currentSession === session.session_id ? "active" : ""
    }`;
    sessionElement.innerHTML = `
            <div class="session-name">${
              session.name || "Untitled Session"
            }</div>
            <div class="session-date">${formatDate(session.last_updated)}</div>
            <button class="delete-session-btn" onclick="event.stopPropagation(); deleteSession('${
              session.session_id
            }')" title="Delete Session">×</button>
            <div class="session-docs">
                ${session.docs
                  .map(
                    (docId) => `
                    <div class="doc-item ${
                      currentDocId == docId ? "active" : ""
                    }"
                         onclick="event.stopPropagation(); loadDocument('${
                           session.session_id
                         }','${docId}')">
                        Document ${docId}
                    </div>`
                  )
                  .join("")}
            </div>`;
    sessionElement.addEventListener("click", () =>
      selectSession(session.session_id)
    );
    sessionsList.appendChild(sessionElement);
  });
}
function formatDate(isoString) {
  if (!isoString) return "No activity yet";
  const date = new Date(isoString);
  return date.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
async function deleteSession(sessionId) {
  if (
    !confirm(
      `Are you sure you want to delete this session? This action cannot be undone.`
    )
  )
    return;
  try {
    const response = await fetch(`${API_BASE}/session/${sessionId}`, {
      method: "DELETE",
    });
    const data = await response.json();
    if (response.ok) {
      showNotification("Session deleted.", "success");
      if (currentSession === sessionId) {
        currentSession = null;
        currentDocId = null;
        document.getElementById("chatMessages").innerHTML = "";
        document.getElementById("addDocsBtn").style.display = "none";
        showUploadArea();
      }
      await loadSessions();
    } else {
      showNotification(data.error || "Failed to delete session", "error");
    }
  } catch (error) {
    showNotification("An error occurred while deleting.", "error");
  }
}
async function selectSession(sessionId) {
  cleanupBlobUrl();
  currentSession = sessionId;
  currentDocId = null;
  renderSessions();
  document.getElementById("addDocsBtn").style.display = "block";
  stopVoiceServices();
  isMicEnabled = false;
  updateMicButtonState();
  const chatMessages = document.getElementById("chatMessages");
  chatMessages.innerHTML = "";
  try {
    const response = await fetch(`${API_BASE}/messages/${sessionId}`);
    if (response.ok) {
      const data = await response.json();
      data.messages.forEach((msg) => {
        addMessageToChat(
          msg.content,
          msg.sender,
          msg.references || [],
          false
        );
      });
    } else {
      showNotification("Could not load chat history.", "error");
    }
  } catch (error) {
    console.error("Error fetching chat history:", error);
    showNotification("Error loading chat history.", "error");
  }
  const session = sessions.find((s) => s.session_id === sessionId);
  if (!session || session.docs.length === 0) {
    showUploadArea();
  } else {
    document.getElementById("uploadArea").style.display = "none";
    document.getElementById("chatPanel").style.display = "flex";
  }
}
function showUploadArea() {
  const viewerArea = document.getElementById("viewerArea");
  const uploadArea = document.getElementById("uploadArea");
  const apryseViewer = document.getElementById("apryseViewer");
  if (apryseViewer) apryseViewer.style.display = "none";
  clearCustomViewers(viewerArea);
  if (uploadArea) uploadArea.style.display = "block";
  setupDragAndDrop();
  if (document.getElementById("chatPanel"))
    document.getElementById("chatPanel").style.display = "none";
  if (document.getElementById("addDocsBtn") && !currentSession)
    document.getElementById("addDocsBtn").style.display = "none";
}
async function createNewSession(callback) {
  if (!currentUser) return;
  const sessionName = prompt("Enter a name for the new session:");
  if (!sessionName || sessionName.trim() === "") {
    showNotification("Session name cannot be empty.", "error");
    pendingUploadData = null;
    return;
  }
  try {
    const formData = new FormData();
    formData.append("user_id", currentUser);
    formData.append("session_name", sessionName);
    const response = await fetch(`${API_BASE}/new_session`, {
      method: "POST",
      body: formData,
    });
    const newSessionData = await response.json();
    if (response.ok) {
      sessions.unshift(newSessionData);
      await selectSession(newSessionData.session_id);
      renderSessions();
      if (typeof callback === "function") {
        callback();
      }
    } else {
      showNotification("Failed to create new session", "error");
      pendingUploadData = null;
    }
  } catch (error) {
    showNotification("Failed to create new session", "error");
    pendingUploadData = null;
  }
}
function promptForSessionAndUpload() {
  createNewSession(() => {
    if (pendingUploadData) {
      if (pendingUploadData.type === "files") {
        handleFileUpload(pendingUploadData.data, true);
      } else if (pendingUploadData.type === "url") {
        uploadFromUrl(pendingUploadData.data, true);
      }
      pendingUploadData = null;
    }
  });
}
async function handleFileUpload(files, skipSessionCheck = false) {
  if (!files || !files.length) return;
  if (!currentSession && !skipSessionCheck) {
    pendingUploadData = { type: "files", data: files };
    promptForSessionAndUpload();
    return;
  }
  showNotification("Uploading files...", "info");
  const formData = new FormData();
  formData.append("session_id", currentSession);
  for (let file of files) formData.append("files", file);
  try {
    const response = await fetch(`${API_BASE}/upload`, {
      method: "POST",
      body: formData,
    });
    const data = await response.json();
    if (response.ok) {
      showNotification("Files uploaded successfully!", "success");
      await loadSessions();
      if (data.doc_ids && data.doc_ids.length > 0) {
        loadDocument(currentSession, data.doc_ids[0]);
      }
      document.getElementById("fileInput").value = "";
      document.getElementById("modalFileInput").value = "";
    } else {
      showNotification(data.error || "Failed to upload files", "error");
    }
  } catch (error) {
    showNotification("Upload failed. Check console.", "error");
  }
}
async function uploadFromUrl(url, skipSessionCheck = false) {
  if (!url) return showNotification("Please enter a URL.", "error");
  if (!currentSession && !skipSessionCheck) {
    pendingUploadData = { type: "url", data: url };
    promptForSessionAndUpload();
    return;
  }
  showNotification("Uploading from URL...", "info");
  const formData = new FormData();
  formData.append("session_id", currentSession);
  formData.append("url", url);
  try {
    const response = await fetch(`${API_BASE}/upload`, {
      method: "POST",
      body: formData,
    });
    const data = await response.json();
    if (response.ok) {
      showNotification("URL content uploaded!", "success");
      await loadSessions();
      if (data.doc_ids && data.doc_ids.length > 0) {
        loadDocument(currentSession, data.doc_ids[0]);
      }
      document.getElementById("urlInput").value = "";
      document.getElementById("modalUrlInput").value = "";
    } else {
      showNotification(data.error || "Failed to upload URL", "error");
    }
  } catch (error) {
    showNotification("Failed to upload URL. Check console.", "error");
  }
}
function showViewerLoader() {
  const viewerArea = document.getElementById("viewerArea");
  hideViewerLoader();
  const loader = document.createElement("div");
  loader.className = "viewer-loading-overlay";
  loader.innerHTML = `
              <div class="spinner"></div>
              <div class="loading-text">Loading Document...</div>
          `;
  viewerArea.appendChild(loader);
}
function hideViewerLoader() {
  const loader = document.querySelector(".viewer-loading-overlay");
  if (loader) {
    loader.remove();
  }
}
async function loadDocument(sessionId, docId) {
  console.log(`Loading document: session=${sessionId}, doc=${docId}`);
  showViewerLoader();
  try {
    documentTextCache.clear();
    clearAllHighlights();
    currentReferences = [];
    currentSession = sessionId;
    currentDocId = docId;
    renderSessions();
    const docIdInt = parseInt(docId);
    const response = await fetch(
      `${API_BASE}/get_doc/${sessionId}/${docIdInt}`
    );
    if (response.ok) {
      const contentType = response.headers.get("content-type");
      if (contentType && contentType.includes("application/json")) {
        const errorData = await response.json();
        showNotification(
          errorData.error || "Could not retrieve document.",
          "error"
        );
        return;
      }
      const blob = await response.blob();
      cleanupBlobUrl();
      currentBlobUrl = URL.createObjectURL(blob);
      const extension =
        getFileExtensionFromContentType(contentType) || "bin";
      await loadDocumentInViewer(currentBlobUrl, extension);
      document.getElementById("chatPanel").style.display = "flex";
    } else {
      const errorText = await response.text();
      console.error(
        "Failed to load document:",
        response.status,
        errorText
      );
      showNotification("Failed to load document", "error");
    }
  } catch (error) {
    console.error("Error loading document:", error);
    showNotification("Failed to load document", "error");
  } finally {
    hideViewerLoader();
  }
}
async function loadDocumentInViewer(documentUrl, extension) {
  const viewerArea = document.getElementById("viewerArea");
  const uploadArea = document.getElementById("uploadArea");
  const apryseViewer = document.getElementById("apryseViewer");
  if (uploadArea) uploadArea.style.display = "none";
  clearCustomViewers(viewerArea);
  const textBasedExtensions = [
    "txt",
    "csv",
    "md",
    "py",
    "js",
    "html",
    "css",
    "java",
    "json",
  ];
  const supportedApryseExtensions = [
    "pdf",
    "docx",
    "pptx",
    "xlsx",
    "doc",
    "ppt",
    "xls",
    "txt",
    "md",
    "png",
    "jpg",
    "jpeg",
  ];
  const extLower = extension.toLowerCase();
  if (textBasedExtensions.includes(extLower)) {
    if (apryseViewer) apryseViewer.style.display = "none";
    await showTextViewer(documentUrl, extLower, viewerArea);
  } else if (
    webviewerInstance &&
    supportedApryseExtensions.includes(extLower)
  ) {
    if (apryseViewer) apryseViewer.style.display = "block";
    try {
      await webviewerInstance.UI.loadDocument(documentUrl, { extension });
    } catch (error) {
      console.error("Apryse WebViewer failed to load document:", error);
      showNotification(
        `Failed to preview document (${extension}).`,
        "error"
      );
      showFallbackViewer(documentUrl, extension, viewerArea);
    }
  } else {
    if (apryseViewer) apryseViewer.style.display = "none";
    showNotification(
      `Preview not available for .${extension} files.`,
      "info"
    );
    showFallbackViewer(documentUrl, extension, viewerArea);
  }
}
async function showTextViewer(documentUrl, extension, viewerArea) {
  clearCustomViewers(viewerArea);
  const textViewer = document.createElement("div");
  textViewer.className = "custom-viewer text-viewer";
  const pre = document.createElement("pre");
  const code = document.createElement("code");
  const langMap = {
    py: "python",
    js: "javascript",
    java: "java",
    html: "markup",
    css: "css",
    json: "json",
    md: "markdown",
    csv: "csv",
  };
  const lang = langMap[extension] || "plaintext";
  code.className = `language-${lang}`;
  try {
    const response = await fetch(documentUrl);
    const textContent = await response.text();
    code.textContent = textContent;
    pre.appendChild(code);
    textViewer.appendChild(pre);
    viewerArea.appendChild(textViewer);
    if (window.Prism) {
      Prism.highlightElement(code);
    }
  } catch (error) {
    console.error("Failed to load text content:", error);
    textViewer.innerHTML = "<h3>Failed to load text content.</h3>";
    viewerArea.appendChild(textViewer);
  }
}
function clearCustomViewers(viewerArea) {
  viewerArea
    .querySelectorAll(".custom-viewer")
    .forEach((el) => el.remove());
}
function showFallbackViewer(documentUrl, extension, viewerArea) {
  clearCustomViewers(viewerArea);
  const fallbackViewer = document.createElement("div");
  fallbackViewer.className = "custom-viewer";
  fallbackViewer.style.cssText =
    "width: 100%; height: 100%; padding: 2rem; display: flex; justify-content: center; align-items: center; text-align: center;";
  let fallbackHTML = `<h3>Preview for .${extension} files is not supported.</h3>`;
  if (["jpg", "jpeg", "png", "gif"].includes(extension.toLowerCase())) {
    fallbackHTML = `<img src="${documentUrl}" style="max-width: 100%; max-height: 100%; object-fit: contain;">`;
  }
  fallbackViewer.innerHTML = fallbackHTML;
  viewerArea.appendChild(fallbackViewer);
}
function getFileExtensionFromContentType(contentType) {
  const mainType = (contentType || "").split(";")[0].trim();
  const typeMap = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
      "docx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
      "xlsx",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation":
      "pptx",
    "application/msword": "doc",
    "application/vnd.ms-excel": "xls",
    "application/vnd.ms-powerpoint": "ppt",
    "text/plain": "txt",
    "text/markdown": "md",
    "image/jpeg": "jpg",
    "image/png": "png",
    "text/csv": "csv",
    "text/html": "html",
    "text/css": "css",
    "application/javascript": "js",
    "application/json": "json",
    "text/x-python": "py",
    "text/x-java-source": "java",
  };
  return typeMap[mainType] || null;
}
function cleanupBlobUrl() {
  if (currentBlobUrl) {
    URL.revokeObjectURL(currentBlobUrl);
    currentBlobUrl = null;
  }
}
async function handleReferenceClick(referenceData, iconElement) {
  clearAllHighlights();
  document
    .querySelectorAll(".reference-icon")
    .forEach((icon) => icon.classList.remove("active"));
  iconElement.classList.add("active");
  showHighlightStatus("Searching for reference...", "searching");
  try {
    // Normalize page number fields from backend: support page_num or page_number
    // Ensure downstream code always reads `referenceData.page_number`.
    const normalizedPage =
      referenceData.page_number ?? referenceData.page_num ?? referenceData.pageNumber ?? null;
    referenceData.page_number = normalizedPage;

    let targetDocId = referenceData.doc_id;
    if (String(targetDocId) === "-1") {
      const session = sessions.find(
        (s) => s.session_id === currentSession
      );
      if (session && session.docs.length > 0) {
        targetDocId = session.docs[0];
      } else {
        showHighlightStatus(
          "Session has no documents to search for reference.",
          "error"
        );
        iconElement.classList.remove("active");
        return;
      }
    }
    if (String(currentDocId) !== String(targetDocId)) {
      await loadDocument(currentSession, targetDocId);
    }
    const matchResult = await findReferenceInDocument(
      referenceData.text_snippet,
      targetDocId,
      referenceData.page_number
    );
    if (matchResult) {
      const highlightId = await highlightTextInDocument(matchResult);
      if (highlightId) {
        showHighlightStatus(
          `Reference found on page ${matchResult.pageNumber}`,
          "success"
        );
      } else {
        showHighlightStatus(
          "Reference found but could not highlight",
          "error"
        );
      }
    } else {
      // Provide more detailed error information
      const referencePreview = referenceData.text_snippet ? 
        referenceData.text_snippet.substring(0, 50) + "..." : 
        "Unknown reference";
      
      console.log("❌ Reference search failed for:", {
        text_snippet: referenceData.text_snippet,
        page_number: referenceData.page_number,
        doc_id: targetDocId
      });
      
      showHighlightStatus(
        `Reference not found on page ${referenceData.page_number || '?'}. The text may have been reformatted or extracted differently.`,
        "error"
      );
      
      // Show a temporary notification with more details
      showNotification(
        `Could not highlight reference: "${referencePreview}". The document viewer may extract text differently than the search engine.`,
        "warning"
      );
    }
  } catch (error) {
    console.error("Error handling reference click:", error);
    showHighlightStatus("Error searching for reference", "error");
  }
}
function createReferenceIcon(referenceData, index) {
  const icon = document.createElement("span");
  icon.className = "reference-icon";
  // Normalize page number fields: prefer `page_number`, then `page_num`, then unknown
  const pageNumberNormalized =
    referenceData.page_number ?? referenceData.page_num ?? referenceData.pageNumber ?? null;
  // Store normalized value back so other handlers can rely on a single key
  referenceData.page_number = pageNumberNormalized;
  const displayPage = pageNumberNormalized === null ? "?" : pageNumberNormalized;
  const tooltipText = `Page ${displayPage}: "${referenceData.text_snippet}"`;
  icon.title = tooltipText;
  icon.innerHTML = `${index + 1}<div class="reference-tooltip">${tooltipText}</div>`;
  icon.addEventListener("click", (e) => {
    e.stopPropagation();
    handleReferenceClick(referenceData, icon);
  });
  return icon;
}
async function sendMessage() {
  const input = document.getElementById("chatInput");
  const message = input.value.trim();
  if (
    !message ||
    !currentSession ||
    document.getElementById("sendBtn").disabled
  )
    return;
  const sendBtn = document.getElementById("sendBtn");
  sendBtn.disabled = true;
  clearAllHighlights();
  currentReferences = [];
  addMessageToChat(message, "user");
  input.value = "";
  input.style.height = "auto";
  try {
    const response = await fetch(`${API_BASE}/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: currentSession,
        question: message,
      }),
    });
    const data = await response.json();
    if (response.ok && data.answer_parts) {
      let fullAnswer = "";
      let allReferences = [];
      data.answer_parts.forEach((part) => {
        fullAnswer += part.text;
        if (part.references) allReferences.push(...part.references);
      });
      addMessageToChat(fullAnswer, "assistant", allReferences, true);
      await loadSessions();
    } else {
      addMessageToChat(
        data.error || "Sorry, I encountered an error.",
        "assistant"
      );
    }
  } catch (error) {
    console.error("Error sending message:", error);
    addMessageToChat("Sorry, I encountered an error.", "assistant");
  } finally {
    sendBtn.disabled = false;
  }
}
function addMessageToChat(
  message,
  sender,
  references = [],
  shouldSpeak = false
) {
  const chatMessages = document.getElementById("chatMessages");
  const messageElement = document.createElement("div");
  messageElement.className = `message ${sender}`;
  const messageText = document.createElement("md-block");
  messageText.className = "message-text";
  messageText.innerText = message;
  messageElement.appendChild(messageText);
  if (sender === "assistant" && references && references.length > 0) {
    currentReferences = references;
    const referencesContainer = document.createElement("div");
    referencesContainer.style.cssText =
      "margin-top: 8px; display: flex; flex-wrap: wrap; gap: 4px;";
    references.forEach((ref, index) => {
      referencesContainer.appendChild(createReferenceIcon(ref, index));
    });
    messageElement.appendChild(referencesContainer);
  }
  chatMessages.appendChild(messageElement);
  if (sender === "assistant" && isSpeechOutputEnabled && shouldSpeak) {
    speakText(message, references);
  }
  chatMessages.scrollTop = chatMessages.scrollHeight;
}
function setupDragAndDrop() {
  const uploadArea = document.getElementById("uploadArea");
  if (!uploadArea) return;
  ["dragenter", "dragover", "dragleave", "drop"].forEach((eventName) => {
    uploadArea.addEventListener(
      eventName,
      (e) => {
        e.preventDefault();
        e.stopPropagation();
      },
      false
    );
  });
  ["dragenter", "dragover"].forEach((eventName) => {
    uploadArea.addEventListener(
      eventName,
      () => {
        uploadArea.style.borderColor = "var(--accent-color)";
        uploadArea.style.background = "rgba(0, 255, 255, 0.1)";
      },
      false
    );
  });
  ["dragleave", "drop"].forEach((eventName) => {
    uploadArea.addEventListener(
      eventName,
      () => {
        uploadArea.style.borderColor = "rgba(75, 85, 99, 0.5)";
        uploadArea.style.background = "var(--panel-bg)";
      },
      false
    );
  });
  uploadArea.addEventListener(
    "drop",
    (e) => {
      handleFileUpload(e.dataTransfer.files);
    },
    false
  );
}
function initializeSpeechServices() {
  try {
    const savedWakeWord = localStorage.getItem("userWakeWord");
    if (savedWakeWord) wakeWord = savedWakeWord;
  } catch (e) {
    console.warn("Could not access localStorage for wake word.");
  }
  const SpeechRecognition =
    window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    console.warn("Speech Recognition API not supported.");
    document.getElementById("micBtn").disabled = true;
    document.getElementById("micBtn").title =
      "Voice commands not supported.";
    document.getElementById("settingsBtn").disabled = true;
    return;
  }
  speechRecognition = new SpeechRecognition();
  speechRecognition.continuous = true;
  speechRecognition.interimResults = true;
  speechRecognition.lang = "en-US";
  speechRecognition.onresult = handleSpeechResult;
  speechRecognition.onerror = (event) =>
    console.error("Speech recognition error:", event.error);
  speechRecognition.onend = handleSpeechEnd;
  if (!("speechSynthesis" in window)) {
    console.warn("Speech Synthesis API not supported.");
    document.getElementById("toggleSpeechBtn").disabled = true;
  }
}
function handleMicButtonPress() {
  micPressTimer = setTimeout(() => {
    startPushToTalk();
    micPressTimer = null;
  }, longPressThreshold);
}
function handleMicButtonRelease() {
  if (micPressTimer) {
    clearTimeout(micPressTimer);
    micPressTimer = null;
    toggleMic();
  } else if (isPushToTalkActive) {
    stopPushToTalk();
  }
}
function toggleMic() {
  isMicEnabled = !isMicEnabled;
  if (isMicEnabled) {
    startWakeWordListening();
  } else {
    stopVoiceServices();
  }
  updateMicButtonState();
}
function toggleSpeechOutput() {
  isSpeechOutputEnabled = !isSpeechOutputEnabled;
  if (!isSpeechOutputEnabled) {
    window.speechSynthesis.cancel();
  }
  updateSpeechButtonState();
}
function setWakeWord() {
  const newWakeWord = prompt(
    "Enter a new wake phrase (e.g., 'hey assistant'):",
    wakeWord
  );
  if (newWakeWord && newWakeWord.trim()) {
    wakeWord = newWakeWord.trim().toLowerCase();
    try {
      localStorage.setItem("userWakeWord", wakeWord);
      showNotification(`Wake word set to "${wakeWord}"`, "success");
    } catch (e) {
      showNotification("Could not save wake word.", "error");
    }
    updateMicButtonState();
    if (isMicEnabled) {
      stopVoiceServices();
      startWakeWordListening();
    }
  }
}
function startWakeWordListening() {
  if (!speechRecognition || !currentSession) {
    isMicEnabled = false;
    updateMicButtonState();
    showNotification(
      "Please select a session to use voice commands.",
      "error"
    );
    return;
  }
  console.log(`Listening for wake word: "${wakeWord}"`);
  isRecording = true;
  showNotification(`Listening for "${wakeWord}"`, "info");
  try {
    speechRecognition.start();
  } catch (e) {
    console.error("Speech recognition could not start:", e);
    stopVoiceServices();
  }
}
function startPushToTalk(event) {
  if (isRecording) return;
  isPushToTalkActive = true;
  isRecording = true;
  console.log("Push-to-talk started.");
  document.getElementById("chatInput").value = "";
  document.getElementById("chatInput").placeholder = "Listening...";
  updateMicButtonState();
  try {
    speechRecognition.start();
  } catch (e) {
    console.error("PTT start failed:", e);
    stopVoiceServices();
  }
}
function stopPushToTalk() {
  if (!isPushToTalkActive) return;
  console.log("Push-to-talk stopped.");
  if (silenceTimer) clearTimeout(silenceTimer);
  if (isRecording) {
    speechRecognition.stop();
  }
}
function stopVoiceServices() {
  console.log("Stopping voice services.");
  if (speechRecognition) {
    speechRecognition.stop();
  }
  if (silenceTimer) clearTimeout(silenceTimer);
  window.speechSynthesis.cancel();
  isRecording = false;
  isMicEnabled = false;
  isPushToTalkActive = false;
  updateMicButtonState();
  document.getElementById("chatInput").placeholder = "Ask a question...";
}
function handleSpeechResult(event) {
  if (silenceTimer) {
    clearTimeout(silenceTimer);
  }
  let fullTranscript = "";
  for (let i = event.resultIndex; i < event.results.length; ++i) {
    fullTranscript += event.results[i][0].transcript;
  }
  if (
    !isPushToTalkActive &&
    !fullTranscript.toLowerCase().includes(wakeWord)
  ) {
    return;
  }
  let question = fullTranscript;
  if (!isPushToTalkActive) {
    const wakeWordIndex = question.toLowerCase().indexOf(wakeWord);
    if (wakeWordIndex !== -1) {
      question = question
        .substring(wakeWordIndex + wakeWord.length)
        .trim();
    }
  }
  document.getElementById("chatInput").value = question;
  if (question && isMicEnabled && !isPushToTalkActive) {
    silenceTimer = setTimeout(() => {
      console.log(
        "Silence detected via timer. Stopping recognition to send."
      );
      if (isRecording) {
        speechRecognition.stop();
      }
    }, silenceTimeoutDuration);
  }
}
function handleSpeechEnd() {
  if (!isRecording) return;
  console.log("Speech recognition ended.");
  isRecording = false;
  const wasPushToTalk = isPushToTalkActive;
  isPushToTalkActive = false;
  const query = document.getElementById("chatInput").value.trim();
  document.getElementById("chatInput").placeholder = "Ask a question...";
  if (query) {
    sendMessage();
  }
  if (isMicEnabled && !wasPushToTalk) {
    startWakeWordListening();
  } else {
    updateMicButtonState();
  }
}
function updateMicButtonState() {
  const micBtn = document.getElementById("micBtn");
  micBtn.classList.remove("active", "recording");
  if (isPushToTalkActive) {
    micBtn.classList.add("recording");
    micBtn.title = "Release to send query";
  } else if (isMicEnabled) {
    micBtn.classList.add("active");
    micBtn.title = `Wake word mode is ON. Say "${wakeWord}" to ask. Click to disable.`;
  } else {
    micBtn.title = "Click to enable wake word mode, or hold to talk.";
  }
}
function updateSpeechButtonState() {
  const speechBtn = document.getElementById("toggleSpeechBtn");
  const speakerOn = speechBtn.querySelector(".speaker-on");
  const speakerOff = speechBtn.querySelector(".speaker-off");
  if (isSpeechOutputEnabled) {
    speechBtn.classList.add("active");
    speechBtn.title = "Speech Output is ON";
    speakerOn.style.display = "block";
    speakerOff.style.display = "none";
  } else {
    speechBtn.classList.remove("active");
    speechBtn.title = "Speech Output is OFF";
    speakerOn.style.display = "none";
    speakerOff.style.display = "block";
  }
}
async function speakText(text, references = []) {
  if (!("speechSynthesis" in window)) return;
  window.speechSynthesis.cancel();
  currentSpokenReferenceIndex = -1;
  const utterance = new SpeechSynthesisUtterance(text);
  const referencePositions = references
    .map((ref, index) => {
      const cleanText = text
        .replace(/[.,\/#!$%\^&\*;:{}=\-_`~()]/g, "")
        .replace(/\s{2,}/g, " ");
      const cleanSnippet = ref.text_snippet
        .replace(/[.,\/#!$%\^&\*;:{}=\-_`~()]/g, "")
        .replace(/\s{2,}/g, " ");
      const startIndex = cleanText.indexOf(cleanSnippet);
      if (startIndex === -1) return null;
      return {
        start: startIndex,
        end: startIndex + cleanSnippet.length,
        refData: ref,
        refIcon: document.querySelector(
          `.message.assistant:last-child .reference-icon:nth-of-type(${
            index + 1
          })`
        ),
      };
    })
    .filter((p) => p !== null);
  utterance.onboundary = async (event) => {
    if (event.name === "word") {
      const charIndex = event.charIndex;
      const activeRef = referencePositions.find(
        (p) => charIndex >= p.start && charIndex < p.end
      );
      const activeRefIndex = referencePositions.indexOf(activeRef);
      if (activeRef && activeRefIndex !== currentSpokenReferenceIndex) {
        currentSpokenReferenceIndex = activeRefIndex;
        console.log(
          `Highlighting reference for: "${activeRef.refData.text_snippet}"`
        );
        if (activeRef.refIcon) {
          await handleReferenceClick(
            activeRef.refData,
            activeRef.refIcon
          );
        }
      }
    }
  };
  utterance.onend = () => {
    console.log("Speech finished.");
    clearAllHighlights();
    currentSpokenReferenceIndex = -1;
    document
      .querySelectorAll(".reference-icon")
      .forEach((icon) => icon.classList.remove("active"));
  };
  window.speechSynthesis.speak(utterance);
}
function showNotification(message, type = "info") {
  const notification = document.createElement("div");
  const colors = {
    success: "rgba(34, 197, 94, 0.9)",
    error: "rgba(239, 68, 68, 0.9)",
    info: "rgba(59, 130, 246, 0.9)",
  };
  notification.style.cssText = `position: fixed; top: 20px; right: 20px; padding: 1rem 1.5rem; background: ${colors[type]}; color: white; border-radius: 8px; z-index: 1002; backdrop-filter: blur(10px); box-shadow: 0 10px 25px rgba(0, 0, 0, 0.3); transform: translateX(400px); transition: transform 0.3s ease; max-width: 300px;`;
  notification.textContent = message;
  document.body.appendChild(notification);
  setTimeout(() => {
    notification.style.transform = "translateX(0)";
  }, 100);
  setTimeout(() => {
    notification.style.transform = "translateX(400px)";
    setTimeout(() => {
      if (notification.parentElement) notification.remove();
    }, 300);
  }, 3000);
}

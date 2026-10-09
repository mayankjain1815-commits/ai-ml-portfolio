/* Orbit frontend — Web Speech API in, speech synthesis out, zero dependencies.
   Works fully offline: no CDN, no fonts, no analytics. */
"use strict";

const chatEl = document.getElementById("chat");
const inputEl = document.getElementById("text-input");
const micBtn = document.getElementById("mic-btn");
const sendBtn = document.getElementById("send-btn");
const badgeEl = document.getElementById("mode-badge");
const notesBtn = document.getElementById("notes-btn");
const notesPanel = document.getElementById("notes-panel");
const notesList = document.getElementById("notes-list");

let sessionId = null;
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
let recognizer = null;

// ---------------------------------------------------------------- mode badge
fetch("/api/mode")
  .then((r) => r.json())
  .then((data) => {
    badgeEl.textContent = data.mode === "llm" ? "LLM mode (Gemini)" : "demo mode (rule-based)";
    badgeEl.classList.toggle("llm", data.mode === "llm");
  })
  .catch(() => { badgeEl.textContent = "offline"; });

// --------------------------------------------------------------- chat plumbing
function addBubble(text, who, meta) {
  const div = document.createElement("div");
  div.className = "bubble " + who;
  div.textContent = text;
  if (meta) {
    const m = document.createElement("span");
    m.className = "meta";
    m.textContent = meta;
    div.appendChild(m);
  }
  chatEl.appendChild(div);
  chatEl.scrollTop = chatEl.scrollHeight;
  return div;
}

function speak(text) {
  if (!("speechSynthesis" in window)) return;
  const utter = new SpeechSynthesisUtterance(text);
  utter.rate = 1.0;
  const voices = speechSynthesis.getVoices();
  const en = voices.find((v) => v.lang && v.lang.startsWith("en"));
  if (en) utter.voice = en;
  speechSynthesis.cancel();
  speechSynthesis.speak(utter);
}

async function send(text) {
  const message = (text || "").trim();
  if (!message) return;
  inputEl.value = "";
  addBubble(message, "user");
  const typing = addBubble("…", "assistant");
  try {
    const resp = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, session_id: sessionId }),
    });
    const data = await resp.json();
    sessionId = data.session_id || sessionId;
    typing.textContent = data.reply || "(no reply)";
    const metaText = data.mode === "demo"
      ? `intent: ${data.intent}` + (data.tools_used.length ? ` · tools: ${data.tools_used.join(", ")}` : "")
      : `mode: ${data.mode}`;
    const meta = document.createElement("span");
    meta.className = "meta";
    meta.textContent = metaText;
    typing.appendChild(meta);
    speak(data.reply || "");
  } catch (err) {
    typing.textContent = "Oops — the assistant is unreachable. Is the server running?";
  }
  chatEl.scrollTop = chatEl.scrollHeight;
}

// --------------------------------------------------------------------- notes
async function refreshNotes() {
  const resp = await fetch("/api/notes");
  const data = await resp.json();
  notesList.innerHTML = "";
  if (!data.notes.length) {
    notesList.innerHTML = "<li>No notes yet — try “remember that Friday is the demo”.</li>";
    return;
  }
  data.notes.forEach((n) => {
    const li = document.createElement("li");
    li.textContent = `${n.text}  [${n.id}, ${n.created}]`;
    notesList.appendChild(li);
  });
}
notesBtn.addEventListener("click", () => {
  notesPanel.classList.toggle("hidden");
  if (!notesPanel.classList.contains("hidden")) refreshNotes();
});

// ------------------------------------------------------------------- events
sendBtn.addEventListener("click", () => send(inputEl.value));
inputEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter") send(inputEl.value);
});
document.querySelectorAll(".chip").forEach((chip) =>
  chip.addEventListener("click", () => send(chip.dataset.text))
);

// ------------------------------------------------------- microphone (SpeechRecognition)
if (SpeechRecognition) {
  recognizer = new SpeechRecognition();
  recognizer.lang = "en-US";
  recognizer.interimResults = false;
  recognizer.maxAlternatives = 1;

  recognizer.onresult = (event) => {
    const transcript = event.results[0][0].transcript;
    micBtn.classList.remove("listening");
    send(transcript);
  };
  recognizer.onend = () => micBtn.classList.remove("listening");
  recognizer.onerror = () => {
    micBtn.classList.remove("listening");
    addBubble("I couldn't hear you — try the mic again or type instead.", "assistant");
  };

  micBtn.addEventListener("click", () => {
    if (micBtn.classList.contains("listening")) {
      recognizer.stop();
      micBtn.classList.remove("listening");
      return;
    }
    try {
      recognizer.start();
      micBtn.classList.add("listening");
    } catch (_err) {
      // Already started; toggle it off instead.
      recognizer.stop();
      micBtn.classList.remove("listening");
    }
  });
} else {
  micBtn.disabled = true;
  micBtn.title = "Speech recognition needs Chrome, Edge, or Safari";
}
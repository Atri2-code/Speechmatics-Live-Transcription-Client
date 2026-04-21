"use strict";

const API_BASE = "http://localhost:8000";
const CONFIDENCE_HIGH = 0.9;
const CONFIDENCE_MID = 0.7;

class TranscriptDashboard {
  constructor() {
    this.transcriptEl = document.getElementById("transcript");
    this.wordCountEl = document.getElementById("word-count");
    this.wpmEl = document.getElementById("wpm");
    this.confidenceEl = document.getElementById("avg-confidence");
    this.durationEl = document.getElementById("duration");
    this.startBtn = document.getElementById("btn-start");
    this.stopBtn = document.getElementById("btn-stop");
    this.exportBtn = document.getElementById("btn-export");
    this.statusEl = document.getElementById("status");
    this.speakersEl = document.getElementById("speakers");

    this.eventSource = null;
    this.words = [];
    this.startTime = null;
    this.timerInterval = null;

    this.startBtn.addEventListener("click", () => this.startSession());
    this.stopBtn.addEventListener("click", () => this.stopSession());
    this.exportBtn.addEventListener("click", () => this.exportTranscript());
  }

  async startSession() {
    const lang = document.getElementById("language-select").value;
    const res = await fetch(`${API_BASE}/session/start?language=${lang}`, {
      method: "POST",
    });
    if (!res.ok) {
      this.setStatus("Failed to start session", "error");
      return;
    }

    this.words = [];
    this.transcriptEl.innerHTML = "";
    this.speakersEl.innerHTML = "";
    this.startTime = Date.now();
    this.startTimer();

    this.startBtn.disabled = true;
    this.stopBtn.disabled = false;
    this.setStatus("Live — transcribing", "active");

    this.connectSSE();
  }

  async stopSession() {
    const res = await fetch(`${API_BASE}/session/stop`, { method: "POST" });
    const data = await res.json();

    this.disconnectSSE();
    this.stopTimer();
    this.startBtn.disabled = false;
    this.stopBtn.disabled = true;
    this.setStatus("Session stopped", "idle");

    if (data.analytics) {
      this.renderAnalytics(data.analytics);
    }
  }

  connectSSE() {
    this.eventSource = new EventSource(`${API_BASE}/transcript/stream`);
    this.eventSource.onmessage = (e) => this.handleEvent(JSON.parse(e.data));
    this.eventSource.onerror = () => {
      this.setStatus("Stream disconnected", "error");
      this.disconnectSSE();
    };
  }

  disconnectSSE() {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
  }

  handleEvent(event) {
    if (event.type === "keepalive" || event.type === "connected") return;
    if (event.type !== "word") return;

    this.words.push(event);
    this.renderWord(event);
    this.updateStats();
  }

  renderWord(event) {
    const span = document.createElement("span");
    span.textContent = event.word + " ";
    span.className = "word";
    span.dataset.confidence = event.confidence;
    span.dataset.speaker = event.speaker;
    span.title = `${event.speaker} · confidence: ${(event.confidence * 100).toFixed(0)}%`;

    if (event.confidence >= CONFIDENCE_HIGH) {
      span.classList.add("conf-high");
    } else if (event.confidence >= CONFIDENCE_MID) {
      span.classList.add("conf-mid");
    } else {
      span.classList.add("conf-low");
    }

    this.transcriptEl.appendChild(span);
    this.transcriptEl.scrollTop = this.transcriptEl.scrollHeight;
  }

  updateStats() {
    const count = this.words.length;
    const avgConf = count > 0
      ? this.words.reduce((s, w) => s + w.confidence, 0) / count
      : 0;

    const elapsed = this.startTime ? (Date.now() - this.startTime) / 60000 : 0;
    const wpm = elapsed > 0 ? Math.round(count / elapsed) : 0;

    this.wordCountEl.textContent = count;
    this.wpmEl.textContent = wpm;
    this.confidenceEl.textContent = (avgConf * 100).toFixed(0) + "%";

    this.updateSpeakers();
  }

  updateSpeakers() {
    const speakers = {};
    for (const w of this.words) {
      if (!speakers[w.speaker]) speakers[w.speaker] = 0;
      speakers[w.speaker]++;
    }

    this.speakersEl.innerHTML = Object.entries(speakers)
      .map(([spk, cnt]) => `<span class="speaker-tag">${spk}: ${cnt}w</span>`)
      .join("");
  }

  renderAnalytics(analytics) {
    this.wordCountEl.textContent = analytics.word_count;
    this.wpmEl.textContent = analytics.words_per_minute;
    this.confidenceEl.textContent = (analytics.avg_confidence * 100).toFixed(0) + "%";
  }

  startTimer() {
    this.timerInterval = setInterval(() => {
      if (!this.startTime) return;
      const elapsed = Math.floor((Date.now() - this.startTime) / 1000);
      const m = Math.floor(elapsed / 60).toString().padStart(2, "0");
      const s = (elapsed % 60).toString().padStart(2, "0");
      this.durationEl.textContent = `${m}:${s}`;
    }, 1000);
  }

  stopTimer() {
    clearInterval(this.timerInterval);
    this.timerInterval = null;
  }

  async exportTranscript() {
    const res = await fetch(`${API_BASE}/transcript/export?fmt=text`);
    const data = await res.json();
    const blob = new Blob([data.transcript], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `transcript-${Date.now()}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  }

  setStatus(text, type) {
    this.statusEl.textContent = text;
    this.statusEl.className = `status status-${type}`;
  }
}

document.addEventListener("DOMContentLoaded", () => {
  new TranscriptDashboard();
});

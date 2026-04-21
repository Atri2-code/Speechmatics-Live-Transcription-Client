"use strict";

const API_BASE = "http://localhost:8000";
const CHUNK_INTERVAL_MS = 100;

class AudioRecorder {
  constructor() {
    this.mediaRecorder = null;
    this.stream = null;
    this.isRecording = false;
  }

  async start() {
    if (this.isRecording) return;

    try {
      this.stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: 16000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
        },
        video: false,
      });
    } catch (err) {
      console.error("Microphone access denied:", err);
      throw new Error("Microphone permission required for live transcription.");
    }

    this.mediaRecorder = new MediaRecorder(this.stream, {
      mimeType: "audio/webm;codecs=opus",
      audioBitsPerSecond: 128000,
    });

    this.mediaRecorder.ondataavailable = async (event) => {
      if (event.data.size === 0) return;
      await this._sendChunk(event.data);
    };

    this.mediaRecorder.start(CHUNK_INTERVAL_MS);
    this.isRecording = true;
    console.log("AudioRecorder: started — chunk interval %dms", CHUNK_INTERVAL_MS);
  }

  stop() {
    if (!this.isRecording) return;
    this.mediaRecorder?.stop();
    this.stream?.getTracks().forEach((t) => t.stop());
    this.isRecording = false;
    console.log("AudioRecorder: stopped");
  }

  async _sendChunk(blob) {
    try {
      await fetch(`${API_BASE}/audio/chunk`, {
        method: "POST",
        body: blob,
        headers: { "Content-Type": "application/octet-stream" },
      });
    } catch (err) {
      console.warn("AudioRecorder: failed to send chunk:", err);
    }
  }
}

export { AudioRecorder };

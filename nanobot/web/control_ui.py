"""UltraBot Control UI with HTTP and WebSocket transport."""

from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import datetime
import json
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import websockets

from nanobot.agent.loop import AgentLoop
from nanobot.providers.custom_provider import CustomProvider
from nanobot.session.manager import SessionManager


_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>UltraBot Control UI</title>
  <style>
    :root {
      --bg: #f6f4ef;
      --surface: #fffdf8;
      --surface-alt: #f1ede4;
      --border: #d9d1c0;
      --ink: #1f1f1b;
      --muted: #6c6a62;
      --primary: #004f73;
      --primary-soft: #dceff7;
      --danger: #b42318;
      --ok: #177245;
      --warn: #9a6700;
      --radius: 14px;
      --shadow: 0 8px 30px rgba(23, 27, 34, 0.08);
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      min-height: 100vh;
      color: var(--ink);
      font-family: "Segoe UI", "Trebuchet MS", "Lucida Grande", sans-serif;
      background:
        radial-gradient(circle at 0% 0%, #eaf3f8 0%, transparent 40%),
        radial-gradient(circle at 100% 100%, #efe8da 0%, transparent 35%),
        var(--bg);
      display: flex;
    }

    .app {
      width: 100%;
      display: grid;
      grid-template-columns: 280px minmax(0, 1fr);
      min-height: 100vh;
    }

    .sidebar {
      border-right: 1px solid var(--border);
      background: linear-gradient(180deg, #fffdf9 0%, #f6f1e5 100%);
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 14px;
    }

    .brand {
      padding: 12px;
      border: 1px solid var(--border);
      border-radius: 12px;
      background: var(--surface);
      box-shadow: var(--shadow);
    }

    .brand h1 {
      margin: 0;
      font-size: 18px;
      letter-spacing: 0.3px;
    }

    .brand p {
      margin: 6px 0 0;
      color: var(--muted);
      font-size: 12px;
    }

    .status {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      font-size: 12px;
      color: var(--muted);
      margin-top: 8px;
    }

    .dot {
      width: 10px;
      height: 10px;
      border-radius: 50%;
      background: var(--warn);
      transition: background 0.15s ease;
      animation: pulse 1.8s infinite;
    }

    @keyframes pulse {
      0% { transform: scale(0.95); opacity: 0.85; }
      70% { transform: scale(1.1); opacity: 1; }
      100% { transform: scale(0.95); opacity: 0.85; }
    }

    .panel {
      border: 1px solid var(--border);
      border-radius: 12px;
      background: var(--surface);
      padding: 12px;
    }

    .meta {
      display: grid;
      gap: 8px;
      font-size: 13px;
    }

    .meta-row {
      display: flex;
      justify-content: space-between;
      gap: 10px;
    }

    .meta-row .label { color: var(--muted); }
    .meta-row .value {
      color: var(--primary);
      font-weight: 600;
      text-align: right;
      max-width: 150px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .controls {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
    }

    .runtime-grid {
      display: grid;
      gap: 8px;
      margin-top: 6px;
    }

    .runtime-grid label {
      font-size: 12px;
      color: var(--muted);
      display: grid;
      gap: 4px;
    }

    .runtime-grid select,
    .runtime-grid input,
    .runtime-grid textarea {
      width: 100%;
      padding: 8px 9px;
      border-radius: 8px;
      border: 1px solid var(--border);
      background: #fffcf6;
      font-size: 12px;
      color: var(--ink);
    }

    .runtime-grid textarea {
      min-height: 86px;
      resize: vertical;
      font-family: Consolas, "Lucida Console", monospace;
    }

    .runtime-actions {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
    }

    .runtime-status {
      font-size: 12px;
      color: var(--muted);
    }

    button {
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 10px 12px;
      font-size: 13px;
      color: var(--ink);
      background: var(--surface-alt);
      cursor: pointer;
      transition: transform 0.1s ease, background 0.15s ease;
    }

    button:hover { background: #e9e2d3; }
    button:active { transform: translateY(1px); }

    .sessions {
      border: 1px solid var(--border);
      border-radius: 12px;
      background: var(--surface);
      overflow: hidden;
      display: flex;
      flex-direction: column;
      min-height: 120px;
    }

    .sessions-header {
      padding: 10px 12px;
      font-size: 12px;
      color: var(--muted);
      border-bottom: 1px solid var(--border);
      background: #f9f6ef;
    }

    .session-list {
      overflow-y: auto;
      max-height: 190px;
    }

    .session-item {
      width: 100%;
      text-align: left;
      border: 0;
      border-radius: 0;
      background: transparent;
      padding: 10px 12px;
      border-left: 4px solid transparent;
      color: var(--muted);
    }

    .session-item:hover {
      background: #f5f0e4;
      color: var(--ink);
    }

    .session-item.active {
      color: var(--primary);
      border-left-color: var(--primary);
      background: var(--primary-soft);
      font-weight: 600;
    }

    .main {
      display: grid;
      grid-template-rows: auto minmax(0, 1fr) auto;
      min-width: 0;
    }

    .topbar {
      border-bottom: 1px solid var(--border);
      padding: 14px 18px;
      background: rgba(255, 253, 248, 0.8);
      backdrop-filter: blur(4px);
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 8px;
    }

    .title {
      font-size: 16px;
      font-weight: 700;
    }

    .subtitle {
      margin-top: 3px;
      font-size: 12px;
      color: var(--muted);
    }

    .connection {
      font-size: 12px;
      color: var(--muted);
      min-width: 108px;
      text-align: right;
    }

    .engine-pill {
      display: inline-block;
      margin-top: 4px;
      font-size: 11px;
      color: var(--primary);
      background: #e8f3f8;
      border: 1px solid #c8deea;
      border-radius: 999px;
      padding: 2px 8px;
    }

    .chat {
      padding: 16px 18px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }

    .row {
      display: flex;
      max-width: 88%;
      align-items: flex-start;
      gap: 8px;
      animation: fadeIn 0.16s ease;
    }

    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(4px); }
      to { opacity: 1; transform: translateY(0); }
    }

    .row.user {
      align-self: flex-end;
      flex-direction: row-reverse;
    }

    .badge {
      width: 30px;
      height: 30px;
      border-radius: 50%;
      border: 1px solid var(--border);
      display: grid;
      place-items: center;
      background: #ece5d6;
      font-size: 12px;
      color: var(--muted);
      flex: 0 0 auto;
    }

    .bubble {
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 10px 12px;
      line-height: 1.5;
      font-size: 14px;
      white-space: pre-wrap;
      word-break: break-word;
      box-shadow: var(--shadow);
      background: var(--surface);
    }

    .user .bubble {
      background: #dbeaf2;
      border-color: #b6d0de;
    }

    .meta-time {
      margin-top: 4px;
      color: var(--muted);
      font-size: 11px;
    }

    .typing {
      display: none;
      align-self: flex-start;
      border: 1px solid var(--border);
      border-radius: 999px;
      padding: 8px 10px;
      background: var(--surface);
      width: fit-content;
    }

    .typing span {
      display: inline-block;
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: var(--muted);
      margin-right: 4px;
      animation: bounce 0.8s infinite ease-in-out;
    }

    .typing span:nth-child(2) { animation-delay: 0.13s; }
    .typing span:nth-child(3) { animation-delay: 0.26s; margin-right: 0; }

    @keyframes bounce {
      0%, 80%, 100% { transform: translateY(0); }
      40% { transform: translateY(-4px); }
    }

    .footer {
      border-top: 1px solid var(--border);
      padding: 12px 18px;
      background: rgba(255, 253, 248, 0.95);
    }

    .input-row {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto auto;
      gap: 8px;
      align-items: center;
    }

    input[type="text"] {
      width: 100%;
      padding: 11px 12px;
      border-radius: 10px;
      border: 1px solid var(--border);
      background: #fffcf6;
      font-size: 14px;
      color: var(--ink);
      outline: none;
    }

    input[type="text"]:focus {
      border-color: var(--primary);
      box-shadow: 0 0 0 3px rgba(0, 79, 115, 0.15);
    }

    .send {
      background: var(--primary);
      border-color: var(--primary);
      color: #ffffff;
      min-width: 84px;
    }

    .clear {
      min-width: 70px;
    }

    .hints {
      margin-top: 8px;
      font-size: 12px;
      color: var(--muted);
      line-height: 1.45;
    }

    .code {
      display: inline-block;
      background: #f0eade;
      border: 1px solid #dbd0bb;
      border-radius: 6px;
      padding: 1px 5px;
      color: #3b3b35;
      margin: 2px 3px 0 0;
    }

    @media (max-width: 900px) {
      .app {
        grid-template-columns: 1fr;
      }

      .sidebar {
        border-right: 0;
        border-bottom: 1px solid var(--border);
      }

      .meta-row .value {
        max-width: 100%;
      }

      .row {
        max-width: 96%;
      }

      .input-row {
        grid-template-columns: 1fr;
      }
    }
  </style>
</head>
<body>
  <div class="app">
    <aside class="sidebar">
      <div class="brand">
        <h1>UltraBot Control</h1>
        <p>Local-first assistant UI</p>
        <div class="status">
          <span id="status-dot" class="dot"></span>
          <span id="status-text">Connecting...</span>
        </div>
      </div>

      <div class="panel meta">
        <div class="meta-row">
          <span class="label">Model</span>
          <span id="model-display" class="value">local brain</span>
        </div>
        <div class="meta-row">
          <span class="label">Language</span>
          <span id="lang-display" class="value">English</span>
        </div>
        <div class="meta-row">
          <span class="label">Transport</span>
          <span id="transport-display" class="value">WebSocket</span>
        </div>
        <div class="meta-row">
          <span class="label">Engine</span>
          <span id="engine-display" class="value">unknown</span>
        </div>
      </div>

      <div class="controls">
        <button id="new-chat-btn" type="button">New Chat</button>
        <button id="clear-chat-btn" type="button">Clear Chat</button>
      </div>

      <section class="panel">
        <div class="sessions-header" style="margin:-12px -12px 8px -12px; border-bottom:1px solid var(--border);">Runtime Control</div>
        <div class="runtime-grid">
          <label>
            Brain Mode
            <select id="brain-mode">
              <option value="hybrid">Hybrid (recommended)</option>
              <option value="local-llm">Local LLM</option>
              <option value="neurosymbolic">Neurosymbolic Brain</option>
              <option value="api">External API</option>
            </select>
          </label>

          <label>
            Preferred Channel
            <select id="preferred-channel">
              <option value="webui">webui</option>
              <option value="telegram">telegram</option>
              <option value="discord">discord</option>
              <option value="slack">slack</option>
              <option value="whatsapp">whatsapp</option>
              <option value="cli">cli</option>
            </select>
          </label>

          <label>
            API Base (OpenAI-compatible)
            <input id="api-base" type="text" placeholder="http://localhost:11434/v1" />
          </label>

          <label>
            API Model
            <input id="api-model" type="text" placeholder="llama3.2:1b" />
          </label>

          <label>
            API Key
            <input id="api-key" type="password" placeholder="optional for local endpoints" />
          </label>

          <label>
            Channel Config (JSON)
            <textarea id="channel-config" placeholder='{"telegram":{"chat_id":"..."}}'></textarea>
          </label>

          <div class="runtime-actions">
            <button id="save-runtime-btn" type="button">Save Runtime</button>
            <button id="test-api-btn" type="button">Test API</button>
          </div>

          <div id="runtime-status" class="runtime-status">Runtime settings are local to this running server process.</div>
        </div>
      </section>

      <section class="sessions">
        <div class="sessions-header">Sessions</div>
        <div id="sessions-list" class="session-list">
          <button class="session-item active" type="button" data-sid="webui:default">Default session</button>
        </div>
      </section>
    </aside>

    <main class="main">
      <header class="topbar">
        <div>
          <div class="title">Control Panel</div>
          <div class="subtitle">Send tasks and commands through WebSocket or HTTP fallback</div>
        </div>
        <div id="conn-indicator" class="connection">offline</div>
      </header>

      <section id="chat" class="chat" aria-live="polite"></section>

      <div id="typing" class="typing"><span></span><span></span><span></span></div>

      <footer class="footer">
        <div class="input-row">
          <input
            id="msg"
            type="text"
            autocomplete="off"
            placeholder="Try fast: !dir, !echo hello, /status, /time"
          />
          <button id="send-btn" class="send" type="button">Send</button>
          <button id="clear-btn" class="clear" type="button">Clear Input</button>
        </div>
        <div class="hints">
          Quick commands:
          <span class="code">/help</span>
          <span class="code">/status</span>
          <span class="code">/time</span>
          <span class="code">!dir</span>
          <span class="code">open url: https://example.com</span>
          <span class="code">clipboard read</span>
        </div>
      </footer>
    </main>
  </div>

  <script>
    const WS_PORT = __WS_PORT__;
    let ws = null;
    let reconnectTimer = null;
    let activeWsUrl = "";
    let currentSession = "webui:default";

    const chat = document.getElementById("chat");
    const msgInput = document.getElementById("msg");
    const sendBtn = document.getElementById("send-btn");
    const clearBtn = document.getElementById("clear-btn");
    const newChatBtn = document.getElementById("new-chat-btn");
    const clearChatBtn = document.getElementById("clear-chat-btn");
    const sessionsList = document.getElementById("sessions-list");
    const statusText = document.getElementById("status-text");
    const statusDot = document.getElementById("status-dot");
    const connInd = document.getElementById("conn-indicator");
    const modelDisp = document.getElementById("model-display");
    const langDisp = document.getElementById("lang-display");
    const transportDisp = document.getElementById("transport-display");
    const engineDisp = document.getElementById("engine-display");
    const typing = document.getElementById("typing");
    const brainModeSel = document.getElementById("brain-mode");
    const preferredChannelSel = document.getElementById("preferred-channel");
    const apiBaseInput = document.getElementById("api-base");
    const apiModelInput = document.getElementById("api-model");
    const apiKeyInput = document.getElementById("api-key");
    const channelConfigInput = document.getElementById("channel-config");
    const saveRuntimeBtn = document.getElementById("save-runtime-btn");
    const testApiBtn = document.getElementById("test-api-btn");
    const runtimeStatus = document.getElementById("runtime-status");

    function nowTime() {
      const d = new Date();
      const hh = String(d.getHours()).padStart(2, "0");
      const mm = String(d.getMinutes()).padStart(2, "0");
      const ss = String(d.getSeconds()).padStart(2, "0");
      return hh + ":" + mm + ":" + ss;
    }

    function setStatus(mode, detail) {
      if (mode === "online") {
        statusText.textContent = detail || "Connected";
        statusDot.style.background = "var(--ok)";
        connInd.textContent = "online";
        connInd.style.color = "var(--ok)";
        return;
      }

      if (mode === "connecting") {
        statusText.textContent = "Connecting...";
        statusDot.style.background = "var(--warn)";
        connInd.textContent = "connecting";
        connInd.style.color = "var(--warn)";
        return;
      }

      if (mode === "retrying") {
        statusText.textContent = "Retrying...";
        statusDot.style.background = "var(--warn)";
        connInd.textContent = "retrying";
        connInd.style.color = "var(--warn)";
        return;
      }

      statusText.textContent = "Disconnected";
      statusDot.style.background = "var(--danger)";
      connInd.textContent = "offline";
      connInd.style.color = "var(--danger)";
    }

    function appendMessage(role, text) {
      const row = document.createElement("div");
      row.className = "row " + role;

      const badge = document.createElement("div");
      badge.className = "badge";
      badge.textContent = role === "user" ? "YOU" : "BOT";

      const wrapper = document.createElement("div");

      const bubble = document.createElement("div");
      bubble.className = "bubble";
      bubble.textContent = text;

      const meta = document.createElement("div");
      meta.className = "meta-time";
      meta.textContent = nowTime();

      wrapper.appendChild(bubble);
      wrapper.appendChild(meta);

      row.appendChild(badge);
      row.appendChild(wrapper);
      chat.appendChild(row);
      chat.scrollTop = chat.scrollHeight;
    }

    function showTyping() {
      typing.style.display = "inline-flex";
      chat.appendChild(typing);
      chat.scrollTop = chat.scrollHeight;
    }

    function hideTyping() {
      typing.style.display = "none";
    }

    function resolveWsCandidates() {
      const proto = location.protocol === "https:" ? "wss" : "ws";
      const rawHost = (location.hostname || "").trim().toLowerCase();
      const primaryHost = (!rawHost || rawHost === "0.0.0.0" || rawHost === "[::]") ? "127.0.0.1" : rawHost;
      const hosts = [primaryHost];
      if (!hosts.includes("127.0.0.1")) hosts.push("127.0.0.1");
      if (!hosts.includes("localhost")) hosts.push("localhost");

      const out = [];
      for (const host of hosts) {
        out.push(proto + "://" + host + ":" + WS_PORT + "/ws");
        out.push(proto + "://" + host + ":" + WS_PORT + "/");
      }
      return out;
    }

    function openWs(url) {
      return new Promise((resolve, reject) => {
        let done = false;
        const sock = new WebSocket(url);
        const timer = setTimeout(() => {
          if (done) return;
          done = true;
          try { sock.close(); } catch (e) { }
          reject(new Error("timeout"));
        }, 2500);

        sock.onopen = () => {
          if (done) return;
          done = true;
          clearTimeout(timer);
          resolve(sock);
        };

        sock.onerror = () => {
          if (done) return;
          done = true;
          clearTimeout(timer);
          reject(new Error("error"));
        };

        sock.onclose = () => {
          if (done) return;
          done = true;
          clearTimeout(timer);
          reject(new Error("closed"));
        };
      });
    }

    async function connect() {
      if (ws && ws.readyState <= 1) return;
      setStatus("connecting");

      const candidates = resolveWsCandidates();
      ws = null;
      activeWsUrl = "";

      for (const candidate of candidates) {
        try {
          ws = await openWs(candidate);
          activeWsUrl = candidate;
          break;
        } catch (e) {
          // Try next candidate.
        }
      }

      if (!ws) {
        try {
          const health = await fetch("/api/health", { method: "GET" });
          if (health.ok) {
            transportDisp.textContent = "HTTP fallback";
            setStatus("online", "Connected via HTTP");
          } else {
            setStatus("retrying");
          }
        } catch (e) {
          setStatus("retrying");
        }

        clearTimeout(reconnectTimer);
        reconnectTimer = setTimeout(() => { connect(); }, 3000);
        return;
      }

      ws.onopen = () => {
        transportDisp.textContent = "WebSocket";
        setStatus("online", "Connected");
        clearTimeout(reconnectTimer);
      };

      ws.onclose = () => {
        hideTyping();
        setStatus("retrying");
        reconnectTimer = setTimeout(() => { connect(); }, 3000);
      };

      ws.onerror = () => {
        setStatus("retrying");
      };

      ws.onmessage = (event) => {
        let content = event.data;

        if (typeof content === "string" && content.indexOf('"type":"ack"') >= 0) {
          setStatus("online", "Processing...");
          return;
        }

        try {
          const data = JSON.parse(event.data);
          if (data && data.type === "ack") {
            setStatus("online", "Processing...");
            return;
          }
          if (data && data.type === "error") {
            hideTyping();
            appendMessage("bot", String(data.content || "Request failed."));
            return;
          }
          if (data && data.type === "message") {
            content = String(data.content || "");
          }
          if (data && data.model) {
            modelDisp.textContent = String(data.model);
          }
          if (data && data.engine) {
            engineDisp.textContent = String(data.engine);
          }
          if (data && data.lang) {
            langDisp.textContent = String(data.lang);
          }
        } catch (e) {
          // Plain text response.
        }

        hideTyping();
        appendMessage("bot", String(content || ""));
      };

      if (activeWsUrl) {
        transportDisp.title = activeWsUrl;
      }

      clearTimeout(reconnectTimer);
      setStatus("online", "Connected");
    }

    async function sendViaHttpFallback(text) {
      const resp = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, session_id: currentSession })
      });

      if (!resp.ok) {
        throw new Error("HTTP " + resp.status);
      }

      const payload = await resp.json();
      if (!payload || !payload.ok) {
        throw new Error("invalid_response");
      }

      if (payload.engine) {
        engineDisp.textContent = String(payload.engine);
      }

      return String(payload.content || "");
    }

    function setRuntimeStatus(text, kind) {
      runtimeStatus.textContent = text;
      if (kind === "ok") {
        runtimeStatus.style.color = "var(--ok)";
        return;
      }
      if (kind === "error") {
        runtimeStatus.style.color = "var(--danger)";
        return;
      }
      runtimeStatus.style.color = "var(--muted)";
    }

    async function loadRuntimeConfig() {
      try {
        const resp = await fetch("/api/runtime-config", { method: "GET" });
        if (!resp.ok) {
          setRuntimeStatus("Unable to load runtime settings.", "error");
          return;
        }
        const cfg = await resp.json();
        if (!cfg || !cfg.ok || !cfg.config) {
          setRuntimeStatus("Runtime settings response is invalid.", "error");
          return;
        }

        const c = cfg.config;
        brainModeSel.value = String(c.brain_mode || "hybrid");
        preferredChannelSel.value = String(c.preferred_channel || "webui");
        apiBaseInput.value = String((c.api && c.api.api_base) || "");
        apiModelInput.value = String((c.api && c.api.model) || "");
        apiKeyInput.value = "";

        const channels = (c.channels && typeof c.channels === "object") ? c.channels : {};
        channelConfigInput.value = JSON.stringify(channels, null, 2);

        const keyState = c.api_key_set ? "API key is set (hidden)." : "No API key set.";
        setRuntimeStatus("Loaded runtime settings. " + keyState, "ok");
      } catch (e) {
        setRuntimeStatus("Failed to load runtime settings.", "error");
      }
    }

    async function saveRuntimeConfig() {
      let channels = {};
      const rawChannels = channelConfigInput.value.trim();
      if (rawChannels) {
        try {
          channels = JSON.parse(rawChannels);
          if (typeof channels !== "object" || channels === null || Array.isArray(channels)) {
            setRuntimeStatus("Channel config must be a JSON object.", "error");
            return;
          }
        } catch (e) {
          setRuntimeStatus("Channel config JSON is invalid.", "error");
          return;
        }
      }

      const payload = {
        brain_mode: brainModeSel.value,
        preferred_channel: preferredChannelSel.value,
        channels: channels,
        api: {
          api_base: apiBaseInput.value.trim(),
          model: apiModelInput.value.trim(),
          api_key: apiKeyInput.value,
        },
      };

      try {
        const resp = await fetch("/api/runtime-config", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        const out = await resp.json();
        if (!resp.ok || !out || !out.ok) {
          setRuntimeStatus("Failed to save runtime settings.", "error");
          return;
        }
        setRuntimeStatus("Runtime settings saved.", "ok");
        apiKeyInput.value = "";
        if (out.config && out.config.brain_mode) {
          engineDisp.textContent = String(out.config.brain_mode);
        }
      } catch (e) {
        setRuntimeStatus("Failed to save runtime settings.", "error");
      }
    }

    async function testApiConfig() {
      setRuntimeStatus("Testing API...", "default");
      try {
        const resp = await fetch("/api/runtime-config/test", { method: "POST" });
        const out = await resp.json();
        if (!resp.ok || !out || !out.ok) {
          const detail = out && out.error ? String(out.error) : "API test failed.";
          setRuntimeStatus(detail, "error");
          return;
        }
        const detail = out.preview ? ("API test OK: " + String(out.preview)) : "API test OK.";
        setRuntimeStatus(detail, "ok");
      } catch (e) {
        setRuntimeStatus("API test failed.", "error");
      }
    }

    async function send() {
      const text = msgInput.value.trim();
      if (!text) return;

      appendMessage("user", text);
      msgInput.value = "";
      msgInput.focus();
      showTyping();

      if (!ws || ws.readyState !== 1) {
        try {
          const content = await sendViaHttpFallback(text);
          hideTyping();
          transportDisp.textContent = "HTTP fallback";
          setStatus("online", "Connected via HTTP");
          appendMessage("bot", content);
          connect();
        } catch (e) {
          hideTyping();
          appendMessage("bot", "Not connected. Please retry in a moment.");
          setStatus("retrying");
          connect();
        }
        return;
      }

      ws.send(JSON.stringify({ type: "chat", message: text, session_id: currentSession }));
    }

    function activateSession(button) {
      const items = sessionsList.querySelectorAll(".session-item");
      items.forEach((item) => item.classList.remove("active"));
      button.classList.add("active");
      currentSession = button.dataset.sid || "webui:default";
    }

    function createSession() {
      const sid = "webui:session_" + Date.now();
      const button = document.createElement("button");
      button.type = "button";
      button.className = "session-item";
      button.dataset.sid = sid;
      button.textContent = "Session " + new Date().toLocaleTimeString();
      button.addEventListener("click", () => activateSession(button));
      sessionsList.appendChild(button);
      activateSession(button);

      chat.innerHTML = "";
      appendMessage("bot", "New session started. What should we do next?");
    }

    function clearChat() {
      chat.innerHTML = "";
      appendMessage("bot", "Chat cleared. I am ready for your next command.");
    }

    sendBtn.addEventListener("click", send);
    clearBtn.addEventListener("click", () => {
      msgInput.value = "";
      msgInput.focus();
    });

    msgInput.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        send();
      }
    });

    newChatBtn.addEventListener("click", createSession);
    clearChatBtn.addEventListener("click", clearChat);
    saveRuntimeBtn.addEventListener("click", saveRuntimeConfig);
    testApiBtn.addEventListener("click", testApiConfig);

    const initialSession = document.querySelector(".session-item");
    if (initialSession) {
      initialSession.addEventListener("click", () => activateSession(initialSession));
    }

    const browserLanguage = (navigator.language || "").trim();
    if (browserLanguage) {
      langDisp.textContent = browserLanguage;
    }

    appendMessage("bot", "Welcome to UltraBot. Use this panel to send commands, tasks, and questions.");
    loadRuntimeConfig();
    connect();
  </script>
</body>
</html>
"""


class ControlUIServer:
    """Serve the UltraBot Control UI and WebSocket chat endpoint."""

    def __init__(
        self,
        host: str,
        port: int,
        agent: AgentLoop,
        sessions: SessionManager,
    ) -> None:
        self.host = host
        self.port = port
        self.agent = agent
        self.sessions = sessions
        self._loop: asyncio.AbstractEventLoop | None = None
        self._http_server: ThreadingHTTPServer | None = None
        self._http_thread: threading.Thread | None = None
        self._ws_server: websockets.server.Serve | None = None
        self._runtime_cfg: dict[str, Any] = {
          "brain_mode": "hybrid",
          "preferred_channel": "webui",
          "channels": {},
          "api": {
            "api_base": "",
            "model": "",
            "api_key": "",
          },
        }
        self._api_provider_cache: tuple[str, str, str, CustomProvider] | None = None

    async def start(self) -> None:
        self._loop = asyncio.get_running_loop()
        self._start_http_server()
        self._ws_server = await websockets.serve(self._handle_ws, self.host, self.port)

    async def stop(self) -> None:
        if self._ws_server:
            self._ws_server.close()
            await self._ws_server.wait_closed()
            self._ws_server = None
        self._stop_http_server()

    def _start_http_server(self) -> None:
        if self._http_server:
            return

        content = (
            _HTML
            .replace("__WS_PORT__", str(self.port))
            .replace("__HOST__", self.host)
        ).encode("utf-8")
        server = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802
                if self.path in ("/api/health",):
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    body = b'{"ok":true}'
                    self.send_header("Content-Length", str(len(body)))
                    self.send_header("X-Content-Type-Options", "nosniff")
                    self.end_headers()
                    self.wfile.write(body)
                    return

                if self.path in ("/api/runtime-config",):
                    payload = {"ok": True, "config": server._runtime_public_config()}
                    body = json.dumps(payload).encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.send_header("Content-Length", str(len(body)))
                    self.send_header("X-Content-Type-Options", "nosniff")
                    self.end_headers()
                    self.wfile.write(body)
                    return

                if self.path not in ("/", "/index.html"):
                    self.send_response(404)
                    self.end_headers()
                    return
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.send_header("X-Content-Type-Options", "nosniff")
                self.end_headers()
                self.wfile.write(content)

            def do_POST(self) -> None:  # noqa: N802
                if self.path not in ("/api/chat", "/api/runtime-config", "/api/runtime-config/test"):
                    self.send_response(404)
                    self.end_headers()
                    return

                content_length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(content_length) if content_length > 0 else b""

                try:
                    payload = json.loads(raw.decode("utf-8")) if raw else {}
                except Exception:
                    self.send_response(400)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    err = b'{"ok":false,"error":"invalid_json"}'
                    self.send_header("Content-Length", str(len(err)))
                    self.end_headers()
                    self.wfile.write(err)
                    return

                if self.path == "/api/runtime-config":
                    server._update_runtime_config(payload if isinstance(payload, dict) else {})
                    out = json.dumps({"ok": True, "config": server._runtime_public_config()}).encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.send_header("Content-Length", str(len(out)))
                    self.end_headers()
                    self.wfile.write(out)
                    return

                if self.path == "/api/runtime-config/test":
                    if server._loop is None:
                        self.send_response(503)
                        self.send_header("Content-Type", "application/json; charset=utf-8")
                        out = b'{"ok":false,"error":"server_not_ready"}'
                        self.send_header("Content-Length", str(len(out)))
                        self.end_headers()
                        self.wfile.write(out)
                        return

                    try:
                        fut = asyncio.run_coroutine_threadsafe(server._test_api_provider(), server._loop)
                        result = fut.result(timeout=20)
                    except Exception as exc:
                        result = {"ok": False, "error": f"API test failed: {exc}"}

                    out = json.dumps(result).encode("utf-8")
                    self.send_response(200 if result.get("ok") else 400)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.send_header("Content-Length", str(len(out)))
                    self.end_headers()
                    self.wfile.write(out)
                    return

                # /api/chat path continues below.

                message = str(payload.get("message", "") or "").strip()
                session_id = str(payload.get("session_id", "webui:default") or "webui:default")
                if not message:
                    self.send_response(400)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    err = b'{"ok":false,"error":"empty_message"}'
                    self.send_header("Content-Length", str(len(err)))
                    self.end_headers()
                    self.wfile.write(err)
                    return

                if server._loop is None:
                    self.send_response(503)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    err = b'{"ok":false,"error":"server_not_ready"}'
                    self.send_header("Content-Length", str(len(err)))
                    self.end_headers()
                    self.wfile.write(err)
                    return

                try:
                    fut = asyncio.run_coroutine_threadsafe(
                        server._process_chat_with_engine(message=message, session_id=session_id),
                        server._loop,
                    )
                    response, engine = fut.result(timeout=90)
                except Exception:
                    self.send_response(500)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    err = b'{"ok":false,"error":"chat_failed"}'
                    self.send_header("Content-Length", str(len(err)))
                    self.end_headers()
                    self.wfile.write(err)
                    return

                body = json.dumps({"ok": True, "content": response, "engine": engine}).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("X-Content-Type-Options", "nosniff")
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
                return

        self._http_server = ThreadingHTTPServer((self.host, self.port + 1), Handler)
        self._http_thread = threading.Thread(target=self._http_server.serve_forever, daemon=True)
        self._http_thread.start()

    def _stop_http_server(self) -> None:
        if not self._http_server:
            return
        self._http_server.shutdown()
        self._http_server.server_close()
        self._http_server = None
        self._http_thread = None

    async def _handle_ws(self, websocket: websockets.WebSocketServerProtocol) -> None:
        async for raw in websocket:
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                continue

            if payload.get("type") != "chat":
                continue

            message = payload.get("message", "")
            session_id = payload.get("session_id", "webui:default")
            if not message:
                continue

            # Send an immediate ack so the UI feels responsive even when LLM inference takes time.
            await websocket.send(json.dumps({"type": "ack", "content": "processing", "engine": "pending"}))

            try:
              response, engine = await self._process_chat_with_engine(message=message, session_id=session_id)
              await websocket.send(json.dumps({"type": "message", "content": response, "engine": engine}))
            except Exception:
                await websocket.send(json.dumps({"type": "error", "content": "Request failed. Please retry."}))

    def _fast_response(self, message: str, session_id: str) -> str | None:
        text = message.strip()
        lower = text.lower()
        if not lower:
            return None

        words = set(lower.replace("?", " ").replace(",", " ").replace(".", " ").split())

        if lower in {"/ping", "ping"}:
            return "pong"

        if lower in {"/help", "help"}:
            return "Quick commands: /ping, /status, /time, /ls, !<shell command>. For full tasks, ask normally."

        if lower in {"/status", "status"}:
            return f"UI online. session={session_id} model={self.agent.model}"

        # Plain-English status checks should stay low-latency.
        if ("status" in words) or ("health" in words) or ("online" in words and "are" in words):
            return f"UI online. session={session_id} model={self.agent.model}"

        if lower in {"/time", "time", "/date", "date"}:
            return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Natural language time/date requests.
        if (
            ("time" in words)
            or ("date" in words)
            or ("day" in words and "today" in words)
        ):
            return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if lower.startswith("/ls"):
            root = self.agent.workspace
            try:
                names = sorted(p.name for p in root.iterdir())[:60]
            except Exception:
                return "Unable to list workspace files right now."
            if not names:
                return "Workspace is empty."
            return "Workspace files:\n" + "\n".join(f"- {name}" for name in names)

        # Natural language file-list requests.
        if (
            ("list" in words and "files" in words)
            or ("show" in words and "files" in words)
            or ("current" in words and "directory" in words)
            or ("workspace" in words and "files" in words)
        ):
            root = self.agent.workspace
            try:
                names = sorted(p.name for p in root.iterdir())[:60]
            except Exception:
                return "Unable to list workspace files right now."
            if not names:
                return "Workspace is empty."
            return "Workspace files:\n" + "\n".join(f"- {name}" for name in names)

        return None

    async def _run_quick_shell(self, command: str) -> str:
        cmd = command.strip()
        if not cmd:
            return "Usage: !<shell command> (example: !dir)"

        try:
            proc = await asyncio.to_thread(
                subprocess.run,
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=2.0,
                cwd=str(self.agent.workspace),
            )
        except subprocess.TimeoutExpired:
            return "Command timed out (2.0s limit)."
        except Exception as exc:
            return f"Command failed: {exc}"

        output = (proc.stdout or proc.stderr or "").strip()
        if not output:
            return f"Done (exit {proc.returncode})"
        if len(output) > 3500:
            output = output[:3500] + "\n... (truncated)"
        return output

    async def _process_chat_with_engine(self, message: str, session_id: str) -> tuple[str, str]:
        if message.strip().startswith("!"):
            return await self._run_quick_shell(message.strip()[1:]), "quick-shell"

        fast = self._fast_response(message=message, session_id=session_id)
        if fast is not None:
            return fast, "fast-local"

        mode = str(self._runtime_cfg.get("brain_mode", "hybrid") or "hybrid").strip().lower()

        if mode == "neurosymbolic":
            return self.agent._local_brain_fallback(message, None), "neurosymbolic"

        if mode == "api":
            return await self._process_api_chat(message=message, session_id=session_id), "api"

        if mode == "local-llm":
            response = await self.agent.process_direct(
                message,
                session_key=session_id,
                channel="webui",
                chat_id=session_id,
            )
            return response, "local-llm"

        response = await self.agent.process_direct(
            message,
            session_key=session_id,
            channel="webui",
            chat_id=session_id,
        )
        if (response or "").startswith("[Local Fallback Mode]"):
            return response, "neurosymbolic-fallback"
        return response, "local-llm"

    def _runtime_public_config(self) -> dict[str, Any]:
        cfg = deepcopy(self._runtime_cfg)
        api = cfg.get("api") if isinstance(cfg.get("api"), dict) else {}
        api_key = str(api.get("api_key", "") or "")
        cfg["api"] = {
            "api_base": str(api.get("api_base", "") or ""),
            "model": str(api.get("model", "") or ""),
        }
        cfg["api_key_set"] = bool(api_key)
        return cfg

    def _update_runtime_config(self, payload: dict[str, Any]) -> None:
        if not isinstance(payload, dict):
            return

        mode = str(payload.get("brain_mode", self._runtime_cfg["brain_mode"]) or "hybrid").strip().lower()
        if mode not in {"hybrid", "local-llm", "neurosymbolic", "api"}:
            mode = "hybrid"

        preferred_channel = str(payload.get("preferred_channel", self._runtime_cfg["preferred_channel"]) or "webui").strip().lower()
        if not preferred_channel:
            preferred_channel = "webui"

        channels = payload.get("channels", self._runtime_cfg.get("channels", {}))
        if not isinstance(channels, dict):
            channels = {}

        incoming_api = payload.get("api", {})
        if not isinstance(incoming_api, dict):
            incoming_api = {}

        old_api = self._runtime_cfg.get("api", {}) if isinstance(self._runtime_cfg.get("api"), dict) else {}
        api_key = incoming_api.get("api_key", old_api.get("api_key", ""))
        if api_key is None:
            api_key = old_api.get("api_key", "")

        self._runtime_cfg = {
            "brain_mode": mode,
            "preferred_channel": preferred_channel,
            "channels": channels,
            "api": {
                "api_base": str(incoming_api.get("api_base", old_api.get("api_base", "")) or ""),
                "model": str(incoming_api.get("model", old_api.get("model", "")) or ""),
                "api_key": str(api_key or ""),
            },
        }

        self._api_provider_cache = None

    def _get_api_provider(self) -> CustomProvider | None:
        api_cfg = self._runtime_cfg.get("api", {}) if isinstance(self._runtime_cfg.get("api"), dict) else {}
        api_base = str(api_cfg.get("api_base", "") or "").strip()
        model = str(api_cfg.get("model", "") or "").strip()
        api_key = str(api_cfg.get("api_key", "") or "").strip()

        if not api_base:
            return None

        cache = self._api_provider_cache
        if cache and cache[0] == api_base and cache[1] == model and cache[2] == api_key:
            return cache[3]

        provider = CustomProvider(
            api_key=api_key or "no-key",
            api_base=api_base,
            default_model=model or "default",
        )
        self._api_provider_cache = (api_base, model, api_key, provider)
        return provider

    async def _process_api_chat(self, message: str, session_id: str) -> str:
        provider = self._get_api_provider()
        if provider is None:
            return "API mode is selected but API Base is not set. Open Runtime Control and set API Base + model."

        session = self.sessions.get_or_create(session_id)
        history = session.get_history(max_messages=16)
        messages: list[dict[str, Any]] = [
            {
                "role": "system",
                "content": "You are UltraBot in API mode. Reply directly with concise plain text.",
            }
        ]
        for item in history:
            role = item.get("role")
            content = item.get("content")
            if role in {"user", "assistant"} and isinstance(content, str) and content.strip():
                messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": message})

        response = await provider.chat(
            messages=messages,
            tools=[],
            model=provider.get_default_model(),
            temperature=0.2,
            max_tokens=512,
        )
        content = (response.content or "").strip()
        if not content:
            content = "API mode returned no output."

        session.add_message("user", message)
        session.add_message("assistant", content)
        self.sessions.save(session)
        return content

    async def _test_api_provider(self) -> dict[str, Any]:
        provider = self._get_api_provider()
        if provider is None:
            return {"ok": False, "error": "API Base is required for API mode."}

        response = await provider.chat(
            messages=[
                {"role": "system", "content": "Reply with one short line."},
                {"role": "user", "content": "Say OK"},
            ],
            tools=[],
            model=provider.get_default_model(),
            temperature=0.0,
            max_tokens=24,
        )
        content = (response.content or "").strip()
        if not content or response.finish_reason == "error":
            return {"ok": False, "error": content or "API call failed."}
        return {"ok": True, "preview": content}

    async def _process_chat(self, message: str, session_id: str) -> str:
        response, _ = await self._process_chat_with_engine(message=message, session_id=session_id)
        return response

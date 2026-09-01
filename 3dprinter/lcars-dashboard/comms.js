/* COMMS — Spock chat bridge (shared by the LCARS dashboard overlay and the
   standalone /comms mobile page). Renders into #comms-root and injects its
   own styles, so host pages only need the root element + this script.

   Flow:
     locked  -> [ENGAGE — REQUEST CODE] -> code DMed to Discord only
             -> enter code -> unlocked (HttpOnly session cookie)
     chat    -> POST /api/chat (SSE streamed Spock replies)
*/
(function () {
  "use strict";
  var ROOT = document.getElementById("comms-root");
  if (!ROOT) return;

  /* ---------------- injected styles ---------------- */
  var css = [
    "#comms-root{display:none;}",
    "#comms-root.open{display:flex;}",
    "#comms-root:not(.standalone){position:fixed;right:18px;bottom:18px;",
    "  width:min(480px,calc(100vw - 36px));height:min(620px,calc(100vh - 36px));",
    "  background:#0d0d12;border:1px solid #2a2a38;border-radius:26px;",
    "  overflow:hidden;z-index:5000;flex-direction:column;",
    "  box-shadow:0 10px 44px rgba(0,0,0,.65);}",
    "#comms-root.standalone{position:fixed;inset:0;width:100%;height:100%;",
    "  background:#050505;flex-direction:column;border:none;border-radius:0;}",
    "@media (max-width:900px){",
    "  #comms-root:not(.standalone){right:0;bottom:0;width:100vw;height:100vh;",
    "    border-radius:0;border:none;}}",
    ".c-head{display:flex;align-items:center;gap:10px;flex:0 0 auto;",
    "  background:#ff9c00;color:#000;padding:10px 16px;}",
    ".c-head .c-title{font-weight:800;letter-spacing:2px;text-transform:uppercase;font-size:15px;}",
    ".c-head .c-sub{font-size:11px;opacity:.75;letter-spacing:1px;}",
    ".c-head .c-close{margin-left:auto;border:none;background:transparent;color:#000;",
    "  font-size:20px;cursor:pointer;font-weight:800;line-height:1;padding:4px 8px;}",
    "#comms-root.standalone .c-close{display:none;}",
    ".c-body{flex:1 1 auto;display:flex;flex-direction:column;min-height:0;padding:14px;}",
    ".c-lock{display:flex;flex-direction:column;align-items:center;justify-content:center;",
    "  gap:14px;height:100%;text-align:center;padding:18px;}",
    ".c-lock .c-locktitle{color:#ff9c00;font-weight:800;letter-spacing:3px;",
    "  text-transform:uppercase;font-size:16px;}",
    ".c-lock .c-locktext{color:#8a8a99;font-size:13px;max-width:34em;line-height:1.5;}",
    ".c-btn{border:none;cursor:pointer;font-weight:800;letter-spacing:2px;",
    "  text-transform:uppercase;padding:12px 26px;border-radius:999px;font-size:14px;}",
    ".c-btn.engage{background:#ff9c00;color:#000;}",
    ".c-btn.engage:hover{filter:brightness(1.1);}",
    ".c-btn:disabled{opacity:.4;cursor:not-allowed;}",
    ".c-codebox{display:none;flex-direction:column;gap:10px;width:100%;max-width:340px;}",
    ".c-codebox.show{display:flex;}",
    ".c-code{background:#101018;border:1px solid #2a2a38;color:#7dff9a;",
    "  font-family:Consolas,'SF Mono',Menlo,monospace;font-size:20px;",
    "  letter-spacing:3px;text-align:center;padding:12px;border-radius:12px;",
    "  text-transform:uppercase;outline:none;}",
    ".c-code:focus{border-color:#ff9c00;}",
    ".c-status{color:#8a8a99;font-size:12px;letter-spacing:1px;min-height:1.2em;}",
    ".c-status.err{color:#ff6b6b;}",
    ".c-status.ok{color:#7dff9a;}",
    ".c-msgs{flex:1 1 auto;overflow-y:auto;display:flex;flex-direction:column;gap:10px;",
    "  padding:6px 2px;min-height:0;}",
    ".c-msg{max-width:82%;padding:10px 14px;border-radius:16px;font-size:14px;",
    "  line-height:1.45;white-space:pre-wrap;word-wrap:break-word;}",
    ".c-msg.user{align-self:flex-end;background:#ff9c00;color:#000;",
    "  border-bottom-right-radius:4px;}",
    ".c-msg.spock{align-self:flex-start;background:#101018;border:1px solid #2a2a38;",
    "  color:#e8e8e8;border-bottom-left-radius:4px;}",
    ".c-msg .c-who{display:block;font-size:10px;letter-spacing:2px;text-transform:uppercase;",
    "  opacity:.6;margin-bottom:4px;}",
    ".c-typing{color:#8a8a99;font-size:12px;letter-spacing:2px;padding:4px 6px;min-height:1.4em;}",
    ".c-inputrow{flex:0 0 auto;display:flex;gap:10px;padding-top:10px;}",
    ".c-input{flex:1;background:#101018;border:1px solid #2a2a38;color:#e8e8e8;",
    "  padding:12px 14px;border-radius:999px;font-size:15px;outline:none;}",
    ".c-input:focus{border-color:#7ab8ff;}",
    ".c-send{border:none;cursor:pointer;font-weight:800;letter-spacing:1px;",
    "  text-transform:uppercase;background:#7ab8ff;color:#000;border-radius:999px;",
    "  padding:0 20px;font-size:13px;}",
    ".c-send:disabled{opacity:.4;cursor:not-allowed;}",
    ".c-lockbtn{flex:0 0 auto;background:transparent;color:#ff6b6b;",
    "  border:1px solid #ff6b6b;border-radius:999px;padding:0 14px;cursor:pointer;",
    "  font-weight:800;letter-spacing:1px;font-size:12px;text-transform:uppercase;}",
    ".c-foot{flex:0 0 auto;color:#8a8a99;font-size:10px;letter-spacing:1px;",
    "  text-align:center;padding:8px 10px 2px;}"
  ].join("\n");
  var styleEl = document.createElement("style");
  styleEl.textContent = css;
  document.head.appendChild(styleEl);

  /* ---------------- state ---------------- */
  var unlocked = false;
  var busy = false;
  var msgsEl = null;
  var SESSION_KEY = "lcars-dash";

  /* ---------------- helpers ---------------- */
  function el(tag, cls, html) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (html != null) e.innerHTML = html;
    return e;
  }
  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function errText(j) {
    var m = {
      no_code: "No code pending — press ENGAGE first.",
      expired: "Code expired — request a new one.",
      locked: "Too many attempts — request a new code.",
      invalid: "Code not recognised.",
      rate_limited: "Slow down — wait a moment before requesting again.",
      discord_dm_failed: "Discord DM failed — check the bot can DM you.",
      unauthorized: "Session expired — re-unlock.",
      bridge_unconfigured: "Bridge not configured yet — gateway restart pending.",
      bridge_unreachable: "Spock unreachable — is the gateway up?",
      empty: "Message empty.",
      too_long: "Message too long (4k limit)."
    };
    return m[j && j.error] || (j && j.error) || "Comms failure.";
  }
  function setStatus(msg, cls) {
    var s = document.getElementById("c-status");
    if (!s) return;
    s.textContent = msg;
    s.className = "c-status" + (cls ? " " + cls : "");
  }
  function scrollDown() {
    if (msgsEl) msgsEl.scrollTop = msgsEl.scrollHeight;
  }

  /* ---------------- render ---------------- */
  function render() {
    ROOT.innerHTML = "";
    var head = el("div", "c-head");
    head.appendChild(el("span", "c-title", "🖖 SPOCK — COMMS"));
    head.appendChild(el("span", "c-sub", "printer bay uplink"));
    var close = el("button", "c-close", "✕");
    close.onclick = function () { ROOT.classList.remove("open"); };
    head.appendChild(close);
    ROOT.appendChild(head);

    var body = el("div", "c-body");
    if (!unlocked) {
      var lock = el("div", "c-lock");
      lock.appendChild(el("div", "c-locktitle", "COMMS LOCKED"));
      lock.appendChild(el("div", "c-locktext",
        "Hailing frequencies closed. To open a channel, Spock transmits a " +
        "one-time code — by direct Discord DM only. Request the code, then " +
        "enter it here."));
      var engage = el("button", "c-btn engage", "▶ Engage — Request Code");
      engage.id = "c-engage";
      engage.onclick = engageFn;
      lock.appendChild(engage);
      var box = el("div", "c-codebox");
      box.id = "c-codebox";
      var input = el("input", "c-code");
      input.id = "c-code";
      input.placeholder = "XXXX-XXXX-XXXX";
      input.maxLength = 14;
      input.autocomplete = "one-time-code";
      var unlockBtn = el("button", "c-btn engage", "Unlock");
      unlockBtn.id = "c-unlock";
      unlockBtn.onclick = unlockFn;
      box.appendChild(input);
      box.appendChild(unlockBtn);
      lock.appendChild(box);
      var status = el("div", "c-status");
      status.id = "c-status";
      lock.appendChild(status);
      body.appendChild(lock);
    } else {
      msgsEl = el("div", "c-msgs");
      msgsEl.id = "c-msgs";
      body.appendChild(msgsEl);
      var typing = el("div", "c-typing");
      typing.id = "c-typing";
      body.appendChild(typing);
      var row = el("div", "c-inputrow");
      var input = el("input", "c-input");
      input.id = "c-input";
      input.placeholder = "Message Spock…";
      input.maxLength = 4000;
      var send = el("button", "c-send", "Send");
      send.id = "c-send";
      send.onclick = function () { sendMsg(input.value); };
      input.addEventListener("keydown", function (ev) {
        if (ev.key === "Enter" && !ev.shiftKey) { ev.preventDefault(); sendMsg(input.value); }
      });
      var lockBtn = el("button", "c-lockbtn", "Lock");
      lockBtn.onclick = lockFn;
      row.appendChild(input);
      row.appendChild(send);
      row.appendChild(lockBtn);
      body.appendChild(row);
    }
    ROOT.appendChild(body);
    ROOT.appendChild(el("div", "c-foot", "OTP via Discord DM · session cookie · tailnet only"));

    if (unlocked && msgsEl) {
      addMsg("spock", "Channel open. What do you need, Captain?");
      if (document.getElementById("c-input")) document.getElementById("c-input").focus();
    }
  }

  /* ---------------- otp flow ---------------- */
  function engageFn() {
    var btn = document.getElementById("c-engage");
    if (btn) btn.disabled = true;
    setStatus("requesting code…");
    fetch("/api/otp/request", { method: "POST" })
      .then(function (r) { return r.json(); })
      .then(function (j) {
        if (j.ok) {
          setStatus("CODE TRANSMITTED — check your Discord DM", "ok");
          var box = document.getElementById("c-codebox");
          if (box) box.classList.add("show");
          var inp = document.getElementById("c-code");
          if (inp) inp.focus();
          if (btn) btn.style.display = "none";
        } else {
          setStatus(errText(j), "err");
          if (btn) btn.disabled = false;
        }
      })
      .catch(function () { setStatus("request failed", "err"); if (btn) btn.disabled = false; });
  }

  function unlockFn() {
    var inp = document.getElementById("c-code");
    var code = inp ? inp.value.trim() : "";
    if (!code) return;
    setStatus("verifying…");
    fetch("/api/otp/verify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code: code })
    })
      .then(function (r) { return r.json(); })
      .then(function (j) {
        if (j.ok) {
          unlocked = true;
          render();
        } else {
          setStatus(errText(j), "err");
          if (inp) { inp.value = ""; inp.focus(); }
        }
      })
      .catch(function () { setStatus("verify failed", "err"); });
  }

  function lockFn() {
    fetch("/api/comms/lock", { method: "POST" })
      .then(function () { unlocked = false; render(); })
      .catch(function () { unlocked = false; render(); });
  }

  /* ---------------- chat ---------------- */
  function addMsg(who, text) {
    if (!msgsEl) return;
    var m = el("div", "c-msg " + who);
    m.appendChild(el("span", "c-who", who === "user" ? "You" : "Spock"));
    m.appendChild(document.createTextNode(text));
    msgsEl.appendChild(m);
    scrollDown();
  }
  function setTyping(on) {
    var t = document.getElementById("c-typing");
    if (t) t.textContent = on ? "SPOCK IS TRANSMITTING…" : "";
  }
  function sendMsg(text) {
    var input = document.getElementById("c-input");
    text = (text || "").trim();
    if (!text || busy) return;
    addMsg("user", text);
    if (input) input.value = "";
    busy = true;
    if (input) input.disabled = true;
    var send = document.getElementById("c-send");
    if (send) send.disabled = true;
    setTyping(true);
    fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text })
    })
      .then(function (r) {
        if (!r.ok) return r.json().then(function (j) { throw new Error(errText(j)); });
        var reader = r.body.getReader();
        var dec = new TextDecoder();
        var buf = "", full = "";
        function pump() {
          return reader.read().then(function (res) {
            if (res.done) return;
            buf += dec.decode(res.value, { stream: true });
            var idx;
            while ((idx = buf.indexOf("\n\n")) >= 0) {
              var evt = buf.slice(0, idx);
              buf = buf.slice(idx + 2);
              evt.split("\n").forEach(function (line) {
                if (line.indexOf("data:") !== 0) return;
                var data = line.slice(5).trim();
                if (data === "[DONE]") return;
                try {
                  var j = JSON.parse(data);
                  var delta = j.choices && j.choices[0] && j.choices[0].delta &&
                              j.choices[0].delta.content;
                  if (delta) full += delta;
                } catch (e) { /* partial json chunk */ }
              });
            }
            return pump();
          });
        }
        return pump().then(function () { return full; });
      })
      .then(function (full) {
        setTyping(false);
        addMsg("spock", full && full.trim() ? full : "…");
      })
      .catch(function (e) {
        setTyping(false);
        addMsg("spock", "⚠ " + (e.message || "comms failure"));
      })
      .then(function () {
        busy = false;
        if (input) input.disabled = false;
        if (send) send.disabled = false;
        if (input) input.focus();
      });
  }

  /* ---------------- init ---------------- */
  function init() {
    fetch("/api/comms/status", { cache: "no-store" })
      .then(function (r) { return r.json(); })
      .then(function (j) { unlocked = !!(j && j.unlocked); render(); })
      .catch(function () { unlocked = false; render(); });
  }

  if (ROOT.classList.contains("standalone")) {
    ROOT.classList.add("open");
    init();
  } else {
    window.__commsInit = init;
    window.__commsToggle = function () {
      if (ROOT.classList.contains("open")) {
        ROOT.classList.remove("open");
      } else {
        ROOT.classList.add("open");
        if (!ROOT.dataset.loaded) { ROOT.dataset.loaded = "1"; init(); }
      }
    };
  }
})();

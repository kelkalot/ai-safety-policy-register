// Admin page for pilot access. The server enforces every rule; this file only
// validates input early and shows the server's answer.
(function () {
  var API = "/admin/api/users";
  var EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
  var MAX_EMAIL = 254;

  var panel = document.getElementById("panel");
  var denied = document.getElementById("denied");
  var deniedText = document.getElementById("deniedText");
  var form = document.getElementById("addForm");
  var input = document.getElementById("email");
  var emailError = document.getElementById("emailError");
  var rows = document.getElementById("rows");
  var message = document.getElementById("message");
  var state = { you: null, allowed: [], admins: [] };

  function say(text, kind) {
    message.textContent = text;
    message.className = kind || "";
  }

  // Returns a clean address, or sets the field error and returns null.
  function validEmail(raw) {
    var value = String(raw || "").trim().toLowerCase();
    var problem = "";
    if (!value) problem = "Enter an email address.";
    else if (value.length > MAX_EMAIL) problem = "Email address is too long.";
    else if (!EMAIL_RE.test(value)) problem = "Enter a valid email address, for example name@example.org.";
    input.setAttribute("aria-invalid", problem ? "true" : "false");
    emailError.textContent = problem;
    return problem ? null : value;
  }

  function call(body) {
    return fetch(API, {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    }).then(function (resp) {
      return resp.json().catch(function () { return {}; }).then(function (data) {
        return { ok: resp.ok, status: resp.status, data: data };
      });
    });
  }

  function apply(data) {
    state.you = data.you;
    state.allowed = data.allowed || [];
    state.admins = data.admins || [];
    state.gate = data.gate_enabled !== false;
    renderGate();
    render();
  }

  var gateState = document.getElementById("gateState");
  var gateBtn = document.getElementById("gateBtn");
  var gateNote = document.getElementById("gateNote");

  function renderGate() {
    // Pilot logout means nothing while the gate is off.
    document.getElementById("tab-logout").hidden = !state.gate;
    gateState.textContent = state.gate ? "On" : "Off (register open to anyone)";
    gateState.className = state.gate ? "on" : "off";
    gateBtn.textContent = state.gate ? "Disable pilot gate" : "Enable pilot gate";
    gateBtn.className = state.gate ? "btn" : "btn primary";
    gateBtn.disabled = false;
    gateNote.textContent = state.gate
      ? "Only approved users can view the register."
      : "Anyone can view the register without signing in. Admins can still sign in and turn the gate back on here.";
  }

  gateBtn.addEventListener("click", function () {
    var turnOff = state.gate;
    if (turnOff && !window.confirm("Turn the pilot gate off? Anyone will be able to view the register.")) return;
    gateBtn.disabled = true;
    say("Saving...");
    call({ action: turnOff ? "gate_off" : "gate_on" }).then(function (res) {
      if (res.ok) {
        apply(res.data);
        say(turnOff ? "Pilot gate is off." : "Pilot gate is on.", "ok");
      } else {
        gateBtn.disabled = false;
        say(res.data.error || "Could not change the gate.", "err");
      }
    }).catch(function () {
      gateBtn.disabled = false;
      say("Could not reach the server. Please try again.", "err");
    });
  });

  function render() {
    var seen = {};
    var everyone = state.allowed.concat(state.admins).filter(function (e) {
      if (seen[e]) return false;
      seen[e] = true;
      return true;
    }).sort();
    rows.textContent = "";
    everyone.forEach(function (email) {
      var isAdmin = state.admins.indexOf(email) !== -1;
      var tr = document.createElement("tr");

      var tdEmail = document.createElement("td");
      tdEmail.textContent = email + (email === state.you ? " (you)" : "");
      tr.appendChild(tdEmail);

      var tdRole = document.createElement("td");
      var badge = document.createElement("span");
      badge.className = "badge" + (isAdmin ? " admin" : "");
      badge.textContent = isAdmin ? "Admin" : "User";
      tdRole.appendChild(badge);
      tr.appendChild(tdRole);

      var tdActions = document.createElement("td");
      tdActions.className = "actions";
      tdActions.appendChild(rowButton(isAdmin ? "Remove admin" : "Make admin", isAdmin ? "revoke" : "grant", email, false));
      tdActions.appendChild(rowButton("Remove access", "remove", email, true));
      tr.appendChild(tdActions);

      rows.appendChild(tr);
    });
  }

  function rowButton(label, action, email, danger) {
    var b = document.createElement("button");
    b.type = "button";
    b.textContent = label;
    b.className = "row-btn" + (danger ? " danger" : "");
    b.addEventListener("click", function () {
      if (action === "remove" && !window.confirm("Remove access for " + email + "?")) return;
      run(action, email, b);
    });
    return b;
  }

  function run(action, email, button) {
    if (button) button.disabled = true;
    say("Saving...");
    call({ action: action, email: email }).then(function (res) {
      if (button) button.disabled = false;
      if (res.ok) {
        apply(res.data);
        say("Saved.", "ok");
      } else {
        say(res.data.error || "Could not save. Please try again.", "err");
      }
    }).catch(function () {
      if (button) button.disabled = false;
      say("Could not reach the server. Please try again.", "err");
    });
  }

  document.getElementById("tab-logout").addEventListener("click", function () {
    location.href = "/_auth/logout";
  });

  form.addEventListener("submit", function (ev) { ev.preventDefault(); });
  form.addEventListener("click", function (ev) {
    var btn = ev.target.closest("button[data-action]");
    if (!btn) return;
    var email = validEmail(input.value);
    if (!email) { input.focus(); return; }
    run(btn.getAttribute("data-action"), email, btn);
    input.value = "";
    input.setAttribute("aria-invalid", "false");
  });
  input.addEventListener("input", function () { if (emailError.textContent) validEmail(input.value); });

  fetch(API, { credentials: "same-origin" }).then(function (resp) {
    if (resp.status === 401) { location.replace("/sign-in/"); return null; }
    return resp.json().then(function (data) { return { ok: resp.ok, status: resp.status, data: data }; });
  }).then(function (res) {
    if (!res) return;
    if (res.ok) {
      apply(res.data);
      panel.hidden = false;
    } else {
      denied.hidden = false;
      deniedText.textContent = res.status === 403
        ? "You are signed in, but this account is not an admin."
        : "Could not load the access list. Please try again.";
    }
  }).catch(function () {
    denied.hidden = false;
    deniedText.textContent = "Could not reach the server. Please try again.";
  });
})();

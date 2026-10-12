// Sign-in for the register. Loads Clerk's SDK from the same Clerk instance as
// naiid, then trades a verified Clerk session token for the register's cookie.
(function () {
  var body = document.body;
  var root = document.getElementById("clerk-root");
  var status = document.getElementById("status");
  var publishableKey = body.getAttribute("data-publishable-key");
  var domain = body.getAttribute("data-clerk-domain");
  var base = "https://" + domain;
  var busy = false;
  var actions = document.getElementById("account-actions");
  var signOutButton = document.getElementById("signout");

  function setStatus(msg) { status.textContent = msg; }
  function fail() { setStatus("Could not load the sign-in service."); }

  // Clerk keeps one signed-in account per browser. Signing out clears it,
  // so the next page load shows the sign-in form for a different account.
  signOutButton.addEventListener("click", function () {
    signOutButton.disabled = true;
    window.Clerk.signOut()
      .then(function () { location.replace("/sign-in/"); })
      .catch(function () { signOutButton.disabled = false; setStatus("Could not sign out. Please try again."); });
  });

  // Same pinned versions as naiid's sign-in page. The UI bundle must load first.
  function loadScript(src, attrs, onload) {
    var s = document.createElement("script");
    s.src = src;
    s.async = true;
    s.crossOrigin = "anonymous";
    Object.keys(attrs).forEach(function (k) { s.setAttribute(k, attrs[k]); });
    s.onerror = fail;
    s.onload = onload;
    document.head.appendChild(s);
  }

  function exchange(session) {
    if (busy) return;
    busy = true;
    setStatus("Checking access...");
    session.getToken()
      .then(function (token) {
        return fetch("/_auth/login", {
          method: "POST",
          credentials: "same-origin",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ token: token })
        });
      })
      .then(function (resp) {
        if (resp.ok) { location.replace("/"); return; }
        busy = false;
        if (resp.status === 403) {
          setStatus("This account does not have access. To request access, email Michael at michael@simula.no.");
          actions.hidden = false;
        } else {
          setStatus("Sign-in could not be verified. Please try again.");
        }
      })
      .catch(function () { busy = false; fail(); });
  }

  // Arrived from the pilot logout link: sign out of Clerk too, so the page
  // shows the sign-in form instead of signing the visitor straight back in.
  var params = new URLSearchParams(location.search);
  var signedOut = params.get("signed_out") === "1";
  if (signedOut) history.replaceState(null, "", "/sign-in/");

  function start() {
    window.Clerk.load({ ui: { ClerkUI: window.__internal_ClerkUICtor } })
      .then(function () {
        if (signedOut && window.Clerk.session) return window.Clerk.signOut().then(function () { return true; });
        return false;
      })
      .then(function () {
        if (window.Clerk.session) { exchange(window.Clerk.session); return; }
        // Invite-only: hide Clerk's "Sign up" link. Access is granted by email to Michael.
        window.Clerk.mountSignIn(root, {
          appearance: { elements: { footerAction: { display: "none" } } }
        });
        window.Clerk.addListener(function () {
          if (window.Clerk.session) exchange(window.Clerk.session);
        });
      })
      .catch(fail);
  }

  loadScript(base + "/npm/@clerk/ui@1.33.0/dist/ui.browser.js", {}, function () {
    loadScript(base + "/npm/@clerk/clerk-js@6.32.0/dist/clerk.browser.js",
      { "data-clerk-publishable-key": publishableKey }, start);
  });
})();

// Pilot tabs: Admin (admins only) and Pilot logout. Only the gate serves these
// routes, so offline (file://) the Admin tab stays hidden and Pilot logout does nothing useful.
(function () {
  var adminTab = document.getElementById("tab-admin");
  var logoutTab = document.getElementById("tab-logout");
  if (!adminTab || !logoutTab) return;

  adminTab.addEventListener("click", function () { location.href = "/admin/"; });
  logoutTab.addEventListener("click", function () { location.href = "/_auth/logout"; });

  // The admin API answers 200 only for admins; everyone else gets 401 or 403 and sees no tab.
  fetch("/admin/api/users", { credentials: "same-origin", cache: "no-store" })
    .then(function (resp) { if (resp.ok) adminTab.hidden = false; })
    .catch(function () { /* not admin, or not served through the gate */ });

  // Pilot logout is hidden by default and shown only while the gate is on,
  // because it means nothing when the gate is off.
  fetch("/_auth/gate", { credentials: "same-origin", cache: "no-store" })
    .then(function (resp) { return resp.ok ? resp.json() : null; })
    .then(function (data) { if (data && data.enabled === true) logoutTab.hidden = false; })
    .catch(function () { /* offline: stays hidden */ });
})();

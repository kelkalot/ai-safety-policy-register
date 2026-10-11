(function () {
  "use strict";
  var DB = window.REGISTER;
  if (!DB || !DB.records) {
    document.body.insertAdjacentHTML("afterbegin", '<p style="padding:16px;color:#b0222a">The data file <code>data/records.js</code> could not be loaded. Run <code>python3 tools/build.py</code> and reload.</p>');
    return;
  }
  var R = DB.records;
  var META = DB.meta;
  var byId = {}, bySlug = {};
  R.forEach(function (r, i) {
    byId[r.id] = r; bySlug[r.slug] = r;
    if (!r.local_copy) r.local_copy = { status: "not-attempted", files: [] };
    r._hay = fold([r.id, r.title, r.short_title, r.original_title, r.jurisdiction, r.country, r.issuing_body, r.official_identifier, r.summary, r.notes, r.instrument_type, (r.safety_topics || []).join(" "), r.local_copy.flag, r.local_copy.integrity_flag].join(" | "));
    r._year = r.date_published ? r.date_published.slice(0, 4) : "";
  });

  /* Related links are shown in both directions: if A lists B, B's drawer also shows A. */
  var reverseRel = {};
  R.forEach(function (r) { (r.related || []).forEach(function (x) { if (x.id && byId[x.id] && x.id !== r.id) (reverseRel[x.id] = reverseRel[x.id] || []).push(r.id); }); });

  /* Lower-case and strip accents, so "declaration" finds "Déclaration" and "Kunstliche" finds "Künstliche". */
  function fold(s) {
    s = String(s == null ? "" : s).toLowerCase();
    try { s = s.normalize("NFD").replace(/[\u0300-\u036f]/g, ""); } catch (e) {}
    return s;
  }

  var $ = function (s) { return document.querySelector(s); };
  var esc = function (s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); };

  var STATUS_ORDER = ["In force", "Partially in force", "Adopted, not yet in force", "Published (non-binding, current)", "Draft / proposed", "Superseded", "Revoked / withdrawn", "Lapsed"];
  var STATUS_CLASS = { "In force": "s-inforce", "Partially in force": "s-partial", "Adopted, not yet in force": "s-adopted", "Published (non-binding, current)": "s-published", "Draft / proposed": "s-draft", "Superseded": "s-gone", "Revoked / withdrawn": "s-gone", "Lapsed": "s-gone" };
  var STATUS_SHORT = { "Published (non-binding, current)": "Published, current", "Adopted, not yet in force": "Adopted, not in force" };
  var VLABEL = { A: "A · official source fetched", B: "B · alternative official source", C: "C · not confirmed on an official page" };
  var LC_ORDER = ["archived", "archived-review", "partial", "failed", "no-url", "not-attempted"];
  var SORT_KEYS = ["date_desc", "date_asc", "updated", "jur", "title", "id"];
  var LC_LABEL = { "archived": "Archived", "archived-review": "Archived, needs review", "partial": "Partial (secondary only)", "failed": "Download failed", "no-url": "No URL to archive", "not-attempted": "Not archived yet" };
  var LC_SHORT = { "archived": "Local copy", "archived-review": "Copy: review", "partial": "Partial copy", "failed": "Copy failed", "no-url": "No URL", "not-attempted": "Not archived" };
  var LC_CLASS = { "archived": "lc-archived", "archived-review": "lc-review", "partial": "lc-partial", "failed": "lc-failed", "no-url": "lc-nourl", "not-attempted": "lc-none" };
  var LC_HELP = {
    "archived": "The official source was downloaded and stored locally with a SHA-256 hash and timestamp.",
    "archived-review": "A copy is stored, but something needs a human look: a bot-check or JavaScript-only page, a page that no longer mentions the document, a source that has since disappeared, or a local file that changed.",
    "partial": "The official source could not be downloaded; only the secondary source is stored.",
    "failed": "Nothing could be downloaded. The flag gives the reason (HTTP error, timeout, robots.txt, TLS error).",
    "no-url": "The record has no URL, so there is nothing to archive.",
    "not-attempted": "The archiver has not been run for this record yet."
  };
  var ICON = {
    ok: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7.5"></path></svg>',
    warn: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 4l9 16H3z"></path><path d="M12 10v4M12 17v.5"></path></svg>',
    bad: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6 6 18"></path></svg>',
    info: '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="8.5"></circle><path d="M12 11v5M12 8v.5"></path></svg>'
  };
  var LC_ICON = { "archived": "ok", "archived-review": "warn", "partial": "warn", "failed": "bad", "no-url": "bad", "not-attempted": "info" };
  var LC_FLAGCLASS = { ok: "flag-ok", warn: "flag-warn", bad: "flag-bad", info: "flag-info" };
  var REGION_ORDER = ["Global", "Europe", "North America", "Latin America & Caribbean", "East Asia", "South & Southeast Asia", "Central Asia", "Oceania", "Middle East & North Africa", "Sub-Saharan Africa"];

  var FACETS = [
    { key: "region", label: "Region", get: function (r) { return [r.region]; }, order: REGION_ORDER, open: true },
    { key: "level", label: "Level", get: function (r) { return [r.jurisdiction_level]; }, order: ["International", "Supranational", "National", "Sub-national"] },
    { key: "force", label: "Legal force", get: function (r) { return [r.legal_force]; }, order: ["Binding", "Non-binding", "Proposed"], open: true },
    { key: "status", label: "Status", get: function (r) { return [r.status]; }, order: STATUS_ORDER, open: true },
    { key: "type", label: "Instrument type", get: function (r) { return [r.instrument_type]; } },
    { key: "topic", label: "Safety topic", get: function (r) { return r.safety_topics || []; } },
    { key: "vlevel", label: "Verification", get: function (r) { return [r.verification.level]; }, order: ["A", "B", "C"], fmt: function (v) { return VLABEL[v]; } },
    { key: "local", label: "Local copy", get: function (r) { return [r.local_copy.status]; }, order: LC_ORDER, fmt: function (v) { return LC_LABEL[v] || v; }, open: true }
  ];
  FACETS.forEach(function (f) {
    var vals = {};
    R.forEach(function (r) { f.get(r).forEach(function (v) { vals[v] = (vals[v] || 0) + 1; }); });
    var keys = Object.keys(vals);
    if (f.order) keys.sort(function (a, b) { var ia = f.order.indexOf(a), ib = f.order.indexOf(b); return (ia < 0 ? 99 : ia) - (ib < 0 ? 99 : ib); });
    else keys.sort(function (a, b) { return vals[b] - vals[a] || a.localeCompare(b); });
    f.values = keys;
  });

  var state = { q: "", sel: {}, country: "", yearFrom: "", yearTo: "", sort: "date_desc" };
  FACETS.forEach(function (f) { state.sel[f.key] = new Set(); });

  try { var saved = JSON.parse(localStorage.getItem("aispr-sort") || "null"); if (saved) state.sort = saved; } catch (e) {}

  /* ---------- static masthead bits ---------- */
  var checked = R.map(function (r) { return r.verification.verified_on; }).sort();
  $("#snapDate").textContent = META.snapshot_date;
  $("#snapVer").textContent = META.version;
  $("#snapCount").textContent = R.length;
  $("#snapChecked").textContent = checked[0] === checked[checked.length - 1] ? checked[0] : checked[0] + " – " + checked[checked.length - 1];
  var cnt = function (fn) { return R.filter(fn).length; };
  function fmtBytes(n) { if (!n) return "0 KB"; if (n < 1048576) return (n / 1024).toFixed(1) + " KB"; if (n < 1073741824) return (n / 1048576).toFixed(1) + " MB"; return (n / 1073741824).toFixed(2) + " GB"; }
  var lastRun = R.map(function (r) { return r.local_copy.last_attempt || ""; }).sort().pop();
  var notAttempted = cnt(function (r) { return r.local_copy.status === "not-attempted"; });
  $("#snapArchive").textContent = lastRun ? "updated " + lastRun.replace("T", " ").replace("Z", " UTC") : "not created yet";
  if (notAttempted) {
    $("#archiveNotice").hidden = false;
    $("#archiveNotice").innerHTML = "<span><strong>" + notAttempted + " of " + R.length + " records have no local copy yet.</strong> Run the archiver on the machine that hosts this register to store every source with a hash and timestamp.</span><code>python3 tools/archive.py</code>";
  }
  $("#lcLegend").innerHTML = LC_ORDER.map(function (k) {
    var ic = LC_ICON[k];
    return '<div class="level"><span class="lc ' + LC_CLASS[k] + '" style="justify-self:start">' + ICON[ic] + "</span><p><strong>" + esc(LC_LABEL[k]) + ".</strong> " + esc(LC_HELP[k]) + "</p></div>";
  }).join("");
  var jurisdictions = new Set(R.map(function (r) { return r.jurisdiction; }));
  var countries = new Set(R.filter(function (r) { return r.jurisdiction_level === "National" || r.jurisdiction_level === "Sub-national"; }).map(function (r) { return r.country; }));
  $("#figures").innerHTML = [
    ["" + cnt(function (r) { return r.legal_force === "Binding"; }), "binding"],
    ["" + cnt(function (r) { return r.legal_force === "Non-binding"; }), "non-binding"],
    ["" + cnt(function (r) { return r.legal_force === "Proposed"; }), "proposed"],
    ["" + countries.size, "countries"],
    ["" + cnt(function (r) { return r.jurisdiction_level === "International" || r.jurisdiction_level === "Supranational"; }), "international & EU instruments"],
    ["" + cnt(function (r) { return r.verification.level === "A"; }) + "/" + R.length, "confirmed on the official page"],
    ["" + cnt(function (r) { return r.local_copy.status === "archived" || r.local_copy.status === "archived-review"; }) + "/" + R.length, "stored locally"],
    ["" + cnt(function (r) { return ["archived-review", "partial", "failed", "no-url"].indexOf(r.local_copy.status) >= 0 || !!r.local_copy.integrity_flag; }), "local-copy flags"]
  ].map(function (x) { return "<li><strong>" + esc(x[0]) + "</strong> " + esc(x[1]) + "</li>"; }).join("");

  $("#snapStats").innerHTML = [
    ["Snapshot", META.snapshot_date], ["Version", META.version], ["Records", R.length], ["Jurisdictions & bodies", jurisdictions.size],
    ["Level A", cnt(function (r) { return r.verification.level === "A"; })], ["Level B", cnt(function (r) { return r.verification.level === "B"; })], ["Level C", cnt(function (r) { return r.verification.level === "C"; })],
    ["Second-checked", cnt(function (r) { return !!r.verification.second_check; })], ["Newest document", R.map(function (r) { return r.date_published || ""; }).sort().pop()],
    ["Last archive run", lastRun || "not run yet"]
  ].concat(LC_ORDER.map(function (k) { return ["Local: " + LC_LABEL[k].toLowerCase(), cnt(function (r) { return r.local_copy.status === k; })]; }))
   .concat([["Local files", R.reduce(function (a, r) { return a + (r.local_copy.files || []).length; }, 0)], ["Local size", fmtBytes(R.reduce(function (a, r) { return a + (r.local_copy.files || []).reduce(function (b, f) { return b + (f.bytes || 0); }, 0); }, 0))]])
   .map(function (x) { return "<dt>" + esc(x[0]) + "</dt><dd>" + esc(x[1]) + "</dd>"; }).join("");

  var weak = R.filter(function (r) { return r.verification.level !== "A"; });
  $("#weakList").innerHTML = weak.map(function (r) {
    return '<li><a href="#' + esc(r.id) + '" data-open="' + esc(r.id) + '">' + esc(r.id) + "</a> " + esc(r.short_title || r.title) + " <span class=\"mono\" style=\"font-size:12px\">(level " + r.verification.level + ")</span></li>";
  }).join("");

  /* ---------- selects ---------- */
  var countryList = Array.from(new Set(R.map(function (r) { return r.jurisdiction_level === "International" ? r.jurisdiction : r.country; }))).sort(function (a, b) { return a.localeCompare(b); });
  $("#country").innerHTML = '<option value="">All</option>' + countryList.map(function (c) { return '<option value="' + esc(c) + '">' + esc(c) + "</option>"; }).join("");
  var years = Array.from(new Set(R.map(function (r) { return r._year; }).filter(Boolean))).sort();
  ["#yearFrom", "#yearTo"].forEach(function (s, i) {
    $(s).innerHTML = '<option value="">' + (i ? "To" : "From") + "</option>" + years.map(function (y) { return '<option value="' + y + '">' + y + "</option>"; }).join("");
  });
  applyQuery();
  $("#sort").value = state.sort;
  $("#country").value = state.country; $("#yearFrom").value = state.yearFrom; $("#yearTo").value = state.yearTo;

  /* ---------- filter state in the URL, so a filtered view can be bookmarked or sent ---------- */
  function stateToQuery() {
    var p = new URLSearchParams();
    if (state.q) p.set("q", state.q);
    if (state.country) p.set("country", state.country);
    if (state.yearFrom) p.set("from", state.yearFrom);
    if (state.yearTo) p.set("to", state.yearTo);
    if (state.sort !== "date_desc") p.set("sort", state.sort);
    FACETS.forEach(function (f) { state.sel[f.key].forEach(function (v) { p.append(f.key, v); }); });
    var q = p.toString();
    return q ? "?" + q : "";
  }
  function syncUrl() {
    try { history.replaceState(null, "", location.pathname + stateToQuery() + (openId ? "#" + openId : (location.hash || ""))); } catch (e) {}
  }
  function applyQuery() {
    var p;
    try { p = new URLSearchParams(location.search); } catch (e) { return; }
    if (p.get("q")) { state.q = p.get("q").trim(); $("#q").value = state.q; }
    if (p.get("country") && countryList.indexOf(p.get("country")) >= 0) state.country = p.get("country");
    if (p.get("from") && years.indexOf(p.get("from")) >= 0) state.yearFrom = p.get("from");
    if (p.get("to") && years.indexOf(p.get("to")) >= 0) state.yearTo = p.get("to");
    if (p.get("sort") && SORT_KEYS.indexOf(p.get("sort")) >= 0) state.sort = p.get("sort");
    FACETS.forEach(function (f) { p.getAll(f.key).forEach(function (v) { if (f.values.indexOf(v) >= 0) state.sel[f.key].add(v); }); });
  }

  /* ---------- filtering ---------- */
  function matches(r, skip) {
    if (state.q) {
      var terms = fold(state.q).split(/\s+/).filter(Boolean);
      for (var i = 0; i < terms.length; i++) if (r._hay.indexOf(terms[i]) < 0) return false;
    }
    if (skip !== "country" && state.country) {
      var c = r.jurisdiction_level === "International" ? r.jurisdiction : r.country;
      if (c !== state.country && r.jurisdiction !== state.country) return false;
    }
    if (skip !== "year") {
      if (state.yearFrom && (!r._year || r._year < state.yearFrom)) return false;
      if (state.yearTo && (!r._year || r._year > state.yearTo)) return false;
    }
    for (var k = 0; k < FACETS.length; k++) {
      var f = FACETS[k];
      if (f.key === skip) continue;
      var s = state.sel[f.key];
      if (s.size) {
        var vals = f.get(r), hit = false;
        for (var j = 0; j < vals.length; j++) if (s.has(vals[j])) { hit = true; break; }
        if (!hit) return false;
      }
    }
    return true;
  }

  function sortRows(rows) {
    var d = function (r) { return r.date_published || ""; };
    var upd = function (r) { return [r.date_last_updated || "", r.date_in_force || "", r.date_published || ""].sort().pop(); };
    var cmp = {
      date_desc: function (a, b) { return (d(b) || "0").localeCompare(d(a) || "0") || a.id.localeCompare(b.id); },
      date_asc: function (a, b) { return (d(a) || "9").localeCompare(d(b) || "9") || a.id.localeCompare(b.id); },
      updated: function (a, b) { return upd(b).localeCompare(upd(a)) || a.id.localeCompare(b.id); },
      jur: function (a, b) { return a.jurisdiction.localeCompare(b.jurisdiction) || (d(b)).localeCompare(d(a)); },
      title: function (a, b) { return (a.short_title || a.title).localeCompare(b.short_title || b.title); },
      id: function (a, b) { return a.id.localeCompare(b.id, undefined, { numeric: true }); }
    }[state.sort];
    return rows.slice().sort(cmp);
  }

  var current = [];

  /* ---------- facets UI ---------- */
  function renderFacets() {
    var html = FACETS.map(function (f) {
      var pool = R.filter(function (r) { return matches(r, f.key); });
      var counts = {};
      pool.forEach(function (r) { f.get(r).forEach(function (v) { counts[v] = (counts[v] || 0) + 1; }); });
      var opts = f.values.map(function (v, i) {
        var n = counts[v] || 0, on = state.sel[f.key].has(v);
        var id = "f-" + f.key + "-" + i;
        return '<label class="opt' + (n === 0 && !on ? " zero" : "") + '" for="' + id + '"><input type="checkbox" id="' + id + '" data-facet="' + f.key + '" value="' + esc(v) + '"' + (on ? " checked" : "") + '><span>' + esc(f.fmt ? f.fmt(v) : v) + '</span><span class="n">' + n + "</span></label>";
      }).join("");
      var openAttr = (f.open || state.sel[f.key].size) ? " open" : "";
      return '<details class="facet" data-key="' + f.key + '"' + openAttr + "><summary>" + esc(f.label) + '</summary><div class="opts">' + opts + "</div></details>";
    }).join("");
    var openNow = {};
    document.querySelectorAll("#facets details").forEach(function (d) { openNow[d.dataset.key] = d.open; });
    $("#facets").innerHTML = html;
    document.querySelectorAll("#facets details").forEach(function (d) { if (d.dataset.key in openNow) d.open = openNow[d.dataset.key] || state.sel[d.dataset.key].size > 0; });
  }

  function renderChips() {
    var chips = [];
    if (state.q) chips.push(['q', '', 'Search: "' + state.q + '"']);
    if (state.country) chips.push(["country", "", state.country]);
    if (state.yearFrom || state.yearTo) chips.push(["year", "", "Years " + (state.yearFrom || "…") + "–" + (state.yearTo || "…")]);
    FACETS.forEach(function (f) { state.sel[f.key].forEach(function (v) { chips.push([f.key, v, f.fmt ? f.fmt(v) : v]); }); });
    $("#chips").innerHTML = chips.map(function (c) { return '<button class="chip" data-k="' + esc(c[0]) + '" data-v="' + esc(c[1]) + '" aria-label="Remove filter ' + esc(c[2]) + '">' + esc(c[2]) + "</button>"; }).join("");
  }

  function statusPill(r) {
    return '<span class="pill ' + (STATUS_CLASS[r.status] || "s-published") + '">' + esc(STATUS_SHORT[r.status] || r.status) + "</span>";
  }
  function lcBadge(r) {
    var lc = r.local_copy, st = lc.status;
    var ic = lc.integrity_flag ? "warn" : LC_ICON[st];
    var cls = lc.integrity_flag && st === "archived" ? "lc-review" : LC_CLASS[st];
    return '<span class="lc ' + cls + '" title="' + esc(LC_LABEL[st] + (lc.flag ? ": " + lc.flag : "")) + '">' + ICON[ic] + esc(LC_SHORT[st]) + "</span>";
  }
  function localSection(r) {
    var lc = r.local_copy, st = lc.status, ic = LC_ICON[st];
    var head = '<div class="flag ' + LC_FLAGCLASS[ic] + '">' + ICON[ic] + "<div><strong>" + esc(LC_LABEL[st]) + ".</strong> " +
      esc(lc.flag || LC_HELP[st]) + (lc.last_attempt ? '<br><span class="mono" style="font-size:12px;color:var(--ink-2)">Last attempt ' + esc(lc.last_attempt.replace("T", " ").replace("Z", " UTC")) + "</span>" : "") + "</div></div>";
    if (lc.integrity_flag) head += '<div class="flag flag-bad">' + ICON.bad + "<div>" + esc(lc.integrity_flag) + "</div></div>";
    var files = (lc.files || []).map(function (f, i) {
      var meta = [f.content_type, fmtBytes(f.bytes), f.http_status ? "HTTP " + f.http_status : "", f.method === "browser" ? "saved by headless browser" : "", f.last_modified ? "server date " + f.last_modified : ""].filter(Boolean);
      return '<div class="file' + (f.stale ? " stale" : "") + '">' +
        '<div class="file-top"><a href="' + esc(f.path) + '" target="_blank" rel="noopener">' + esc(f.label || f.role) + '</a><span class="mono" style="font-size:12px;color:var(--ink-3)">' + esc(f.path) + "</span></div>" +
        '<div class="meta"><span>Retrieved ' + esc((f.retrieved_at || "").replace("T", " ").replace("Z", " UTC")) + "</span>" + (f.last_checked && f.last_checked !== f.retrieved_at ? "<span>unchanged at " + esc(f.last_checked.replace("T", " ").replace("Z", " UTC")) + "</span>" : "") + meta.map(function (m) { return "<span>" + esc(m) + "</span>"; }).join("") + "</div>" +
        '<div class="hash"><span>SHA-256 ' + esc(f.sha256) + '</span><button type="button" data-hash="' + esc(f.sha256) + '">Copy</button></div>' +
        (f.final_url && f.final_url !== f.url ? '<div class="meta"><span>Redirected to ' + esc(f.final_url) + "</span></div>" : "") +
        (f.stale ? '<div class="warn">This source could not be downloaded on ' + esc((f.last_failed || "").slice(0, 10)) + " (" + esc(f.last_error || "") + "). This is the earlier copy.</div>" : "") +
        (f.changed ? '<div class="warn">Changed since the previous snapshot' + (f.previous_path ? ' (earlier version: <a href="' + esc(f.previous_path) + '" target="_blank" rel="noopener">' + esc(f.previous_path) + "</a>)" : "") + ".</div>" : "") +
        (f.warning ? '<div class="warn">' + esc(f.warning) + "</div>" : "") +
        (f.integrity && f.integrity !== "ok" ? '<div class="warn" style="color:var(--bad)">Integrity check: file ' + esc(f.integrity) + ".</div>" : "") +
        "</div>";
    }).join("");
    return '<div class="sec"><h3>Local copy</h3><div class="files">' + head + files + "</div></div>";
  }
  function vBadge(r) {
    var v = r.verification;
    return '<span class="vbadge v-' + v.level + '" title="' + esc(VLABEL[v.level]) + '"><span class="lv">' + v.level + "</span><span>verified</span><span>" + esc(v.verified_on) + "</span></span>";
  }

  function renderRows() {
    current = sortRows(R.filter(function (r) { return matches(r); }));
    var n = current.length;
    $("#count").textContent = (n === R.length ? "All " + n + " records" : n + " of " + R.length + " records");
    if (!n) {
      $("#rows").innerHTML = '<div class="empty">No records match these filters. <button class="linkbtn" data-clear>Clear all filters</button></div>';
      return;
    }
    $("#rows").innerHTML = current.map(function (r) {
      var sub = r.jurisdiction_level === "Sub-national" ? r.country : r.jurisdiction_level;
      return '<button class="row" data-id="' + esc(r.id) + '">' +
        '<span class="id">' + esc(r.id) + "</span>" +
        '<span class="c-title"><span class="t1">' + esc(r.short_title || r.title) + '</span><span class="t2">' + esc(r.short_title && r.short_title !== r.title ? r.title : r.summary) + "</span></span>" +
        '<span class="c-jur"><span class="lbl">Where</span><span><span class="jur">' + esc(r.jurisdiction) + '</span><br><span class="sub">' + esc(sub) + "</span></span></span>" +
        '<span class="col-type type">' + esc(r.instrument_type) + "</span>" +
        '<span class="c-status"><span class="lbl">Status</span>' + statusPill(r) + '<span class="force">' + esc(r.legal_force) + "</span></span>" +
        '<span class="c-date"><span class="lbl">Published</span><span class="date">' + esc(r.date_published || "—") + "</span></span>" +
        '<span class="c-v">' + vBadge(r) + lcBadge(r) + "</span>" +
        "</button>";
    }).join("");
  }

  /* ---------- chart ---------- */
  function renderChart() {
    var pool = R.filter(function (r) { return matches(r, "year"); });
    var ys = years.slice();
    var data = ys.map(function (y) {
      var rows = pool.filter(function (r) { return r._year === y; });
      return { y: y, b: rows.filter(function (r) { return r.legal_force === "Binding"; }).length, n: rows.filter(function (r) { return r.legal_force === "Non-binding"; }).length, p: rows.filter(function (r) { return r.legal_force === "Proposed"; }).length };
    });
    data.forEach(function (d) { d.t = d.b + d.n + d.p; });
    var svg = $("#chart");
    var W = Math.max(340, $("#chartBox").clientWidth || 800), H = 190, padL = 30, padR = 8, padT = 18, padB = 24;
    svg.setAttribute("viewBox", "0 0 " + W + " " + H);
    var max = Math.max(5, Math.max.apply(null, data.map(function (d) { return d.t; })));
    var step = max > 40 ? 20 : max > 20 ? 10 : 5;
    var top = Math.ceil(max / step) * step;
    var plotH = H - padT - padB, plotW = W - padL - padR;
    var bw = plotW / data.length, barW = Math.min(46, bw * 0.66);
    var yS = function (v) { return padT + plotH - (v / top) * plotH; };
    var out = "";
    for (var g = 0; g <= top; g += step) {
      out += '<line class="grid" x1="' + padL + '" x2="' + (W - padR) + '" y1="' + yS(g) + '" y2="' + yS(g) + '"></line>';
      out += '<text x="' + (padL - 6) + '" y="' + (yS(g) + 4) + '" text-anchor="end">' + g + "</text>";
    }
    var selYear = state.yearFrom && state.yearFrom === state.yearTo ? state.yearFrom : "";
    data.forEach(function (d, i) {
      var x = padL + i * bw + (bw - barW) / 2;
      var segs = [["b", "var(--series-1)"], ["n", "var(--series-2)"], ["p", "var(--series-3)"]];
      var acc = 0, inner = "";
      var nonzero = segs.filter(function (s) { return d[s[0]] > 0; });
      nonzero.forEach(function (s, si) {
        var v = d[s[0]];
        var y1 = yS(acc + v), y0 = yS(acc);
        var h = Math.max(0, y0 - y1 - (si < nonzero.length - 1 ? 2 : 0));
        var isTop = si === nonzero.length - 1;
        if (isTop && h > 4) {
          var r = 4;
          inner += '<path d="M' + x + "," + (y1 + h) + " V" + (y1 + r) + " Q" + x + "," + y1 + " " + (x + r) + "," + y1 + " H" + (x + barW - r) + " Q" + (x + barW) + "," + y1 + " " + (x + barW) + "," + (y1 + r) + " V" + (y1 + h) + ' Z" fill="' + s[1] + '"></path>';
        } else {
          inner += '<rect x="' + x + '" y="' + y1 + '" width="' + barW + '" height="' + h + '" fill="' + s[1] + '"></rect>';
        }
        acc += v;
      });
      var dim = selYear && selYear !== d.y ? ' opacity="0.35"' : "";
      out += '<g' + dim + ">" + inner + "</g>";
      if (d.t) out += '<text class="total" x="' + (x + barW / 2) + '" y="' + (yS(d.t) - 5) + '" text-anchor="middle">' + d.t + "</text>";
      out += '<text x="' + (x + barW / 2) + '" y="' + (H - 6) + '" text-anchor="middle">' + d.y + "</text>";
      out += '<rect class="bar-hit" data-year="' + d.y + '" data-i="' + i + '" x="' + (padL + i * bw) + '" y="' + padT + '" width="' + bw + '" height="' + (plotH + padB) + '" tabindex="0" role="button" aria-label="' + d.y + ": " + d.t + ' instruments. Filter to this year."></rect>';
    });
    svg.innerHTML = out;
    svg._data = data; svg._bw = bw; svg._padL = padL; svg._W = W;
  }

  var tip = $("#tip");
  $("#chart").addEventListener("mousemove", function (e) {
    var t = e.target;
    if (!t.classList || !t.classList.contains("bar-hit")) { tip.hidden = true; return; }
    var d = this._data[+t.dataset.i];
    tip.innerHTML = "<b>" + d.y + "</b> · " + d.t + " instruments<br>Binding " + d.b + " · Non-binding " + d.n + " · Proposed " + d.p;
    tip.hidden = false;
    var box = $("#chartBox").getBoundingClientRect();
    var x = e.clientX - box.left + $("#chartBox").scrollLeft, y = e.clientY - box.top;
    var tw = tip.offsetWidth;
    tip.style.left = Math.max(4, Math.min(x + 12, box.width - tw - 4 + $("#chartBox").scrollLeft)) + "px";
    tip.style.top = Math.max(0, y - 52) + "px";
  });
  $("#chart").addEventListener("mouseleave", function () { tip.hidden = true; });
  function pickYear(y) {
    if (state.yearFrom === y && state.yearTo === y) { state.yearFrom = state.yearTo = ""; }
    else { state.yearFrom = state.yearTo = y; }
    $("#yearFrom").value = state.yearFrom; $("#yearTo").value = state.yearTo;
    update();
  }
  $("#chart").addEventListener("click", function (e) { if (e.target.dataset && e.target.dataset.year) pickYear(e.target.dataset.year); });
  $("#chart").addEventListener("keydown", function (e) { if ((e.key === "Enter" || e.key === " ") && e.target.dataset && e.target.dataset.year) { e.preventDefault(); pickYear(e.target.dataset.year); } });

  function update() { renderFacets(); renderChips(); renderRows(); renderChart(); syncUrl(); }

  /* ---------- events ---------- */
  var qTimer;
  $("#q").addEventListener("input", function () { clearTimeout(qTimer); var v = this.value; qTimer = setTimeout(function () { state.q = v.trim(); update(); }, 120); });
  $("#sort").addEventListener("change", function () { state.sort = this.value; try { localStorage.setItem("aispr-sort", JSON.stringify(state.sort)); } catch (e) {} renderRows(); syncUrl(); });
  $("#country").addEventListener("change", function () { state.country = this.value; update(); });
  $("#yearFrom").addEventListener("change", function () { state.yearFrom = this.value; update(); });
  $("#yearTo").addEventListener("change", function () { state.yearTo = this.value; update(); });
  $("#facets").addEventListener("change", function (e) {
    var t = e.target; if (!t.dataset.facet) return;
    var s = state.sel[t.dataset.facet];
    if (t.checked) s.add(t.value); else s.delete(t.value);
    update();
  });
  function clearAll() {
    state.q = ""; state.country = ""; state.yearFrom = ""; state.yearTo = "";
    FACETS.forEach(function (f) { state.sel[f.key].clear(); });
    $("#q").value = ""; $("#country").value = ""; $("#yearFrom").value = ""; $("#yearTo").value = "";
    update();
  }
  $("#clearAll").addEventListener("click", clearAll);
  $("#copyLink").addEventListener("click", function () { copyText(location.href, "Link to this view copied"); });
  document.addEventListener("click", function (e) { if (e.target.closest && e.target.closest("[data-clear]")) clearAll(); });
  $("#chips").addEventListener("click", function (e) {
    var c = e.target.closest(".chip"); if (!c) return;
    var k = c.dataset.k, v = c.dataset.v;
    if (k === "q") { state.q = ""; $("#q").value = ""; }
    else if (k === "country") { state.country = ""; $("#country").value = ""; }
    else if (k === "year") { state.yearFrom = state.yearTo = ""; $("#yearFrom").value = ""; $("#yearTo").value = ""; }
    else state.sel[k].delete(v);
    update();
  });
  $("#toggleFilters").addEventListener("click", function () {
    var f = $("#filters"); var closed = f.classList.toggle("closed");
    this.setAttribute("aria-expanded", String(!closed));
  });
  $("#rows").addEventListener("click", function (e) { var row = e.target.closest(".row"); if (row) openRecord(row.dataset.id); });

  /* tabs */
  function showTab(which) {
    var reg = which === "register";
    $("#tab-register").setAttribute("aria-selected", String(reg));
    $("#tab-about").setAttribute("aria-selected", String(!reg));
    $("#view-register").hidden = !reg; $("#view-about").hidden = reg;
    if (reg) renderChart();
  }
  $("#tab-register").addEventListener("click", function () { showTab("register"); });
  $("#tab-about").addEventListener("click", function () { showTab("about"); });
  $("#weakList").addEventListener("click", function (e) { var a = e.target.closest("[data-open]"); if (a) { e.preventDefault(); openRecord(a.dataset.open); } });

  /* ---------- drawer ---------- */
  var openId = null, lastFocus = null;
  function fact(label, val, wide, mono) {
    if (val == null || val === "") val = "—";
    return '<div class="' + (wide ? "wide" : "") + '"><dt>' + esc(label) + '</dt><dd' + (mono ? ' class="mono"' : "") + ">" + esc(val) + "</dd></div>";
  }
  function localCite(r) {
    var f = (r.local_copy.files || []).filter(function (x) { return !x.stale; })[0];
    return f ? "Local copy " + f.path + " retrieved " + f.retrieved_at + ", SHA-256 " + f.sha256 + "." : "";
  }
  function citation(r) {
    return [r.issuing_body + ".", (r.title || "") + (r.official_identifier ? " [" + r.official_identifier + "]" : "") + ".", (r.date_published || "n.d.") + ".", r.official_url ? r.official_url + "." : "", "Status: " + r.status + "; verified " + r.verification.verified_on + " (level " + r.verification.level + ").", localCite(r), "AI Safety Policy Register, snapshot " + META.snapshot_date + ", record " + r.id + "."].filter(Boolean).join(" ");
  }
  function openRecord(id) {
    var r = byId[id]; if (!r) return;
    if (!openId) lastFocus = document.activeElement;
    openId = id;
    $("#dId").textContent = r.id + " · " + r.jurisdiction;
    var v = r.verification;
    var srcs = "";
    if (r.official_url) srcs += '<a class="src" href="' + esc(r.official_url) + '" target="_blank" rel="noopener"><span class="k">Official</span><span>Open the official source</span><span class="u">' + esc(r.official_url) + "</span></a>";
    if (r.secondary_url) srcs += '<a class="src" href="' + esc(r.secondary_url) + '" target="_blank" rel="noopener"><span class="k">Second</span><span>Secondary source</span><span class="u">' + esc(r.secondary_url) + "</span></a>";
    if (!srcs) srcs = '<p style="color:var(--bad)">No official URL could be confirmed for this record.</p>';
    var relIds = [], seenRel = {};
    (r.related || []).forEach(function (x) { if (x.id && byId[x.id] && !seenRel[x.id]) { seenRel[x.id] = 1; relIds.push(x.id); } });
    (reverseRel[r.id] || []).forEach(function (id) { if (!seenRel[id]) { seenRel[id] = 1; relIds.push(id); } });
    var rel = relIds.map(function (id) {
      var o = byId[id];
      return '<button class="relbtn" data-rel="' + esc(o.id) + '"><span class="mono">' + esc(o.id) + "</span><span>" + esc(o.short_title || o.title) + " <span style=\"color:var(--ink-3)\">· " + esc(o.status) + "</span></span></button>";
    }).join("");
    $("#dBody").innerHTML =
      '<div><div class="d-kicker">' + statusPill(r) + "<span>" + esc(r.legal_force) + "</span><span>·</span><span>" + esc(r.instrument_type) + "</span></div>" +
      '<h2 id="dTitle">' + esc(r.title) + "</h2>" +
      (r.original_title ? '<p class="orig">' + esc(r.original_title) + "</p>" : "") + "</div>" +
      '<dl class="facts">' +
      fact("Issued by", r.issuing_body, true) +
      fact("Jurisdiction", r.jurisdiction) + fact("Level · region", r.jurisdiction_level + " · " + r.region) +
      fact("Published / adopted", r.date_published, false, true) + fact("In force", r.date_in_force, false, true) +
      fact("Last updated", r.date_last_updated, false, true) + fact("Language", r.language) +
      fact("Official identifier", r.official_identifier, true, true) +
      "</dl>" +
      '<div class="sec"><h3>Summary</h3><p>' + esc(r.summary) + "</p></div>" +
      ((r.safety_topics || []).length ? '<div class="sec"><h3>Safety topics</h3><div class="tags">' + r.safety_topics.map(function (t) { return '<span class="tag">' + esc(t) + "</span>"; }).join("") + "</div></div>" : "") +
      (r.notes ? '<div class="sec"><h3>Status notes</h3><p>' + esc(r.notes) + "</p></div>" : "") +
      '<div class="sec"><h3>Sources</h3><div class="sources">' + srcs + "</div></div>" +
      localSection(r) +
      '<div class="sec"><h3>Verification</h3><div class="verify v-' + v.level + '"><span class="big">' + v.level + '</span><span class="vt">' + esc(VLABEL[v.level].replace(/^[ABC] · /, "")) + '</span><span class="vm">checked ' + esc(v.verified_on) + " · " + esc(v.method || "") + '</span><span class="vn">' + esc(v.note || "") + "</span>" +
      (v.second_check ? '<span class="v2"><strong>Second check, ' + esc(META.snapshot_date) + ":</strong> " + esc(v.second_check) + "</span>" : "") + "</div></div>" +
      (rel ? '<div class="sec"><h3>Related records</h3><div class="related">' + rel + "</div></div>" : "") +
      '<div class="sec cite"><h3>Citation</h3><textarea id="citeText" readonly aria-label="Citation text">' + esc(citation(r)) + '</textarea><div class="row-actions"><button class="btn" id="copyCite">Copy citation</button><button class="btn" id="copyUrl"' + (r.official_url ? "" : " disabled") + ">Copy official URL</button></div></div>";
    $("#drawer").hidden = false; $("#scrim").hidden = false;
    $("#dBody").scrollTop = 0;
    var idx = current.findIndex(function (x) { return x.id === id; });
    $("#dPrev").disabled = idx <= 0; $("#dNext").disabled = idx < 0 || idx >= current.length - 1;
    try { history.replaceState(null, "", "#" + id); } catch (e) {}
    $("#dClose").focus();
  }
  function closeRecord() {
    $("#drawer").hidden = true; $("#scrim").hidden = true; openId = null;
    try { history.replaceState(null, "", location.pathname + location.search); } catch (e) {}
    if (lastFocus && lastFocus.focus) lastFocus.focus();
  }
  function step(dir) {
    var idx = current.findIndex(function (x) { return x.id === openId; });
    var n = current[idx + dir]; if (n) openRecord(n.id);
  }
  $("#dClose").addEventListener("click", closeRecord);
  $("#scrim").addEventListener("click", closeRecord);
  $("#dPrev").addEventListener("click", function () { step(-1); });
  $("#dNext").addEventListener("click", function () { step(1); });
  document.addEventListener("keydown", function (e) {
    if ($("#drawer").hidden) return;
    if (e.key === "Escape") closeRecord();
    else if (e.key === "ArrowRight" && e.target.tagName !== "TEXTAREA") step(1);
    else if (e.key === "ArrowLeft" && e.target.tagName !== "TEXTAREA") step(-1);
  });
  $("#dBody").addEventListener("click", function (e) {
    var rb = e.target.closest("[data-rel]"); if (rb) { openRecord(rb.dataset.rel); return; }
    var hb = e.target.closest("[data-hash]"); if (hb) { copyText(hb.dataset.hash, "SHA-256 copied"); return; }
    if (e.target.id === "copyCite") copyText($("#citeText").value, "Citation copied", $("#citeText"));
    if (e.target.id === "copyUrl" && openId) copyText(byId[openId].official_url, "Official URL copied");
  });

  /* ---------- clipboard, toast, export ---------- */
  var toastTimer;
  function toast(msg) { var t = $("#toast"); t.textContent = msg; t.hidden = false; clearTimeout(toastTimer); toastTimer = setTimeout(function () { t.hidden = true; }, 3200); }
  function copyText(text, okMsg, selectEl) {
    try {
      navigator.clipboard.writeText(text).then(function () { toast(okMsg); }, function () { fallback(); });
    } catch (e) { fallback(); }
    function fallback() { if (selectEl) { selectEl.focus(); selectEl.select(); toast("Text selected. Press Ctrl+C or ⌘C to copy."); } else toast("Copy is blocked here. Select the text and copy it manually."); }
  }

  var COLS = ["id", "title", "original_title", "short_title", "jurisdiction", "country", "jurisdiction_level", "region", "issuing_body", "instrument_type", "legal_force", "status", "date_published", "date_in_force", "date_last_updated", "official_identifier", "official_url", "secondary_url", "language", "summary", "safety_topics", "related_ids", "notes", "verification_level", "verified_on", "verification_method", "verification_note", "second_check", "local_status", "local_flag", "local_last_attempt", "local_files", "local_sha256"];
  function flat(r) {
    var v = r.verification;
    return { id: r.id, title: r.title, original_title: r.original_title, short_title: r.short_title, jurisdiction: r.jurisdiction, country: r.country, jurisdiction_level: r.jurisdiction_level, region: r.region, issuing_body: r.issuing_body, instrument_type: r.instrument_type, legal_force: r.legal_force, status: r.status, date_published: r.date_published, date_in_force: r.date_in_force, date_last_updated: r.date_last_updated, official_identifier: r.official_identifier, official_url: r.official_url, secondary_url: r.secondary_url, language: r.language, summary: r.summary, safety_topics: (r.safety_topics || []).join("; "), related_ids: (r.related || []).map(function (x) { return x.id; }).filter(Boolean).join("; "), notes: r.notes, verification_level: v.level, verified_on: v.verified_on, verification_method: v.method, verification_note: v.note, second_check: v.second_check, local_status: r.local_copy.status, local_flag: [r.local_copy.flag, r.local_copy.integrity_flag].filter(Boolean).join(" "), local_last_attempt: r.local_copy.last_attempt, local_files: (r.local_copy.files || []).map(function (f) { return f.path; }).join("; "), local_sha256: (r.local_copy.files || []).map(function (f) { return f.sha256; }).join("; ") };
  }
  function toCSV(rows) {
    var q = function (x) { x = x == null ? "" : String(x); return /[",\n\r]/.test(x) ? '"' + x.replace(/"/g, '""') + '"' : x; };
    return "﻿" + COLS.join(",") + "\r\n" + rows.map(function (r) { var f = flat(r); return COLS.map(function (c) { return q(f[c]); }).join(","); }).join("\r\n") + "\r\n";
  }
  function toJSON(rows) {
    return JSON.stringify({ meta: Object.assign({}, META, { exported_records: rows.length, filters: describeFilters() }), records: rows.map(function (r) { var o = Object.assign({}, r); delete o._hay; delete o._year; return o; }) }, null, 2);
  }
  function describeFilters() {
    var d = {};
    if (state.q) d.search = state.q; if (state.country) d.country = state.country;
    if (state.yearFrom) d.year_from = state.yearFrom; if (state.yearTo) d.year_to = state.yearTo;
    FACETS.forEach(function (f) { if (state.sel[f.key].size) d[f.key] = Array.from(state.sel[f.key]); });
    return d;
  }
  function exportAs(kind) {
    var rows = current.length ? current : [];
    if (!rows.length) { toast("No records to export. Clear some filters first."); return; }
    var data = kind === "csv" ? toCSV(rows) : toJSON(rows);
    var name = "ai-safety-policy-register_" + META.snapshot_date + (rows.length < R.length ? "_filtered-" + rows.length : "") + "." + kind;
    try {
      var blob = new Blob([data], { type: kind === "csv" ? "text/csv;charset=utf-8" : "application/json" });
      var a = document.createElement("a");
      a.href = URL.createObjectURL(blob); a.download = name;
      document.body.appendChild(a); a.click();
      setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
      toast("Exported " + rows.length + " records as " + kind.toUpperCase());
    } catch (e) {
      copyText(data, "Download blocked, so the " + kind.toUpperCase() + " was copied to your clipboard");
    }
  }
  $("#dlCsv").addEventListener("click", function () { exportAs("csv"); });
  $("#dlJson").addEventListener("click", function () { exportAs("json"); });

  var rz; window.addEventListener("resize", function () { clearTimeout(rz); rz = setTimeout(renderChart, 120); });

  update();
  if (window.innerWidth > 900) $("#filters").classList.remove("closed");
  var h = (location.hash || "").slice(1);
  if (h && byId[h]) openRecord(h);
})();

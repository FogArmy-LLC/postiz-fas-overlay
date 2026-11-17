(function () {
  "use strict";

  function buildLockup(compact) {
    var el = document.createElement("div");
    el.className = "fas-brand-lockup";
    el.setAttribute("data-fas-lockup", "1");
    if (compact) {
      el.innerHTML =
        '<span class="fas-dot"></span>' +
        '<span class="fas-wordmark" style="font-size:13px">FOGARMY</span>';
      return el;
    }
    el.innerHTML =
      '<span class="fas-dot"></span>' +
      '<span class="fas-wordmark">FOGARMY</span>' +
      '<span class="fas-sep"></span>' +
      '<span class="fas-sub">POST-IT</span>';
    return el;
  }

  function replaceLogos() {
    var svgs = document.querySelectorAll('svg[viewBox="0 0 101 33"]');
    for (var i = 0; i < svgs.length; i++) {
      var svg = svgs[i];
      var parent = svg.parentElement;
      if (parent && !parent.querySelector("[data-fas-lockup]")) {
        var rect = svg.getBoundingClientRect();
        var compact = rect.width < 88 && rect.width > 0;
        parent.insertBefore(buildLockup(compact), svg);
      }
    }
  }

  function replaceAuthShowcase() {
    if (window.location.pathname.indexOf("/auth") !== 0) return;
    var rootRow = document.querySelector("div.min-h-screen.w-screen");
    if (!rootRow || rootRow.children.length < 2) return;
    var rightCol = rootRow.children[1];
    if (!rightCol || rightCol.getAttribute("data-fas-showcase") === "1") return;
    rightCol.setAttribute("data-fas-showcase", "1");
    rightCol.style.background =
      "radial-gradient(ellipse 85% 75% at 90% 0%, rgba(56, 189, 248, 0.13), transparent 65%), rgba(6, 9, 17, 0.78)";
    rightCol.style.border = "1px solid rgba(255, 255, 255, 0.085)";
    rightCol.style.borderRadius = "14px";
    rightCol.innerHTML =
      '<div class="fas-auth-showcase">' +
        '<div class="fas-auth-kicker"><span class="fas-auth-kicker-dot"></span>FOGARMY · ZTSP SOCIAL STUDIO</div>' +
        '<div class="fas-auth-headline">Multi-Channel Publishing.<br/><span class="fas-grad">Zero Per-Seat Tax.</span></div>' +
        '<div class="fas-auth-sub">Unified social scheduling, omnichannel Day-1 inbox triage, and verified UTM short-link attribution — isolated per client workspace on sovereign FogArmy infrastructure.</div>' +
        '<div class="fas-bento-grid">' +
          '<div class="fas-bento-cell">' +
            '<div class="fas-bento-eyebrow">01 // UNIFIED PUBLISHING</div>' +
            '<div class="fas-bento-title">Instagram, YouTube, LinkedIn, X, Facebook &amp; TikTok</div>' +
            '<div class="fas-bento-desc">Connect channels once via OAuth and orchestrate Reels, Shorts, carousels, and threads from a single calendar.</div>' +
          '</div>' +
          '<div class="fas-bento-cell">' +
            '<div class="fas-bento-eyebrow">02 // ZTOPS SOCIAL COMMAND</div>' +
            '<div class="fas-bento-title">AI Concierge + Instant Human Takeover</div>' +
            '<div class="fas-bento-desc">Paired with inbox.fogarmy.com to route live chat, comments, and DMs straight into operator pipeline.</div>' +
          '</div>' +
          '<div class="fas-bento-cell">' +
            '<div class="fas-bento-eyebrow">03 // HARD TENANT ISOLATION</div>' +
            '<div class="fas-bento-title">Dedicated Client Workspaces &amp; Attribution</div>' +
            '<div class="fas-bento-desc">Every brand runs inside an isolated organization boundary with branded go.fogarmy.com link telemetry.</div>' +
          '</div>' +
        '</div>' +
      '</div>';
  }

  function ensureOssComplianceFooter() {
    if (document.getElementById("fas-oss-compliance")) return;
    if (!document.body) return;
    var bar = document.createElement("div");
    bar.id = "fas-oss-compliance";
    bar.className = "fas-oss-footer";
    bar.innerHTML = '<a href="https://github.com/FogArmy-LLC/postiz-fas-overlay" target="_blank" rel="noopener noreferrer">Source on GitHub</a> · <a href="/_fas/open-source.html" target="_blank" rel="noopener noreferrer">Open Source &amp; AGPL-3.0 Source</a>';
    document.body.appendChild(bar);
  }

  var googleConfigured = null;
  function checkGoogleOauthOnce() {
    if (googleConfigured !== null || window.location.pathname.indexOf("/auth") !== 0) return;
    googleConfigured = false;
    fetch("/api/auth/oauth/GOOGLE")
      .then(function (r) { return r.ok ? r.text() : ""; })
      .then(function (u) {
        if (u && u.indexOf("client_id=") !== -1 && u.indexOf("client_id=&") === -1) {
          googleConfigured = true;
          var hidden = document.querySelectorAll("[data-fas-sso-hidden]");
          for (var i = 0; i < hidden.length; i++) {
            hidden[i].style.display = "";
          }
        }
      })
      .catch(function () {});
  }

  function scrubTextAndLinks() {
    if (document.title.indexOf("Postiz") !== -1) {
      document.title = document.title.replace(/Postiz/gi, "FAS Post-It");
    }
    checkGoogleOauthOnce();

    // Replace public Register link on Login screen (tenants are onboarded via FogArmy)
    var links = document.querySelectorAll('a[href="/auth"], a[href*="/auth/register"], a[href*="discord.gg"]');
    for (var i = 0; i < links.length; i++) {
      var a = links[i];
      if (a.getAttribute("href") === "/auth" || (a.textContent || "").toLowerCase().indexOf("register") !== -1) {
        var wrap = a.parentElement;
        if (wrap && !wrap.getAttribute("data-fas-managed")) {
          wrap.setAttribute("data-fas-managed", "1");
          wrap.style.fontFamily = "'JetBrains Mono', monospace";
          wrap.style.fontSize = "10.5px";
          wrap.style.letterSpacing = "0.08em";
          wrap.style.color = "#71717A";
          wrap.textContent = "Managed Workspace · Need access? Contact support@fogarmy.com";
        }
      } else {
        a.style.display = "none";
      }
    }

    var walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null);
    var node;
    while ((node = walker.nextNode())) {
      if (node.nodeValue && node.nodeValue.indexOf("Postiz") !== -1) {
        node.nodeValue = node.nodeValue.replace(/Postiz/g, "FAS Post-It");
      }
    }
  }

  function applyAll() {
    replaceLogos();
    replaceAuthShowcase();
    ensureOssComplianceFooter();
    scrubTextAndLinks();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", applyAll);
  } else {
    applyAll();
  }

  var obs = new MutationObserver(function () {
    applyAll();
  });
  obs.observe(document.documentElement, { childList: true, subtree: true });
})();

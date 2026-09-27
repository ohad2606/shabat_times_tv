/* Auto-reload for the TV display.
   Polls a deploy marker; when it changes, the TV refreshes itself.
   Injected into every page under /tv/ by nginx sub_filter. */
(function () {
  var POLL_MS = 10000;
  var current = null;

  function fetchVersion(cb) {
    var x = new XMLHttpRequest();
    x.open('GET', '/_tv/version?t=' + Date.now(), true);
    x.onreadystatechange = function () {
      if (x.readyState === 4 && x.status === 200) cb(x.responseText);
    };
    try { x.send(); } catch (e) {}
  }

  function poll() {
    fetchVersion(function (v) {
      if (current === null) { current = v; return; }
      if (v !== current) location.reload();
    });
  }

  poll();
  setInterval(poll, POLL_MS);

  // TVs suspend timers while the app is backgrounded; re-check on wake.
  document.addEventListener('visibilitychange', function () {
    if (!document.hidden) poll();
  });
})();

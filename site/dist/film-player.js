/* A silent loop with persistent user intent and a native-player fallback. */
(() => {
  'use strict';
  const video = document.getElementById('research-film');
  const controls = document.getElementById('film-controls');
  const toggle = document.getElementById('film-toggle');
  const fullscreen = document.getElementById('film-fullscreen');
  const status = document.getElementById('film-status');
  if (!video || !controls || !toggle || !fullscreen || !status) return;

  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
  let manualPaused = false;
  let userStarted = false;
  let inViewport = false;
  let policyPauseEvents = 0;
  let failed = false;
  const wanted = () => !failed && inViewport && !document.hidden &&
    !manualPaused && (!reduced.matches || userStarted);
  const updateControls = () => {
    toggle.textContent = video.paused ? 'Play' : 'Pause';
    toggle.setAttribute('aria-label', video.paused ? 'Play research film' : 'Pause research film');
    toggle.setAttribute('aria-pressed', String(!video.paused));
  };
  const policyPause = () => {
    if (!video.paused) {
      policyPauseEvents += 1;
      video.pause();
    }
    updateControls();
  };
  const sync = () => {
    if (!wanted()) return policyPause();
    const attempt = video.play();
    if (attempt && typeof attempt.then === 'function') {
      attempt.then(() => {
        if (!wanted()) policyPause();
        updateControls();
      }).catch(() => {
        // Autoplay can be blocked by a browser or an in-flight pause. The
        // visible Play button remains usable without changing user intent.
        updateControls();
      });
    }
  };
  const fallback = () => {
    failed = true;
    policyPause();
    video.controls = true;
    controls.hidden = true;
    status.textContent = 'The film could not be loaded here. Open the player or download the video below.';
    status.hidden = false;
  };

  toggle.addEventListener('click', () => {
    if (!video.paused) {
      manualPaused = true;
      video.pause();
    } else {
      manualPaused = false;
      userStarted = true;
      sync();
    }
    updateControls();
  });
  video.addEventListener('pause', () => {
    if (policyPauseEvents > 0) policyPauseEvents -= 1;
    else manualPaused = true;
    updateControls();
  });
  video.addEventListener('play', () => {
    if (!wanted()) policyPause();
    updateControls();
  });
  video.addEventListener('error', fallback);
  fullscreen.hidden = !(video.requestFullscreen || video.webkitEnterFullscreen);
  fullscreen.addEventListener('click', async () => {
    try {
      if (video.requestFullscreen) await video.requestFullscreen();
      else if (video.webkitEnterFullscreen) video.webkitEnterFullscreen();
    } catch (_) {
      video.controls = true;
    }
  });
  document.addEventListener('visibilitychange', sync);
  window.addEventListener('pagehide', policyPause);
  window.addEventListener('pageshow', sync);
  const motionChanged = () => {
    if (reduced.matches) userStarted = false;
    sync();
  };
  if (reduced.addEventListener) reduced.addEventListener('change', motionChanged);
  else reduced.addListener(motionChanged);

  const visibleFraction = () => {
    const box = video.getBoundingClientRect();
    const width = Math.max(0, Math.min(box.right, innerWidth) - Math.max(box.left, 0));
    const height = Math.max(0, Math.min(box.bottom, innerHeight) - Math.max(box.top, 0));
    return box.width && box.height ? width * height / (box.width * box.height) : 0;
  };
  inViewport = visibleFraction() >= 0.15;
  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver(entries => {
      inViewport = entries[0].isIntersecting && entries[0].intersectionRatio >= 0.15;
      sync();
    }, {threshold: [0, 0.15]});
    observer.observe(video);
  } else {
    const measure = () => { inViewport = visibleFraction() >= 0.15; sync(); };
    window.addEventListener('scroll', measure, {passive: true});
    window.addEventListener('resize', measure, {passive: true});
  }
  // Until this point, native controls remain available if enhancement fails.
  video.muted = true;
  video.controls = false;
  controls.hidden = false;
  updateControls();
  if (video.error) fallback();
  else sync();
})();

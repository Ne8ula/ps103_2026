(() => {
  const slide = document.getElementById('slide-mockups');
  const video = document.getElementById('mockup-video');
  const start = slide.querySelector('.mockup-start');
  const active = () => !slide.hidden && !document.hidden;
  const setSpeed = () => {
    if (video.defaultPlaybackRate !== 1.75) video.defaultPlaybackRate = 1.75;
    if (video.playbackRate !== 1.75) video.playbackRate = 1.75;
  };
  const sync = () => {
    setSpeed();
    if (!active()) { video.pause(); start.hidden = true; return; }
    video.play().then(() => { start.hidden = true; }).catch(() => {
      start.hidden = !active();
    });
  };
  video.muted = true;
  video.loop = true;
  video.addEventListener('ratechange', setSpeed);
  video.addEventListener('loadedmetadata', sync);
  video.addEventListener('play', () => {
    setSpeed();
    if (!active()) video.pause();
  });
  new MutationObserver(sync).observe(slide, { attributes: true, attributeFilter: ['hidden'] });
  document.addEventListener('visibilitychange', sync);
  start.addEventListener('click', sync);
  sync();
})();

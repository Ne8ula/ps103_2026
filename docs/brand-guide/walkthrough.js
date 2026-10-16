(() => {
  const slide = document.getElementById('slide-walkthrough');
  const video = document.getElementById('walkthrough-video');
  const visible = () => !slide.hidden && !document.hidden;
  const sync = () => {
    if (!visible()) { video.pause(); return; }
    if (video.ended) video.currentTime = 0;
    video.play().catch(() => { /* Native controls remain available if autoplay is blocked. */ });
  };
  video.muted = true;
  video.addEventListener('play', () => { if (!visible()) video.pause(); });
  new MutationObserver(sync).observe(slide, {attributes:true,attributeFilter:['hidden']});
  document.addEventListener('visibilitychange', sync);
  sync();
})();

// How long the UI waits, repeats and keeps things up: the one place these numbers live.
// (Animation durations are CSS tokens in tokens.css; these are behaviour, read by scripts.)

export const TIMING = {
  agentPollMs: 5000, // sessions and limits refresh
  statusSettleMs: 6000, // "Applied" shows this long before "In sync"
  liveDebounceMs: 450, // a burst of edits sends one live preview
  quickDebounceMs: 200, // dragging a slider sends one change
  toastMs: 4000,
  toastErrorMs: 8000,
  transitionStartMs: 250, // a view transition that has not started by then is skipped
  citySearchMs: 220,
  cityBlurMs: 120, // lets a click on a result land before the list closes
  messagePreviewMs: 250,
  previewTickMs: 100, // LED preview frame
  clockBlinkMs: 500, // the colon of the simulated clock
  simCycleMs: 2500, // each item of a simulated built-in
  hotspotPollMs: 2000, // is this Mac on a new clock's hotspot yet
  discoverRetryMs: 4000, // looking for a clock that is joining Wi-Fi
  clockJoinMs: 90000, // give up waiting for it after this long
  gameFrameMs: 100, // the browser mirrors a game at the clock's frame rate
  liveCheckKeepMs: 60000, // a screen tried with real data is not asked again for this long
};

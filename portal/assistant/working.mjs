export function workingStatus(element) {
  let timer, started;
  function clear() {
    clearInterval(timer);
    started = undefined;
    element.replaceChildren();
  }
  function show(label) {
    started ??= performance.now();
    clearInterval(timer);
    const clock = document.createElement('span');
    clock.setAttribute('aria-hidden', 'true');
    element.replaceChildren(document.createTextNode(label), clock);
    function tick() {
      const seconds = Math.floor((performance.now() - started) / 1000);
      clock.textContent = seconds >= 5 ? ' · ' + seconds + '秒経過' : '';
    }
    tick();
    timer = setInterval(tick, 1000);
  }
  return {show, clear};
}

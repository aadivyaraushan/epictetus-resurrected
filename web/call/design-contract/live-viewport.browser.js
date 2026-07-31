(() => {
  const transcript = Array.from({ length: 12 }, (_, index) => `
    <p class="turn ${index % 2 === 0 ? "you" : "him"}">
      <span class="who">${index % 2 === 0 ? "You" : "Epictetus"}</span>
      <span class="what">A demanding conversation turn with enough detail to test the reading column when the exchange grows beyond a single viewport and the controls must remain available.</span>
    </p>
  `).join("");

  const sources = Array.from({ length: 4 }, (_, index) => `
    <article class="source">
      <div class="cite">Discourses, Book ${index + 1}, Chapter ${index + 2}</div>
      <div class="title">What remains in our power</div>
      <p class="quote">A long grounding passage belongs in the margin without making the whole desktop page grow. It should remain complete and readable inside its own scrolling evidence column while the call controls stay fixed within the initial viewport. This repeated sentence supplies realistic source density for the regression check.</p>
      <div class="score">similarity 0.${index + 4}17</div>
    </article>
  `).join("");

  document.body.innerHTML = `
    <main class="shell live-shell">
      <header class="live-masthead">
        <div class="brand"><div><h1>Epictetus, Resurrected</h1><p class="sub">Nicopolis, c. 108 — and now</p></div></div>
        <span class="destination">review after call</span>
      </header>
      <div class="call live-layout">
        <section class="column"><h2>Conversation</h2><div class="scroller">${transcript}</div></section>
        <aside class="evidence-rail">
          <section class="column"><h2>What he is drawing on</h2><div class="scroller">${sources}</div></section>
          <section class="column" style="flex: 0 0 auto"><h2>What he is doing</h2><div class="deed"><span class="mark">›</span><span>writing in the session log</span></div></section>
        </aside>
      </div>
      <footer class="controls live-controls">
        <span class="status"><span class="dot speaking"></span>Speaking</span>
        <button type="button" class="quiet">Mute</button>
        <button type="button" class="danger">End Call</button>
      </footer>
    </main>
  `;

  const shell = document.querySelector(".live-shell");
  const footer = document.querySelector(".live-controls");
  const scrollers = [...document.querySelectorAll(".live-layout .scroller")];
  const footerBox = footer.getBoundingClientRect();
  const result = {
    viewport: { width: innerWidth, height: innerHeight },
    documentHeight: document.documentElement.scrollHeight,
    shellHeight: shell.getBoundingClientRect().height,
    footerTop: footerBox.top,
    footerBottom: footerBox.bottom,
    footerInViewport: footerBox.top >= 0 && footerBox.bottom <= innerHeight,
    transcriptScrollable: scrollers[0].scrollHeight > scrollers[0].clientHeight,
    evidenceScrollable: scrollers[1].scrollHeight > scrollers[1].clientHeight,
    horizontalOverflow: document.documentElement.scrollWidth > innerWidth,
  };
  window.__liveViewportRegression = result;
  return result;
})();

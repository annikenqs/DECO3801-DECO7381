// scenario1.js
const STORAGE_KEY = 'worldMode';

document.addEventListener('DOMContentLoaded', () => {
  const choices = Array.from(document.querySelectorAll('.choice'));

  // mapping next page
  const NEXT_BY_MODE = {
    rightists: 'After_rightchoice.html',
    resourceists: 'After_resourcechoice.html',
    responsibilists: 'After_rightchoice.html',
  };

  choices.forEach((btn) => {
    btn.addEventListener('click', () => {
      // Selected state
      choices.forEach((b) => b.classList.remove('selected'));
      btn.classList.add('selected');

      // save changes
      const mode = btn.dataset.mode;
      localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({mode, decidedAt: new Date().toISOString()})
      );

      // skip
      const nextUrl = NEXT_BY_MODE[mode];
      if (nextUrl) {
        setTimeout(() => {
          location.href = nextUrl;
        }, 200);
      }
    });
  });

  // save click
  // try {
  //   const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null');
  //   if (saved?.mode) {
  //     const target = document.querySelector(`.choice[data-mode="${saved.mode}"]`);
  //     target?.classList.add('selected');
  //   }
  // } catch {}
});

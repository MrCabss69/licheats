// Reads opponent + orientation from the current Lichess DOM.
// Lichess is a SPA, so we never cache: the popup queries on demand and we
// re-read the live DOM on every message (fresh across in-app navigation).

function cleanName(text) {
  if (!text) return null;
  // Strip the "@" prefix and any trailing rating/title decorations.
  const name = text.trim().replace(/^@/, '').split(/\s+/)[0];
  return name || null;
}

function nameFrom(root) {
  if (!root) return null;
  const link = root.querySelector('a.user-link, a[href^="/@/"]');
  if (link) return cleanName(link.textContent);
  return cleanName(root.textContent);
}

// The board wrapper carries orientation-white / orientation-black,
// which is the *viewer's* color while playing.
function viewerColor() {
  const wrap = document.querySelector('.cg-wrap, .round__app .cg-wrap');
  if (!wrap) return null;
  if (wrap.classList.contains('orientation-black')) return 'black';
  if (wrap.classList.contains('orientation-white')) return 'white';
  return null;
}

function opposite(color) {
  if (color === 'white') return 'black';
  if (color === 'black') return 'white';
  return null;
}

// In a game view the opponent sits at the top (.ruser-top); you are at
// the bottom (.ruser-bottom). Falling back to a generic scan when spectating
// or on non-game pages.
function detectContext() {
  const top = document.querySelector('.ruser-top');
  const bottom = document.querySelector('.ruser-bottom');

  if (top && bottom) {
    const yourColor = viewerColor();
    return {
      nickname: nameFrom(top),
      yourColor: yourColor,
      opponentColor: opposite(yourColor),
    };
  }

  // Generic fallback: first plausible player link, no reliable color context.
  const selectors = ['.ruser.user-link', '.round__app .ruser', 'a.user-link[href^="/@/"]'];
  for (const selector of selectors) {
    const nickname = nameFrom(document.querySelector(selector));
    if (nickname) return { nickname, yourColor: null, opponentColor: null };
  }
  return { nickname: null, yourColor: null, opponentColor: null };
}

chrome.runtime.onMessage.addListener((request, _sender, sendResponse) => {
  if (request.action === 'fetchNickname') {
    sendResponse(detectContext());
  }
});

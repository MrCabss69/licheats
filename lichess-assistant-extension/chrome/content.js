function findOpponentNickname() {
  const selectors = [
    '.ruser.user-link a',
    '.round__app .ruser a',
    'a.user-link[href^="/@/"]'
  ];
  for (const selector of selectors) {
    const element = document.querySelector(selector);
    const text = element && element.textContent && element.textContent.trim();
    if (text) return text.replace(/^@/, '');
  }
  return null;
}

chrome.runtime.onMessage.addListener((request, _sender, sendResponse) => {
  if (request.action === 'fetchNickname') {
    sendResponse({ nickname: findOpponentNickname() });
  }
});

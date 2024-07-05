//content.js
chrome.runtime.onMessage.addListener(function(request, sender, sendResponse) {
    if (request.action === "fetchNickname") {
      const userElement = document.querySelector('.ruser.user-link a');
      const nickname = userElement ? userElement.innerText : null;
      chrome.runtime.sendMessage({ action: "updateNickname", nickname: nickname });
    }
  });

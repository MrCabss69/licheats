console.log("EEEEE");

document.addEventListener("DOMContentLoaded", () => {
  // null here defaults to active tab of current window
  chrome.tabs.executeScript(null, {
    code: `
      (function() {
        const userElement = document.querySelector('.ruser.user-link a');
        return userElement ? userElement.innerText : null;
      })();
    `
  }, response => {
    const pageData = response[0];

    if (!pageData) {
      console.log("Could not get data from page.");
      return;
    }

    document.getElementById("activeTabTitle").innerText = pageData;
  });
});


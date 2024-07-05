// Function to update the nickname in the popup
function updateNickname(nickname) {
  console.log("Updating nickname in popup:", nickname);
  document.getElementById('opponentNickname').textContent = nickname || 'Not found';
}

// Function to request the nickname using the script content.js
function requestNickname() {
  chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
    console.log("Requesting nickname for tab:", tabs[0].id);
    chrome.tabs.sendMessage(tabs[0].id, {action: "fetchNickname"});
  });
}

// Fetch and display player statistics
function fetchPlayerStats(username) {
  console.log("Fetching player stats for username:", username);
  fetch('http://localhost:5000/get_player_stats', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({username: username})
  })
  .then(response => {
    console.log("Received response from server");
    return response.json();
  })
  .then(data => {
    console.log("Processed JSON data:", data);
    if (data && data.player && data.stats) {
      displayStats(data);
    } else {
      console.error('Invalid data received:', data);
    }
  })
  .catch(error => console.error('Error fetching player stats:', error));
}

// Display player statistics in the popup
function displayStats(data) {
  console.log("Displaying stats in popup:", data);
  const playerInfo = document.getElementById('playerInfo');
  const statsInfo = document.getElementById('statsInfo');
  playerInfo.textContent = `Player: ${data.player.username}, Rating: ${data.player.rating}`;
  statsInfo.innerHTML = `Win rate: ${data.stats.win_rate}%<br>Average opponent rating: ${data.stats.avg_opponent_rating}`;
}

// Handle incoming messages from other scripts
chrome.runtime.onMessage.addListener(function(request, sender, sendResponse) {
  console.log("Received message:", request);
  if (request.action === "updateNickname") {
    updateNickname(request.nickname);
    fetchPlayerStats(request.nickname);
  }
});

// Initial function calls when the popup is loaded
document.addEventListener('DOMContentLoaded', function() {
  console.log("Popup DOM fully loaded");
  requestNickname();
});

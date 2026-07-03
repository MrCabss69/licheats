const API_BASE = 'http://127.0.0.1:8000';

function setStatus(message) {
  document.getElementById('status').textContent = message;
}

function setNickname(nickname) {
  document.getElementById('opponentNickname').textContent = nickname || 'Not found';
}

function topOpening(openings) {
  const entries = Object.entries(openings || {});
  if (!entries.length) return 'n/a';
  entries.sort((a, b) => b[1].total - a[1].total);
  return entries[0][0];
}

function displayStats(data) {
  document.getElementById('gamesCount').textContent = data.games_count;
  document.getElementById('winRate').textContent = `${data.summary.win_rate}%`;
  document.getElementById('avgOpponent').textContent = data.summary.avg_opponent_rating ?? 'n/a';
  document.getElementById('topOpening').textContent = topOpening(data.openings);
  document.getElementById('statsContainer').hidden = false;
}

async function fetchPlayerStats(username) {
  const encoded = encodeURIComponent(username);
  const response = await fetch(`${API_BASE}/players/${encoded}/analysis?limit=100&refresh=false`);
  const body = await response.json();
  if (!response.ok) {
    const message = body && body.error ? body.error.message : `HTTP ${response.status}`;
    throw new Error(message);
  }
  return body;
}

function requestNickname() {
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    const tab = tabs && tabs[0];
    if (!tab || !tab.id) {
      setStatus('No active Lichess tab found.');
      return;
    }
    chrome.tabs.sendMessage(tab.id, { action: 'fetchNickname' }, async (response) => {
      const nickname = response && response.nickname;
      setNickname(nickname);
      if (!nickname) {
        setStatus('Could not detect an opponent on this page.');
        return;
      }
      try {
        setStatus('Loading local analysis...');
        displayStats(await fetchPlayerStats(nickname));
        setStatus('Analysis loaded from local Licheats API.');
      } catch (error) {
        setStatus(`Backend unavailable or failed: ${error.message}`);
      }
    });
  });
}

document.addEventListener('DOMContentLoaded', requestNickname);

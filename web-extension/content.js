alert("Script loaded");
console.log("Script loaded");
function checkForOpponentName() {
    console.log("Checking for opponent name...");
    const opponentLink = document.querySelector('.ruser-top .user-link a');
    if (opponentLink) {
        const opponentName = opponentLink.textContent.trim();
        console.log('Opponent Name:', opponentName);
    } else {
        console.log("Opponent link not found");
    }
}


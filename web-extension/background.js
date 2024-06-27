// background.js
chrome.runtime.onInstalled.addListener(function() {
    console.log("La extensión se ha instalado correctamente.");
});

// Escucha las solicitudes de content.js
chrome.runtime.onMessage.addListener(
    function(request, sender, sendResponse) {
        console.log("Recibido desde content.js:", request);
        // Aquí puedes añadir más lógica para manejar los datos recibidos
        sendResponse({confirmation: "Datos recibidos en background.js"});
    }
);

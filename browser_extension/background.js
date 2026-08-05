importScripts("logger.js");

// Muss exakt mit dem "name" im native-host manifest json übereinstimmen
const NATIVE_HOST_NAME = "com.piifilter.host";

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type !== "PROCESS_TEXT") return;

  try {
    const port = chrome.runtime.connectNative(NATIVE_HOST_NAME);
    let responded = false;

    const timeout = setTimeout(() => {
      if (!responded) {
        responded = true;
        sendResponse({ ok: false, error: "Host hat nicht rechtzeitig geantwortet" });
        port.disconnect();
      }
    }, 5000);

    port.onMessage.addListener((response) => {
      sendResponse({ ok: true, result: response.result, replacements: response.replacements });
      port.disconnect();
    });

    port.onDisconnect.addListener(() => {
      if (chrome.runtime.lastError) {
        logError("Native host disconnect:", chrome.runtime.lastError.message);
      }
    });

    port.postMessage({ text: message.text });
  } catch (err) {
    logError("Fehler in background.js:", err);
    sendResponse({ ok: false, error: err.message });
  }

  // wichtig: signalisiert Chrome, dass sendResponse asynchron kommt
  return true;
});
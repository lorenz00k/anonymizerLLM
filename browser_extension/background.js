// Muss exakt mit dem "name" im native-host manifest json übereinstimmen
const NATIVE_HOST_NAME = "com.piifilter.host";

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type !== "PROCESS_TEXT") return;

  try {
    const port = chrome.runtime.connectNative(NATIVE_HOST_NAME);

    port.onMessage.addListener((response) => {
      sendResponse({ ok: true, result: response.result });
      port.disconnect();
    });

    port.onDisconnect.addListener(() => {
      if (chrome.runtime.lastError) {
        console.error("Native host disconnect:", chrome.runtime.lastError.message);
      }
    });

    port.postMessage({ text: message.text });
  } catch (err) {
    sendResponse({ ok: false, error: err.message });
  }

  // wichtig: signalisiert Chrome, dass sendResponse asynchron kommt
  return true;
});
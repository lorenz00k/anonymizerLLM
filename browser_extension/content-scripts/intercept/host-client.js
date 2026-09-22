/**
 * Kommunikationsschicht zu background.js (und darueber zum Native Host).
 * Kein Wissen ueber Review-Panel, Vault oder DOM - nur reines
 * Request/Response-Mapping als Promises.
 */

function getLlmEnabled() {
  return new Promise((resolve) => {
    chrome.storage.local.get(["llmEnabled"], (result) => {
      resolve(result.llmEnabled === true); // Standard: aus
    });
  });
}

function callHost(text, chatId, llmEnabled) {
  return new Promise((resolve, reject) => {
    chrome.runtime.sendMessage({ type: "PROCESS_TEXT", text, chatId, llmEnabled }, (response) => {
      if (chrome.runtime.lastError) {
        reject(new Error(chrome.runtime.lastError.message));
        return;
      }
      if (response && response.ok) {
        resolve(response);
      } else {
        reject(new Error(response ? response.error : "keine Antwort vom Host"));
      }
    });
  });
}

function callApplyLlm(text, suggestions, acceptedIds) {
  return new Promise((resolve, reject) => {
    chrome.runtime.sendMessage(
      { type: "APPLY_LLM", text, suggestions, acceptedIds },
      (response) => {
        if (chrome.runtime.lastError) {
          reject(new Error(chrome.runtime.lastError.message));
          return;
        }
        if (response && response.ok) {
          resolve(response);
        } else {
          reject(new Error(response ? response.error : "keine Antwort vom Host (apply_llm)"));
        }
      }
    );
  });
}

function callRetryRewrite(text, category) {
  return new Promise((resolve, reject) => {
    chrome.runtime.sendMessage({ type: "RETRY_REWRITE", text, category }, (response) => {
      if (chrome.runtime.lastError) {
        reject(new Error(chrome.runtime.lastError.message));
        return;
      }
      if (response && response.ok) {
        resolve(response.suggestedReplacement);
      } else {
        reject(new Error(response ? response.error : "keine Antwort vom Host (retry_rewrite)"));
      }
    });
  });
}
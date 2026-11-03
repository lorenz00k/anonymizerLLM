const js = require("@eslint/js");
const globals = require("globals");

// The content scripts are loaded by the browser in the order listed in
// manifest.json and share ONE global scope (no imports/exports). Anything a
// file defines at the top level and another file uses must be listed here,
// otherwise ESLint reports it as "not defined".
// If lint says "'xyz' is not defined", either you have a typo or you added a
// new cross-file function/variable: add its name to this list.
const sharedAcrossContentScripts = [
  // logger.js
  "CURRENT_LOG_LEVEL", "LOG_LEVELS", "logTrace", "logDebug", "logInfo", "logWarn", "logError",
  // content-scripts/shared.js
  "INPUT_SELECTOR", "filterEnabled", "deanonymizeEnabled", "vaults",
  "getInputElement", "getSendButton", "getChatId", "getVault", "saveVaults",
  // content-scripts/intercept/*.js
  "isProcessing", "activeReview", "suppressInputTracking",
  "escapeHtml", "setText", "showInlineError",
  "getLlmEnabled", "callHost", "callApplyLlm", "callRetryRewrite",
  "renderReviewPanel", "removeReviewPanel",
  "cancelActiveReview", "finalizeAndSend", "processAndResend",
];

module.exports = [
  js.configs.recommended,
  {
    files: ["browser_extension/**/*.js"],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "script",
      globals: {
        ...globals.browser,
        ...globals.webextensions,
        ...Object.fromEntries(sharedAcrossContentScripts.map((name) => [name, "writable"])),
      },
    },
    rules: {
      // Top-level variables/functions are "global" in these scripts and are
      // used by other files, so only check unused variables inside functions.
      "no-unused-vars": ["error", { vars: "local", args: "none" }],
      // The shared names above are declared (not redeclared) in their own file.
      "no-redeclare": ["error", { builtinGlobals: false }],
    },
  },
  {
    // background.js runs as a service worker (see manifest.json)
    files: ["browser_extension/background.js"],
    languageOptions: { globals: { ...globals.serviceworker, ...globals.webextensions } },
  },
];
/**
 * Minimaler Logger mit einstellbarem Level, kein Build-System noetig.
 * Wird in jedem Kontext einzeln eingebunden (Content Scripts, Popup,
 * Background), da diese sich keine Variablen teilen.
 */

const LOG_LEVELS = { trace: 0, debug: 1, info: 2, warn: 3, error: 4 };

// Zentral hier einstellen: debug waehrend der Entwicklung, info/warn fuer
// normale Nutzung, um die Konsole ruhig zu halten.
const CURRENT_LOG_LEVEL = LOG_LEVELS.info;

function  logTrace(...args){
    if(CURRENT_LOG_LEVEL <= LOG_LEVELS.trace) console.log("[PII Filter]", ...args);
}
function logDebug(...args) {
  if (CURRENT_LOG_LEVEL <= LOG_LEVELS.debug) console.log("[PII Filter]", ...args);
}
function logInfo(...args) {
  if (CURRENT_LOG_LEVEL <= LOG_LEVELS.info) console.log("[PII Filter]", ...args);
}
function logWarn(...args) {
  if (CURRENT_LOG_LEVEL <= LOG_LEVELS.warn) console.warn("[PII Filter]", ...args);
}
function logError(...args) {
  if (CURRENT_LOG_LEVEL <= LOG_LEVELS.error) console.error("[PII Filter]", ...args);
}
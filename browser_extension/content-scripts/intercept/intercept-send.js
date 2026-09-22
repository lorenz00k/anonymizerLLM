/**
 * Einstiegspunkt: faengt das Absenden von Nachrichten ab (Enter oder Klick
 * auf Senden) und stoesst die Verarbeitung in review-controller.js an.
 *
 * Enthaelt bewusst NUR das Event-Wiring - die eigentliche Logik lebt in:
 *   - host-client.js       (Kommunikation mit background.js/Native Host)
 *   - review-panel.js      (Rendering des Review-Panels)
 *   - review-controller.js (Zustand, Entscheidungslogik, Senden)
 *   - dom-utils.js         (generische DOM-/Text-Helfer)
 *
 * Nutzt filterEnabled, getInputElement, getSendButton aus shared.js.
 */

document.addEventListener(
  "keydown",
  (event) => {
    const inputEl = getInputElement();
    if (!inputEl || !inputEl.contains(event.target)) return;
    if (event.key !== "Enter" || event.shiftKey) return;

    if (isProcessing) {
      // Phase 1 laeuft noch ODER das Review-Panel wird gerade angezeigt.
      // WICHTIG: hier IMMER preventDefault/stopPropagation, sonst reagiert
      // Claude.ai selbst auf dieses Enter (natives Senden) - genau das
      // fuehrte bisher dazu, dass eine Nachricht am Panel vorbei gesendet
      // wurde und das Panel danach verwaist stehen blieb.
      event.preventDefault();
      event.stopPropagation();

      if (activeReview && activeReview.phase2Status !== "pending") {
        // Panel ist sichtbar und wartet nicht mehr auf das LLM - zweites
        // Enter = "Senden" (gleich wie Klick auf den Senden-Button).
        finalizeAndSend();
      }
      // Sonst (Phase 1 noch nicht zurueck, oder Phase 2 "pending"):
      // einfach ignorieren, der Nutzer sieht ja den Wartehinweis/den
      // deaktivierten Senden-Button im Panel.
      return;
    }

    if (!filterEnabled) {
      logTrace("Observer: filter deaktiviert");
      return;
    }

    event.preventDefault();
    event.stopPropagation();
    processAndResend(inputEl);
  },
  true
);

document.addEventListener(
  "click",
  (event) => {
    const inputEl = getInputElement();
    if (!inputEl) return;
    const sendButton = getSendButton(inputEl);
    if (!sendButton || !sendButton.contains(event.target)) return;
    if (isProcessing) return;
    if (!filterEnabled) {
      logTrace("Observer: filter deaktiviert");
      return;
    }

    event.preventDefault();
    event.stopPropagation();
    processAndResend(inputEl);
  },
  true
);

// Tippt der Nutzer weiter, waehrend das Review-Panel offen ist, ist der
// bisherige Stand (Positionen, Vorschlaege) potenziell veraltet. Statt das
// stillschweigend zu ignorieren, verwerfen wir die laufende Review
// komplett - das naechste Enter startet dann einen ganz frischen Scan auf
// dem aktuellen Text. event.isTrusted filtert dabei die "input"-Events
// heraus, die unser EIGENES setText() (Live-Vorschau) ausloest - die sind
// nie isTrusted, echte Tastatureingaben des Nutzers schon.
document.addEventListener(
  "input",
  (event) => {
    if (!activeReview) return;
    const inputEl = getInputElement();
    if (!inputEl || !inputEl.contains(event.target)) return;
    if (suppressInputTracking) return; // eigene setText()-Aenderung, kein echtes Tippen

    logInfo("Nutzer tippt waehrend der Review weiter - Review wird verworfen, naechstes Enter scannt neu");
    cancelActiveReview();
  },
  true
);

logInfo("intercept-send.js geladen");
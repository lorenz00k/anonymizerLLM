const ARTICLE_SELECTOR = 'div[role="article"]';
const POST_STREAM_DELAY_MS = 500; // Puffer, bis React fertig ge-re-rendert hat

const pendingArticles = new WeakSet(); // verhindert doppelte Timer fuer denselben Artikel

//letzte Nachricht von claude
function getLastArticle() {
  const articles = document.querySelectorAll(ARTICLE_SELECTOR);
  return articles.length > 0 ? articles[articles.length - 1] : null;
}

function getStreamingState(article) {
  const streamingEl = article.querySelector("[data-is-streaming]");
  if (!streamingEl) return null;
  return streamingEl.getAttribute("data-is-streaming");
}

function replaceTextInNode(node, vault) {
  if (node.nodeType === Node.TEXT_NODE) {
    const text = node.textContent;
    const placeholders = Object.keys(vault).filter((p) => text.includes(p));
    if (placeholders.length === 0) return false;

    const fragment = document.createDocumentFragment();
    let remaining = text;
    let changed = false;

    while (remaining.length > 0) {
      let earliestIndex = -1;
      let matchedPlaceholder = null;
      for (const placeholder of placeholders) {
        const idx = remaining.indexOf(placeholder);
        if (idx !== -1 && (earliestIndex === -1 || idx < earliestIndex)) {
          earliestIndex = idx;
          matchedPlaceholder = placeholder;
        }
      }

      if (earliestIndex === -1) {
        fragment.appendChild(document.createTextNode(remaining));
        break;
      }

      if (earliestIndex > 0) {
        fragment.appendChild(document.createTextNode(remaining.slice(0, earliestIndex)));
      }

      const mark = document.createElement("mark");
      mark.className = "pii-filter-restored";
      mark.title = "Automatisch zurückübersetzt";
      mark.textContent = vault[matchedPlaceholder];
      fragment.appendChild(mark);
      changed = true;

      remaining = remaining.slice(earliestIndex + matchedPlaceholder.length);
    }

    if (changed) {
      node.parentNode.replaceChild(fragment, node);
    }
    return changed;
  }

  if (node.nodeType === Node.ELEMENT_NODE) {
    if (node.classList?.contains("sr-only") || node.getAttribute?.("aria-hidden") === "true") {
      return false;
    }
  }

  let anyChanged = false;
  for (const child of Array.from(node.childNodes)) {
    if (replaceTextInNode(child, vault)) {
      anyChanged = true;
    }
  }
  return anyChanged;
}

function deanonymizeArticle(article) {
  if (!deanonymizeEnabled) {
    logDebug("Deanonymisierung deaktiviert, überspringe.");
    return;
  }
  logTrace("deanonymizeArticle gestartet, article:", article);
  logTrace("ist article noch im DOM?", document.body.contains(article));

  const textEl = article.querySelector("p.font-claude-response-body");
  logTrace("textEl gefunden:", textEl);
  const target = textEl || article;

  const foundAny = replaceTextInNode(target, getVault());

  if (foundAny) {
    logInfo("Antwort deanonymisiert (Formatierung erhalten)");
  }
}
function isAssistantArticle(article) {
  return getStreamingState(article) !== null;
}

function deanonymizeAllArticles() {
  const articles = document.querySelectorAll(ARTICLE_SELECTOR);
  articles.forEach((article) => {
    if(isAssistantArticle(article)){
      deanonymizeArticle(article)
    }
  });
}

const responseObserver = new MutationObserver(() => {
  const article = getLastArticle();
  if (!article) {
    logTrace("Observer: kein Nachrichtenelement gefunden");
    return;
  }

  const streamingState = getStreamingState(article);
  logDebug("Observer: streamingState =", streamingState);
  if (streamingState !== "false") return;

  // Sofortiger Check: enthaelt der Text GERADE JETZT einen bekannten
  // Platzhalter? Falls ja (egal ob zum ersten Mal oder erneut nach
  // einem Re-Render), reparieren wir sofort - kein Timer noetig fuer
  // diesen Wiederholungsfall.
  const textEl = article.querySelector("p.font-claude-response-body");
  const target = textEl || article;
  const needsFix = Object.keys(getVault()).some((placeholder) =>
    target.innerText.includes(placeholder)
  );

  if (needsFix) {
    deanonymizeArticle(article);
    return;
  }

  // Erstmaliger Fall direkt nach dem Streaming-Ende: kurzer Puffer,
  // damit React seinen finalen Render-Pass abschliessen kann.
  if (pendingArticles.has(article)) return;
  pendingArticles.add(article);
  setTimeout(() => {
    deanonymizeArticle(article);
    pendingArticles.delete(article); // erlaubt erneutes Reagieren spaeter
  }, POST_STREAM_DELAY_MS);
});

responseObserver.observe(document.body, {
  childList: true,
  subtree: true,
  attributes: true,
  attributeFilter: ["data-is-streaming"],
});

logInfo("deanonymize-response.js geladen");

// Einmalig nach dem Laden der Seite: kompletten bisherigen Verlauf
// fixen, nicht nur die neueste Antwort (relevant nach einem Reload,
// wenn React die ganze Konversation aus dem Server-Zustand neu
// rendert).
setTimeout(deanonymizeAllArticles, POST_STREAM_DELAY_MS);

const style = document.createElement("style");
style.textContent = `
  mark.pii-filter-restored {
    background: ##90D5FF;
    color: inherit;
    padding: 0 2px;
    border-radius: 2px;
  }
`;
document.head.appendChild(style);
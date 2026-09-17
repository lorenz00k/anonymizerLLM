const ARTICLE_SELECTOR = 'div[role="article"]';
const POST_STREAM_DELAY_MS = 500; // Puffer, bis React fertig ge-re-rendert hat

const pendingArticles = new WeakSet(); // verhindert doppelte Timer fuer denselben Artikel

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
    let text = node.textContent;
    let changed = false;
    for (const [placeholder, real] of Object.entries(vault)) {
      if (text.includes(placeholder)) {
        text = text.replaceAll(placeholder, real);
        changed = true;
      }
    }
    if (changed) {
      node.textContent = text;
    }
    return changed;
  }

  // sr-only / aria-hidden Elemente ueberspringen, damit wir nicht in
  // unsichtbaren Screenreader-Text hineinschreiben
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
  logTrace("deanonymizeArticle gestartet, article:", article);
  logTrace("ist article noch im DOM?", document.body.contains(article));

  const textEl = article.querySelector("p.font-claude-response-body");
  logTrace("textEl gefunden:", textEl);
  const target = textEl || article;

  const foundAny = replaceTextInNode(target, vault);

  if (foundAny) {
    logInfo("Antwort deanonymisiert (Formatierung erhalten)");
  }
}

const responseObserver = new MutationObserver(() => {
  if (!filterEnabled) {
    logTrace("Observer: filter deaktiviert");
    return;
  }

  const article = getLastArticle();
  if (!article) {
    logTrace("Observer: kein Artikel gefunden");
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
  const needsFix = Object.keys(vault).some((placeholder) =>
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
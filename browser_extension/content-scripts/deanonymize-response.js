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

function deanonymizeArticle(article) {
  //console.log("[PII Filter DEBUG] deanonymizeArticle gestartet, article:", article);
  //console.log("[PII Filter DEBUG] ist article noch im DOM?", document.body.contains(article));

  const textEl = article.querySelector("p.font-claude-response-body");
  //console.log("[PII Filter DEBUG] textEl gefunden:", textEl);
  const target = textEl || article;
  const currentText = target.innerText;
  console.log("Deanonmisiert input: ", currentText);

  let replaced = currentText;
  let foundAny = false;
  for (const [placeholder, real] of Object.entries(vault)) {
    if (replaced.includes(placeholder)) {
      foundAny = true;
      replaced = replaced.replaceAll(placeholder, real);
    }
  }

  if (foundAny) {
    console.log("[PII Filter] Deanonymisiere Antwort:", replaced);
    target.innerText = replaced;
  }
}

const responseObserver = new MutationObserver(() => {
  if (!filterEnabled) {
    console.log("[PII Filter DEBUG] Observer: filter deaktiviert");
    return;
  }

  const article = getLastArticle();
  if (!article) {
    console.log("[PII Filter DEBUG] Observer: kein Artikel gefunden");
    return;
  }

  const streamingState = getStreamingState(article);
  console.log("[PII Filter DEBUG] Observer: streamingState =", streamingState);
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

console.log("[PII Filter] deanonymize-response.js geladen");
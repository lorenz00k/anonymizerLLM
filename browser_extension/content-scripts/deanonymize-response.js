const ARTICLE_SELECTOR = 'div[role="article"]';
const POST_STREAM_DELAY_MS = 500; // Puffer, bis React fertig ge-re-rendert hat

const processedArticles = new WeakSet();
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
  const textEl = article.querySelector("p.font-claude-response-body");
  const target = textEl || article;
  const currentText = target.innerText;

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

  processedArticles.add(article);
}

const responseObserver = new MutationObserver(() => {
  if (!filterEnabled) return;

  const article = getLastArticle();
  if (!article) return;
  if (processedArticles.has(article) || pendingArticles.has(article)) return;

  const streamingState = getStreamingState(article);
  if (streamingState !== "false") return;

  // Nicht sofort schreiben - React braucht nach dem Streaming-Ende
  // noch einen Moment fuer den finalen Re-Render (Markdown, Highlighting).
  pendingArticles.add(article);
  setTimeout(() => {
    deanonymizeArticle(article);
  }, POST_STREAM_DELAY_MS);
});

responseObserver.observe(document.body, {
  childList: true,
  subtree: true,
  attributes: true,
  attributeFilter: ["data-is-streaming"],
});

console.log("[PII Filter] deanonymize-response.js geladen");
// Thin client for the UI's FastAPI backend.
// Exposes window.ForgeAPI with fetch helpers + an SSE consumer.

(function () {
  const API_BASE = window.FORGE_API_BASE || "";

  async function getJSON(path) {
    const resp = await fetch(API_BASE + path, { headers: { Accept: "application/json" } });
    if (!resp.ok) throw new Error(`${path}: ${resp.status} ${resp.statusText}`);
    return resp.json();
  }

  // POST a JSON body, consume the SSE stream, call onEvent(obj) for each `data:` chunk.
  // Returns a promise that resolves with the abort controller, so callers can cancel.
  async function streamSSE(path, body, { onEvent, onDone, onError, signal }) {
    let resp;
    try {
      resp = await fetch(API_BASE + path, {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
        body: JSON.stringify(body),
        signal,
      });
    } catch (err) {
      onError?.(err);
      return;
    }
    if (!resp.ok || !resp.body) {
      onError?.(new Error(`${path}: ${resp.status} ${resp.statusText}`));
      return;
    }
    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        let idx;
        while ((idx = buffer.indexOf("\n\n")) >= 0) {
          const chunk = buffer.slice(0, idx);
          buffer = buffer.slice(idx + 2);
          if (!chunk.startsWith("data: ")) continue;
          const payload = chunk.slice(6).trim();
          if (!payload) continue;
          try {
            const obj = JSON.parse(payload);
            if (obj.type === "all_done") {
              onDone?.();
              return;
            }
            onEvent?.(obj);
          } catch (err) {
            // ignore malformed lines
          }
        }
      }
      onDone?.();
    } catch (err) {
      onError?.(err);
    }
  }

  window.ForgeAPI = {
    getKbStats:     () => getJSON("/api/kb-stats"),
    getEvalResults: () => getJSON("/api/eval-results"),
    getDataset:     () => getJSON("/api/dataset"),
    getFindings:    () => getJSON("/api/findings"),
    getAgents:      () => getJSON("/api/agents"),
    streamAudit:    (message, graph_id, handlers) =>
      streamSSE("/api/audit/stream", { message, graph_id }, handlers),
    streamRace:     (message, question_id, handlers) =>
      streamSSE("/api/race/stream", { message, question_id }, handlers),
  };
})();

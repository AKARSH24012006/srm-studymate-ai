// Test double for the Claude artifact runtime (window.claude.use).
// Lets the e2e suite exercise every AI path without network access.
// window.__mockMode: "ok" (default) | "fail" (every call rejects) | "badjson"
(() => {
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  window.__mockMode = window.__mockMode || "ok";
  window.__calls = [];
  const fail = () => { const e = new Error("rate limited"); e.code = "rate_limited"; return e; };
  const text = input => typeof input === "string" ? input : input.map(m => m.content).join("\n\n");

  async function stream(full, opts) {
    let out = "";
    for (const part of full.match(/.{1,24}/gs)) {
      if (opts?.signal?.aborted) { const e = new Error("cancelled"); e.code = "cancelled"; e.text = out; throw e; }
      out += part; opts?.onText?.({ text: out, delta: part }); await sleep(window.__mockDelay || 5);
    }
    return { text: out, truncated: false };
  }

  async function sample(input, opts = {}) {
    const p = text(input); window.__calls.push({ kind: "text", p });
    if (window.__mockMode === "fail") throw fail();
    if (/cheat sheet/i.test(p)) {
      const topics = [...p.matchAll(/\(Topic: (.*?)\)/g)].map(m => m[1]).filter((v, i, a) => a.indexOf(v) === i);
      return stream(topics.map(t => `## ${t}\n- **${t}** key point one\n- Formula: \`O(n)\``).join("\n\n") + "\n\n## Likely exam questions\n1. Explain it.", opts);
    }
    return stream("**Merge sort** splits the array into halves and merges them in linear time [1]. It runs in `Θ(n log n)` in every case [1,2].\n\n- Stable\n- Needs Θ(n) extra space [2]", opts);
  }

  sample.json = async (prompt, opts = {}) => {
    window.__calls.push({ kind: "json", p: prompt });
    if (window.__mockMode === "fail") throw fail();
    if (window.__mockMode === "badjson") return { nope: true };
    await sleep(20);
    if (/multiple-choice questions/.test(prompt)) {
      const n = +(prompt.match(/Write (\d+) multiple-choice/) || [0, 5])[1];
      const ex = [...prompt.matchAll(/\[(\d+)\] \(Subject: (.*?) \| Topic: (.*?)\)/g)];
      return Array.from({ length: n }, (_, i) => {
        const e = ex[i % ex.length];
        // question 1 deliberately cites the wrong excerpt number; the app must still quote the right topic
        return { q: `Mock question ${i + 1} about ${e[3]}?`, options: ["Alpha", "Beta", "Gamma", "Delta"], answer: i % 4, explain: "Because the notes say so.", source: i === 0 && ex.length > 1 ? +ex[ex.length - 1][1] : +e[1], topic: e[3] };
      });
    }
    if (/flashcards/.test(prompt)) {
      const t = [...prompt.matchAll(/\(Topic: (.*?)\)/g)].map(m => m[1]);
      return Array.from({ length: 8 }, (_, i) => ({ front: `Card ${i + 1}: what is ${t[i % t.length]}?`, back: `**${t[i % t.length]}** is explained in your notes.`, topic: t[i % t.length] }));
    }
    if (/Feynman/.test(prompt)) {
      return { score: 82, clarity: 8, accuracy: 7, completeness: 8, verdict: "Clear and mostly correct.",
        good: ["You explained the split step", "You gave the running time"],
        misconceptions: [{ said: "It is in place", fix: "Merge sort needs Θ(n) extra space, so it is not in place.", source: 1 }],
        missing: ["Preferred for linked lists and external sorting"],
        questions: ["Why is the merge step linear?", "When would you pick quick sort instead?"],
        model: "Merge sort divides the array into halves, sorts each recursively, then merges them in **linear** time." };
    }
    return [];
  };
  sample.limits = async () => ({ images: false });

  const downloads = { save: async ({ filename, data }) => {
    const body = typeof data === "string" ? data : await data.text();
    window.__saved = { filename, body };
  } };

  window.claude = { use: async name => (name === "sample" ? sample : name === "downloads" ? downloads : null) };
})();

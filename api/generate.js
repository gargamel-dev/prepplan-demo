// Vercel serverless function: POST /api/generate
// This is the deployable twin of server.py. The browser never sees the key:
// it lives only in Vercel's environment variables as ANTHROPIC_API_KEY.
// No dependencies — uses the built-in fetch in Node 18+.
const MODEL = process.env.ANTHROPIC_MODEL || "claude-haiku-4-5";

function extractJson(text) {
  const match = String(text).match(/\{[\s\S]*\}/);
  if (!match) throw new Error("no-json");
  return JSON.parse(match[0]);
}

module.exports = async (req, res) => {
  if (req.method !== "POST") {
    return res.status(405).json({ error: "Method not allowed.", code: "bad_request" });
  }
  const prompt = req.body && req.body.prompt;
  if (typeof prompt !== "string" || !prompt.trim() || prompt.length > 8000) {
    return res.status(400).json({ error: "A prompt is required.", code: "bad_request" });
  }
  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) {
    return res.status(503).json({
      error: "AI is not set up yet on this server. Add your Anthropic API key and redeploy.",
      code: "missing_api_key",
    });
  }
  let upstream;
  try {
    upstream = await fetch("https://api.anthropic.com/v1/messages", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "x-api-key": apiKey,
        "anthropic-version": "2023-06-01",
      },
      body: JSON.stringify({
        model: MODEL,
        max_tokens: 2000,
        messages: [{ role: "user", content: prompt }],
      }),
    });
  } catch (e) {
    return res.status(502).json({ error: "Could not reach the AI service. Try again.", code: "upstream_error" });
  }
  if (upstream.status === 401) {
    return res.status(401).json({ error: "The API key was rejected.", code: "unauthorized" });
  }
  if (upstream.status === 429) {
    return res.status(429).json({ error: "Too many requests. Wait a moment and try again.", code: "rate_limited" });
  }
  if (!upstream.ok) {
    return res.status(502).json({ error: "The AI service returned an error. Try again.", code: "upstream_error" });
  }
  const payload = await upstream.json();
  const text = (payload.content || [])
    .filter((b) => b && b.type === "text")
    .map((b) => b.text)
    .join("");
  try {
    return res.status(200).json(extractJson(text));
  } catch (e) {
    return res.status(502).json({ error: "The AI returned something unexpected. Try again.", code: "bad_response" });
  }
};

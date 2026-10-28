# PrepPlan demo — AI version with a backend, as a shareable website

This is the Claude-exported PrepPlan demo, reworked so it works outside
claude.ai. The only Claude-only pieces were replaced:

- **Meal suggestions + 5-day plan:** used to call `claude.use('sample')`.
  Now the page calls `POST /api/generate` on its own backend, and the
  backend calls the Anthropic API. The key never appears in the HTML.
- **Save as text file:** used to call `claude.use('downloads')`.
  Now it downloads with a normal browser file download. No key needed.

Everything else (ingredient picker, low items, cooking-for/time/diet,
reset) is unchanged.

## What you need

1. An Anthropic API key — from console.anthropic.com, with billing set up
   there. API use is pay-as-you-go, not free, but a small demo like this
   uses very little per meal/plan request.
2. **Do not send me your key, and do not paste it into `index.html`.**
   It goes only in the server's environment (step 2 or 3 below).

## 1. Test it on your own computer first (recommended)

```
cd prepplan-demo-ai
cp .env.example .env
# open .env and put your key after ANTHROPIC_API_KEY=
python3 server.py
```

Open http://localhost:8000 — pick ingredients, Suggest meals, Build a
5-day plan, Save as text file. If the key is missing you will see a
clear "AI is not set up yet" message instead of a silent failure.

## 2. Deploy it as a shareable website link (Vercel)

Vercel is used here because the frontend already calls `/api/generate`,
and Vercel turns `api/generate.js` into exactly that endpoint, with no
extra config.

1. Put this whole folder in a GitHub repo (or use `vercel` CLI:
   `npm i -g vercel`, then `vercel` in this folder).
2. In Vercel, import the repo and deploy. No build command is needed.
3. In Vercel go to Settings → Environment Variables and add:
   `ANTHROPIC_API_KEY` = your key. Then redeploy.
4. Vercel gives you a link like `https://prepplan-demo.vercel.app`.
   Share that link — anyone opening it can use the demo, and your key
   stays on Vercel's server, not in the page they see.

## 3. Later, if you want a home-screen / App Store app

- Home screen: this site already has a manifest and icon, so on a phone
  you can use Share → Add to Home Screen. It will feel like an app.
- Real App Store: that's a separate, bigger step (wrapping this site,
  an Apple Developer account at $99/year, and App Store review). The
  backend above does not change for that — it is still the same
  `/api/generate` endpoint.

## Files

- `index.html` — the demo page (modified from the Claude export)
- `server.py` — local test backend (Python, no packages needed)
- `api/generate.js` — deployed backend for Vercel (Node, no packages)
- `manifest.webmanifest`, `icon.svg` — home-screen install bits
- `.env.example` — template for the local key file (never commit `.env`)

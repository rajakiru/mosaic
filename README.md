# Mosaic Mind

An interactive decision-making tool that helps you explore every angle of a decision through a branching tree visualization. Built for TartanHacks 2026 (theme: MOSAIC).

## What it does

Type a decision you're facing. Mosaic Mind asks clarifying questions with clickable options, building a visual tree as you explore. The key differentiator: you can click back on unchosen nodes to explore alternate branches simultaneously, something impossible in linear chat.

**Features:**
- **Branching decision tree** — click options to grow the tree, click unchosen nodes to explore alternate paths
- **Free text input** — type your own answer and the AI classifies it into the closest option, then branches from there
- **Periodic insights** — every 4 steps, the AI reflects back what it's learned about you
- **Research cards** — factual data (salaries, costs, ratings) auto-attaches when you mention concrete details. Hover the gold "R" dots on the tree to see research.
- **Show me the full picture** — synthesizes all explored branches into a personalized recommendation (available after 2+ paths)
- **Force a decision** — one bold answer with a 3-step action plan, no hedging (available after 4+ paths)

## Setup

1. Get an OpenAI API key from [platform.openai.com/api-keys](https://platform.openai.com/api-keys)

2. Start the server:
   ```
   node server.js
   ```

3. Open [http://localhost:3001](http://localhost:3001)

4. Enter your API key when prompted

## Tech stack

- React 18 (CDN, no build step)
- Tailwind CSS (CDN)
- Babel standalone (in-browser JSX)
- Node.js proxy server (zero dependencies)
- OpenAI GPT-4o API

## Files

- `index.html` — the entire app (single file)
- `server.js` — proxy server for CORS + API key forwarding
- `sample.tsx` — original React component (reference only)

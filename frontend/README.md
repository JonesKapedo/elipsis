# Frontend (Experimental)

This directory contains an experimental React + Vite SPA.

**It is not the production UI and is not deployed to Vercel.**

## Production path

The live website and workspace use **FastAPI + Jinja2** templates under `elipsis_api/templates/` and static assets under `static/`.

See `DEPLOY.md` and the root `README.md` for the official deploy target.

## Why this folder exists

Early exploration of a client-side SPA for marketplace browsing, bidder shop, and interactive assessment flows. The production product has since been built as a server-rendered app so that:

- SEO and public pages stay simple
- Auth and session handling stay server-side
- Cold starts and Vercel Python serverless stay predictable
- One codebase path is maintained for operators

## Current status

- Kept for reference and possible future extraction of highly interactive widgets
- Not linked from production routes
- Not built or served by the Vercel deployment

If you want to run it locally for experiments:

```bash
cd frontend
npm install
npm run dev
```

Do **not** point production traffic or the main `vercel.json` at this folder.

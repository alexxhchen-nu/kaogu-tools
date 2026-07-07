# Kaogu Tools 
A catalog of tools for archaeology literature analysis and data collection -- occassionally 3d visualization. 

## Stack 
1. Frontend: Next.js 
2. Backend: Python
3. Data: BunnyCDN, CloudfareR2 
4. API: FastAPI 
5. LLM: Xiaomi Token Plan (China), Codex 5.5, Grok 4.3; allowing BYOK
6. Agentic
	- OCR: PaddleOCR, MinerU 
	- Tooling: CrewAI
7. Deployment 
	- Frontend: Netlify / Railway 
	- Backend: Railway
	- DNS: Cloudfare
	- Caching: BunnyCDN 

## Deployment Notes

The default Python install keeps PaddleOCR out of the dependency set so Vercel
can bundle the FastAPI app under the serverless function size limit. OCR is an
optional runtime:

```bash
uv sync --extra ocr
```

Deploy OCR-enabled backends to Railway or another container/server platform.
Without the `ocr` extra, `/ocr/*` endpoints return `503` while the lighter API
routes continue to run.

## Folder Structure 
- Frontend 
- Backend 
- Shared 
  - Data catalogu references to BunnyCDN and Cloudfare R2

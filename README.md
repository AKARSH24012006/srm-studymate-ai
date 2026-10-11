# SRM StudyMate AI

A GenAI + RAG personalised learning companion for SRM students. Upload your own syllabus units, notes and PYQs, then ask a tutor that answers from them with citations, quiz yourself, and review flashcards while StudyMate tracks which topics need another pass.

## Pipeline

```
Knowledge ingestion (once per upload)
  Notes / PDFs ─▶ Parse ─▶ Structure (topics) ─▶ Chunk ─▶ BM25 index

Runtime (per question)
  Student query ─▶ RAG retrieval ─▶ LLM (Claude) ─▶ Grounding check ─▶ Learning modules ─▶ Dashboard
                        ▲                                                     │
                        └──── Personalisation router (weak-topic boost) ◀─────┘
```

## Features

- **Knowledge base**: PDF / TXT / MD upload or paste; heading-aware chunking with topic tags
- **AI Tutor**: BM25 retrieval, cited answers `[1]` linked to source passages, groundedness score, four answer styles (Explain, 13-mark exam answer, Quick revision, From scratch)
- **Quiz**: MCQs written from your own passages; every answer updates per-topic mastery
- **Flashcards**: 5-box spaced repetition; missed quiz questions convert to cards
- **Dashboard**: topic mastery, "Up next" recommendation, weak-topic focus, adaptive learning cycle, streak
- **Offline mode**: without an LLM, the tutor returns best-matching passages and quizzes become fill-in-the-blank

## Run

Single file, no build step: open `index.html` in a browser. AI features use the Claude artifact runtime (`window.claude.use("sample")`); elsewhere the app runs in offline mode. Data is stored in the browser's `localStorage`.

## Tech

Vanilla JS, BM25 retrieval, pdf.js for PDF text extraction, Claude for generation.

## Roadmap

- Backend (FastAPI) with embeddings + vector store for semantic retrieval
- User accounts and synced progress
- PYQ-aware question weighting

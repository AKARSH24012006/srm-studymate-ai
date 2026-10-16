# SRM StudyMate AI

A GenAI + RAG personalised learning companion for SRM students. Upload your own syllabus units, notes and PYQs, then ask a tutor that answers from them with citations, quiz yourself, review flashcards, plan for exams and study in focused blocks while StudyMate tracks which topics need another pass.

**v2.1** brings an animated "glow desk" design (a drifting colour-glow background, frosted glass panels, animated gradient hero, page transitions, light/dark themes and four accent colours) plus a planner, focus timer, gamification and a command palette.

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

- **Home**: greeting, level + XP bar, daily XP goal ring, smart "Up next" (exam prep → due cards → weakest topic), streak / mastery / due / focus stats, topic mastery, 16-week activity heatmap, achievements, recent activity
- **Notes**: PDF / TXT / MD upload or paste; heading-aware chunking with topic tags; per-subject readiness, one-tap **AI cheat sheet** (copy or download as Markdown), quiz and ask shortcuts
- **AI Tutor**: BM25 retrieval, cited answers `[1]` linked to source passages, groundedness score, four answer styles; follow-ups (simpler, another example, exam answer, quiz me), copy, read-aloud, save answer as a flashcard
- **Quiz**: MCQs written from your own passages; Easy / Mixed / Hard; exam mode with a 45 s timer; keys 1–4 and Enter; full answer review; missed questions turn into cards
- **Flashcards**: 5-box spaced repetition, AI or hand-written cards, keyboard flip and rating
- **Exam planner**: add exam dates; StudyMate spreads weak and unstarted topics across the days left and shows today's plan with Quiz / Learn buttons
- **Focus timer**: 25/5, 50/10, 15/3 Pomodoro blocks tagged by subject; 1 XP per focused minute; running timer stays visible in the sidebar
- **Gamification**: XP, levels, 12 badges, streaks, daily goal
- **Command palette** (Ctrl/⌘ K or /): search your notes, jump to any topic, run actions, or type a doubt and press Enter to ask the tutor
- **Settings**: name, theme, accent, daily goal, backup download / copy, restore, reset
- **Offline mode**: without an LLM, the tutor returns best-matching passages and quizzes become fill-in-the-blank

## Run

Single file, no build step: open `index.html` in a browser. AI features use the Claude artifact runtime (`window.claude.use("sample")`); elsewhere the app runs in offline mode. Data is stored in the browser's `localStorage` (v1 data carries over).

## Tech

Vanilla JS, BM25 retrieval, pdf.js for PDF text extraction, Claude for generation, Web Audio for the timer chime, Speech Synthesis for read-aloud.

## Roadmap

- Backend (FastAPI) with embeddings + vector store for semantic retrieval
- User accounts and synced progress
- PYQ-aware question weighting

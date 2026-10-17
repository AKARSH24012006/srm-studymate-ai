# SRM StudyMate AI

A GenAI + RAG personalised learning companion for SRM students. Upload your own syllabus units, notes and PYQs, then ask a tutor that answers from them with citations, quiz yourself, review flashcards, plan for exams and study in focused blocks while StudyMate tracks which topics need another pass.

**v2.3** adds **Teach it back**, a Feynman-technique mode where you explain a topic in your own words and StudyMate shows exactly what you missed, plus a set of ease-of-use upgrades (quick-action button, one-tap quiz, select-to-explain, drop files anywhere, undo, text size and calm motion).

Design: an animated "glow desk" look with a drifting colour-glow background, frosted glass panels, an animated gradient hero, page transitions, and one colourful theme with four colour worlds.

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
- **Teach it back (Feynman mode)**: pick a topic and explain it in your own words. Key ideas pulled from your notes start blurred and light up live as you cover them, with a coverage ring. "Check my explanation" has an AI junior grade it against your notes (clarity, accuracy and completeness, what you nailed, misconceptions with citations, what you left out) and ask two follow-up questions you can answer and re-check. Gaps become flashcards in one tap, the score feeds topic mastery, and drafts autosave. Works offline using key-idea coverage
- **Quiz**: MCQs written from your own passages; Easy / Mixed / Hard; exam mode with a 45 s timer; keys 1–4 and Enter; full answer review; missed questions turn into cards
- **Flashcards**: 5-box spaced repetition, AI or hand-written cards, keyboard flip and rating
- **Exam planner**: add exam dates; StudyMate spreads weak and unstarted topics across the days left and shows today's plan with Quiz / Learn buttons
- **Focus timer**: 25/5, 50/10, 15/3 Pomodoro blocks tagged by subject; 1 XP per focused minute; running timer stays visible in the sidebar
- **Gamification**: XP, levels, 14 badges, streaks, daily goal
- **Ease of use**: floating quick-action button (ask, quick quiz, teach, review, 25-min focus, add notes); one-tap **Quick 5** quiz on weak spots; select any text in an answer or your notes to explain it, copy it or turn it into a flashcard; drop a PDF anywhere to add it to your notes; Undo after removing a note or exam; Getting-started checklist on Home; `?` shows all keyboard shortcuts; "Up next" suggests a teach-back when quizzes haven't fixed a topic
- **Command palette** (Ctrl/⌘ K or /): search your notes, jump to any topic, run actions, or type a doubt and press Enter to ask the tutor
- **Settings**: name, colour world, text size, calm motion, daily goal, backup download / copy, restore, reset
- **Offline mode**: without an LLM, the tutor returns best-matching passages and quizzes become fill-in-the-blank

## Run

Single file, no build step: open `index.html` in a browser. AI features use the Claude artifact runtime (`window.claude.use("sample")`); elsewhere the app runs in offline mode. Data is stored in the browser's `localStorage` (v1 data carries over).

## Tech

Vanilla JS, BM25 retrieval, pdf.js for PDF text extraction, Claude for generation, Web Audio for the timer chime, Speech Synthesis for read-aloud.

## Roadmap

- Backend (FastAPI) with embeddings + vector store for semantic retrieval
- User accounts and synced progress
- PYQ-aware question weighting

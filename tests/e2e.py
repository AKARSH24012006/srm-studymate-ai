"""End-to-end test suite for SRM StudyMate AI.

Runs the single-file app in headless Chromium with a mock Claude runtime
(tests/mock_claude.js), so every AI path is exercised without network access.

    pip install playwright && playwright install chromium
    python tests/e2e.py                      # desktop + phone, all checks
    PDFJS_DIR=node_modules/pdfjs-dist/build AXE=node_modules/axe-core/axe.min.js python tests/e2e.py

Optional extras: PDFJS_DIR serves pdf.js 3.11.174 locally so the PDF upload
path runs offline; AXE runs axe-core accessibility checks on every page.
"""
import asyncio, json, os, sys, tempfile, time
from pathlib import Path
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parent.parent
FILE = (ROOT / "index.html").as_uri()
MOCK = (ROOT / "tests" / "mock_claude.js").read_text()
PDFJS_DIR = os.environ.get("PDFJS_DIR")
AXE = os.environ.get("AXE")
SHOTS = os.environ.get("SHOTS")  # folder to save screenshots into (optional)
VIEWS = ["dash", "lib", "tutor", "teach", "quiz", "cards", "plan", "settings"]
TMP = Path(tempfile.mkdtemp(prefix="studymate-e2e-"))
results = []


def check(name, ok, detail=""):
    results.append((bool(ok), name, detail))
    print(("PASS " if ok else "FAIL ") + name + (f"  [{detail}]" if detail else ""), flush=True)


async def newpage(b, vp=(1360, 900), mock=True, mode="ok", init=""):
    ctx = await b.new_context(viewport={"width": vp[0], "height": vp[1]})
    if mock:
        await ctx.add_init_script(f"window.__mockMode={json.dumps(mode)};" + MOCK)
    if init:
        await ctx.add_init_script(init)
    if PDFJS_DIR:
        async def serve(route):
            name = route.request.url.rsplit("/", 1)[-1]
            f = Path(PDFJS_DIR) / name
            if f.exists():
                await route.fulfill(path=str(f), content_type="application/javascript")
            else:
                await route.abort()
        await ctx.route("https://cdnjs.cloudflare.com/ajax/libs/pdf.js/**", serve)
    pg = await ctx.new_page()
    pg.errs = []
    pg.on("pageerror", lambda e: pg.errs.append(str(e)))
    return ctx, pg


async def go(pg, view, wait=300):
    await pg.goto(FILE + "#" + view)
    await pg.wait_for_timeout(wait)


def make_pdf(path):
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
    except ImportError:
        return False
    c = canvas.Canvas(str(path), pagesize=A4)
    y = 800
    for line in ["UNIT 2 PROCESS SYNCHRONIZATION", "", "2.1 Critical Section Problem",
                 "A critical section is a part of a program that accesses shared data. Only one process",
                 "may execute in its critical section at a time. Solutions need mutual exclusion, progress",
                 "and bounded waiting.", "", "2.2 Semaphores",
                 "A semaphore is an integer variable accessed only through wait and signal operations.",
                 "A binary semaphore works like a mutex lock. Counting semaphores guard many instances.", "",
                 "2.3 Deadlocks",
                 "A deadlock occurs when a set of processes wait forever for resources held by each other.",
                 "The Coffman conditions are mutual exclusion, hold and wait, no preemption, circular wait."]:
        c.drawString(60, y, line); y -= 18
    c.save()
    return True


async def ai_paths(b):
    ctx, pg = await newpage(b)
    await pg.goto(FILE); await pg.wait_for_timeout(900)
    check("AI status shows connected", "Claude connected" in await pg.text_content("#aiText"))
    # tutor
    await go(pg, "tutor")
    await pg.fill("#askBox", "Why is merge sort n log n?"); await pg.keyboard.press("Enter")
    await pg.wait_for_selector(".msg.ai .trace", timeout=8000)
    check("Tutor streams a cited answer", await pg.eval_on_selector_all(".msg.ai .cite", "e=>e.length") >= 3)
    check("Tutor shows grounded score", "Grounded" in await pg.text_content(".msg.ai .trace"))
    await pg.click(".msg.ai .cite"); await pg.wait_for_timeout(250)
    check("Citation opens its source", await pg.is_visible("details.srcs[open]"))
    await pg.click("[data-fu='simpler']")
    await pg.wait_for_function("document.querySelectorAll('.msg.ai').length>=2 && !document.querySelector('.msg.ai .thinking')", timeout=8000)
    check("Follow-up keeps chat history", "Why is merge sort" in await pg.evaluate("window.__calls.filter(c=>c.kind==='text').slice(-1)[0].p"))
    await pg.click("[data-card]"); await pg.wait_for_timeout(150)
    check("Answer saves as a flashcard", await pg.evaluate("JSON.parse(localStorage.getItem('sm2.cards')).length") >= 1)
    await pg.evaluate("window.__mockDelay=60")
    await pg.fill("#askBox", "Explain quick sort pivot"); await pg.keyboard.press("Enter"); await pg.wait_for_timeout(120)
    stop = await pg.is_visible("#stopBtn")
    if stop: await pg.click("#stopBtn")
    await pg.wait_for_timeout(300); await pg.evaluate("window.__mockDelay=5")
    check("Stop cancels a streaming answer", stop and await pg.is_visible("#askBtn"))
    await pg.reload(); await pg.wait_for_timeout(600); await go(pg, "tutor")
    check("Tutor chat survives a reload", await pg.eval_on_selector_all(".msg.ai", "e=>e.length") >= 2)
    await pg.click("#clearChat"); await pg.reload(); await pg.wait_for_timeout(500); await go(pg, "tutor")
    check("New chat clears saved history", await pg.eval_on_selector_all(".msg.ai", "e=>e.length") == 0)
    # quiz
    await go(pg, "quiz", 400)
    await pg.click("#qStart"); await pg.wait_for_selector(".qtext", timeout=8000)
    check("AI quiz renders", (await pg.text_content(".qtext")).startswith("Mock question"))
    await pg.keyboard.press("1"); await pg.wait_for_timeout(150)
    ok = await pg.evaluate("""()=>{ const topic=document.querySelector('#quizBox .subj').textContent.trim();
      const quote=document.querySelector('.explain blockquote').textContent.replace(/^From your notes: “|”$/g,'').replace(/…$/,'').trim();
      return JSON.parse(localStorage.getItem('sm2.docs')).some(d=>d.chunks.some(c=>c.topic===topic && c.text.replace(/\s+/g,' ').includes(quote.slice(0,60)))); }""")
    check("Quiz quotes a sentence from the question's own topic", ok)
    await pg.keyboard.press("Enter"); await pg.wait_for_timeout(100); await go(pg, "dash"); await go(pg, "quiz")
    check("Leaving and returning resumes the quiz", "Question 2 of 5" in await pg.text_content("#quizBox"))
    await pg.click("#qQuit"); await pg.wait_for_timeout(300)
    check("End quiz counts only answered questions", "1 of 1 correct" in await pg.text_content("#quizBox") or "0 of 1 correct" in await pg.text_content("#quizBox"))
    await pg.click("#again"); await pg.wait_for_timeout(200); await pg.click("#qStart"); await pg.wait_for_selector(".qtext", timeout=8000)
    for i in range(5):
        await pg.keyboard.press(str(i % 4 + 1)); await pg.wait_for_timeout(50)
        await pg.keyboard.press("Enter"); await pg.wait_for_timeout(50)
    await pg.wait_for_timeout(300)
    check("Quiz keys 1-4 + Enter score 5/5", "5 of 5 correct" in await pg.text_content("#quizBox"))
    # flashcards
    await go(pg, "cards")
    n0 = await pg.evaluate("JSON.parse(localStorage.getItem('sm2.cards')||'[]').length")
    await pg.click("#genCards"); await pg.wait_for_timeout(600)
    n1 = await pg.evaluate("JSON.parse(localStorage.getItem('sm2.cards')||'[]').length")
    check("AI makes 8 flashcards", n1 - n0 == 8, f"{n0}->{n1}")
    first = await pg.text_content(".face.front .q")
    await pg.keyboard.press(" "); await pg.wait_for_timeout(250); await pg.keyboard.press("1"); await pg.wait_for_timeout(250)
    check("'Again' moves card to the back of today's queue",
          await pg.text_content(".face.front .q") != first and await pg.evaluate("JSON.parse(localStorage.getItem('sm2.cards')).filter(c=>c.due<=Date.now()).length") == n1)
    await pg.click("#browseDeck"); await pg.wait_for_timeout(200)
    check("Browse deck lists every card", await pg.eval_on_selector_all(".deck-row", "e=>e.length") == n1)
    await pg.fill("#deckQ", "Card 3"); await pg.wait_for_timeout(100)
    check("Deck search filters", await pg.eval_on_selector_all(".deck-row", "e=>e.length") == 1)
    await pg.click("[data-ce]"); await pg.wait_for_timeout(150)
    await pg.fill("#mcFront", "Edited front"); await pg.click("#modalFoot .btn.primary"); await pg.wait_for_timeout(250)
    check("Edit saves a card", await pg.evaluate("JSON.parse(localStorage.getItem('sm2.cards')).some(c=>c.front==='Edited front')"))
    await pg.fill("#deckQ", ""); await pg.dispatch_event("#deckQ", "input")
    await pg.click(".deck-row [data-cdel]"); await pg.wait_for_timeout(150)
    mid = await pg.evaluate("JSON.parse(localStorage.getItem('sm2.cards')).length")
    await pg.click(".toast-btn"); await pg.wait_for_timeout(200)
    check("Delete card + Undo", mid == n1 - 1 and await pg.evaluate("JSON.parse(localStorage.getItem('sm2.cards')).length") == n1)
    for _ in range(12): await pg.keyboard.press("Tab")
    check("Keyboard focus stays inside the dialog", await pg.evaluate("!!document.activeElement.closest('.modal')"))
    await pg.keyboard.press("Escape")
    # cheat sheet + download
    await go(pg, "lib")
    await pg.click("[data-sheet]"); await pg.wait_for_selector("#shSave", timeout=8000)
    check("Cheat sheet renders", await pg.eval_on_selector_all("#modalBody h4", "e=>e.length") >= 2)
    await pg.click("#shSave"); await pg.wait_for_timeout(250)
    saved = await pg.evaluate("window.__saved")
    check("Cheat sheet downloads as .md", bool(saved) and saved["filename"].endswith(".md"))
    await pg.keyboard.press("Escape")
    # teach
    await go(pg, "teach")
    await pg.select_option("#teSubject", "Design and Analysis of Algorithms"); await pg.select_option("#teTopic", "Merge Sort")
    await pg.fill("#teachBox", "Merge sort splits the array into halves, sorts them and merges them back in linear time using a temporary array. It is in place.")
    await pg.dispatch_event("#teachBox", "input")
    check("Teach lights up key ideas while typing", await pg.eval_on_selector_all("#conceptList .concept.on", "e=>e.length") >= 2)
    await pg.focus("#teachBox"); await pg.keyboard.press("Control+Enter")
    await pg.wait_for_selector(".teach-res", timeout=8000)
    check("Teach AI flags the misconception", "not in place" in await pg.text_content("#teachResult"))
    await pg.click("[data-jq='0']"); await pg.wait_for_timeout(100)
    check("Junior question appends to explanation", "Q: Why is the merge step linear?" in await pg.input_value("#teachBox"))
    # backup
    await go(pg, "settings")
    await pg.click("#exportBtn"); await pg.wait_for_timeout(250)
    body = (await pg.evaluate("window.__saved"))["body"]
    check("Backup exports JSON", json.loads(body)["app"] == "srm-studymate")
    (TMP / "backup.json").write_text(body)
    check("No page errors (AI run)", not pg.errs, "; ".join(pg.errs)[:300])
    await ctx.close()


async def failures(b):
    for mode in ["fail", "badjson"]:
        ctx, pg = await newpage(b, mode=mode)
        await go(pg, "tutor", 700)
        if mode == "fail":
            await pg.fill("#askBox", "What is DHCP?"); await pg.keyboard.press("Enter"); await pg.wait_for_timeout(500)
            check(f"[{mode}] tutor falls back to note passages", "best-matching passages" in await pg.text_content(".msg.ai"))
        await go(pg, "quiz")
        await pg.click("#qStart"); await pg.wait_for_timeout(2200)
        check(f"[{mode}] quiz falls back offline", "Fill in the blank" in (await pg.text_content(".qtext") or ""))
        await go(pg, "teach")
        await pg.fill("#teachBox", "DHCP gives a host an address using discover offer request acknowledge messages over UDP from a server.")
        await pg.dispatch_event("#teachBox", "input"); await pg.click("#teachCheck"); await pg.wait_for_timeout(900)
        check(f"[{mode}] teach falls back offline", "Offline" in (await pg.text_content(".teach-res") or ""))
        check(f"[{mode}] no page errors", not pg.errs, "; ".join(pg.errs)[:300])
        await ctx.close()


async def notes_and_content(b):
    ctx, pg = await newpage(b)
    await go(pg, "lib", 500)
    # hostile text is never executed
    evil = '<img src=x onerror="window.__xss=1">'
    await pg.fill("#fSubject", evil); await pg.fill("#fTitle", evil)
    await pg.fill("#fText", f"# {evil} Topic\n" + "Evil passage text with enough words to make a chunk for the index. " * 5)
    await pg.click("#addBtn"); await pg.wait_for_timeout(1300)
    for v in VIEWS: await go(pg, v, 200)
    await go(pg, "tutor"); await pg.fill("#askBox", f"evil passage {evil}"); await pg.keyboard.press("Enter"); await pg.wait_for_timeout(800)
    await pg.keyboard.press("Control+k"); await pg.fill("#palInput", "evil"); await pg.wait_for_timeout(250); await pg.keyboard.press("Escape")
    check("Hostile note text never runs as code", await pg.evaluate("window.__xss") is None)
    # subject names merge case-insensitively, duplicates are refused
    await go(pg, "lib")
    note = "# Paging\nPaging divides memory into fixed size frames and pages so a process need not be contiguous in memory at all."
    await pg.fill("#fSubject", "Operating Systems"); await pg.fill("#fText", note); await pg.click("#addBtn"); await pg.wait_for_timeout(1200)
    await pg.fill("#fSubject", "operating  systems"); await pg.fill("#fText", note + " Extra line here."); await pg.click("#addBtn"); await pg.wait_for_timeout(1200)
    subs = await pg.evaluate("[...new Set(JSON.parse(localStorage.getItem('sm2.docs')).map(d=>d.subject))]")
    check("Subject names merge ignoring case/spaces", subs.count("Operating Systems") == 1 and "operating  systems" not in subs, str(subs))
    n = await pg.evaluate("JSON.parse(localStorage.getItem('sm2.docs')).length")
    await pg.fill("#fSubject", "Operating Systems"); await pg.fill("#fText", note); await pg.click("#addBtn"); await pg.wait_for_timeout(1000)
    check("Same note twice is refused", n == await pg.evaluate("JSON.parse(localStorage.getItem('sm2.docs')).length") and "already in" in await pg.text_content("#addMsg"))
    # PDF upload
    pdf = TMP / "os_unit2.pdf"
    if PDFJS_DIR and make_pdf(pdf):
        await pg.fill("#fSubject", "OS Lab"); await pg.set_input_files("#fFile", str(pdf)); await pg.click("#addBtn")
        await pg.wait_for_function("/Added|Couldn't|No readable/.test(document.querySelector('#addMsg').textContent)", timeout=20000)
        topics = await pg.evaluate("JSON.parse(localStorage.getItem('sm2.docs')).filter(d=>d.subject==='OS Lab').flatMap(d=>d.chunks.map(c=>c.topic))")
        check("PDF upload extracts headings as topics", {"Critical Section Problem", "Semaphores", "Deadlocks"} <= set(topics), str(sorted(set(topics))))
    else:
        print("SKIP PDF upload (set PDFJS_DIR and install reportlab)")
    # drop a file anywhere
    await go(pg, "dash")
    await pg.evaluate("""()=>{ const dt=new DataTransfer(); dt.items.add(new File(['# Deadlocks\\nA deadlock is when processes wait forever.'],'unit3.txt',{type:'text/plain'}));
      document.dispatchEvent(new DragEvent('dragenter',{dataTransfer:dt,bubbles:true})); window.__ov=!document.getElementById('dropAll').hidden;
      document.body.dispatchEvent(new DragEvent('drop',{dataTransfer:dt,bubbles:true,cancelable:true})); }""")
    await pg.wait_for_timeout(250)
    check("Drop a file anywhere stages it in Notes", await pg.evaluate("window.__ov") and "unit3.txt" in await pg.text_content("#fileList"))
    # undo note removal
    await go(pg, "lib")
    n = await pg.eval_on_selector_all(".doc", "e=>e.length")
    await pg.click("[data-del]"); await pg.wait_for_timeout(150); await pg.click(".toast-btn"); await pg.wait_for_timeout(250)
    check("Remove note + Undo", n == await pg.eval_on_selector_all(".doc", "e=>e.length"))
    check("No page errors (notes)", not pg.errs, "; ".join(pg.errs)[:300])
    await ctx.close()


async def empty_and_storage(b):
    ctx, pg = await newpage(b)
    await go(pg, "lib", 500); await pg.click("#rmEx"); await pg.wait_for_timeout(250)
    for v in VIEWS: await go(pg, v, 200)
    await go(pg, "quiz"); await pg.click("#qStart"); await pg.wait_for_timeout(250)
    check("Empty: quiz explains there are no passages", "No passages" in (await pg.text_content("#qMsg") or ""))
    await go(pg, "dash"); await pg.click("#fabBtn"); await pg.click("[data-fab='1']"); await pg.wait_for_timeout(250)
    check("No page errors (empty state)", not pg.errs, "; ".join(pg.errs)[:300])
    if (TMP / "backup.json").exists():
        await go(pg, "settings"); await pg.set_input_files("#importFile", str(TMP / "backup.json")); await pg.wait_for_timeout(500)
        check("Restore brings notes back", await pg.evaluate("JSON.parse(localStorage.getItem('sm2.docs')).length") == 2)
    await ctx.close()
    ctx, pg = await newpage(b, init="Storage.prototype.getItem=function(){throw new Error('blocked')};Storage.prototype.setItem=function(){throw new Error('blocked')};")
    await pg.goto(FILE); await pg.wait_for_timeout(700)
    await go(pg, "quiz"); await pg.click("#qStart"); await pg.wait_for_timeout(500)
    check("Works with browser storage blocked", await pg.is_visible(".qtext") and not pg.errs, "; ".join(pg.errs)[:200])
    await ctx.close()


async def performance(b):
    ctx, pg = await newpage(b, mock=False)
    await go(pg, "lib", 500)
    big = "\n\n".join(f"# Topic {i}\n" + f"Process scheduling round robin quantum {i} context switch overhead throughput waiting time. " * 30 for i in range(120))
    await pg.fill("#fSubject", "Operating Systems"); await pg.fill("#fText", big)
    t0 = time.time(); await pg.click("#addBtn")
    await pg.wait_for_function("document.querySelector('#addMsg').textContent.startsWith('Added')", timeout=30000)
    check("~330k-char notes index in under 4 s", time.time() - t0 < 4, f"{time.time()-t0:.2f}s")
    await go(pg, "tutor"); await pg.fill("#askBox", "round robin quantum")
    t0 = time.time(); await pg.keyboard.press("Enter"); await pg.wait_for_selector(".msg.ai .trace")
    check("Retrieval over big notes is instant", time.time() - t0 < 2, f"{time.time()-t0:.2f}s")
    await ctx.close()


async def timer(b):
    ctx, pg = await newpage(b)
    await pg.clock.install()
    await go(pg, "plan", 500)
    await pg.click("[data-tm='15']"); await pg.click("#tStart")
    await pg.clock.run_for(15 * 60 * 1000 + 2000)
    sess = await pg.evaluate("JSON.parse(localStorage.getItem('sm2.sessions')||'[]')")
    check("Focus block completes and is logged", len(sess) == 1 and sess[0]["min"] == 15)
    check("Break starts automatically", "Break" in await pg.text_content("#tPhase"))
    await ctx.close()


async def layout_and_a11y(b):
    for vp, tag in [((1360, 900), "desktop"), ((360, 740), "phone-360")]:
        ctx, pg = await newpage(b, vp=vp)
        await pg.goto(FILE); await pg.wait_for_timeout(600)
        bad = []
        for v in VIEWS:
            await go(pg, v, 800)
            ow = await pg.evaluate("document.documentElement.scrollWidth - innerWidth")
            if ow > 0: bad.append(f"{v}:{ow}px")
            if SHOTS:
                Path(SHOTS).mkdir(parents=True, exist_ok=True)
                await pg.screenshot(path=f"{SHOTS}/{tag}_{v}.png")
            if AXE and tag == "desktop":
                await pg.add_script_tag(path=AXE)
                vio = await pg.evaluate("async()=>(await axe.run(document,{resultTypes:['violations']})).violations.filter(v=>['serious','critical'].includes(v.impact)).map(v=>v.id)")
                if vio: bad.append(f"{v}: axe {','.join(vio)}")
        check(f"[{tag}] no sideways scroll" + (" or accessibility violations" if AXE and tag == "desktop" else ""), not bad, "; ".join(bad))
        check(f"[{tag}] no page errors on any page", not pg.errs, "; ".join(pg.errs)[:200])
        await ctx.close()


async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        for suite in [ai_paths, failures, notes_and_content, empty_and_storage, performance, timer, layout_and_a11y]:
            print(f"\n== {suite.__name__} ==", flush=True)
            await suite(b)
        await b.close()
    fails = [r for r in results if not r[0]]
    print(f"\n{len(results) - len(fails)} passed, {len(fails)} failed")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    asyncio.run(main())

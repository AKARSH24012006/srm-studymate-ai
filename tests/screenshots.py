"""Regenerates the README screenshots in docs/screenshots/.

Uses the mock Claude runtime with realistic sample answers, drives the app
like a student would (quiz, teach-back, tutor), then captures each screen.

    python tests/screenshots.py
"""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
FILE = (ROOT / "index.html").as_uri()
OUT = ROOT / "docs" / "screenshots"
MOCK = (ROOT / "tests" / "mock_claude.js").read_text()
QUIZ = """
(() => { const u = window.claude.use; window.claude.use = async n => { const s = await u(n);
  if (n === 'sample' && !s.__wrapped) { const j = s.json; s.__wrapped = true;
    s.json = async (p, o) => /multiple-choice/.test(p) ? [
      {q:"What is the worst-case running time of quick sort?", options:["Θ(n)","Θ(n log n)","Θ(n²)","Θ(log n)"], answer:2, explain:"A pivot that is always the smallest or largest element gives n levels of Θ(n) partitioning work.", source:1, topic:"Quick Sort"},
      {q:"Which property does merge sort have that quick sort lacks?", options:["In place","Stable","O(1) extra space","Randomised"], answer:1, explain:"Merge sort keeps equal keys in their original order; quick sort does not.", source:1, topic:"Merge Sort"},
      {q:"For T(n) = 2T(n/2) + n, which Master Theorem case applies?", options:["Case 1","Case 2","Case 3","None"], answer:1, explain:"f(n) = n matches n^(log_2 2) = n, so Case 2 gives Θ(n log n).", source:1, topic:"Recurrence Relations and the Master Theorem"},
      {q:"Binary search needs which kind of input?", options:["Any list","A sorted array","A linked list","A heap"], answer:1, explain:"It halves a sorted range using random access to the middle element.", source:1, topic:"Binary Search"},
      {q:"Which notation gives a tight bound?", options:["Big-O","Big-Omega","Big-Theta","Little-o"], answer:2, explain:"Θ holds when f(n) is both O(g(n)) and Ω(g(n)).", source:1, topic:"Asymptotic Notations"}
    ] : j(p, o); }
  return s; }; })();
"""
EXPLAIN = ("Merge sort is a divide and conquer algorithm. It splits the array into two halves, sorts each half "
           "recursively and then merges the two sorted halves using a temporary array. The merge step compares "
           "the front elements and copies the smaller one, so merging is linear. Because the split is always even "
           "there are log n levels, so it runs in n log n time. It is in place.")


async def main():
    OUT.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as p:
        b = await p.chromium.launch()
        for tag, vp in [("desktop", (1360, 860)), ("phone", (390, 844))]:
            ctx = await b.new_context(viewport={"width": vp[0], "height": vp[1]}, device_scale_factor=2 if tag == "phone" else 1)
            await ctx.add_init_script(MOCK); await ctx.add_init_script(QUIZ)
            pg = await ctx.new_page()
            await pg.goto(FILE); await pg.wait_for_timeout(600)
            await pg.evaluate("()=>{ localStorage.setItem('sm2.prof', JSON.stringify({name:'Akarsh', accent:'coral', goal:50})); localStorage.setItem('sm2.guideHidden','true'); }")
            await pg.reload(); await pg.wait_for_timeout(500)
            # a quiz, a teach-back and a tutor question, done for real
            await pg.goto(FILE + "#quiz"); await pg.wait_for_timeout(400)
            await pg.click("#qStart"); await pg.wait_for_selector(".qtext")
            for k in ["3", "1", "2", "2", "3"]:
                await pg.keyboard.press(k); await pg.wait_for_timeout(250)
                if tag == "desktop" and k == "1":
                    await pg.wait_for_timeout(500); await pg.screenshot(path=str(OUT / "quiz.png"))
                await pg.keyboard.press("Enter"); await pg.wait_for_timeout(150)
            await pg.goto(FILE + "#teach"); await pg.wait_for_timeout(400)
            await pg.select_option("#teSubject", "Design and Analysis of Algorithms"); await pg.select_option("#teTopic", "Merge Sort")
            await pg.fill("#teachBox", EXPLAIN); await pg.dispatch_event("#teachBox", "input"); await pg.wait_for_timeout(500)
            if tag == "phone":
                await pg.evaluate("window.scrollTo(0,0)"); await pg.wait_for_timeout(300)
                await pg.screenshot(path=str(OUT / "phone-teach.png"))
            await pg.click("#teachCheck"); await pg.wait_for_selector(".teach-res"); await pg.wait_for_timeout(3200)
            await pg.wait_for_function("document.getElementById('confetti').hidden", timeout=15000)
            if tag == "desktop":
                await pg.evaluate("window.scrollTo(0,0)"); await pg.wait_for_timeout(1500)
                await pg.screenshot(path=str(OUT / "teach.png"))
                await pg.evaluate("document.querySelector('#teachResult').scrollIntoView({block:'start'})"); await pg.wait_for_function("document.getElementById('confetti').hidden", timeout=15000); await pg.wait_for_timeout(600)
                await pg.screenshot(path=str(OUT / "teach-result.png"))
            await pg.goto(FILE + "#tutor"); await pg.wait_for_timeout(400)
            await pg.fill("#askBox", "Why is merge sort Θ(n log n) in every case?"); await pg.keyboard.press("Enter")
            await pg.wait_for_selector(".msg.ai .trace"); await pg.wait_for_timeout(900)
            if tag == "desktop":
                await pg.evaluate("window.scrollTo(0,0)"); await pg.wait_for_timeout(300)
                await pg.screenshot(path=str(OUT / "tutor.png"))
            await pg.goto(FILE + "#dash"); await pg.wait_for_timeout(2600)
            await pg.screenshot(path=str(OUT / ("home.png" if tag == "desktop" else "phone-home.png")))
            await ctx.close()
        await b.close()
    for f in OUT.glob("*.png"):  # ship small JPEGs, keep repo light
        Image.open(f).convert("RGB").save(f.with_suffix(".jpg"), quality=82, optimize=True, progressive=True)
        f.unlink()
    print("\n".join(sorted(f"{f.name}  {f.stat().st_size//1024} KB" for f in OUT.glob("*.jpg"))))


if __name__ == "__main__":
    asyncio.run(main())

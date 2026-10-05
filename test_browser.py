import asyncio
import json
import os
import subprocess
import time
import requests
import websockets
import sys
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
from dotenv import load_dotenv

load_dotenv()
pwd = os.getenv("DASHBOARD_PASSWORD", "")

chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
port = 9222
user_data_dir = r"C:\Temp\chrome_test_profile"
html_url = "file:///O:/03_Obsidian-Local/Obsidian-Local/13_ProductHunt%E5%88%86%E6%9E%90/docs/index.html"

proc = subprocess.Popen([
    chrome_path,
    f"--remote-debugging-port={port}",
    f"--user-data-dir={user_data_dir}",
    "--headless=new",
    "--disable-gpu",
    "--no-sandbox",
    html_url
])

time.sleep(2.5)

async def test_page():
    try:
        tabs = requests.get(f"http://127.0.0.1:{port}/json/list").json()
        target_tab = None
        for t in tabs:
            if t.get("type") == "page":
                target_tab = t
                break
        if not target_tab:
            target_tab = tabs[0]
        
        print("Target tab:", target_tab.get("url"), target_tab.get("title"))
        ws_url = target_tab["webSocketDebuggerUrl"]
        
        async with websockets.connect(ws_url) as ws:
            msg_id = 1
            async def send_cmd(method, params=None):
                nonlocal msg_id
                cid = msg_id
                msg_id += 1
                await ws.send(json.dumps({"id": cid, "method": method, "params": params or {}}))
                while True:
                    resp = json.loads(await ws.recv())
                    if resp.get("method") == "Runtime.consoleAPICalled":
                        args = [str(a.get("value")) for a in resp.get("params", {}).get("args", [])]
                        print("[CONSOLE]", resp["params"]["type"], ":", " ".join(args))
                    elif resp.get("method") == "Runtime.exceptionThrown":
                        print("[EXCEPTION]", resp["params"]["exceptionDetails"])
                    elif resp.get("id") == cid:
                        return resp.get("result", {})

            await send_cmd("Runtime.enable")
            await send_cmd("Page.enable")
            await asyncio.sleep(1)

            res = await send_cmd("Runtime.evaluate", {
                "expression": "document.title"
            })
            print("Document title:", res.get("result", {}).get("value"))

            res_input = await send_cmd("Runtime.evaluate", {
                "expression": "Boolean(document.getElementById('lockInput'))"
            })
            print("lockInput exists:", res_input.get("result", {}).get("value"))

            eval_unlock = f"""
            (async () => {{
                const input = document.getElementById('lockInput');
                input.value = {json.dumps(pwd)};
                await handleUnlock();
            }})()
            """
            print("Calling handleUnlock()...")
            res_unlock = await send_cmd("Runtime.evaluate", {
                "expression": eval_unlock,
                "awaitPromise": True
            })
            print("Unlock result:", res_unlock)

            await asyncio.sleep(1)

            eval_test = """(() => {
                let errs = [];
                for (let p of PRODUCTS) {
                  try {
                    cardHTML(p);
                  } catch (e) {
                    errs.push({ id: p.id, err: e.message, stack: e.stack });
                  }
                }
                const cardsEl = document.getElementById('cards');
                return {
                  errs: errs,
                  cardsHTML_length: cardsEl ? cardsEl.innerHTML.length : -1,
                  cardsInnerHTML: cardsEl ? cardsEl.innerHTML.slice(0, 300) : '',
                  totalProducts: PRODUCTS.length
                };
            })()"""
            res_eval = await send_cmd("Runtime.evaluate", {
                "expression": eval_test,
                "returnByValue": True
            })
            print("Evaluation result:", json.dumps(res_eval, ensure_ascii=False, indent=2))

            res_rank = await send_cmd("Runtime.evaluate", {
                "expression": "rank"
            })
            print("Current rank:", res_rank.get("result", {}).get("value"))

            res_chips = await send_cmd("Runtime.evaluate", {
                "expression": "document.getElementById('chips').innerText"
            })
            print("Chips text:", res_chips.get("result", {}).get("value"))

            # Test clicking 'all' chip
            eval_click_all = """(() => {
                document.querySelector('.chip[data-rank="all"]').click();
                return {
                    currentRank: rank,
                    visibleCount: document.querySelectorAll('.card:not([hidden])').length
                };
            })()"""
            res_all = await send_cmd("Runtime.evaluate", {
                "expression": eval_click_all,
                "returnByValue": True
            })
            print("After clicking 'すべて' chip:", res_all.get("result", {}).get("value"))

    finally:
        proc.terminate()

asyncio.run(test_page())

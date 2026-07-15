"""Web UI: FastAPI + WebSocket chat interface to the Mythos brain.

Text in, text out (v1) — perfect for phones on your LAN and for testing the
brain without any audio hardware. Requires the [web] extra:
    pip install fastapi uvicorn
Run with:
    python -m mythos --web
"""

from __future__ import annotations

from mythos.config import config
from mythos.llm import Brain

_PAGE = """<!doctype html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__NAME__ AI</title>
<style>
  :root { color-scheme: dark; }
  * { box-sizing: border-box; margin: 0; }
  body { background:#0f0f1a; color:#e6e6f0; font-family:ui-monospace,Consolas,monospace;
         display:flex; flex-direction:column; height:100dvh; }
  header { padding:14px 18px; border-bottom:1px solid #2a2a4a; }
  h1 { font-size:1.1rem; color:#00ff9c; letter-spacing:.12em; }
  small { color:#7a7a99; }
  #log { flex:1; overflow-y:auto; padding:16px 18px; display:flex;
         flex-direction:column; gap:10px; }
  .msg { max-width:80%; padding:9px 13px; border-radius:10px; line-height:1.45;
         white-space:pre-wrap; word-break:break-word; }
  .user { align-self:flex-end; background:#24406b; }
  .bot { align-self:flex-start; background:#1a1a2e; border:1px solid #2a2a4a; }
  .bot b { color:#00ff9c; }
  form { display:flex; gap:8px; padding:12px 18px; border-top:1px solid #2a2a4a; }
  input { flex:1; background:#1a1a2e; color:#e6e6f0; border:1px solid #2a2a4a;
          border-radius:8px; padding:10px 12px; font:inherit; }
  button { background:#00ff9c; color:#000; border:0; border-radius:8px;
           padding:10px 18px; font:inherit; font-weight:700; cursor:pointer; }
</style></head><body>
<header><h1>◉ __NAME__ AI</h1><small>web console — type a command</small></header>
<div id="log"></div>
<form id="f"><input id="i" autocomplete="off"
  placeholder="e.g. what's the weather in Tokyo?" autofocus>
<button>Send</button></form>
<script>
const log = document.getElementById('log');
const ws = new WebSocket((location.protocol === 'https:' ? 'wss://' : 'ws://')
                         + location.host + '/ws');
let current = null;
ws.onmessage = (ev) => {
  const m = JSON.parse(ev.data);
  if (m.type === 'assistant') {
    if (!current) {
      current = document.createElement('div');
      current.className = 'msg bot';
      current.innerHTML = '<b>__NAME__:</b> ';
      log.appendChild(current);
    }
    current.append(m.text + ' ');
  } else if (m.type === 'done') {
    current = null;
  }
  log.scrollTop = log.scrollHeight;
};
document.getElementById('f').onsubmit = (e) => {
  e.preventDefault();
  const i = document.getElementById('i');
  if (!i.value.trim()) return;
  const d = document.createElement('div');
  d.className = 'msg user';
  d.textContent = i.value;
  log.appendChild(d);
  ws.send(JSON.stringify({text: i.value}));
  i.value = '';
  log.scrollTop = log.scrollHeight;
};
</script></body></html>"""


def create_app():
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect
    from fastapi.responses import HTMLResponse

    app = FastAPI(title=f"{config.assistant_name} AI")
    brain = Brain(config)

    @app.get("/")
    async def index() -> HTMLResponse:
        return HTMLResponse(_PAGE.replace("__NAME__", config.assistant_name))

    @app.websocket("/ws")
    async def ws_endpoint(ws: WebSocket) -> None:
        await ws.accept()
        try:
            while True:
                data = await ws.receive_json()
                text = str(data.get("text", "")).strip()
                if not text:
                    continue
                async for sentence in brain.respond_stream(text):
                    await ws.send_json({"type": "assistant", "text": sentence})
                await ws.send_json({"type": "done"})
        except WebSocketDisconnect:
            pass

    return app


def main() -> None:
    import uvicorn

    uvicorn.run(create_app(), host=config.web_host, port=config.web_port)

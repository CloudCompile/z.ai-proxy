import os
import time
import uuid
import json
import base64
import hmac
import hashlib
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse, HTMLResponse
from curl_cffi.requests import AsyncSession
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Z.ai Proxy API")

JWT_TOKEN = os.getenv("JWT_TOKEN")
COOKIE = os.getenv("COOKIE")
UPSTREAM_URL = "https://chat.z.ai/api/v2/chat/completions"
FIXED_KEY = b"key-@@@@)))()((9))-xxxx&&&%%%%%"

def get_user_id(jwt_token):
    try:
        payload_b64 = jwt_token.split('.')[1]
        payload_b64 += "=" * ((4 - len(payload_b64) % 4) % 4)
        payload = json.loads(base64.b64decode(payload_b64).decode())
        return payload.get("id")
    except Exception:
        return ""

USER_ID = get_user_id(JWT_TOKEN) if JWT_TOKEN else ""

def generate_zai_request(messages, is_stream: bool, tools: list = None, tool_choice: str = None):
    timestamp = int(time.time() * 1000)
    request_id = str(uuid.uuid4())
    chat_id = str(uuid.uuid4())
    current_msg_id = str(uuid.uuid4())
    
    last_prompt = messages[-1].get("content", "") if messages else ""
    
    # 1. Generate Signature
    window_index = str(timestamp // 300000).encode()
    E = hmac.new(FIXED_KEY, window_index, hashlib.sha256).hexdigest()
    
    base_params = {
        "timestamp": str(timestamp),
        "requestId": request_id,
        "user_id": USER_ID
    }
    
    # Python dict keeps insertion order, but we explicitly sort
    sorted_items = sorted(base_params.items(), key=lambda x: x[0])
    flattened = []
    for k, v in sorted_items:
        flattened.extend([str(k), str(v)])
    sortedPayload = ",".join(flattened)
    
    d = f"{sortedPayload}|{base64.b64encode(last_prompt.encode('utf-8')).decode()}|{timestamp}".encode()
    signature = hmac.new(E.encode(), d, hashlib.sha256).hexdigest()

    # 2. URL Parameters
    params = {
        "timestamp": timestamp,
        "requestId": request_id,
        "user_id": USER_ID,
        "version": "0.0.1",
        "platform": "web",
        "token": JWT_TOKEN,
        "user_agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
        "language": "en-US",
        "languages": "en-US,en",
        "timezone": "Asia/Calcutta",
        "cookie_enabled": "true",
        "screen_width": "1920",
        "screen_height": "1080",
        "screen_resolution": "1920x1080",
        "viewport_height": "948",
        "viewport_width": "921",
        "viewport_size": "921x948",
        "color_depth": "24",
        "pixel_ratio": "1",
        "current_url": f"https://chat.z.ai/c/{chat_id}",
        "pathname": f"/c/{chat_id}",
        "search": "",
        "hash": "",
        "host": "chat.z.ai",
        "hostname": "chat.z.ai",
        "protocol": "https:",
        "referrer": "",
        "title": "Z.ai - Free AI Chatbot & Agent",
        "timezone_offset": "-330",
        "local_time": time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime()),
        "utc_time": time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime()),
        "is_mobile": "false",
        "is_touch": "false",
        "max_touch_points": "0",
        "browser_name": "Chrome",
        "os_name": "Linux",
        "signature_timestamp": timestamp
    }
    
    param_qs = "&".join([f"{k}={v}" for k, v in params.items()])
    full_url = f"{UPSTREAM_URL}?{param_qs}"

    # 3. Headers
    headers = {
        "x-fe-version": "prod-fe-1.0.241",
        "authorization": f"Bearer {JWT_TOKEN}",
        "x-signature": signature,
        "content-type": "application/json",
        "user-agent": params["user_agent"],
        "accept": "*/*",
        "referer": params["current_url"],
        "origin": "https://chat.z.ai",
        "Cookie": COOKIE if COOKIE else ""
    }

    # 4. Payload
    payload = {
        "stream": True, # Always stream from upstream so we don't timeout, we buffer if client wants no-stream
        "model": "glm-5",
        "messages": messages,
        "signature_prompt": last_prompt,
        "params": {},
        "extra": {},
        "features": {
            "image_generation": False,
            "web_search": False,
            "auto_web_search": False,
            "preview_mode": True,
            "flags": [],
            "enable_thinking": True
        },
        "chat_id": chat_id,
        "id": request_id, 
        "current_user_message_id": current_msg_id,
        "background_tasks": {"title_generation": True, "tags_generation": True}
    }
    
    if tools:
        payload["tools"] = tools
    if tool_choice:
        payload["tool_choice"] = tool_choice
        
    return full_url, headers, payload

@app.get("/", response_class=HTMLResponse)
async def root():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Z.ai Proxy API</title>
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap" rel="stylesheet">
        <style>
            :root {
                --primary: #6366f1;
                --primary-hover: #4f46e5;
                --bg: #0f172a;
                --card-bg: #1e293b;
                --text: #f8fafc;
                --text-muted: #94a3b8;
                --accent: #22d3ee;
            }
            * {
                box-sizing: border-box;
                margin: 0;
                padding: 0;
            }
            body {
                font-family: 'Outfit', sans-serif;
                background-color: var(--bg);
                color: var(--text);
                line-height: 1.6;
                overflow-x: hidden;
            }
            .container {
                max-width: 1000px;
                margin: 0 auto;
                padding: 4rem 2rem;
            }
            header {
                text-align: center;
                margin-bottom: 4rem;
                animation: fadeInDown 0.8s ease-out;
            }
            h1 {
                font-size: 3.5rem;
                font-weight: 700;
                margin-bottom: 1rem;
                background: linear-gradient(135deg, #fff 0%, var(--primary) 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }
            .subtitle {
                font-size: 1.25rem;
                color: var(--text-muted);
                max-width: 600px;
                margin: 0 auto;
            }
            .grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 2rem;
                margin-bottom: 4rem;
            }
            .card {
                background: var(--card-bg);
                padding: 2rem;
                border-radius: 1.5rem;
                border: 1px solid rgba(255, 255, 255, 0.1);
                transition: all 0.3s ease;
                backdrop-filter: blur(10px);
                animation: fadeInUp 0.8s ease-out backwards;
            }
            .card:hover {
                transform: translateY(-5px);
                border-color: var(--primary);
                box-shadow: 0 10px 30px -10px rgba(99, 102, 241, 0.3);
            }
            .card h2 {
                font-size: 1.5rem;
                margin-bottom: 1rem;
                color: var(--accent);
                display: flex;
                align-items: center;
                gap: 0.75rem;
            }
            .card p {
                color: var(--text-muted);
            }
            .endpoints {
                background: rgba(0, 0, 0, 0.3);
                padding: 2rem;
                border-radius: 1.5rem;
                border: 1px solid rgba(255, 255, 255, 0.05);
                margin-bottom: 4rem;
                animation: fadeIn 1s ease-out;
            }
            .endpoints h2 {
                margin-bottom: 1.5rem;
                text-align: center;
            }
            code {
                background: #000;
                padding: 0.2rem 0.5rem;
                border-radius: 0.4rem;
                color: var(--accent);
                font-family: monospace;
            }
            .endpoint-item {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 1rem;
                border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            }
            .endpoint-item:last-child {
                border-bottom: none;
            }
            .badge {
                padding: 0.25rem 0.75rem;
                border-radius: 1rem;
                font-size: 0.75rem;
                font-weight: 600;
                text-transform: uppercase;
                background: var(--primary);
            }
            footer {
                text-align: center;
                color: var(--text-muted);
                padding: 2rem 0;
                border-top: 1px solid rgba(255, 255, 255, 0.05);
            }
            @keyframes fadeInDown {
                from { opacity: 0; transform: translateY(-30px); }
                to { opacity: 1; transform: translateY(0); }
            }
            @keyframes fadeInUp {
                from { opacity: 0; transform: translateY(30px); }
                to { opacity: 1; transform: translateY(0); }
            }
            @keyframes fadeIn {
                from { opacity: 0; }
                to { opacity: 1; }
            }
            .shine {
                position: relative;
                overflow: hidden;
            }
            .shine::after {
                content: '';
                position: absolute;
                top: -50%;
                left: -50%;
                width: 200%;
                height: 200%;
                background: linear-gradient(
                    to bottom right,
                    rgba(255,255,255,0) 0%,
                    rgba(255,255,255,0) 40%,
                    rgba(255,255,255,0.1) 50%,
                    rgba(255,255,255,0) 60%,
                    rgba(255,255,255,0) 100%
                );
                transform: rotate(45deg);
                transition: all 0.5s;
                opacity: 0;
            }
            .card:hover .shine::after {
                opacity: 1;
                left: 100%;
                top: 100%;
                transition: all 0.7s;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <h1>Z.ai Proxy</h1>
                <p class="subtitle">A high-performance bridge converting Z.ai intelligence into OpenAI and Anthropic compatible formats. Built for developers, by developers.</p>
            </header>

            <div class="grid">
                <div class="card shine" style="animation-delay: 0.1s">
                    <h2>🚀 Dual Compatibility</h2>
                    <p>Native support for both <code>OpenAI v1</code> and <code>Anthropic v1</code> message formats. Use your favorite SDKs without changing a line of code.</p>
                </div>
                <div class="card shine" style="animation-delay: 0.2s">
                    <h2>🛡️ Signature Engine</h2>
                    <p>Automated request signing and JWT payload management. We handle the complex Z.ai security handshake so you don't have to.</p>
                </div>
                <div class="card shine" style="animation-delay: 0.3s">
                    <h2>⚡ Real-time Streaming</h2>
                    <p>Support for Server-Sent Events (SSE). Experience the speed of <code>glm-5</code> with ultra-low latency token-by-token generation.</p>
                </div>
            </div>

            <div class="endpoints">
                <h2>API Endpoints</h2>
                <div class="endpoint-item">
                    <div>
                        <strong>OpenAI Chat</strong><br>
                        <code>POST /v1/chat/completions</code>
                    </div>
                    <span class="badge">Active</span>
                </div>
                <div class="endpoint-item">
                    <div>
                        <strong>Anthropic Messages</strong><br>
                        <code>POST /v1/messages</code>
                    </div>
                    <span class="badge">Active</span>
                </div>
                <div class="endpoint-item">
                    <div>
                        <strong>Model List</strong><br>
                        <code>GET /v1/models</code>
                    </div>
                    <span class="badge">Active</span>
                </div>
            </div>

            <footer>
                <p>&copy; 2024 Z.ai Proxy API. All models served via secure upstream proxy.</p>
            </footer>
        </div>
    </body>
    </html>
    """

@app.post("/v1/chat/completions")
async def openai_proxy(request: Request):
    if not JWT_TOKEN:
        raise HTTPException(status_code=500, detail="JWT_TOKEN is missing")
    
    try:
        data = await request.json()
        messages = data.get("messages", [])
        is_stream = data.get("stream", False)
        tools = data.get("tools")
        tool_choice = data.get("tool_choice")
        
        url, headers, payload = generate_zai_request(messages, is_stream, tools, tool_choice)
        
        session = AsyncSession()
        
        async def generate_stream():
            try:
                response = await session.post(
                    url,
                    json=payload,
                    headers=headers,
                    impersonate="chrome124",
                    stream=True,
                    timeout=60
                )
                
                if response.status_code != 200:
                    yield f"data: {json.dumps({'error': f'Upstream error: {response.status_code}'})}\n\n"
                    yield "data: [DONE]\n\n"
                    return
                
                chat_cmpl_id = f"chatcmpl-{uuid.uuid4()}"
                
                async for chunk in response.aiter_lines():
                    if not chunk: continue
                    chunk = chunk.decode('utf-8')
                    if not chunk.startswith("data: "): continue
                    
                    data_str = chunk[6:]
                    if data_str.strip() == "[DONE]":
                        yield "data: [DONE]\n\n"
                        break
                    
                    try:
                        chunk_data = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue
                        
                    delta_content = chunk_data.get("data", {}).get("delta_content", "")
                    is_done = chunk_data.get("data", {}).get("done", False)
                    
                    if delta_content:
                        openai_chunk = {
                            "id": chat_cmpl_id,
                            "object": "chat.completion.chunk",
                            "created": int(time.time()),
                            "model": "glm-5",
                            "choices": [{"index": 0, "delta": {"content": delta_content}}]
                        }
                        yield f"data: {json.dumps(openai_chunk)}\n\n"
                        
                    if is_done:
                        yield "data: [DONE]\n\n"
                        break
            finally:
                await session.close()

        if is_stream:
            return StreamingResponse(generate_stream(), media_type="text/event-stream")
        else:
            # Buffer the streaming response and return JSON
            full_content = ""
            async for chunk in generate_stream():
                if chunk.startswith("data: ") and not "[DONE]" in chunk and "chat.completion.chunk" in chunk:
                    try:
                        chunk_json = json.loads(chunk[6:])
                        full_content += chunk_json["choices"][0]["delta"].get("content", "")
                    except:
                        pass
                
            return {
                "id": f"chatcmpl-{uuid.uuid4()}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": "glm-5",
                "choices": [{"index": 0, "message": {"role": "assistant", "content": full_content}, "finish_reason": "stop"}]
            }
            
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/v1/messages")
async def anthropic_proxy(request: Request):
    if not JWT_TOKEN:
        raise HTTPException(status_code=500, detail="JWT_TOKEN is missing")
    
    try:
        data = await request.json()
        messages = data.get("messages", [])
        is_stream = data.get("stream", False)
        tools = data.get("tools")
        tool_choice = data.get("tool_choice")
        
        # Anthropic format is slightly different, let's just support simple text messages for now.
        url, headers, payload = generate_zai_request(messages, is_stream, tools, tool_choice)
        
        session = AsyncSession()
        
        async def generate_stream():
            try:
                response = await session.post(
                    url,
                    json=payload,
                    headers=headers,
                    impersonate="chrome124",
                    stream=True,
                    timeout=60
                )
                
                if response.status_code != 200:
                    # Generic error event
                    yield "event: error\n"
                    yield f"data: {json.dumps({'type': 'error', 'error': {'type': 'api_error', 'message': f'Upstream error: {response.text}'}})}\n\n"
                    return
                
                msg_id = f"msg_{uuid.uuid4()}"
                
                # Send message_start
                yield "event: message_start\n"
                yield f"data: {json.dumps({'type': 'message_start', 'message': {'id': msg_id, 'type': 'message', 'role': 'assistant', 'content': [], 'model': 'claude-3-5-sonnet-20241022', 'stop_reason': None, 'stop_sequence': None, 'usage': {'input_tokens': 0, 'output_tokens': 0}}})}\n\n"
                
                # Send content_block_start
                yield "event: content_block_start\n"
                yield f"data: {json.dumps({'type': 'content_block_start', 'index': 0, 'content_block': {'type': 'text', 'text': ''}})}\n\n"
                        
                async for chunk in response.aiter_lines():
                    if not chunk: continue
                    chunk = chunk.decode('utf-8')
                    if not chunk.startswith("data: "): continue
                    
                    data_str = chunk[6:]
                    if data_str.strip() == "[DONE]":
                        break
                    
                    try:
                        chunk_data = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue
                        
                    delta_content = chunk_data.get("data", {}).get("delta_content", "")
                    is_done = chunk_data.get("data", {}).get("done", False)
                    
                    if delta_content:
                        yield "event: content_block_delta\n"
                        yield f"data: {json.dumps({'type': 'content_block_delta', 'index': 0, 'delta': {'type': 'text_delta', 'text': delta_content}})}\n\n"
                        
                    if is_done:
                        break
                
                # Send content_block_stop
                yield "event: content_block_stop\n"
                yield f"data: {json.dumps({'type': 'content_block_stop', 'index': 0})}\n\n"
                
                # Send message_stop
                yield "event: message_stop\n"
                yield f"data: {json.dumps({'type': 'message_stop'})}\n\n"
            finally:
                await session.close()

        if is_stream:
            return StreamingResponse(generate_stream(), media_type="text/event-stream")
        else:
            full_content = ""
            async for chunk in generate_stream():
                if chunk.startswith("event: content_block_delta"):
                    continue # Skip event lines in buffer mode
                if chunk.startswith("data: "):
                    try:
                        chunk_json = json.loads(chunk[6:])
                        if chunk_json.get("type") == "content_block_delta":
                            full_content += chunk_json["delta"]["text"]
                    except:
                        pass
                        
            return {
                "id": f"msg_{uuid.uuid4()}",
                "type": "message",
                "role": "assistant",
                "content": [{"type": "text", "text": full_content}],
                "model": "claude-3-5-sonnet-20241022",
                "stop_reason": "end_turn",
                "usage": {"input_tokens": 0, "output_tokens": 0}
            }
            
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": {"message": str(e)}})

@app.get("/v1/models")
async def get_models():
    return {
        "object": "list",
        "data": [
            {
                "id": "glm-5",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "z.ai"
            },
            {
                "id": "claude-3-5-sonnet-20241022",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "z.ai"
            }
        ]
    }
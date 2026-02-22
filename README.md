# Z.ai API Proxy

A high-performance, asynchronous FastAPI proxy server that transforms Z.ai's private web API into standard, fully-compatible OpenAI (`/v1/chat/completions`) and Anthropic (`/v1/messages`) endpoints.

## 🚀 Why this Proxy?

Z.ai provides a powerful chat interface, but utilizing their web endpoints in standard desktop AI clients (like XibeCode, Cursor, or standard SDKs) is blocked by robust security measures such as `426 Upgrade Required` versions and `403 Forbidden` HMAC-SHA256 signature verifications.

This proxy directly solves these issues by:

1. **Dynamic Signature Generation**: Reverse-engineers Z.ai's undocumented `x-signature` header requirements, recreating perfectly matched HMAC-SHA256 checksum algorithms for every outgoing request based on an exact salt.
2. **Device Fingerprint Spoofing**: Bypasses `426` out-of-date errors by constantly spoofing updated and expected client parameters.
3. **SSE Streaming Support**: Emulates OpenAI and Anthropic Server-Sent Events identically, meaning words type out in real-time in your client exactly as they do on the Z.ai website.
4. **Reasoning Stream Extraction**: Z.ai models provide native `<details type="reasoning">` thinking streams. This proxy correctly parses and streams these thought processes out so compatible clients render them seamlessly before the final response.

## 📦 Features

- **OpenAI Compatible Endpoint**: `/v1/chat/completions`
- **Anthropic Compatible Endpoint**: `/v1/messages`
- **Model Listing Endpoint**: `/v1/models` (Provides mock standard identifiers so clients don't fail)
- **Asynchronous I/O**: Built with FastAPI and `curl_cffi.AsyncSession` for non-blocking stream handling, ensuring high throughput.
- **Message History Tracking**: Converts standard multi-turn `messages` payloads into the continuous format expected by Z.ai's backend.
- **Cloudflare/Cookie Passthrough**: Utilizes your native browser cookie to successfully execute Cloudflare challenges.

## 🛠 Setup & Installation

### 1. Retrieve your Z.ai Credentials

To route traffic successfully, the proxy acts on behalf of your active Z.ai web session. You need to extract two values from your browser after logging into `chat.z.ai`:

- **`JWT_TOKEN`**: Found in your browser's local storage or application tab as the bearer authentication token.
- **`COOKIE`**: The full raw cookie string passed in the network request headers to `https://chat.z.ai/api/v2/chat/completions`.

Create a `.env` file in the root directory and add the credentials:

```env
JWT_TOKEN="eyJhbGciOi..."
COOKIE="__stripe_mid=..."
```

*(Note: These credentials represent your account. Do not share them or expose them publicly!)*

### 2. Deploy via Docker (Recommended for VPS)

The provided `Dockerfile` leverages a lightweight Python 3.11 environment.

```bash
# Build the Docker image
docker build -t zai-proxy .

# Run the container in the background, exposing port 8000
docker run -d -p 8000:8000 --env-file .env --name zai-proxy zai-proxy
```

### 3. Run Locally (Python Environment)

If you prefer running it directly on your host machine:

```bash
# Install dependencies
pip install -r requirements.txt

# Start the uvicorn server
uvicorn main:app --host 0.0.0.0 --port 8000
```

## 💻 Usage Examples

Once deployed, simply point your favorite AI code editor (Cursor, Cline, XibeCode) or script towards `http://<YOUR_IP_OR_LOCALHOST>:8000/v1` and use standard SDKs.

### Testing OpenAI Format (cURL)

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer mock-api-key" \
  -d '{
    "model": "glm-5",
    "stream": true,
    "messages": [
      {
        "role": "system",
        "content": "You are a helpful assistant."
      },
      {
        "role": "user",
        "content": "Count from 1 to 3."
      }
    ]
  }'
```

### Testing Anthropic Format (cURL)

```bash
curl -X POST http://localhost:8000/v1/messages \
  -H "Content-Type: application/json" \
  -d '{
    "model": "claude-3-5-sonnet",
    "stream": true,
    "messages": [
      {"role": "user", "content": "Hello!"}
    ]
  }'
```

## ⚠️ Notes & Limitations

- **Tool Calling**: The proxy parses standard `tools` and `tool_choice` arrays from incoming requests and passes them up to Z.ai. However, native JSON tool execution (actually returning a standard `tool_calls` object) is *experimental/unstable* as Z.ai's internal web SSE format expects different custom UI triggers. It's highly recommended to utilize a system-prompt (ReAct) wrapper utilizing standard string outputs when combining this proxy with tools.
- **Rate Limits**: The proxy is bound by whatever rate limits are applied to your specific Z.ai account tier.

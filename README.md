# Z.ai API Proxy

A high-performance, asynchronous FastAPI proxy server that transforms Z.ai's private web API into standard, fully-compatible OpenAI (`/v1/chat/completions`) and Anthropic (`/v1/messages`) endpoints.

## 🚀 Why this Proxy?

Z.ai provides a powerful chat interface, but utilizing their web endpoints in standard desktop AI clients (like XibeCode, Cursor, or standard SDKs) is blocked by robust security measures such as `426 Upgrade Required` versions and `403 Forbidden` HMAC-SHA256 signature verifications.

This proxy directly solves these issues by:

1. **Dynamic Signature Generation**: Reverse-engineers Z.ai's undocumented `x-signature` header requirements, recreating perfectly matched HMAC-SHA256 checksum algorithms for every outgoing request based on an exact salt.
2. **Device Fingerprint Spoofing**: Bypasses `426` out-of-date errors by constantly spoofing updated and expected client parameters.
3. **SSE Streaming Support**: Emulates OpenAI and Anthropic Server-Sent Events identically, meaning words type out in real-time in your client exactly as they do on the Z.ai website.
4. **Reasoning Stream Extraction**: Z.ai models provide native `<details type="reasoning">` thinking streams. This proxy correctly parses and streams these thought processes out so compatible clients render them seamlessly before the final response.

## ⚙️ How it Works

The proxy acts as a bridge between standard AI clients and Z.ai's web-based API. Here's a technical breakdown:

- **Request Transformation**: When you send a request to `/v1/chat/completions`, the proxy transforms the OpenAI-formatted payload into the Z.ai internal JSON format.
- **Signature Algorithm**: Z.ai requires a complex HMAC-SHA256 signature (`x-signature`). The proxy calculates this by:
    1. Generating a 5-minute windowed HMAC key using a fixed internal salt.
    2. Sorting and flattening key request parameters (timestamp, request ID, user ID).
    3. Hashing the flattened metadata along with the base64-encoded user message.
- **Session Impersonation**: Using `curl_cffi`, the proxy impersonates a real Chrome browser instance (TLS fingerprints, headers, etc.) to avoid detection by automated bot-protection systems.
- **Stream Buffering**: It maintains a persistent connection to Z.ai's SSE stream, re-mapping custom Z.ai events into standard `chat.completion.chunk` events.

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

#### Steps to get `JWT_TOKEN` and `COOKIE`

1. **Login**: Go to [chat.z.ai](https://chat.z.ai) and log in to your account.
2. **Open Developer Tools**: Press `F12` (or `Right Click > Inspect`) and go to the **Network** tab.
3. **Find a Chat Request**: Start a new chat or send a message. Look for a request named `completions` (or similar under `chat/completions`).
4. **Extract JWT**:
    - Click on the request.
    - Go to the **Headers** tab.
    - Look for `authorization: Bearer <YOUR_TOKEN>`.
    - Copy everything *after* `Bearer`. This is your `JWT_TOKEN`.
5. **Extract Cookie**:
    - In the same **Headers** tab, look for the `Cookie` header.
    - Copy the *entire* value string. This is your `COOKIE`.
6. **(Optional) Alternative JWT Location**:
    - Go to the **Application** tab (in DevTools).
    - Under **Storage**, click on **Local Storage** > `https://chat.z.ai`.
    - Look for a key like `zai-user-token` or similar (though the Network tab method is more reliable).

Create a `.env` file in the root directory and add the credentials:

```env
JWT_TOKEN="eyJhbGciOi..."
COOKIE="__stripe_mid=..."
```

*(Note: These credentials represent your account. Do not share them or expose them publicly!)*

### 2. Deploy on Vercel (Recommended for Serverless)

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/CloudCompile/z.ai-proxy)

1. **Fork / clone** this repository and import it in the [Vercel dashboard](https://vercel.com/new).
2. During import, add your environment variables:
   - `JWT_TOKEN` – your Z.ai JWT (see step 1 above)
   - `COOKIE` – your full Z.ai cookie string
3. Click **Deploy**. Vercel will detect the `vercel.json` configuration and deploy the FastAPI app automatically.

> **Note**: Long streaming responses may hit Vercel's function timeout (10 s on Hobby, 60 s on Pro). For heavy streaming usage, consider the Docker deployment or upgrading to a Pro plan and adding `"maxDuration": 60` to the function config in `vercel.json`.

### 3. Deploy via Docker (Recommended for VPS)

The provided `Dockerfile` leverages a lightweight Python 3.11 environment.

```bash
# Build the Docker image
docker build -t zai-proxy .

# Run the container in the background, exposing port 8000
docker run -d -p 8000:8000 --env-file .env --name zai-proxy zai-proxy
```

### 4. Run Locally (Python Environment)

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

## 📄 License

This project is licensed under the **MIT License**. See the `LICENSE` file for details (or just know it's open for use and modification).

## 🤝 Contributing

Contributions are welcome! If you find a bug or have a feature suggestion, please open an issue or submit a pull request. Make sure to follow the existing code style and provide clear descriptions of your changes.

---

*Disclaimer: This project is for educational and personal use only. Use at your own risk. Respect Z.ai's Terms of Service.*

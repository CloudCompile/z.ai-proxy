# What is This Project?

## Overview

**Z.ai API Proxy** is a FastAPI-based proxy server that acts as a bridge between standard AI clients and Z.ai's web-based chat API.

## The Problem It Solves

Z.ai provides a powerful AI chat interface through their website (chat.z.ai), but using their API directly from standard AI clients (like Cursor, XibeCode, or SDKs) is blocked by robust security measures:

- **426 Upgrade Required errors** - Server rejects outdated client versions
- **403 Forbidden errors** - HMAC-SHA256 signature verification fails for unauthorized clients

This proxy bypasses these restrictions and provides a clean, standard API interface.

## Key Features

### 🔄 Dual API Compatibility

- **OpenAI Format**: `/v1/chat/completions` endpoint
- **Anthropic Format**: `/v1/messages` endpoint
- Use any existing SDK or client that supports OpenAI or Anthropic APIs

### 🔐 Security Bypass

1. **Dynamic Signature Generation**: Reverse-engineers Z.ai's `x-signature` header by recreating the HMAC-SHA256 checksum algorithm
2. **Device Fingerprint Spoofing**: Bypasses version checks by spoofing up-to-date Chrome browser parameters
3. **Session Impersonation**: Uses `curl_cffi` to mimic real Chrome browser TLS fingerprints

### ⚡ Real-Time Streaming

- Full Server-Sent Events (SSE) support
- Token-by-token streaming response
- Reasoning stream extraction for `<details type="reasoning">` thinking blocks
- Works identically to OpenAI/Anthropic streaming APIs

## How It Works

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│   Your Client   │ ──── │   Z.ai Proxy    │ ──── │   Z.ai Server   │
│ (Cursor/Cline)  │      │   (This App)    │      │ (chat.z.ai)     │
└─────────────────┘      └─────────────────┘      └─────────────────┘
        │                        │                        │
   OpenAI/Anthropic        Transform request        Web API with
        format              + add signatures          security checks
                                                      + signatures
```

### Request Flow

1. You send a standard OpenAI/Anthropic formatted request to the proxy
2. The proxy:
   - Extracts your message content
   - Generates a valid HMAC-SHA256 signature based on timestamp, request ID, and user ID
   - Spoofs browser fingerprint parameters
   - Adds all required headers (including cookies and JWT)
3. The transformed request is sent to Z.ai's web API
4. The streaming response is converted back to standard OpenAI/Anthropic SSE format
5. Your client receives the response as if talking directly to OpenAI/Anthropic

## Technical Components

| Component | Purpose |
|-----------|---------|
| `main.py` | FastAPI application with all endpoints and signature logic |
| `Dockerfile` | Container for easy deployment |
| `requirements.txt` | Python dependencies (FastAPI, curl_cffi, etc.) |

## Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Beautiful landing page (HTML) |
| `/v1/chat/completions` | POST | OpenAI-compatible chat endpoint |
| `/v1/messages` | POST | Anthropic-compatible messages endpoint |
| `/v1/models` | GET | List available models |

## Available Models

- `glm-5` - Z.ai's primary model
- `claude-3-5-sonnet-20241022` - Anthropic model via Z.ai

## Setup Requirements

To use this proxy, you need:

1. **JWT_TOKEN** - Your authentication token from Z.ai website (found in browser DevTools > Network tab > Authorization header)
2. **COOKIE** - Your session cookie from Z.ai website (found in browser DevTools > Network tab > Cookie header)

These are stored in a `.env` file and the proxy uses them to authenticate requests on your behalf.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Create .env file with your credentials
echo 'JWT_TOKEN="your-jwt-token-here"' > .env
echo 'COOKIE="your-cookie-string-here"' >> .env

# Run the proxy
uvicorn main:app --host 0.0.0.0 --port 8000
```

Then configure your AI client to use `http://localhost:8000/v1` as the API endpoint.

## Use Cases

- **AI Code Editors**: Use Z.ai with Cursor, XibeCode, Cline, or any OpenAI-compatible editor
- **Scripting**: Integrate Z.ai into Python/Node/other scripts using standard SDKs
- **Testing**: Test AI functionality without using official API calls
- **Prototyping**: Quick integration without learning new API formats

## Security Note

⚠️ This proxy uses YOUR authentication credentials. Keep your `.env` file secure and never share your JWT token or cookies publicly.

---

*This project is for educational and personal use only. Use at your own risk and respect Z.ai's Terms of Service.*
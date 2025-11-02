
---

```markdown
# 🤖 Telex AI Agent — Django + Google Gemini

[![Made with Django](https://img.shields.io/badge/Made%20with-Django-092E20?style=for-the-badge&logo=django&logoColor=white)]
[![Powered by Google Gemini](https://img.shields.io/badge/Powered%20by-Gemini-4285F4?style=for-the-badge&logo=google&logoColor=white)]
[![Telex A2A Compatible](https://img.shields.io/badge/Telex-A2A%20Compatible-blueviolet?style=for-the-badge)]
[![License: MIT](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)]

A **Django-based Telex Agent** that implements the Agent-to-Agent (A2A) JSON-RPC protocol and uses **Google Gemini** for AI responses.  
This agent validates incoming Telex requests, forwards the user's text to Gemini (via an `Ai_Agent` wrapper), and returns a JSON-RPC response Telex expects.

---

## 🔎 Table of contents

- [A2A Overview](#a2a-overview)  
- [Features](#features)  
- [Project Structure](#project-structure)  
- [Requirements](#requirements)  
- [Configuration (.env)](#configuration-env)  
- [Local Development](#local-development)  
- [API Endpoints](#api-endpoints)  
- [JSON-RPC Examples](#json-rpc-examples)  
- [Testing](#testing)  
- [CI / GitHub Actions](#ci--github-actions)   
- [Troubleshooting & Debugging](#troubleshooting--debugging)  
- [Roadmap & Improvements](#roadmap--improvements)  
- [Contributing](#contributing)  
- [License](#license)

---

## A2A Overview

Telex expects your agent to expose two endpoints:

1. **GET `/.well-known/agent.json`** — Returns the Agent Card (metadata) so Telex can discover and contact your agent.  
2. **POST `/`** — Single unified JSON-RPC endpoint for all A2A calls (e.g., `message/send`, `task/subscribe`). Requests have `Content-Type: application/json`.

Your server will:
- Validate the JSON-RPC request structure.
- Route by `method` (e.g., `message/send`).
- Use `Ai_Agent.gemini_response(user_text)` to generate a reply.
- Return a JSON-RPC success or error payload.

---

## Features

- JSON-RPC A2A handling (`message/send`).
- Agent card at `/.well-known/agent.json`.
- Google Gemini integration via `Ai_Agent`.
- Clean JSON-RPC error responses with standard codes.
- Built on Django + Django REST Framework.
- `python-decouple` for environment-based configuration.

---

## Project structure (recommended)

```

telex_ai_agent/
├── ai/                        # app: ai/webhook & agent code
│   ├── views.py               # GetResponse and get_agent_info
│   ├── ai.py            # Ai_Agent wrapper for Gemini
│   └── utils.py               # helpers (error builders, validators)
├── ai_agent/
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── .env
├── manage.py
├── requirements.txt
├── Dockerfile
└── README.md

```

---

## Requirements

- Python 3.10+ (3.11 preferred)  
- Django 4.x  
- djangorestframework  
- google-genai (or `google` genai package; ensure compatibility with SDK version)  
- python-decouple  
- hashlib (stdlib)

Example `requirements.txt` snippet:
```

Django>=4.2
djangorestframework
python-decouple
google-genai   # or `google` depending on SDK package name
gunicorn

```

---

## Configuration (`.env`)

Place `.env` at the **project root** (same directory as `manage.py`):

```

SECRET_KEY=your_django_secret_key
DEBUG=True
BASE_URL= project live url
GEMINI_API_KEY=your_google_gemini_api_key

````

**Important:** Add `.env` to `.gitignore`. Do not commit secrets.

---

## Local development

1. Clone, create venv, activate:
```bash
git clone https://github.com/digitalboi0/AI_AGENT_CODEHELPER.git
cd ai-agent
python -m venv venv
source venv/bin/activate   # macOS/Linux
venv\Scripts\activate      # Windows
pip install -r requirements.txt
````

2. Create `.env` as above.

3. Run migrations (if you have DB models or want save data) :

```bash
python manage.py migrate
```

4. Run dev server:

```bash
python manage.py runserver 0.0.0.0:8000
```

5. Visit agent card URL:

```
http://127.0.0.1:8000/.well-known/agent.json
```

---

## API Endpoints

### GET `/.well-known/agent.json`

Returns agent metadata. Example response:

```json
{
  "name": "ai_codehelper",
  "description": "An AI agent to help with coding questions in Python, Django, and JavaScript.",
  "version": "1.0.0",
  "methods": ["message/send"],
  "endpoint": "https://your-domain.com/"
}
```

> Ensure `endpoint` is a public HTTPS URL in production.

---

### POST `/`  — JSON-RPC A2A endpoint

* Accepts JSON body described by Telex A2A spec.
* Must use `Content-Type: application/json`.
* Routes using `method` field (e.g., `"message/send"`).

---

## JSON-RPC Examples

### Request: `message/send`

```json
{
  "jsonrpc": "2.0",
  "method": "message/send",
  "id": 3,
  "params": {
    "message": {
      "role": "user",
      "parts": [
        { "type": "text", "text": "ping" }
      ]
    }
  }
}
```

### Success Response

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "result": {
    "role": "agent",
    "parts": [
      { "type": "text", "text": "pong" }
    ],
    "kind": "message",
    "message_id": "fbuvdhb4ke6vq8hbva9qh9ha"
  }
}
```

### Error Response (example)

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "error": {
    "code": -32600,
    "message": "Invalid Request"
  }
}
```

---

## Error codes used

| JSON-RPC code | Name                | When returned                                  |
| ------------: | ------------------- | ---------------------------------------------- |
|      `-32700` | Parse error         | Invalid JSON (request not parseable)           |
|      `-32600` | Invalid Request     | Missing `params` / invalid structure           |
|      `-32601` | Method not found    | Unknown method in `method` field               |
|      `-32602` | Invalid params      | Missing or wrong-typed params (e.g., no text)  |
|      `-32603` | Internal error      | AI/network/runtime error                       |
|      `-32000` | Server/AI init fail | Failure to initialize Ai_Agent (server config) |

> Implementation returns JSON-RPC error payloads with HTTP `200` for application-level errors, and appropriate HTTP codes (400/500) for parse/transport problems — adjust to your integration needs.

---

## Example view (how routing works)

```python
class GetResponse(APIView):
    def post(self, request, *args, **kwargs):
        body = request.data
        method = body.get("method")
        if method == "message/send":
            params = body.get("params", {})
            message = params.get("message", {})
            # find first text part and extract user_text...
            ai_agent = Ai_Agent()
            ai_text = ai_agent.gemini_response(user_text)
            return Response({
                "jsonrpc": "2.0",
                "id": body.get("id"),
                "result": {
                    "role": "agent",
                    "parts": [{"type": "text", "text": ai_text}],
                    "kind": "message",
                    "message_id": "<hash>"
                }
            })
        else:
            return Response({
                "jsonrpc": "2.0",
                "id": body.get("id"),
                "error": {"code": -32601, "message": "Method not found"}
            })
```

---

## Extracting Gemini text (SDK example)

If `resp` is the result of `client.models.generate_content(...)`:

```python

try:
    text = resp.candidates[0].content.parts[0].text
except (AttributeError, IndexError) as e:
    raise RuntimeError(f"Unexpected Gemini response shape: {e}")
```

Use this in `Ai_Agent.gemini_response` and return a plain string.

---

## Testing

### Quick curl test (valid):

```bash
curl -X POST http://127.0.0.1:8000/ \
 -H "Content-Type: application/json" \
 -d '{
   "jsonrpc":"2.0",
   "method":"message/send",
   "id":1,
   "params":{
     "message":{"parts":[{"type":"text","text":"How do I loop through a list in Python?"}]}
   }
 }'
```

### Test missing params (invalid):

```bash
curl -X POST http://127.0.0.1:8000/ -H "Content-Type: application/json" -d '{"jsonrpc":"2.0","id":1}'
```


## CI: GitHub Actions (basic test & lint)

`.github/workflows/ci.yml`:

```yaml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v4
        with: {python-version: 3.11}
      - name: Install deps
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
      - name: Run tests
        run: pytest -q
```

---

## Deployment suggestions

* Use Render, Railway, Fly.io, or a VPS with Gunicorn + Nginx.
* Ensure `BASE_URL` matches public HTTPS URL.
* Add `AGENT_PUBLIC_KEY` if Telex signs/encrypts messages (check Telex docs).
* Configure an application-level log sink (Sentry / LogDNA) for tracebacks.

---

## Troubleshooting & debugging

* If you get `AI AGENT is unreachable`:

  * Check `.env` `GEMINI_API_KEY` value and SDK init.
  * Run a quick shell test:

    ```bash
    python manage.py shell
    from ai.ai_agent import Ai_Agent
    a = Ai_Agent()      # see if raises
    print(a.gemini_response("hello"))
    ```
  * Add `logger.exception()` where exceptions are caught to see tracebacks in server logs.

* If `gemini_response` object shape differs, extract the text using the `gemini_response.candidates[0].content.parts[0].text` path, checking for `AttributeError` / `IndexError`.

---


## Contributing

Contributions welcome — open an issue or PR. Please follow these steps:

1. Fork the repo.
2. Create a feature branch: `git checkout -b feat/my-feature`.
3. Write tests.
4. Open a pull request.

Add a short description of your change and why it helps.

---

## Author

**Osaretin Festus** — AI & Backend Developer

---

## License

This project is released under the **MIT License**. See `LICENSE` for details.

```


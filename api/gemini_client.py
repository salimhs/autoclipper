import os
import json
import requests

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

SYSTEM = (
  "You evaluate Twitch stream moments. "
  "Return ONLY valid JSON with keys: "
  "clip_worthy (bool), score (0-100 int), title (string), tags (array of strings), reason (string)."
)

def evaluate_moment(context: dict) -> dict:
  key = os.getenv("GEMINI_API_KEY")
  if not key:
    raise RuntimeError("Missing GEMINI_API_KEY")

  url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={key}"

  prompt = f"{SYSTEM}\n\nContext:\n{json.dumps(context, ensure_ascii=False)}"

  payload = {
    "contents": [{"parts": [{"text": prompt}]}],
    "generationConfig": {
      "temperature": 0.4,
      "maxOutputTokens": 256
    }
  }

  r = requests.post(url, json=payload, timeout=30)
  r.raise_for_status()
  text = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()

  # Sometimes models wrap JSON in ```json ... ```
  if text.startswith("```"):
    text = text.split("```", 2)[1]
    text = text.replace("json", "", 1).strip()

  return json.loads(text)

import os
import httpx
import json
from typing import Any, Dict, List, Optional
from app.core.config import settings

class AIEngine:
    def __init__(self):
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")

    async def generate_text(self, provider: str, model: str, prompt: str, system_prompt: Optional[str] = None) -> str:
        if provider == "ollama":
            return await self._call_ollama(model, prompt, system_prompt)
        elif provider == "gemini":
            return await self._call_gemini(model, prompt, system_prompt)
        elif provider == "openai":
            return await self._call_openai(model, prompt, system_prompt)
        else:
            raise ValueError(f"Provider {provider} not supported")

    async def generate_structured_output(self, provider: str, model: str, prompt: str, schema: Dict[str, Any], system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        Calls the LLM and forces a structured JSON output based on the provided schema.
        """
        if provider == "gemini":
            return await self._call_gemini_structured(model, prompt, schema, system_prompt)
        elif provider == "ollama":
            return await self._call_ollama_structured(model, prompt, schema, system_prompt)
        else:
            # Fallback to text generation and manual parsing if structured output is not directly supported
            text = await self.generate_text(provider, model, prompt, system_prompt)
            try:
                # Basic attempt to find JSON in the response
                start = text.find("{")
                end = text.rfind("}") + 1
                if start != -1 and end != -1:
                    return json.loads(text[start:end])
                return json.loads(text)
            except Exception:
                return {"error": "Failed to parse JSON from LLM response", "raw": text}

    async def _call_ollama(self, model: str, prompt: str, system_prompt: Optional[str] = None) -> str:
        async with httpx.AsyncClient(timeout=60.0) as client:
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False
            }
            if system_prompt:
                payload["system"] = system_prompt
                
            response = await client.post(f"{self.ollama_base_url}/api/generate", json=payload)
            response.raise_for_status()
            return response.json().get("response", "")

    async def _call_gemini(self, model: str, prompt: str, system_prompt: Optional[str] = None) -> str:
        # Simplistic Gemini API call. In real scenario, would use google-generativeai or more robust REST call.
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.gemini_api_key}"
        async with httpx.AsyncClient(timeout=60.0) as client:
            contents = []
            if system_prompt:
                contents.append({"role": "user", "parts": [{"text": f"System: {system_prompt}"}]})
            contents.append({"role": "user", "parts": [{"text": prompt}]})
            
            payload = {"contents": contents}
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            return data['candidates'][0]['content']['parts'][0]['text']

    async def _call_gemini_structured(self, model: str, prompt: str, schema: Dict[str, Any], system_prompt: Optional[str] = None) -> Dict[str, Any]:
        # Using Gemini's responseMimeType: "application/json"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.gemini_api_key}"
        async with httpx.AsyncClient(timeout=60.0) as client:
            contents = []
            if system_prompt:
                contents.append({"role": "user", "parts": [{"text": f"System Instruction: {system_prompt}"}]})
            contents.append({"role": "user", "parts": [{"text": prompt + "\nReturn ONLY a JSON object matching this schema: " + json.dumps(schema)}]})
            
            payload = {
                "contents": contents,
                "generationConfig": {
                    "responseMimeType": "application/json"
                }
            }
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            text = data['candidates'][0]['content']['parts'][0]['text']
            return json.loads(text)

    async def _call_ollama_structured(self, model: str, prompt: str, schema: Dict[str, Any], system_prompt: Optional[str] = None) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=60.0) as client:
            payload = {
                "model": model,
                "prompt": prompt + "\nReturn ONLY a JSON object matching this schema: " + json.dumps(schema),
                "format": "json",
                "stream": False
            }
            if system_prompt:
                payload["system"] = system_prompt
                
            response = await client.post(f"{self.ollama_base_url}/api/generate", json=payload)
            response.raise_for_status()
            return json.loads(response.json().get("response", "{}"))

    async def _call_openai(self, model: str, prompt: str, system_prompt: Optional[str] = None) -> str:
        # Placeholder for OpenAI
        return "OpenAI integration pending"

ai_engine = AIEngine()

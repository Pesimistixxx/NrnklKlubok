from __future__ import annotations

import os
import sys

import httpx


def main() -> int:
    base_url = os.getenv("AGENTS_URL", "http://localhost:8010").rstrip("/")
    with httpx.Client(timeout=10.0) as client:
        health = client.get(f"{base_url}/health")
        print("health:", health.status_code, health.text)
        health.raise_for_status()

        modes = client.get(f"{base_url}/api/v1/agents/modes")
        print("modes:", modes.status_code, modes.text)
        modes.raise_for_status()

        response = client.post(
            f"{base_url}/api/v1/agents/run",
            json={
                "query": "Сформируй исследовательские гипотезы по технологиям переработки никеля",
                "mode": "hypothesis_mode",
                "user_role": "researcher",
                "limit": 5,
            },
        )
        print("run:", response.status_code)
        print(response.text)
        if response.status_code == 503:
            print("LLM is not configured; /run correctly returned 503.")
            return 0
        response.raise_for_status()

        payload = response.json()
        print("elapsed_ms:", payload.get("elapsed_ms"))
        print("summary:", payload.get("summary"))
        print("evidence:", len(payload.get("evidence") or []))
        print("issues:", len(payload.get("issues") or []))
        print("hypotheses:", len(payload.get("hypotheses") or []))
        print("recommendations:", len(payload.get("recommendations") or []))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

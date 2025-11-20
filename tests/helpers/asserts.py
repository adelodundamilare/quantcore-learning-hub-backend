from typing import Optional, Dict, Any
from fastapi.testclient import TestClient

def api_call(client: TestClient, method: str, path: str, headers: Optional[Dict[str, str]] = None, json: Optional[Dict[str, Any]] = None, expected_min: int = 200, expected_max: int = 300):
    response = client.request(method, path, headers=headers, json=json)
    ok = expected_min <= response.status_code < expected_max
    try:
        body = response.json()
    except Exception:
        body = response.text
    assert ok, f"{method} {path} => {response.status_code}, body={body}, json={json}"
    return response
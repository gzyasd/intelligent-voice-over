from __future__ import annotations

from urllib.parse import urlparse

import httpx

from ivo.adapters.http import ApiAdapterProfile


def unload_lm_studio_model_for_profile(
    profile: ApiAdapterProfile,
    *,
    client: httpx.Client | None = None,
) -> list[str]:
    """Unload LM Studio model instances referenced by an OpenAI-compatible profile."""
    model_id = profile.request_template.get("model")
    if not isinstance(model_id, str) or not model_id:
        return []
    base_url = _lm_studio_base_url(profile.url)
    if base_url is None:
        return []

    owns_client = client is None
    active_client = client or httpx.Client()
    try:
        response = active_client.get(f"{base_url}/api/v1/models", timeout=10)
        response.raise_for_status()
        loaded_instance_ids = _loaded_instance_ids(response.json(), model_id)
        unloaded: list[str] = []
        for instance_id in loaded_instance_ids:
            unload_response = active_client.post(
                f"{base_url}/api/v1/models/unload",
                json={"instance_id": instance_id},
                timeout=30,
            )
            unload_response.raise_for_status()
            unloaded.append(instance_id)
        return unloaded
    except httpx.HTTPError:
        return []
    finally:
        if owns_client:
            active_client.close()


def _lm_studio_base_url(url: str) -> str | None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return None
    if parsed.hostname not in {"127.0.0.1", "localhost"}:
        return None
    if not parsed.path.startswith("/v1/"):
        return None
    netloc = parsed.netloc
    return f"{parsed.scheme}://{netloc}"


def _loaded_instance_ids(payload: object, model_id: str) -> list[str]:
    if not isinstance(payload, dict):
        return []
    models = payload.get("models")
    if not isinstance(models, list):
        return []
    for model in models:
        if not isinstance(model, dict) or model.get("key") != model_id:
            continue
        raw_instances = model.get("loaded_instances")
        if not isinstance(raw_instances, list):
            return []
        instance_ids: list[str] = []
        for instance in raw_instances:
            if isinstance(instance, dict) and isinstance(instance.get("id"), str):
                instance_ids.append(instance["id"])
        return instance_ids
    return []

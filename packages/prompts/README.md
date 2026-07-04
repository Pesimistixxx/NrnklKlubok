# MKG Prompts (`mkg_prompts`)

Реестр промптов для пайплайна MKG — без RAG-обёртки, только **ingestion** и **extraction**.

## Структура каталога

```text
packages/prompts/
  catalog/
    _meta.json                 # алиасы моделей
    ingestion/
      chunk_filter.json        # ingestion.chunk_filter
    extraction/
      document_meta.json       # extraction.document_meta
      entities_facts.json
      economics.json
  src/mkg_prompts/
    registry.py                # PromptRegistry
    renderer.py
```

Каждый файл промпта:

```json
{
  "id": "ingestion.chunk_filter",
  "title": "…",
  "models": {
    "yandexgpt": {
      "system_prompt": "…",
      "user_prompt": "… {{text}}",
      "required_params": ["text"],
      "temperature": 0.0,
      "max_tokens": 8
    }
  }
}
```

## Использование

```python
from mkg_prompts import PromptRegistry

PromptRegistry.configure("./packages/prompts/catalog", model="yandexgpt-5.1")
prompt = PromptRegistry.instance().get(stage="ingestion", prompt_type="chunk_filter", text="…")
```

`PROMPTS_PATH` в `.env` → путь к каталогу `catalog/` (или legacy `prompts.json`).

## Модели

Алиасы в `_meta.json`: `yandexgpt-5.1` → `yandexgpt`.

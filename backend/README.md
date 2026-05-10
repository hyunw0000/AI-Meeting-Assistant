# Local LLM Setup

## 1. Install Ollama

https://ollama.com

## 2. Pull Qwen model
cmd에서 하면됨
```bash
ollama pull qwen2.5:1.5b
```

## 3. Run model
cmd에서
```bash
ollama run qwen2.5:1.5b
```

## 4. Run FastAPI
실행.
```bash
uvicorn main:app --reload
```
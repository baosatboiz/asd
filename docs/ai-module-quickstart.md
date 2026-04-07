# AI Module Quickstart

## 1. Start services

From project root:

```powershell
docker compose up --build ai-service api-gateway
```

If you want full system demo:

```powershell
docker compose up --build
```

## 2. Open browser demo page

- Gateway UI: http://localhost:8011/ai-assistant/
- Health check AI: http://localhost:8013/health

## 3. API examples

### Behavior analysis

```bash
curl -X POST http://localhost:8013/analyze-behavior \
  -H "Content-Type: application/json" \
  -d '{
    "clicks": 28,
    "add_to_cart": 6,
    "total_spend": 59,
    "session_duration": 1260
  }'
```

### RAG chatbot

```bash
curl -X POST http://localhost:8013/chat-tu-van \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Tôi muốn mua tiết kiệm thì nên chọn gì?",
    "behavior": {
      "clicks": 28,
      "add_to_cart": 6,
      "total_spend": 59,
      "session_duration": 1260
    },
    "top_k": 4
  }'
```

## 4. Rebuild demo data (mock + FAISS)

Run inside AI service folder:

```powershell
cd ai-service
python init_data.py
```

This regenerates:

- `knowledge_base/*.md`
- `data/mock_behavior_samples.json`
- `data/demo_predictions.json`
- `artifacts/faiss_index/*`

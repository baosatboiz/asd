from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from model_behavior import BehaviorInput, BehaviorModel
from rag_engine import RAGEngine


BASE_DIR = Path(__file__).resolve().parent
KNOWLEDGE_BASE_DIR = BASE_DIR / "knowledge_base"
ARTIFACTS_DIR = BASE_DIR / "artifacts"
DATA_DIR = BASE_DIR / "data"


KNOWLEDGE_FILES: Dict[str, str] = {
    "service_policy.md": """
# Chính Sách Dịch Vụ

## Giao Hàng
- Đơn hàng được xử lý sau khi thanh toán thành công.
- Thời gian giao hàng phụ thuộc vào khu vực và đơn vị vận chuyển.

## Đổi Trả
- Sản phẩm lỗi từ nhà cung cấp có thể được đổi trả theo quy trình hỗ trợ.
- Khách cần giữ hóa đơn và mã đơn hàng.

## Khuyến Mãi
- Mã giảm giá có thể thay đổi theo từng chiến dịch.
- Một số ưu đãi chỉ áp dụng cho khách hàng mới hoặc đơn hàng đạt điều kiện.
""".strip(),
    "faq.md": """
# FAQ E-commerce

## Tôi xem trạng thái đơn hàng ở đâu?
Bạn có thể theo dõi đơn hàng trong trang quản lý hoặc qua thông báo hệ thống.

## Có mã giảm giá không?
Mã giảm giá thường xuất hiện trong banner, email marketing hoặc mục khuyến mãi.

## Tôi muốn sản phẩm giá rẻ thì xem ở đâu?
Hãy ưu tiên mục giảm giá, combo tiết kiệm và các sản phẩm giá tốt.

## Có gợi ý sản phẩm cao cấp không?
Danh mục cao cấp thường tập trung vào chất lượng, thương hiệu và trải nghiệm sử dụng.
""".strip(),
    "shopping_tips.md": """
# Gợi Ý Mua Sắm

## Khách nhạy cảm về giá
- Ưu tiên sản phẩm giảm giá, combo tiết kiệm và mã khuyến mãi.
- Trình bày rõ lợi ích tài chính trước.

## Khách có xu hướng cao cấp
- Nhấn mạnh chất lượng, thương hiệu, độ bền và dịch vụ đi kèm.
- Gợi ý sản phẩm premium hoặc phiên bản nổi bật.

## Khách trung thành
- Cá nhân hóa theo lịch sử mua hàng.
- Ưu tiên ưu đãi dành cho khách quay lại hoặc thành viên.
""".strip(),
}


def ensure_directories() -> None:
    KNOWLEDGE_BASE_DIR.mkdir(parents=True, exist_ok=True)
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def seed_knowledge_base() -> None:
    ensure_directories()
    for filename, content in KNOWLEDGE_FILES.items():
        target_path = KNOWLEDGE_BASE_DIR / filename
        target_path.write_text(content + "\n", encoding="utf-8")


def seed_behavior_samples() -> list[dict[str, float | str]]:
    samples: list[dict[str, float | str]] = [
        {"name": "sample_explore", "clicks": 14, "add_to_cart": 1, "total_spend": 24, "session_duration": 840},
        {"name": "sample_budget", "clicks": 28, "add_to_cart": 6, "total_spend": 59, "session_duration": 1260},
        {"name": "sample_premium", "clicks": 9, "add_to_cart": 2, "total_spend": 980, "session_duration": 510},
        {"name": "sample_loyal", "clicks": 24, "add_to_cart": 7, "total_spend": 310, "session_duration": 1440},
    ]
    output_path = DATA_DIR / "mock_behavior_samples.json"
    output_path.write_text(json.dumps(samples, ensure_ascii=False, indent=2), encoding="utf-8")
    return samples


def seed_faiss_index() -> None:
    engine = RAGEngine(knowledge_base_dir=KNOWLEDGE_BASE_DIR, artifacts_dir=ARTIFACTS_DIR)
    engine.refresh()


def seed_preview_predictions() -> list[dict[str, object]]:
    behavior_model = BehaviorModel()
    demo_inputs = [
        BehaviorInput(clicks=14, add_to_cart=1, total_spend=24, session_duration=840),
        BehaviorInput(clicks=28, add_to_cart=6, total_spend=59, session_duration=1260),
        BehaviorInput(clicks=9, add_to_cart=2, total_spend=980, session_duration=510),
        BehaviorInput(clicks=24, add_to_cart=7, total_spend=310, session_duration=1440),
    ]
    results = [behavior_model.predict(sample) for sample in demo_inputs]
    preview_path = DATA_DIR / "demo_predictions.json"
    preview_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    return results


def main() -> None:
    seed_knowledge_base()
    seed_behavior_samples()
    seed_preview_predictions()
    seed_faiss_index()
    print("Demo data and FAISS index are ready in ai-service/.")


if __name__ == "__main__":
    main()
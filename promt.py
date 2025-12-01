from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import json

from openai import OpenAI


# =====================
# 1. SYSTEM PROMPT
# =====================

SYSTEM_PROMPT = """
Ты — модуль генерации рекламных креативов для ИИ-платформы GENAI-4.  
Твоя задача — создавать эффективные рекламные тексты для интернет-магазина электроники, адаптированные под разные каналы (Telegram, VK, Yandex Ads).  
Сосредоточься на конверсии (кликах и покупках). Не используй лишнего текста, только то, что помогает продавать.

=====================
ОБЩИЕ ПРАВИЛА
=====================
1. Пиши только на русском языке.
2. Формируй тексты современно, понятно, без канцелярита.
3. Не придумывай технических характеристик, которых нет во входных данных.
4. Подчеркивай выгоды товара, а не только параметры.
5. Учитывай тренды маркетинга:  
   - "минимализм" → краткость, сухая подача выгоды  
   - "FOMO" → ограниченность, «успей», «мало осталось»  
   - "честность" → без преувеличений  
   - "социальное доказательство" → популярность, отзывы  
   - "юмор" → легкий, не кринж  
6. Строго соблюдай требования канала (см. ниже).
7. Отвечай ТОЛЬКО JSON-структурой, без текста вне JSON.

=====================
ВХОДНЫЕ ДАННЫЕ
=====================
Ты получаешь JSON следующего вида:
- product:
    - name — название
    - category — категория товара
    - price — цена
    - margin — маржа
    - tags — теги
    - features — характеристики
- audience_profile:
    - age_range — возраст
    - interests — интересы
    - behavior — поведенческие особенности
- channel — целевой канал ("telegram", "vk", "yandex_ads")
- trends — активные маркетинговые тренды
- n_variants — сколько вариантов рекламы нужно сгенерировать

=====================
ШАБЛОНЫ ДЛЯ КАНАЛОВ
=====================

------ TELEGRAM ------
Короткий, эмоциональный формат.
Правила:
- Заголовок до ~50 символов.
- Текст 1–3 предложения.
- Можно использовать эмодзи, но ≤ 5 штук.
- Мгновенная выгода в первых словах.
- Допускаются эмоциональные формулировки.
- CTA: "Успеть взять сейчас", "Смотреть в каталоге", "Перейти к покупке".

Структура:
headline: цепляющий 3–7 слов.
text: короткое ясное описание + выгоды.
cta: прямой призыв.
notes: объяснение, почему креатив должен конвертировать.

------ VK ------
Более объемный текст: 2–5 предложений.
Правила:
- До 2 абзацев.
- Можно легкий сторителлинг или «представьте…».
- Желательно социальное доказательство (популярность, отзывы).
- CTA: "Заказать онлайн", "Узнать цену", "Смотреть характеристики".

Структура:
headline: до ~70 символов.
text: преимущества + мини-сценарий + доказательства.
cta: CTA под российский рынок.
notes: короткая причина эффективности.

------ YANDEX ADS ------
Строгий, информативный стиль.
Правила:
- Никаких эмодзи.
- Максимальная конкретика.
- Короткий заголовок: бренд/товар + выгода.
- 1–2 предложения без воды.
- Используй категории/ключевые слова (смартфон, наушники, доставка, скидка).
- CTA: "Купить онлайн", "Заказать с доставкой", "Смотреть в магазине".

Структура:
headline: максимально ёмкая фраза.
text: выгоды, быстрый смысл.
cta: прямой, нейтральный.
notes: причина высокой конверсии.

=====================
ФОРМАТ ВЫХОДА
=====================
Ты обязан вернуть строго JSON:

{
  "variants": [
    {
      "channel": "<канал>",
      "headline": "<заголовок>",
      "text": "<основной текст>",
      "cta": "<призыв к действию>",
      "notes": "<краткое объяснение логики>"
    }
  ]
}

Количество вариантов = n_variants из входных данных.

НЕ добавляй никаких комментариев вне JSON.
НЕ изменяй структуру.
"""


# ==========================
# 2. DATA-MODEL
# ==========================

@dataclass
class Product:
    name: str
    category: str
    price: Optional[float] = None
    margin: Optional[str] = None
    tags: Optional[List[str]] = None
    features: Optional[List[str]] = None


@dataclass
class AudienceProfile:
    age_range: str
    interests: List[str]
    behavior: List[str]


@dataclass
class GenerationRequest:
    product: Product
    audience_profile: AudienceProfile
    channel: str
    trends: List[str]
    n_variants: int = 1


@dataclass
class AdVariant:
    channel: str
    headline: str
    text: str
    cta: str
    notes: str


# ==========================
# 3. LLM CLIENT (исправлено здесь)
# ==========================

class LLMClient:
    """
    Обёртка над LLM. Сейчас — OpenAI, потом можно заменить на что угодно.
    """

    def __init__(self, api_key: str, model: str = "gpt-4.1-mini"):
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def generate_variants(self, payload: Dict[str, Any]) -> List[AdVariant]:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}
            ]
        )

        content = response.choices[0].message.content
        data = json.loads(content)

        variants_raw = data.get("variants", [])
        variants: List[AdVariant] = []
        for v in variants_raw:
            variants.append(
                AdVariant(
                    channel=v.get("channel", ""),
                    headline=v.get("headline", ""),
                    text=v.get("text", ""),
                    cta=v.get("cta", ""),
                    notes=v.get("notes", ""),
                )
            )
        return variants


# ==========================
# 4. BUILDERS
# ==========================

def build_payload_from_request(req: GenerationRequest) -> Dict[str, Any]:
    return {
        "product": {
            "name": req.product.name,
            "category": req.product.category,
            "price": req.product.price,
            "margin": req.product.margin,
            "tags": req.product.tags or [],
            "features": req.product.features or [],
        },
        "audience_profile": {
            "age_range": req.audience_profile.age_range,
            "interests": req.audience_profile.interests,
            "behavior": req.audience_profile.behavior,
        },
        "channel": req.channel,
        "trends": req.trends,
        "n_variants": req.n_variants,
    }


def build_request_from_input_json(input_json: Dict[str, Any]) -> GenerationRequest:
    p = input_json["product"]
    a = input_json["audience_profile"]

    product = Product(
        name=p["name"],
        category=p["category"],
        price=p.get("price"),
        margin=p.get("margin"),
        tags=p.get("tags", []),
        features=p.get("features", []),
    )

    audience = AudienceProfile(
        age_range=a["age_range"],
        interests=a.get("interests", []),
        behavior=a.get("behavior", []),
    )

    return GenerationRequest(
        product=product,
        audience_profile=audience,
        channel=input_json["channel"],
        trends=input_json.get("trends", []),
        n_variants=input_json.get("n_variants", 1),
    )


# ==========================
# 5. FORMATTERS
# ==========================

def format_variant_for_channel(variant: AdVariant) -> str:
    ch = variant.channel.lower()

    if ch == "telegram":
        return (
            f"Telegram\n\n"
            f"{variant.headline}\n"
            f"{variant.text}\n"
            f"👉 {variant.cta}\n"
        )
    elif ch == "vk":
        return (
            f"VK\n\n"
            f"{variant.headline}\n\n"
            f"{variant.text}\n\n"
            f"👉 {variant.cta}\n"
        )
    elif ch == "yandex_ads":
        return (
            f"Yandex Ads\n\n"
            f"{variant.headline}\n"
            f"{variant.text}\n"
            f"[CTA: {variant.cta}]\n"
        )
    else:
        return (
            f"{variant.channel}\n\n"
            f"{variant.headline}\n"
            f"{variant.text}\n"
            f"{variant.cta}\n"
        )


def format_all_variants_human_readable(variants: List[AdVariant]) -> List[str]:
    return [format_variant_for_channel(v) for v in variants]


# ==========================
# 6. FACADE
# ==========================

class AdGenerator:
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    def generate_from_json_dict(
        self,
        input_json: Dict[str, Any],
        return_human_texts: bool = True,
    ) -> Dict[str, Any]:

        req = build_request_from_input_json(input_json)
        payload = build_payload_from_request(req)

        variants = self.llm_client.generate_variants(payload)
        texts: List[str] = []
        if return_human_texts:
            texts = format_all_variants_human_readable(variants)

        variants_as_dicts = [
            {
                "channel": v.channel,
                "headline": v.headline,
                "text": v.text,
                "cta": v.cta,
                "notes": v.notes,
            }
            for v in variants
        ]

        return {
            "variants": variants_as_dicts,
            "texts": texts,
        }


# ==========================
# 7. MAIN
# ==========================

if __name__ == "__main__":
    JSON_FILE = "input/product_2.json"

    with open(JSON_FILE, "r", encoding="utf-8") as f:
        example_input = json.load(f)

    llm_client = LLMClient(api_key="YOUR_API_KEY_HERE")
    generator = AdGenerator(llm_client)

    result = generator.generate_from_json_dict(example_input, return_human_texts=True)

    print("=== ЧЕЛОВЕКОЧИТАЕМЫЕ ТЕКСТЫ ===")
    for t in result["texts"]:
        print(t)
        print("-" * 40)
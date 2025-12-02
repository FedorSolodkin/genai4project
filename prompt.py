from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import json

from openai import OpenAI
from main import evaluate_ad  # импортируем оценщик из main.py


# ==========================
# 1. SYSTEM PROMPT
# ==========================

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
# 2. DATA-MODEL (структуры данных)
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
    channel: str               # "telegram" | "vk" | "yandex_ads"
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
# 3. LLM CLIENT (отдельный слой)
# ==========================

class LLMClient:
    """
    Обёртка над LLM. Сейчас — OpenAI, потом можно заменить на что угодно.
    """

    def __init__(self, api_key: str, model: str = "gpt-4.1-mini"):
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def generate_variants(self, payload: Dict[str, Any]) -> List[AdVariant]:
        """
        Отправляем SYSTEM_PROMPT + payload (JSON) и получаем список AdVariant.
        """
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
# 4. BUILDERS (подготовка входных данных для LLM)
# ==========================

def build_payload_from_request(req: GenerationRequest) -> Dict[str, Any]:
    """
    Превращает наш internal-объект GenerationRequest в JSON для LLM.
    Это изолирует формат, можно легко менять.
    """
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
    """
    Строим GenerationRequest из "сырого" JSON, который к тебе прилетает
    от предыдущего модуля (каталог/анализ).
    Ожидается структура:
    {
      "product": {...},
      "audience_profile": {...},
      "channel": "...",
      "trends": [...],
      "n_variants": 1
    }
    """
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

    req = GenerationRequest(
        product=product,
        audience_profile=audience,
        channel=input_json["channel"],
        trends=input_json.get("trends", []),
        n_variants=input_json.get("n_variants", 1),
    )
    return req


# ==========================
# 5. FORMATTERS (человекочитаемый текст)
# ==========================

def format_variant_for_channel(variant: AdVariant) -> str:
    """
    Один форматтер — внутри уже разные ветки по каналам.
    """
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
    """
    На вход — список вариантов от модели,
    на выход — список готовых текстов для интерфейса/логирования.
    """
    return [format_variant_for_channel(v) for v in variants]


# ==========================
# 6. FACADE (одна точка входа для всего твоего модуля)
# ==========================

class AdGenerator:
    """
    Высокоуровневый класс: принимает сырые JSON-данные, возвращает:
    - структурированные варианты
    - и/или тексты объявлений
    """

    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    def generate_from_json_dict(
        self,
        input_json: Dict[str, Any],
        return_human_texts: bool = True,
    ) -> Dict[str, Any]:
        """
        Основной метод:
        - input_json: то, что тебе кидают другие части системы (каталог/симуляция).
        Возвращает dict:
            "variants": List[AdVariant как dict]
            "texts": List[str] (если return_human_texts=True)
        """
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
# 7. ОПТИМИЗАЦИЯ РЕКЛАМЫ ЧЕРЕЗ main.evaluate_ad
# ==========================

BEST_CLICK_THRESHOLD = 0.7   # порог "достаточно хорошей" вероятности клика
MAX_ITERS = 3                # максимум итераций улучшения


def generate_and_optimize_ad(
    generator: AdGenerator,
    input_json: Dict[str, Any],
    target_audience: str,
    best_click_threshold: float = BEST_CLICK_THRESHOLD,
    max_iters: int = MAX_ITERS,
) -> Dict[str, Any]:
    """
    1) Генерирует варианты рекламы через AdGenerator.
    2) Для каждого варианта вызывает main.evaluate_ad(ad_text, target_audience).
    3) Выбирает лучший вариант по click_probability.
    4) Если на какой-то итерации найден вариант с click_probability >= порога —
       сразу возвращаем его.

    Возвращает dict:
    {
      "ad_text": "...",
      "variant": {...},
      "scores": {"click_probability": ..., "purchase_probability": ...}
    }
    """
    best_variant: Optional[Dict[str, Any]] = None
    best_scores: Optional[Dict[str, float]] = None

    for _ in range(max_iters):
        result = generator.generate_from_json_dict(input_json, return_human_texts=False)
        variants = result["variants"]

        for v in variants:
            # Собираем текст объявления (заголовок + текст + CTA)
            ad_text = f"{v['headline']}\n{v['text']}\n{v['cta']}"

            # Оцениваем рекламу через main.evaluate_ad
            scores = evaluate_ad(ad_text, target_audience)
            click_p = scores.get("click_probability", 0.0)

            # Обновляем лучший, если нужно
            if best_scores is None or click_p > best_scores.get("click_probability", 0.0):
                best_scores = scores
                best_variant = v

            # Если вариант достаточно хорош — сразу возвращаем
            if click_p >= best_click_threshold:
                return {
                    "ad_text": ad_text,
                    "variant": v,
                    "scores": scores,
                }

    # Если порог так и не достигнут — возвращаем лучший из того, что было
    if best_variant is not None and best_scores is not None:
        ad_text = f"{best_variant['headline']}\n{best_variant['text']}\n{best_variant['cta']}"
        return {
            "ad_text": ad_text,
            "variant": best_variant,
            "scores": best_scores,
        }

    raise RuntimeError("Не удалось сгенерировать ни одного варианта рекламы")


# ==========================
# 8. MAIN (запуск для проверки)
# ==========================

if __name__ == "__main__":
    # 1. Путь к JSON с товаром
    JSON_FILE = "input/product_2.json"

    # 2. Загружаем JSON
    with open(JSON_FILE, "r", encoding="utf-8") as f:
        example_input = json.load(f)

    # 3. Инициализируем клиента LLM
    llm_client = LLMClient(api_key="YOUR_API_KEY_HERE")
    generator = AdGenerator(llm_client)

    # 4. Генерируем и оптимизируем рекламу для конкретной аудитории
    result = generate_and_optimize_ad(
        generator,
        example_input,
        target_audience="Low_income_pragmatic_youth",
    )

    print("=== ЛУЧШИЙ ВАРИАНТ ===")
    print(result["ad_text"])
    print("Оценка:", result["scores"])
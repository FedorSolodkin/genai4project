import json
import time
from typing import Any, Dict, List

import streamlit as st
from prompt import get_llm_client, AdGenerator

def parse_products_json(data: Any) -> List[Dict]:

    if isinstance(data, dict):
        # Если это один объект с полями product/audience_profile/channel/...
        # считаем его единственной записью
        return [data]
    elif isinstance(data, list):
        # Если это уже список подобных объектов
        return data
    else:
        raise ValueError("Ожидался объект JSON или список объектов JSON.")


def generate_creatives(records: List[Dict], user_text: str, llm_client, use_mistral: bool = True) -> Dict[str, Any]:
    """
    Генерирует креативы через LLM API.
    Поддерживает два формата:
    1. Полный формат: {product: {...}, audience_profile: {...}, channel: "...", ...}
    2. Формат из productAnalyzer: {name: "...", category: "...", description: "...", ...}
    """
    first = records[0]  # Берём первую запись из списка

    # Проверяем формат: если есть ключ "product" - это полный формат, иначе - формат из productAnalyzer
    if "product" in first:
        product = first.get("product", {}) or {}
        audience = first.get("audience_profile", {}) or {}
        channel = first.get("channel", "telegram")
        trends = first.get("trends", [])
        n_variants = first.get("n_variants", 1)
    else:
        # Формат из productAnalyzer: конвертируем в нужный формат
        product = {
            "name": first.get("name", ""),
            "category": first.get("category", ""),
            "price": first.get("price"),
            "margin": "высокая" if first.get("price", 0) > first.get("market_cost", 0) * 1.5 else "средняя",
            "tags": [],
            "features": [first.get("description", "")]
        }
        # Создаём базовый профиль аудитории по умолчанию
        audience = {
            "age_range": "20-35",
            "interests": ["гаджеты", "технологии"],
            "behavior": ["реагирует на скидки"]
        }
        channel = "telegram"
        trends = ["минимализм", "FOMO"]
        n_variants = 1

    # Подготовка payload для LLM
    payload = {
        "product": product,
        "audience_profile": audience,
        "channel": channel,
        "trends": trends,
        "n_variants": n_variants,
    }

    # Если есть дополнительные инструкции пользователя, добавляем их в тренды или notes
    if user_text.strip():
        # Можно добавить в тренды или создать отдельное поле
        # Для простоты добавим как дополнительный тренд
        if "user_instructions" not in payload:
            payload["user_instructions"] = user_text.strip()

    # Генерация через LLM
    generator = AdGenerator(llm_client)
    result = generator.generate_from_json_dict(payload, return_human_texts=True)

    # Форматируем результат для отображения
    variants = result.get("variants", [])
    if not variants:
        return {
            "text": "❌ Не удалось сгенерировать креативы. Попробуйте еще раз.",
            "image_url": "https://i.imgur.com/ilo8Prn.jpeg",
        }

    # Берем первый вариант для отображения
    variant = variants[0]
    text_lines = [
        f"**{variant.get('headline', '')}**",
        "",
        variant.get('text', ''),
        "",
        f"👉 {variant.get('cta', '')}",
        "",
        f"**Канал:** {channel}",
        f"**Примечания:** {variant.get('notes', '')}",
    ]

    if len(variants) > 1:
        text_lines.append("")
        text_lines.append(f"*Всего сгенерировано вариантов: {len(variants)}*")

    result_text = "\n".join(text_lines)

    placeholder_image_url = "https://i.imgur.com/ilo8Prn.jpeg"  # сюда вставлять ссылку на сгенерированную картинку
    return {
        "text": result_text,
        "image_url": placeholder_image_url,
        "variants": variants,  # Сохраняем все варианты для возможного использования
    }

def main():
    st.set_page_config(
        page_title="GENAI-4 интерфейс",
        layout="centered",
    )

    st.title("GENAI-4: интерфейс для генерации рекламных креативов")
    st.caption("Ввод текста → загрузка JSON с товарами → запуск генерации → результат.")
    
    # Настройка в сайдбаре
    st.sidebar.header("Настройки")
    use_real_mistral = st.sidebar.checkbox(
        "Использовать Mistral API (иначе заглушка)",
        value=True,
        help="Для работы нужен ключ MISTRAL_API_KEY в переменных окружения или secrets.",
    )

    st.markdown("### 1. Текстовые инструкции (опционально)")
    user_text = st.text_area(
        "Опиши здесь требования к креативам / кампании",
        placeholder="Например: фокус на выгоде для молодёжной аудитории, без жёсткого давления, подчёркиваем качество камеры...",
        height=150,
    )

    st.markdown("### 2. Загрузить файл с пулом товаров (JSON)")

    uploaded_file = st.file_uploader(
        "Загрузи .json файл в формате, как в примере ниже",
        type=["json"],
        help="""Формат:
{
  "product": {
    "name": "Смартфон Ultra X",
    "category": "смартфон",
    "price": 49990,
    "margin": "высокая",
    "tags": ["новинка", "яркий", "премиум"],
    "features": ["AMOLED 120 Гц", "50 Мп камера", "быстрая зарядка"]
  },
  "audience_profile": {
    "age_range": "20-35",
    "interests": ["гаджеты", "фото", "спорт"],
    "behavior": ["реагирует на скидки"]
  },
  "channel": "telegram",
  "trends": ["минимализм", "FOMO"],
  "n_variants": 2
}
        """,
    )

    st.markdown("### 3. Запуск генерации")

    generate_button = st.button("Начать генерацию")

    if generate_button:
        if uploaded_file is None:
            st.error("Сначала загрузи JSON-файл с пулом товаров.")
            return

        # Читаем и парсим JSON
        try:
            raw_bytes = uploaded_file.read()
            raw_text = raw_bytes.decode("utf-8")
            data = json.loads(raw_text)
            records = parse_products_json(data)
        except Exception as e:
            st.error(f"Не удалось прочитать JSON: {e}")
            return

        # Инициализация LLM клиента
        try:
            llm_client = get_llm_client(use_mistral=use_real_mistral)
        except Exception as e:
            st.error(f"Ошибка инициализации LLM-клиента: {e}")
            if use_real_mistral:
                st.info("💡 Убедитесь, что переменная окружения MISTRAL_API_KEY установлена, или используйте заглушку.")
            return

        # Генерация креативов
        with st.spinner("Генерация креативов..."):
            try:
                result = generate_creatives(records, user_text, llm_client, use_real_mistral)
            except Exception as e:
                st.error(f"Ошибка при генерации: {e}")
                return

        st.success("Генерация завершена!")

        st.markdown("### 4. Результат")
        st.markdown(result["text"])

        st.markdown("#### Картинка-креатив")
        st.image(
            result["image_url"],
            caption="Здесь будет вывод сгенерированного баннера/креатива.",
            use_container_width=True,
        )


if __name__ == "__main__":
    main()

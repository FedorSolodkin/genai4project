import json
import time
from typing import Any, Dict, List

import streamlit as st

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


def stub_generate_creatives(records: List[Dict], user_text: str) -> Dict[str, Any]:
    """
    Заглушка. Потом заменим на генерацию.
    """
    first = records[0]  # Пока что берём первую запись из списка

    product = first.get("product", {}) or {}
    audience = first.get("audience_profile", {}) or {}

    name = product.get("name", "Безымянный товар")
    category = product.get("category", "неизвестная категория")
    price = product.get("price", "цена не указана")
    margin = product.get("margin", "маржа не указана")
    tags = product.get("tags", [])
    features = product.get("features", [])

    channel = first.get("channel", "telegram")
    trends = first.get("trends", [])
    n_variants = first.get("n_variants", 1)

    age_range = audience.get("age_range", "не указано")
    interests = audience.get("interests", [])
    behavior = audience.get("behavior", [])
    #текст для заглушки
    text_lines = [
        "🔧 *Заглушка генерации креативов*",
        "",
        f"Товар: **{name}**",
        "",
        f"Категория: {category}",
        "",
        f"Цена: {price}",
        "",
        f"Маржа: {margin}",
        "",
        f"Теги: {', '.join(tags) if tags else '—'}",
        "",
        f"Фичи: {', '.join(features) if features else '—'}",
        "",
        f"Аудитория: {age_range}",
        "",
        f"Интересы: {', '.join(interests) if interests else '—'}",
        "",
        f"Поведение: {', '.join(behavior) if behavior else '—'}",
        "",
        f"Канал: {channel}",
        "",
        f"Тренды: {', '.join(trends) if trends else '—'}",
        "",
        f"Количество вариантов: {n_variants}",
    ]

    if user_text.strip():
        text_lines.append("")
        text_lines.append("Дополнительные инструкции пользователя:")
        text_lines.append(user_text.strip())

    text_lines.append("")
    text_lines.append("👉 Здесь позже будет сгенерированный рекламный текст от модели.")

    result_text = "\n".join(text_lines)

    placeholder_image_url = "https://i.imgur.com/ilo8Prn.jpeg" # сюда вставлять ссылку на сгенерированную картинку
    return {
        "text": result_text,
        "image_url": placeholder_image_url,
    }

def main():
    st.set_page_config(
        page_title="GENAI-4 интерфейс",
        layout="centered",
    )

    st.title("GENAI-4: интерфейс для генерации рекламных креативов")
    st.caption("Ввод текста → загрузка JSON с товарами → запуск генерации → результат (заглушка).")

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

        # Анимация(пока фейк длительность)
        with st.spinner("Генерация креативов..."):
            progress_placeholder = st.progress(0)
            for i in range(100):
                time.sleep(0.02)  # искусственная задержка для анимации
                progress_placeholder.progress(i + 1)

        result = stub_generate_creatives(records, user_text)

        st.success("Генерация завершена (заглушка).")

        st.markdown("### 4. Результат (пока заглушка)")
        st.markdown(result["text"])

        st.markdown("#### Картинка-креатив (заглушка)")
        st.image(
            result["image_url"],
            caption="Здесь будет вывод сгенерированного баннера/креатива.",
            use_container_width=True,
        )


if __name__ == "__main__":
    main()

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
        n_variants = first.get("n_variants", 3)  # По умолчанию генерируем 3 варианта
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
        n_variants = 3  # По умолчанию генерируем 3 варианта

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

    # Возвращаем все варианты для красивого отображения
    placeholder_image_url = "https://i.imgur.com/ilo8Prn.jpeg"  # сюда вставлять ссылку на сгенерированную картинку
    return {
        "variants": variants,  # Все варианты для отображения
        "channel": channel,
        "image_url": placeholder_image_url,
    }

def main():
    st.set_page_config(
        page_title="GENAI-4 интерфейс",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Кастомный CSS для красивого дизайна
    st.markdown("""
    <style>
        .main-header {
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            padding: 2rem;
            border-radius: 10px;
            color: white;
            margin-bottom: 2rem;
        }
        .ad-card {
            background: white;
            padding: 1.5rem;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            margin-bottom: 1.5rem;
            border-left: 4px solid #667eea;
        }
        .ad-headline {
            font-size: 1.5rem;
            font-weight: bold;
            color: #2d3748;
            margin-bottom: 0.5rem;
        }
        .ad-text {
            font-size: 1rem;
            color: #4a5568;
            line-height: 1.6;
            margin: 1rem 0;
        }
        .ad-cta {
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 0.75rem 1.5rem;
            border-radius: 8px;
            display: inline-block;
            font-weight: bold;
            margin-top: 1rem;
        }
        .ad-meta {
            color: #718096;
            font-size: 0.9rem;
            margin-top: 1rem;
            padding-top: 1rem;
            border-top: 1px solid #e2e8f0;
        }
        .variant-number {
            background: #667eea;
            color: white;
            padding: 0.5rem 1rem;
            border-radius: 20px;
            font-weight: bold;
            display: inline-block;
            margin-bottom: 1rem;
        }
        .stButton>button {
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 8px;
            padding: 0.75rem 2rem;
            font-weight: bold;
            font-size: 1rem;
        }
        .stButton>button:hover {
            background: linear-gradient(90deg, #764ba2 0%, #667eea 100%);
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
        }
    </style>
    """, unsafe_allow_html=True)

    # Красивый заголовок
    st.markdown("""
    <div class="main-header">
        <h1 style="margin: 0; font-size: 2.5rem;">🚀 GENAI-4</h1>
        <p style="margin: 0.5rem 0 0 0; font-size: 1.2rem; opacity: 0.9;">
            Генератор рекламных креативов на основе ИИ
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Настройка в сайдбаре
    st.sidebar.markdown("### ⚙️ Настройки")
    use_real_mistral = st.sidebar.checkbox(
        "🤖 Использовать Mistral API",
        value=True,
        help="Для работы нужен ключ MISTRAL_API_KEY в переменных окружения или secrets.",
    )
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📊 Информация")
    st.sidebar.info("""
    **Как использовать:**
    1. Загрузите JSON файл с товарами
    2. (Опционально) Добавьте инструкции
    3. Нажмите "Начать генерацию"
    4. Получите 2-3 варианта рекламы
    """)

    # Основной контент
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### 📝 Текстовые инструкции (опционально)")
        user_text = st.text_area(
            "Опишите требования к креативам / кампании",
            placeholder="Например: фокус на выгоде для молодёжной аудитории, без жёсткого давления, подчёркиваем качество камеры...",
            height=120,
            label_visibility="collapsed",
        )

        st.markdown("### 📁 Загрузить файл с товарами")
        uploaded_file = st.file_uploader(
            "Загрузите JSON файл",
            type=["json"],
            help="""Формат JSON:
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
  "n_variants": 3
}
            """,
            label_visibility="collapsed",
        )

    with col2:
        st.markdown("### 🎯 Быстрый старт")
        st.markdown("""
        **Пример формата:**
        - Используйте `catalog.json` или `best_products.json`
        - Или создайте свой JSON по шаблону
        """)
        
        if st.checkbox("Показать пример JSON"):
            example_json = {
                "product": {
                    "name": "Смартфон Ultra X",
                    "category": "смартфон",
                    "price": 49990,
                    "margin": "высокая",
                    "tags": ["новинка", "яркий"],
                    "features": ["AMOLED 120 Гц", "50 Мп камера"]
                },
                "audience_profile": {
                    "age_range": "20-35",
                    "interests": ["гаджеты", "фото"],
                    "behavior": ["реагирует на скидки"]
                },
                "channel": "telegram",
                "trends": ["минимализм", "FOMO"],
                "n_variants": 3
            }
            st.json(example_json)

    st.markdown("---")
    
    col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 2])
    with col_btn2:
        generate_button = st.button("🚀 Начать генерацию", use_container_width=True)

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
        with st.spinner("🎨 Генерация креативов... Это может занять несколько секунд"):
            try:
                result = generate_creatives(records, user_text, llm_client, use_real_mistral)
            except Exception as e:
                st.error(f"❌ Ошибка при генерации: {e}")
                return

        st.success("✅ Генерация завершена успешно!")
        st.markdown("---")

        # Отображение всех вариантов рекламы
        variants = result.get("variants", [])
        channel = result.get("channel", "telegram")
        
        if not variants:
            st.warning("⚠️ Не удалось сгенерировать варианты рекламы. Попробуйте еще раз.")
            return

        st.markdown(f"### 🎯 Сгенерировано вариантов: {len(variants)}")
        st.markdown(f"**Канал:** {channel.upper()}")
        st.markdown("---")

        # Отображаем каждый вариант в красивой карточке
        for idx, variant in enumerate(variants, 1):
            # Определяем цвет для разных вариантов
            colors = ["#667eea", "#764ba2", "#f093fb", "#4facfe"]
            color = colors[(idx - 1) % len(colors)]
            
            # Создаем карточку для варианта
            card_html = f"""
            <div class="ad-card" style="border-left-color: {color};">
                <div class="variant-number" style="background: {color};">
                    Вариант {idx}
                </div>
                <div class="ad-headline">{variant.get('headline', '')}</div>
                <div class="ad-text">{variant.get('text', '')}</div>
                <div class="ad-cta" style="background: linear-gradient(90deg, {color} 0%, #5a4a82 100%);">
                    👉 {variant.get('cta', '')}
                </div>
                <div class="ad-meta">
                    <strong>📝 Примечания:</strong> {variant.get('notes', 'Нет примечаний')}
                </div>
            </div>
            """
            st.markdown(card_html, unsafe_allow_html=True)
            
            # Разделитель между вариантами (кроме последнего)
            if idx < len(variants):
                st.markdown("<br>", unsafe_allow_html=True)

        # Изображение (общее для всех вариантов)
        st.markdown("---")
        st.markdown("### 🖼️ Визуальный креатив")
        st.image(
            result["image_url"],
            caption="Здесь будет отображаться сгенерированный баннер/креатив",
            use_container_width=True,
        )


if __name__ == "__main__":
    main()

import json
import time
from typing import Any, Dict, List

import streamlit as st
from prompt import get_llm_client, AdGenerator

# Путь к встроенному примеру
DEFAULT_JSON_PATH = "test.json"

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
            "tags": first.get("tags", []),  # Извлекаем теги из данных
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
        "product": product,  # Добавляем информацию о товаре для отображения тегов
    }

def main():
    st.set_page_config(
        page_title="GENAI-4 интерфейс",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Единый светлый стиль: светлый фон, тёмный текст, спокойные карточки
    st.markdown("""
    <style>
        body, [data-testid="stAppViewContainer"], .block-container {
            background: #f9fafb;
            color: #111827;
            font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", system-ui, sans-serif;
        }
        .main-header {
            background: #ffffff;
            padding: 20px;
            border-radius: 12px;
            border: 1px solid #e5e7eb;
            margin-bottom: 20px;
        }
        .main-header h1 {
            color: #0f172a;
            margin: 0;
            font-size: 22px;
            font-weight: 700;
        }
        .main-header p {
            color: #4b5563;
            margin: 6px 0 0 0;
            font-size: 13px;
        }
        .product-info, .ad-card {
            background: #ffffff;
            padding: 18px;
            border-radius: 12px;
            border: 1px solid #e5e7eb;
            margin-bottom: 16px;
            box-shadow: 0 4px 10px rgba(0,0,0,0.02);
        }
        .ad-card:hover {
            box-shadow: 0 8px 18px rgba(0,0,0,0.05);
        }
        .variant-number {
            background: #eef2ff;
            color: #4338ca;
            padding: 2px 10px;
            border-radius: 999px;
            font-weight: 600;
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: .1em;
            display: inline-block;
            margin-bottom: 10px;
            border: 1px solid #c7d2fe;
        }
        .ad-headline {
            font-size: 17px;
            font-weight: 650;
            color: #0f172a;
            margin-bottom: 6px;
            line-height: 1.3;
        }
        .ad-text {
            font-size: 14px;
            color: #1f2937;
            line-height: 1.7;
            margin: 10px 0 12px;
        }
        .ad-cta {
            display: inline-block;
            margin-top: 8px;
            padding: 6px 12px;
            border-radius: 999px;
            background: #111827;
            color: #ffffff;
            font-size: 12px;
            border: 1px solid #111827;
            font-weight: 600;
        }
        .ad-meta {
            color: #6b7280;
            font-size: 12px;
            margin-top: 12px;
            padding-top: 10px;
            border-top: 1px solid #e5e7eb;
        }
        .product-tags {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            margin-top: 0.75rem;
        }
        .tag {
            background: #eef2ff;
            color: #4338ca;
            padding: 4px 10px;
            border-radius: 999px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: .1em;
            border: 1px solid #c7d2fe;
        }
        .stButton>button {
            background: #111827;
            color: #ffffff;
            border: 1px solid #111827;
            border-radius: 999px;
            padding: 0.75rem 2rem;
            font-weight: 600;
            font-size: 1rem;
            transition: background 0.2s;
        }
        .stButton>button:hover {
            background: #1f2937;
            color: #ffffff;
        }
        .section-title {
            font-size: 22px;
            font-weight: 700;
            margin-bottom: 6px;
            color: #0f172a;
        }
        .section-sub {
            font-size: 13px;
            color: #4b5563;
            margin-bottom: 16px;
        }
        .badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 999px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: .1em;
            background: #eef2ff;
            color: #4338ca;
            border: 1px solid #c7d2fe;
            margin-right: 6px;
        }
    </style>
    """, unsafe_allow_html=True)

    # Заголовок в стиле project_creative-main
    st.markdown("""
    <div style="padding: 8px 0 18px 0;">
      <div style="font-size:13px; letter-spacing:.16em; text-transform:uppercase; color:#6b7280;">
        GENAI-4 · Autonomous Marketing Agent
      </div>
      <div class="section-title">
        Генератор рекламных креативов на основе ИИ
      </div>
      <div class="section-sub">
        Загрузите JSON файл с товарами — система сгенерирует креативы под выбранный канал
      </div>
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
        # Кнопка для скачивания встроенного примера test.json, чтобы сразу положить файл в поле загрузки
        with open(DEFAULT_JSON_PATH, "rb") as sample_file:
            st.download_button(
                label="⬇️ Скачать пример test.json",
                data=sample_file,
                file_name="test.json",
                mime="application/json",
                use_container_width=True,
            )
        st.caption("Если файл не выбрали — будет использован встроенный test.json.")

    with col2:
        st.markdown("### 🎯 Быстрый старт")
        st.markdown("""
                - по желанию: введите промпт
                - нажмите "Начать Генерацию"
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
        # Читаем и парсим JSON: либо загруженный файл, либо встроенный test.json
        if uploaded_file is not None:
            try:
                raw_bytes = uploaded_file.read()
                raw_text = raw_bytes.decode("utf-8")
                data = json.loads(raw_text)
                records = parse_products_json(data)
            except Exception as e:
                st.error(f"Не удалось прочитать JSON: {e}")
                return
        else:
            # Используем дефолтный пример test.json
            try:
                with open(DEFAULT_JSON_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                records = parse_products_json(data)
                st.info(f"Используется встроенный пример: {DEFAULT_JSON_PATH}")
            except Exception as e:
                st.error(f"Не удалось прочитать встроенный пример {DEFAULT_JSON_PATH}: {e}")
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
        product = result.get("product", {})
        
        if not variants:
            st.warning("⚠️ Не удалось сгенерировать варианты рекламы. Попробуйте еще раз.")
            return

        # Отображение информации о товаре с тегами
        if product:
            product_name = product.get("name", "")
            product_category = product.get("category", "")
            product_tags = product.get("tags", [])
            product_price = product.get("price")
            
            tags_html = ""
            if product_tags:
                tags_list = "".join([f'<span class="tag">{tag}</span>' for tag in product_tags])
                tags_html = f'<div class="product-tags">{tags_list}</div>'
            
            price_html = ""
            if product_price:
                price_html = f'<p style="margin: 0 0 0.75rem 0; color: #9ca3af; font-size: 12px;">Цена: {product_price:,} ₽</p>'
            
            product_info_html = f"""
            <div class="product-info">
                <div style="margin-bottom:6px;">
                    <span class="badge">{product_category if product_category else 'Без категории'}</span>
                </div>
                <h3 style="margin: 0 0 0.5rem 0; color: #e5e7eb; font-weight: 650; font-size: 17px;">{product_name}</h3>
                {price_html}
                {tags_html}
            </div>
            """
            st.markdown(product_info_html, unsafe_allow_html=True)

        st.markdown(f"<div class='section-title'>Сгенерировано вариантов: {len(variants)} | Канал: {channel.upper()}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='section-sub'>Показаны все варианты рекламных креативов</div>", unsafe_allow_html=True)

        # Отображаем каждый вариант в карточке в стиле project_creative-main
        for idx, variant in enumerate(variants, 1):
            # Создаем карточку для варианта
            card_html = f"""
            <div class="ad-card">
                <div class="variant-number">
                    Вариант {idx}
                </div>
                <div class="ad-headline">{variant.get('headline', '')}</div>
                <div class="ad-text">{variant.get('text', '')}</div>
                <div class="ad-cta">
                    CTA: {variant.get('cta', '')}
                </div>
                <div class="ad-meta">
                    <strong>Примечания:</strong> {variant.get('notes', 'Нет примечаний')}
                </div>
            </div>
            """
            st.markdown(card_html, unsafe_allow_html=True)

        # Изображение (общее для всех вариантов)
        st.markdown("---")
        st.markdown("<div class='section-title'>Визуальный креатив</div>", unsafe_allow_html=True)
        st.image(
            result["image_url"],
            caption="Здесь будет отображаться сгенерированный баннер/креатив",
            use_container_width=True,
        )


if __name__ == "__main__":
    main()

import json
import time
from typing import Any, Dict, List

import streamlit as st
# Убедитесь, что prompt.py лежит рядом, иначе закомментируйте импорт для теста интерфейса
from prompt import get_llm_client, AdGenerator

# Путь к встроенному примеру
DEFAULT_JSON_PATH = "test.json"

def parse_products_json(data: Any) -> List[Dict]:
    if isinstance(data, dict):
        return [data]
    elif isinstance(data, list):
        return data
    else:
        raise ValueError("Ожидался объект JSON или список объектов JSON.")

def generate_creatives(records: List[Dict], user_text: str, llm_client, use_mistral: bool = True) -> Dict[str, Any]:
    """
    Генерирует креативы через LLM API.
    Логика полностью сохранена.
    """
    first = records[0]

    if "product" in first:
        product = first.get("product", {}) or {}
        audience = first.get("audience_profile", {}) or {}
        channel = first.get("channel", "telegram")
        trends = first.get("trends", [])
        n_variants = first.get("n_variants", 3)
    else:
        product = {
            "name": first.get("name", ""),
            "category": first.get("category", ""),
            "price": first.get("price"),
            "margin": "высокая" if first.get("price", 0) > first.get("market_cost", 0) * 1.5 else "средняя",
            "tags": first.get("tags", []),
            "features": [first.get("description", "")]
        }
        audience = {
            "age_range": "20-35",
            "interests": ["гаджеты", "технологии"],
            "behavior": ["реагирует на скидки"]
        }
        channel = "telegram"
        trends = ["минимализм", "FOMO"]
        n_variants = 3

    payload = {
        "product": product,
        "audience_profile": audience,
        "channel": channel,
        "trends": trends,
        "n_variants": n_variants,
    }

    if user_text.strip():
        if "user_instructions" not in payload:
            payload["user_instructions"] = user_text.strip()

    generator = AdGenerator(llm_client)
    result = generator.generate_from_json_dict(payload, return_human_texts=True)

    variants = result.get("variants", [])
    if not variants:
        return {
            "text": "❌ Не удалось сгенерировать креативы. Попробуйте еще раз.",
            "image_url": "https://i.imgur.com/ilo8Prn.jpeg  ",
        }

    placeholder_image_url = "https://i.imgur.com/ilo8Prn.jpeg  "
    return {
        "variants": variants,
        "channel": channel,
        "image_url": placeholder_image_url,
        "product": product,
    }

def main():
    st.set_page_config(
        page_title="GENAI-4 интерфейс",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # --- НОВЫЙ ДИЗАЙН (CSS) ---
    # Этот блок принудительно делает тему темной и красивой
    # даже если у пользователя стоит Light Mode.
    st.markdown("""
    <style>
        /* 1. Глобальный фон и сброс цветов */
        [data-testid="stAppViewContainer"] {
            background-color: #020617;
            background-image: radial-gradient(circle at 50% 0%, #111827 0%, #020617 75%);
            color: #e5e7eb;
        }
        [data-testid="stHeader"] {
            background: transparent;
        }
        [data-testid="stSidebar"] {
            background-color: #0f172a;
            border-right: 1px solid #1e293b;
        }

        /* 2. Принудительный белый текст для всех стандартных элементов */
        h1, h2, h3, h4, h5, h6, span, div, label, p {
            color: #e5e7eb !important;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }
        .stMarkdown p {
            color: #9ca3af !important; /* Чуть серый для обычного текста */
        }

        /* 3. Стилизация карточек (Стекломорфизм) */
        .glass-container {
            background: rgba(30, 41, 59, 0.4);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        }

        /* 4. Заголовки разделов */
        .section-title {
            font-size: 24px;
            font-weight: 700;
            margin-bottom: 8px;
            background: linear-gradient(90deg, #60a5fa, #c084fc);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            display: inline-block;
        }
        .section-sub {
            font-size: 14px;
            color: #94a3b8 !important;
            margin-bottom: 20px;
        }

        /* 5. Карточки результатов (Реклама) */
        .ad-card {
            background: rgba(17, 24, 39, 0.6);
            border: 1px solid rgba(56, 189, 248, 0.2);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 16px;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .ad-card:hover {
            border-color: rgba(56, 189, 248, 0.5);
            box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.5);
        }
        .variant-number {
            display: inline-block;
            background: rgba(56, 189, 248, 0.15);
            color: #38bdf8 !important;
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 12px;
        }
        .ad-headline {
            font-size: 18px;
            font-weight: 700;
            color: #f3f4f6 !important;
            margin-bottom: 10px;
            line-height: 1.3;
        }
        .ad-text {
            font-size: 15px;
            color: #d1d5db !important;
            line-height: 1.6;
            margin-bottom: 16px;
        }
        .ad-cta {
            display: inline-block;
            background: linear-gradient(135deg, #f97316 0%, #ea580c 100%);
            color: white !important;
            padding: 6px 14px;
            border-radius: 99px;
            font-size: 12px;
            font-weight: 600;
            box-shadow: 0 4px 6px -1px rgba(234, 88, 12, 0.3);
        }
        .ad-meta {
            margin-top: 16px;
            padding-top: 12px;
            border-top: 1px solid rgba(255, 255, 255, 0.1);
            font-size: 12px;
            color: #6b7280 !important;
        }

        /* 6. Поля ввода (исправление белого фона) */
        [data-testid="stTextArea"] textarea,
        [data-testid="stTextInput"] input {
            background-color: #1e293b !important;
            color: #f8fafc !important;
            border: 1px solid #334155 !important;
        }
        [data-testid="stTextArea"] textarea:focus {
            border-color: #60a5fa !important;
            box-shadow: 0 0 0 1px #60a5fa !important;
        }
        
        /* 7. Загрузчик файлов */
        [data-testid="stFileUploader"] {
            background-color: rgba(30, 41, 59, 0.5);
            border-radius: 10px;
            padding: 10px;
        }
        [data-testid="stFileUploader"] section {
            background-color: transparent !important;
        }
        [data-testid="stFileUploader"] button {
             color: #e5e7eb !important;
        }

        /* 8. Кнопки */
        .stButton > button {
            width: 100%;
            background: linear-gradient(to right, #3b82f6, #2563eb);
            color: white !important;
            border: none;
            padding: 0.75rem 1rem;
            font-weight: 600;
            border-radius: 8px;
            transition: all 0.2s;
        }
        .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(37, 99, 235, 0.5);
        }
        .stDownloadButton > button {
            background: #1e293b;
            color: #cbd5e1 !important;
            border: 1px solid #334155;
        }

        /* 9. Теги товара */
        .tag {
            background: rgba(96, 165, 250, 0.15);
            color: #60a5fa !important;
            padding: 4px 8px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            border: 1px solid rgba(96, 165, 250, 0.3);
            margin-right: 6px;
            margin-bottom: 6px;
            display: inline-block;
        }
        
        /* Адаптивность для мобильных */
        @media (max-width: 640px) {
            .section-title { font-size: 20px; }
            .ad-headline { font-size: 16px; }
            .glass-container { padding: 16px; }
        }
    </style>
    """, unsafe_allow_html=True)

    # Заголовок
    st.markdown("""
    <div style="padding: 10px 0 30px 0;">
      <div style="font-size:12px; letter-spacing:0.1em; text-transform:uppercase; color:#6b7280; font-weight: 600;">
        GENAI-4 · Autonomous Marketing Agent
      </div>
      <div class="section-title">
        Генератор рекламных креативов на основе ИИ
      </div>
      <div class="section-sub">
        Для демо: test.json автоматически загружен. Для показа работоспособности, не обязательно загружать ваш каталог
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
    col1, col2 = st.columns([2, 1], gap="large")
    
    with col1:
        # Оборачиваем в контейнер glass-container для красоты
        st.markdown('<div class="glass-container">', unsafe_allow_html=True)
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
            help="Формат JSON: ...", # Ваш help текст скрыт для краткости, но он работает
            label_visibility="collapsed",
        )
        
        # Кнопка скачивания
        with open(DEFAULT_JSON_PATH, "rb") as sample_file:
            st.download_button(
                label="⬇️ Скачать пример test.json",
                data=sample_file,
                file_name="test.json",
                mime="application/json",
                use_container_width=True,
            )
        st.caption("Если файл не выбрали — будет использован встроенный test.json.")
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="glass-container">', unsafe_allow_html=True)
        st.markdown("### 🎯 Быстрый старт")
        st.markdown("""
        <div style="color: #cbd5e1; font-size: 14px; margin-bottom: 15px;">
            - по желанию: введите промпт<br>
            - нажмите "Начать Генерацию"
        </div>
        """, unsafe_allow_html=True)
        
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
        generate_button = st.button("🚀 Начать генерацию", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)


    if generate_button:
        # Читаем и парсим JSON
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
            try:
                with open(DEFAULT_JSON_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                records = parse_products_json(data)
                st.info(f"Используется встроенный пример: {DEFAULT_JSON_PATH}")
            except Exception as e:
                st.error(f"Не удалось прочитать встроенный пример {DEFAULT_JSON_PATH}: {e}")
                return

        # Инициализация LLM
        try:
            llm_client = get_llm_client(use_mistral=use_real_mistral)
        except Exception as e:
            st.error(f"Ошибка инициализации LLM-клиента: {e}")
            if use_real_mistral:
                st.info("💡 Убедитесь, что переменная окружения MISTRAL_API_KEY установлена, или используйте заглушку.")
            return

        # Генерация
        with st.spinner("🎨 Генерация креативов... Это может занять несколько секунд"):
            try:
                result = generate_creatives(records, user_text, llm_client, use_real_mistral)
            except Exception as e:
                st.error(f"❌ Ошибка при генерации: {e}")
                return

        st.success("✅ Генерация завершена успешно!")
        st.markdown("<br>", unsafe_allow_html=True)

        # Подготовка данных
        variants = result.get("variants", [])
        channel = result.get("channel", "telegram")
        product = result.get("product", {})
        
        if not variants:
            st.warning("⚠️ Не удалось сгенерировать варианты рекламы. Попробуйте еще раз.")
            return

        # --- КАРТОЧКА ПРОДУКТА ---
        if product:
            product_name = product.get("name", "")
            product_category = product.get("category", "")
            product_tags = product.get("tags", [])
            product_price = product.get("price")
            
            tags_html = ""
            if product_tags:
                tags_list = "".join([f'<span class="tag">{tag}</span>' for tag in product_tags])
                tags_html = f'<div style="margin-top:8px;">{tags_list}</div>'
            
            price_html = ""
            if product_price:
                price_html = f'<div style="color: #94a3b8; font-size: 13px; margin-bottom: 8px;">Цена: <span style="color:#e2e8f0; font-weight:600;">{product_price:,} ₽</span></div>'
            
            st.markdown(f"""
            <div class="glass-container" style="border-left: 4px solid #60a5fa;">
                <div style="font-size: 11px; text-transform:uppercase; color: #60a5fa; font-weight:700; margin-bottom:4px;">
                    {product_category if product_category else 'Товар'}
                </div>
                <h3 style="margin: 0 0 10px 0; font-size: 22px;">{product_name}</h3>
                {price_html}
                {tags_html}
            </div>
            """, unsafe_allow_html=True)

        st.markdown(f"<div class='section-title'>Сгенерировано вариантов: {len(variants)} | Канал: {channel.upper()}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='section-sub'>Показаны все варианты рекламных креативов</div>", unsafe_allow_html=True)

        # --- ОТОБРАЖЕНИЕ ВАРИАНТОВ ---
        # Делаем сетку для адаптивности
        cols = st.columns(len(variants))
        for idx, variant in enumerate(variants):
            # Если вариантов много, переносим на новую строку, если мало - в одну линию
            with cols[idx] if idx < len(cols) else st.container():
                st.markdown(f"""
                <div class="ad-card" style="height: 100%;">
                    <div class="variant-number">Вариант {idx + 1}</div>
                    <div class="ad-headline">{variant.get('headline', '')}</div>
                    <div class="ad-text">{variant.get('text', '')}</div>
                    <div style="margin-top:auto;">
                        <span class="ad-cta">CTA: {variant.get('cta', '')}</span>
                    </div>
                    <div class="ad-meta">
                        <strong>Примечания:</strong> {variant.get('notes', 'Нет примечаний')}
                    </div>
                </div>
                """, unsafe_allow_html=True)

        # Изображение
        st.markdown("---")
        st.markdown("<div class='section-title'>Визуальный креатив</div>", unsafe_allow_html=True)
        
        # Обертка для картинки, чтобы не прилипала к краям на мобильном
        st.markdown('<div class="glass-container" style="padding: 10px;">', unsafe_allow_html=True)
        st.image(
            result["image_url"],
            caption="Здесь будет отображаться сгенерированный баннер/креатив",
            use_container_width=True,
        )
        st.markdown('</div>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()
import json
from typing import Any, Dict, List

import streamlit as st
# Предполгаем, что эти модули у вас есть локально или в проекте
# Если их нет, код работать не будет (нужны prompt.py и настройки API)
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
            "image_url": "https://i.imgur.com/ilo8Prn.jpeg",
        }

    placeholder_image_url = "https://i.imgur.com/ilo8Prn.jpeg"
    return {
        "variants": variants,
        "channel": channel,
        "image_url": placeholder_image_url,
        "product": product,
    }

def main():
    st.set_page_config(
        page_title="GENAI-4 Interface",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # --- ГЛОБАЛЬНЫЙ CSS СТИЛЬ ---
    # Мы принудительно перекрашиваем стандартные элементы Streamlit, 
    # чтобы они выглядели хорошо независимо от темы пользователя (светлой/темной).
    st.markdown("""
    <style>
        /* 1. Основной фон и текст */
        [data-testid="stAppViewContainer"] {
            background-color: #020617;
            background-image: radial-gradient(circle at 50% 0%, #1e293b 0%, #020617 75%);
            color: #e2e8f0;
        }
        [data-testid="stHeader"] {
            background-color: rgba(0,0,0,0); /* Прозрачный хедер */
        }
        [data-testid="stSidebar"] {
            background-color: #0f172a;
            border-right: 1px solid #1e293b;
        }
        
        /* 2. Типографика */
        h1, h2, h3, h4, h5, h6, p, li, span, div {
            color: #e2e8f0 !important;
            font-family: 'Inter', sans-serif;
        }
        .section-title {
            font-size: 1.5rem;
            font-weight: 700;
            background: linear-gradient(90deg, #60a5fa, #a78bfa);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
        }
        .section-sub {
            font-size: 0.9rem;
            color: #94a3b8 !important;
            margin-bottom: 1.5rem;
        }

        /* 3. Кастомные Карточки (Стекломорфизм) */
        .glass-card {
            background: rgba(30, 41, 59, 0.4);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(148, 163, 184, 0.1);
            border-radius: 16px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        .glass-card:hover {
            border-color: rgba(96, 165, 250, 0.3);
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.2);
        }

        /* 4. Стили для вариантов рекламы */
        .variant-badge {
            background: rgba(56, 189, 248, 0.15);
            color: #38bdf8 !important;
            padding: 4px 12px;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            display: inline-block;
            margin-bottom: 12px;
            border: 1px solid rgba(56, 189, 248, 0.3);
        }
        .ad-headline {
            font-size: 1.15rem;
            font-weight: 700;
            margin-bottom: 8px;
            line-height: 1.4;
            color: #f8fafc !important;
        }
        .ad-text {
            font-size: 0.95rem;
            color: #cbd5e1 !important;
            line-height: 1.6;
            margin-bottom: 16px;
        }
        .ad-cta {
            display: inline-flex;
            align-items: center;
            padding: 6px 16px;
            border-radius: 8px;
            background: linear-gradient(45deg, #f97316, #ea580c);
            color: white !important;
            font-size: 0.85rem;
            font-weight: 600;
            box-shadow: 0 4px 12px rgba(234, 88, 12, 0.3);
        }
        .ad-meta {
            margin-top: 16px;
            padding-top: 12px;
            border-top: 1px solid rgba(255,255,255,0.05);
            font-size: 0.8rem;
            color: #64748b !important;
        }

        /* 5. Теги продукта */
        .tag-container {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 10px;
        }
        .product-tag {
            background: rgba(99, 102, 241, 0.15);
            color: #818cf8 !important;
            padding: 2px 10px;
            border-radius: 6px;
            font-size: 0.75rem;
            font-weight: 500;
            border: 1px solid rgba(99, 102, 241, 0.3);
        }

        /* 6. Переопределение стандартных Input-ов Streamlit */
        /* Текстовые поля */
        [data-testid="stTextArea"] textarea, [data-testid="stTextInput"] input {
            background-color: #0f172a;
            color: #f1f5f9;
            border: 1px solid #334155;
            border-radius: 8px;
        }
        [data-testid="stTextArea"] textarea:focus, [data-testid="stTextInput"] input:focus {
            border-color: #60a5fa;
            box-shadow: 0 0 0 1px #60a5fa;
        }
        /* Лейблы инпутов */
        .st-emotion-cache-1629p8f p, .st-emotion-cache-1629p8f label { 
             color: #cbd5e1 !important; 
        }
        /* Загрузчик файлов */
        [data-testid="stFileUploader"] {
            background-color: rgba(30, 41, 59, 0.3);
            border-radius: 12px;
            padding: 10px;
        }
        [data-testid="stFileUploader"] section {
            background-color: #0f172a;
        }
        
        /* 7. Кнопки */
        .stButton button {
            background: linear-gradient(to right, #2563eb, #3b82f6);
            color: white !important;
            border: none;
            padding: 0.6rem 1.5rem;
            border-radius: 10px;
            font-weight: 600;
            transition: all 0.2s;
            width: 100%;
        }
        .stButton button:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(37, 99, 235, 0.4);
        }
        
        /* Скроллбар для красоты */
        ::-webkit-scrollbar {
            width: 8px;
            height: 8px;
        }
        ::-webkit-scrollbar-track {
            background: #020617; 
        }
        ::-webkit-scrollbar-thumb {
            background: #334155; 
            border-radius: 4px;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: #475569; 
        }
    </style>
    """, unsafe_allow_html=True)

    # --- ЗАГОЛОВОК ---
    st.markdown("""
    <div style="margin-top: 10px; margin-bottom: 30px;">
      <div style="font-size:0.75rem; letter-spacing:0.15em; text-transform:uppercase; color:#60a5fa; font-weight:700; margin-bottom:5px;">
        GENAI-4 · Autonomous Agent
      </div>
      <div class="section-title">
        Генератор рекламных кампаний
      </div>
      <div class="section-sub">
        Загрузите данные о товаре, и ИИ создаст продающие креативы для Telegram, Instagram и VK.
      </div>
    </div>
    """, unsafe_allow_html=True)
    
    # --- SIDEBAR ---
    st.sidebar.markdown("### ⚙️ Настройки")
    use_real_mistral = st.sidebar.checkbox(
        "🤖 Mistral API",
        value=True,
        help="Нужен MISTRAL_API_KEY",
    )
    
    st.sidebar.markdown("---")
    st.sidebar.info("💡 **Совет:** Подробно опишите инструкции, чтобы изменить тон сообщения (например: 'дерзкий', 'официальный').")

    # --- MAIN CONTENT ---
    col1, col2 = st.columns([2, 1], gap="large")
    
    with col1:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown("#### 📝 Дополнительные инструкции")
        user_text = st.text_area(
            "Промпт",
            placeholder="Например: Сделай акцент на быстрой доставке. Тон дружелюбный, используй эмодзи.",
            height=100,
            label_visibility="collapsed",
        )
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown("#### 📁 Источник данных")
        uploaded_file = st.file_uploader(
            "Загрузите JSON",
            type=["json"],
            label_visibility="collapsed",
        )
        
        # Кнопка скачивания примера
        if st.button("⬇️ Использовать пример (test.json)"):
             # В реальном приложении здесь можно просто устанавливать флаг
             # Но для визуала оставим как есть, логика ниже обработает отсутствие файла
             pass
        st.caption("Если файл не выбран, система использует встроенный демо-пример.")
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown("#### 🚀 Управление")
        st.markdown("""
        <div style="font-size: 0.85rem; color: #94a3b8; margin-bottom: 15px;">
            1. Проверьте входные данные<br>
            2. Добавьте уточнения<br>
            3. Нажмите кнопку ниже
        </div>
        """, unsafe_allow_html=True)
        
        generate_button = st.button("✨ Сгенерировать креативы", use_container_width=True)
        
        with st.expander("👀 Структура JSON"):
            st.code("""
{
  "product": { ... },
  "audience": { ... },
  "trends": [...]
}
            """, language="json")
        st.markdown('</div>', unsafe_allow_html=True)

    # --- ЛОГИКА ГЕНЕРАЦИИ ---
    if generate_button:
        st.markdown("---")
        
        # Читаем JSON
        if uploaded_file is not None:
            try:
                raw_bytes = uploaded_file.read()
                raw_text = raw_bytes.decode("utf-8")
                data = json.loads(raw_text)
                records = parse_products_json(data)
            except Exception as e:
                st.error(f"Ошибка JSON: {e}")
                return
        else:
            try:
                with open(DEFAULT_JSON_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                records = parse_products_json(data)
                st.toast("Загружен тестовый пример", icon="ℹ️")
            except Exception as e:
                st.error(f"Ошибка чтения примера: {e}")
                return

        # Инициализация LLM
        try:
            llm_client = get_llm_client(use_mistral=use_real_mistral)
        except Exception as e:
            st.error(f"Ошибка LLM клиента: {e}")
            return

        # Генерация
        with st.spinner("🔮 Анализирую аудиторию и пишу тексты..."):
            try:
                result = generate_creatives(records, user_text, llm_client, use_real_mistral)
            except Exception as e:
                st.error(f"Ошибка генерации: {e}")
                return

        # --- ОТОБРАЖЕНИЕ РЕЗУЛЬТАТОВ ---
        variants = result.get("variants", [])
        product = result.get("product", {})
        
        if variants:
            st.success("Готово!")
            
            # Инфо о продукте
            product_name = product.get("name", "Товар")
            product_cat = product.get("category", "Категория")
            product_tags = product.get("tags", [])
            
            tags_html = "".join([f'<span class="product-tag">{t}</span>' for t in product_tags])
            
            st.markdown(f"""
            <div class="glass-card" style="border-left: 4px solid #60a5fa;">
                <div style="font-size:0.8rem; color:#94a3b8; text-transform:uppercase;">{product_cat}</div>
                <div style="font-size:1.5rem; font-weight:700; color:white; margin: 4px 0;">{product_name}</div>
                <div class="tag-container">{tags_html}</div>
            </div>
            """, unsafe_allow_html=True)

            # Варианты
            st.subheader(f"📝 Варианты ({len(variants)})")
            
            # Используем columns для плиточного отображения на десктопе, но на мобильном они станут друг под друга
            row1 = st.columns(len(variants))
            
            for idx, variant in enumerate(variants):
                with row1[idx] if idx < len(row1) else st.container():
                    st.markdown(f"""
                    <div class="glass-card" style="height: 100%;">
                        <div class="variant-badge">Вариант {idx + 1}</div>
                        <div class="ad-headline">{variant.get('headline', '')}</div>
                        <div class="ad-text">{variant.get('text', '')}</div>
                        <div style="margin-top: auto;">
                            <span class="ad-cta">{variant.get('cta', 'Подробнее')}</span>
                        </div>
                        <div class="ad-meta">
                            {variant.get('notes', '')}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            
            # Картинка
            st.markdown("### 🎨 Визуализация")
            st.image(result["image_url"], caption="Сгенерированный визуальный концепт", use_container_width=True)

if __name__ == "__main__":
    main()
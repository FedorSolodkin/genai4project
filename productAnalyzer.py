import json
import asyncio
import httpx
import math
import time
import os
from sentence_transformers import SentenceTransformer, util


class ProductAnalyzer:
    def __init__(self, JSON_FILE):
        print("Загрузка нейросети...")
        self.model = SentenceTransformer('intfloat/multilingual-e5-base')
        
        self.visual_pos = self.model.encode(["query: яркий красочный насыщенный неоновый броский дизайн визуально привлекательный"], convert_to_tensor=True)

        self.visual_neg = self.model.encode(["query: тусклый серый блеклый простой стандартный обычный скучный матовый"], convert_to_tensor=True)

        self.novelty_pos = self.model.encode(["query: новинка новый релиз последняя модель 2024 современный инновация тренд"], convert_to_tensor=True)

        self.novelty_neg = self.model.encode(["query: старый антиквариат устаревший ретро винтаж прошлый век история"], convert_to_tensor=True)

        self.hype_pos = self.model.encode(["query: бестселлер хит продаж топ популярный выбор покупателей высокий рейтинг"], convert_to_tensor=True)

        self.hype_neg = self.model.encode(["query: средний неизвестный нишевый базовый запасная часть обыденный"], convert_to_tensor=True)

        self.OAUTH_TOKEN = os.getenv("OAUTH_TOKEN")

        self.JSON_FILE = JSON_FILE 

    def _get_score(self, embedding, pos, neg):
        score = (util.cos_sim(embedding, pos).item() - util.cos_sim(embedding, neg).item()) * 100
        return max(0, score + 5)

    async def get_trend_info(self, phrase_name):
        url = "https://api.wordstat.yandex.net/v1/topRequests"

        payload = {
            "phrase": phrase_name,
            "devices": ["phone", "desktop"]
        }

        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": f"Bearer {self.OAUTH_TOKEN}"
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                print(f"http ошибка для '{phrase_name}': {e}")
                return None
            except Exception as e:
                print(f"Ошибка соединения для '{phrase_name}': {e}")
                return None

    async def run(self):
        try:
            with open(self.JSON_FILE, 'r', encoding='utf-8') as f:
                products = json.load(f)
        except FileNotFoundError:
            print(f"Файл {self.JSON_FILE} не найден.")
            return

        print(f"Анализ {len(products)} товаров. Запрос к API...")

        tasks = [self.get_trend_info(p['name']) for p in products]
        api_responses = await asyncio.gather(*tasks)

        processed = []
        
        print(f"\n{'ТОВАР':<25} | {'СПРОС (Сумма)':<13} | {'СЧЕТ'}")
        print("-" * 55)

        for i, p in enumerate(products):
            json_data = api_responses[i]
            total_trend = 0
            
            if json_data and 'topRequests' in json_data:
                for item in json_data['topRequests']:
                    total_trend += item.get('count', 0)
            
            desc_emb = self.model.encode(f"passage: {p['name']}. {p['description']}", convert_to_tensor=True)
            
            m_score = (self._get_score(desc_emb, self.visual_pos, self.visual_neg) + 
                       self._get_score(desc_emb, self.novelty_pos, self.novelty_neg) + 
                       self._get_score(desc_emb, self.hype_pos, self.hype_neg)) / 3
            
            margin = 0
            if p['price'] > 0:
                margin = ((p['price'] - p['market_cost']) / p['price']) * 100
            
            trend_score = math.log1p(total_trend) * 2.5 
            final = (m_score * 1.5) + (margin * 0.4) + trend_score
            
            processed.append({**p, "trend": total_trend, "final": final})
            print(f"{p['name'][:25]:<25} | {total_trend:<13} | {final:.1f}")

        top3 = sorted(processed, key=lambda x: x['final'], reverse=True)[:3]
        
        print("\n" + "="*50)
        print("🏆 ФИНАЛЬНЫЙ ТОП-3")
        print("="*50)
        for idx, t in enumerate(top3):
            print(f"{idx+1}. {t['name']}")
            print(f"   🔥 Спрос: {t['trend']} запросов")
            print(f"   💰 Маржа: {int(((t['price']-t['market_cost'])/t['price'])*100)}%")
            print(f"   ⭐ Рейтинг привлекательных характеристик: {t['final']:.2f}")
            print("-" * 50)

if __name__ == "__main__":
    app = ProductAnalyzer()
    asyncio.run(app.run("products.json"))
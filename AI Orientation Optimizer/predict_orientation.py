import numpy as np
import json
import os
import sys
from pathlib import Path
import joblib

print("="*70)
print("🎯 РЕКОМЕНДАЦИЯ ОПТИМАЛЬНОЙ ОРИЕНТАЦИИ ДЛЯ STL-МОДЕЛИ")
print("="*70)

# ============================================================================
# КЛАСС РЕКОМЕНДАТЕЛЯ (ДОБАВЛЯЕМ ПРЯМО СЮДА)
# ============================================================================

class OrientationRecommender:
    def __init__(self, model_filament, model_time, scaler_X):
        self.model_filament = model_filament
        self.model_time = model_time
        self.scaler_X = scaler_X
        self.test_orientations = [
            [0, 0, 0],    # default
            [90, 0, 0],   # на боку
            [0, 90, 0],
            [0, 0, 90],
            [45, 0, 0],
            [0, 45, 0],
            [0, 0, 45],
            [45, 45, 0],
            [45, 0, 45],
            [0, 45, 45],
            [45, 45, 45],
            [30, 60, 0],
            [60, 30, 0]
        ]
    
    def recommend(self, stl_vector, top_k=5):
        """Рекомендует top_k лучших ориентаций для данного STL-вектора"""
        predictions = []
        for angles in self.test_orientations:
            # Конвертируем углы в радианы
            angles_rad = [np.radians(a) for a in angles]
            features = list(stl_vector) + angles_rad
            
            # Добавляем нули для дополнительных признаков если нужно
            expected_len = self.scaler_X.n_features_in_
            if len(features) < expected_len:
                features = features + [0] * (expected_len - len(features))
            
            features_scaled = self.scaler_X.transform([features])
            filament_pred = self.model_filament.predict(features_scaled)[0]
            time_pred = self.model_time.predict(features_scaled)[0]
            score = 0.7 * filament_pred + 0.3 * time_pred
            predictions.append({
                'angles': angles,  # возвращаем углы в градусах для вывода
                'filament_pred': filament_pred,
                'time_pred': time_pred,
                'score': score
            })
        
        predictions.sort(key=lambda x: x['score'])
        return predictions[:top_k]
# ============================================================================
# ОСНОВНАЯ ФУНКЦИЯ
# ============================================================================

def main():
    # 1. Поиск STL-файла в текущей папке
    stl_files = [f for f in os.listdir('.') if f.lower().endswith('.stl')]
    if not stl_files:
        print("❌ В текущей папке не найдено STL-файлов.")
        print("   Поместите STL-файл в ту же папку, где находится этот скрипт.")
        return
    
    stl_file = stl_files[0]  # берём первый найденный
    print(f"📁 Найден файл: {stl_file}")
    
    # 2. Векторизация STL
    try:
        from stl_vectorizer_fixed import SimpleSTLVectorizer
        vectorizer = SimpleSTLVectorizer()
        result = vectorizer.extract_basic_features(stl_file)
        stl_vector = result['vector']
        print(f"✅ STL-модель векторизована ({len(stl_vector)} признаков)")
    except ImportError:
        print("❌ Не удалось импортировать stl_vectorizer_fixed.py")
        print("   Убедитесь, что файл находится в той же папке.")
        return
    except Exception as e:
        print(f"❌ Ошибка при векторизации: {e}")
        return
    
    # 3. Загрузка обученных моделей
    models_dir = 'models_improved'
    if not os.path.exists(models_dir):
        print(f"❌ Папка '{models_dir}' не найдена!")
        print("   Сначала обучите модель, запустив: python ai_orientation_predictor.py")
        return
    
    try:
        model_filament = joblib.load(f'{models_dir}/model_filament.pkl')
        model_time = joblib.load(f'{models_dir}/model_time.pkl')
        scaler_X = joblib.load(f'{models_dir}/scaler_X.pkl')
        print("✅ Базовые модели загружены")
        
        # Создаем рекомендателя на месте
        recommender = OrientationRecommender(model_filament, model_time, scaler_X)
        
    except Exception as e:
        print(f"❌ Ошибка загрузки моделей: {e}")
        
        # Проверяем, какие файлы есть в папке
        print("\n📁 Содержимое папки models_fixed:")
        for file in os.listdir(models_dir):
            print(f"   • {file}")
        
        # Если нет файла recommender.pkl, но есть другие модели
        if os.path.exists(f'{models_dir}/model_filament.pkl'):
            print("\n⚠️  Файл recommender.pkl не найден, создаю рекомендателя...")
            try:
                model_filament = joblib.load(f'{models_dir}/model_filament.pkl')
                model_time = joblib.load(f'{models_dir}/model_time.pkl')
                scaler_X = joblib.load(f'{models_dir}/scaler_X.pkl')
                recommender = OrientationRecommender(model_filament, model_time, scaler_X)
                print("✅ Рекомендатель создан")
            except Exception as e2:
                print(f"❌ Не удалось создать рекомендателя: {e2}")
                return
        else:
            return
    
    # 4. Получение рекомендаций
    print("🧠 Поиск оптимальной ориентации...")
    
    # Убедимся, что stl_vector имеет длину 10
    if len(stl_vector) != 10:
        stl_vector = list(stl_vector[:10]) + [0] * max(0, 10 - len(stl_vector))
        print(f"⚠️  STL-вектор приведён к длине 10 (было {len(result['vector'])})")
    
    recommendations = recommender.recommend(stl_vector, top_k=5)
    
    # 5. Вывод результатов
    print("\n" + "="*70)
    print("🏆 РЕКОМЕНДАЦИИ ПО ОРИЕНТАЦИИ")
    print("="*70)
    
    print(f"\nМодель: {stl_file}")
    if result.get('features'):
        feats = result['features']
        print(f"Размеры: {feats.get('width', 0):.1f}×{feats.get('depth', 0):.1f}×{feats.get('height', 0):.1f} мм")
        print(f"Объём: {feats.get('volume', 0):.1f} мм³")
    
    print("\nКритерий: минимизация филамента (70%) и времени печати (30%)\n")
    
    # Лучшая рекомендация
    best = recommendations[0]
    print("🎯 ЛУЧШАЯ ОРИЕНТАЦИЯ:")
    print(f"   Углы: X={best['angles'][0]}°, Y={best['angles'][1]}°, Z={best['angles'][2]}°")
    print(f"   Предсказанный расход филамента: {best['filament_pred']:.2f} м")
    print(f"   Предсказанное время печати: {best['time_pred']:.1f} мин")
    print(f"   Общая оценка: {best['score']:.2f}")
    
    # Альтернативные варианты
    print(f"\n📊 АЛЬТЕРНАТИВНЫЕ ВАРИАНТЫ:")
    for i, rec in enumerate(recommendations[1:], 2):
        print(f"\n   {i}. Углы: X={rec['angles'][0]}°, Y={rec['angles'][1]}°, Z={rec['angles'][2]}°")
        print(f"      Филамент: {rec['filament_pred']:.2f} м")
        print(f"      Время: {rec['time_pred']:.1f} мин")
        print(f"      Оценка: {rec['score']:.2f}")
    
    # 6. Сравнение с ориентацией по умолчанию (0,0,0)
    default_rec = None
    for rec in recommendations:
        if rec['angles'] == [0, 0, 0]:
            default_rec = rec
            break
    
    if default_rec:
        filament_saving = default_rec['filament_pred'] - best['filament_pred']
        time_saving = default_rec['time_pred'] - best['time_pred']
        
        if filament_saving > 0 or time_saving > 0:
            print(f"\n💎 ЭКОНОМИЯ ПО СРАВНЕНИЮ С ОРИЕНТАЦИЕЙ (0,0,0):")
            if filament_saving > 0:
                percent = (filament_saving / default_rec['filament_pred']) * 100
                print(f"   Филамент: экономия {filament_saving:.2f} м ({percent:.1f}%)")
            if time_saving > 0:
                percent = (time_saving / default_rec['time_pred']) * 100
                print(f"   Время: экономия {time_saving:.1f} мин ({percent:.1f}%)")
    
    # 7. Сохранение рекомендаций в JSON-файл
    output_data = {
        "stl_file": stl_file,
        "stl_vector": stl_vector if isinstance(stl_vector, list) else stl_vector.tolist(),
        "recommendations": [
            {
                "rank": i + 1,
                "angles": {
                    "x": rec['angles'][0],
                    "y": rec['angles'][1],
                    "z": rec['angles'][2]
                },
                "predicted_filament_m": round(rec['filament_pred'], 2),
                "predicted_time_min": round(rec['time_pred'], 1),
                "score": round(rec['score'], 2)
            }
            for i, rec in enumerate(recommendations)
        ],
        "best_orientation": {
            "angles": {
                "x": best['angles'][0],
                "y": best['angles'][1],
                "z": best['angles'][2]
            },
            "predicted_filament_m": round(best['filament_pred'], 2),
            "predicted_time_min": round(best['time_pred'], 1)
        }
    }
    
    output_filename = f"orientation_recommendation_{Path(stl_file).stem}.json"
    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Рекомендации сохранены в файл: {output_filename}")
    
    print("\n" + "="*70)
    print("✅ АНАЛИЗ ЗАВЕРШЁН!")
    print("="*70)

if __name__ == "__main__":
    main()
import json
import numpy as np
import os
import joblib
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split

print("="*70)
print("🤖 ОБУЧЕНИЕ МОДЕЛИ ДЛЯ РЕКОМЕНДАЦИИ ОРИЕНТАЦИИ")
print("="*70)

# 1. Загрузка данных
if not os.path.exists('training_dataset.json'):
    print("❌ Файл training_dataset.json не найден!")
    print("   Сначала создайте датасет")
    exit()

try:
    with open('training_dataset.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Фильтруем некорректные записи
    cleaned_data = []
    for item in data:
        try:
            # Проверяем наличие всех необходимых полей
            if all(key in item for key in ['stl_vector', 'angle_x', 'angle_y', 'angle_z', 'filament_length_m', 'time_minutes']):
                # Проверяем, что stl_vector имеет правильную длину
                if len(item['stl_vector']) >= 10:
                    cleaned_data.append(item)
                else:
                    print(f"⚠️  Пропущена запись: stl_vector имеет длину {len(item['stl_vector'])} вместо 10")
        except:
            continue
    
    data = cleaned_data
    
    print(f"📊 Загружено {len(data)} записей (после очистки)")
    
    if len(data) < 10:
        print(f"❌ Слишком мало данных для обучения! Только {len(data)} записей.")
        print("   Добавьте больше данных в training_dataset.json")
        exit()
        
except Exception as e:
    print(f"❌ Ошибка загрузки данных: {e}")
    exit()

# 2. Подготовка данных
X = []
y_filament = []
y_time = []

for item in data:
    stl_vector = item['stl_vector']
    # Убедимся, что вектор имеет 10 элементов
    if len(stl_vector) != 10:
        stl_vector = list(stl_vector[:10]) + [0] * max(0, 10 - len(stl_vector))
    
    # Используем углы из данных
    angles = [item['angle_x'], item['angle_y'], item['angle_z']]
    
    features = stl_vector + angles
    X.append(features)
    y_filament.append(item['filament_length_m'])
    y_time.append(item['time_minutes'])

X = np.array(X)
y_filament = np.array(y_filament)
y_time = np.array(y_time)

print(f"\n📈 Размерность данных:")
print(f"   X: {X.shape} (13 признаков на запись)")
print(f"   y_filament: {y_filament.shape}")
print(f"   y_time: {y_time.shape}")

# Остальной код без изменений...

# 3. Разделение на обучающую и тестовую выборки
X_train, X_test, y_fil_train, y_fil_test, y_time_train, y_time_test = train_test_split(
    X, y_filament, y_time, test_size=0.2, random_state=42
)

print(f"\n📊 Разделение данных:")
print(f"   Обучающая выборка: {X_train.shape[0]} примеров")
print(f"   Тестовая выборка:   {X_test.shape[0]} примеров")

# 4. Обучение модели для филамента
print("\n🎯 Обучение модели для предсказания расхода филамента...")
model_filament = RandomForestRegressor(
    n_estimators=100,
    max_depth=10,
    min_samples_split=5,
    random_state=42
)
model_filament.fit(X_train, y_fil_train)

# 5. Обучение модели для времени печати
print("🎯 Обучение модели для предсказания времени печати...")
model_time = RandomForestRegressor(
    n_estimators=100,
    max_depth=10,
    min_samples_split=5,
    random_state=42
)
model_time.fit(X_train, y_time_train)

# 6. Создание и обучение скейлера
scaler_X = StandardScaler()
X_train_scaled = scaler_X.fit_transform(X_train)
X_test_scaled = scaler_X.transform(X_test)

# 7. Оценка моделей
train_score_fil = model_filament.score(X_train, y_fil_train)
test_score_fil = model_filament.score(X_test, y_fil_test)
train_score_time = model_time.score(X_train, y_time_train)
test_score_time = model_time.score(X_test, y_time_test)

print(f"\n📊 Результаты обучения:")
print(f"   Филамент (обучение): R² = {train_score_fil:.3f}")
print(f"   Филамент (тест):     R² = {test_score_fil:.3f}")
print(f"   Время (обучение):    R² = {train_score_time:.3f}")
print(f"   Время (тест):        R² = {test_score_time:.3f}")

# 8. Сохранение моделей
os.makedirs('models_fixed', exist_ok=True)

joblib.dump(model_filament, 'models_fixed/model_filament.pkl')
joblib.dump(model_time, 'models_fixed/model_time.pkl')
joblib.dump(scaler_X, 'models_fixed/scaler_X.pkl')

print("\n💾 Модели сохранены в папке 'models_fixed/'")

# 9. Создание класса-рекомендателя
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
            # Объединяем STL-вектор с углами
            features = list(stl_vector) + angles
            features_scaled = self.scaler_X.transform([features])
            
            filament_pred = self.model_filament.predict(features_scaled)[0]
            time_pred = self.model_time.predict(features_scaled)[0]
            
            # Комбинированная оценка (чем меньше, тем лучше)
            score = 0.7 * filament_pred + 0.3 * time_pred
            
            predictions.append({
                'angles': angles,
                'filament_pred': filament_pred,
                'time_pred': time_pred,
                'score': score
            })
        
        # Сортируем по оценке (по возрастанию)
        predictions.sort(key=lambda x: x['score'])
        return predictions[:top_k]

# 10. Тестирование рекомендателя
print("\n🧪 Тестирование рекомендательной системы...")
recommender = OrientationRecommender(model_filament, model_time, scaler_X)

# Берём случайный STL-вектор из данных
test_idx = np.random.randint(0, len(X))
test_stl_vector = X[test_idx, :10]

recommendations = recommender.recommend(test_stl_vector, top_k=3)

print(f"\n🏆 Топ-3 рекомендации для тестовой модели:")
for i, rec in enumerate(recommendations):
    print(f"\n{i+1}. Углы: X={rec['angles'][0]}°, Y={rec['angles'][1]}°, Z={rec['angles'][2]}°")
    print(f"   Филамент: {rec['filament_pred']:.2f} м")
    print(f"   Время: {rec['time_pred']:.1f} мин")
    print(f"   Оценка: {rec['score']:.2f}")

# 11. Сохранение рекомендателя (необязательно, т.к. он создается в predict_orientation.py)
try:
    joblib.dump(recommender, 'models_fixed/recommender.pkl')
    print("💾 Рекомендатель сохранен")
except:
    print("⚠️  Не удалось сохранить рекомендатель (не критично)")

print("\n" + "="*70)
print("✅ ОБУЧЕНИЕ ЗАВЕРШЕНО!")
print("="*70)
print("\n🚀 Для использования с новой STL-моделью запустите:")
print("   python predict_orientation.py")
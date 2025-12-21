import json
import os
from pathlib import Path
from stl_vectorizer_fixed import SimpleSTLVectorizer

print("="*70)
print("🔄 ОБНОВЛЕНИЕ ДАТАСЕТА (РЕКУРСИВНЫЙ ПОИСК)")
print("="*70)

JSON_BASE_PATH = "json_files"
DATASET_FILE = "training_dataset.json"

# Проверяем наличие папки с JSON
if not os.path.exists(JSON_BASE_PATH):
    print(f"❌ Папка {JSON_BASE_PATH} не найдена!")
    exit()

# Загружаем существующий датасет
existing_dataset = []
if os.path.exists(DATASET_FILE):
    try:
        with open(DATASET_FILE, 'r', encoding='utf-8') as f:
            existing_dataset = json.load(f)
        print(f"📁 Загружен существующий датасет: {len(existing_dataset)} записей")
    except Exception as e:
        print(f"⚠️  Ошибка загрузки датасета: {e}. Создаем новый.")
        existing_dataset = []
else:
    print("📁 Создаем новый датасет")

# Инициализация векторизатора
vectorizer = SimpleSTLVectorizer()

# Создаем словарь существующих записей
existing_entries = {}
for item in existing_dataset:
    try:
        if all(key in item for key in ['stl_path', 'angle_x', 'angle_y', 'angle_z']):
            key = f"{item['stl_path']}_{item['angle_x']}_{item['angle_y']}_{item['angle_z']}"
            existing_entries[key] = True
    except:
        continue

# Рекурсивно ищем все пары STL+JSON
stl_json_pairs = []

print("\n🔍 Поиск STL и JSON файлов...")
for root, dirs, files in os.walk(JSON_BASE_PATH):
    # Ищем STL файлы в текущей папке
    stl_files = [f for f in files if f.lower().endswith('.stl')]
    
    for stl_file in stl_files:
        stl_path = os.path.join(root, stl_file)
        
        # Ищем JSON файлы в той же папке
        json_files = [f for f in files if f.lower().endswith('.json')]
        
        for json_file in json_files:
            json_path = os.path.join(root, json_file)
            stl_json_pairs.append((stl_path, json_path))

print(f"🔍 Найдено пар STL+JSON: {len(stl_json_pairs)}")

if not stl_json_pairs:
    print("❌ Не найдено ни одной пары STL+JSON файлов!")
    print("\n📁 Проверьте структуру папок:")
    print("   Должно быть: json_files/папка_модели/подпапка/файл.stl")
    print("   И в той же подпапке: json_files/папка_модели/подпапка/файл.json")
    exit()

# Обрабатываем каждую пару
new_entries = []
added_count = 0
skipped_count = 0

for i, (stl_path, json_path) in enumerate(stl_json_pairs):
    print(f"\n📦 Пара {i+1}/{len(stl_json_pairs)}:")
    print(f"   STL: {os.path.relpath(stl_path, JSON_BASE_PATH)}")
    print(f"   JSON: {os.path.relpath(json_path, JSON_BASE_PATH)}")
    
    # Загружаем JSON данные
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        
        # Извлекаем данные
        model_name = json_data.get("model_name", "unknown")
        angle_x = json_data.get("rotation_info", {}).get("angles_degrees", {}).get("x", 0)
        angle_y = json_data.get("rotation_info", {}).get("angles_degrees", {}).get("y", 0)
        angle_z = json_data.get("rotation_info", {}).get("angles_degrees", {}).get("z", 0)
        time_minutes = json_data.get("estimated_values", {}).get("time_minutes", 0)
        filament_length_m = json_data.get("estimated_values", {}).get("filament_length_m", 0)
        
        # Создаем ключ для проверки
        key = f"{stl_path}_{angle_x}_{angle_y}_{angle_z}"
        
        if key in existing_entries:
            print(f"   ⏭️  Уже есть в датасете")
            skipped_count += 1
            continue
        
        # Векторизуем STL
        try:
            result = vectorizer.extract_basic_features(stl_path)
            
            # Создаем запись
            new_entry = {
                'model_name': model_name,
                'stl_path': stl_path,
                'json_path': json_path,
                'stl_vector': result['vector'].tolist(),
                'angle_x': float(angle_x),
                'angle_y': float(angle_y),
                'angle_z': float(angle_z),
                'filament_length_m': float(filament_length_m),
                'time_minutes': float(time_minutes),
                'features': result['features']
            }
            
            new_entries.append(new_entry)
            existing_entries[key] = True
            added_count += 1
            
            print(f"   ✅ Добавлено: углы [{angle_x}°, {angle_y}°, {angle_z}°]")
            print(f"      Филамент: {filament_length_m} м, Время: {time_minutes} мин")
            
        except Exception as e:
            print(f"   ❌ Ошибка векторизации: {e}")
            skipped_count += 1
            
    except Exception as e:
        print(f"   ❌ Ошибка загрузки JSON: {e}")
        skipped_count += 1

# Объединяем датасеты
updated_dataset = existing_dataset + new_entries

# Фильтруем записи
cleaned_dataset = []
for item in updated_dataset:
    try:
        if all(key in item for key in ['stl_vector', 'angle_x', 'angle_y', 'angle_z', 'filament_length_m', 'time_minutes']):
            # Исправляем вектор
            if len(item['stl_vector']) != 10:
                item['stl_vector'] = list(item['stl_vector'][:10]) + [0] * max(0, 10 - len(item['stl_vector']))
            cleaned_dataset.append(item)
    except:
        continue

# Сохраняем
with open(DATASET_FILE, 'w', encoding='utf-8') as f:
    json.dump(cleaned_dataset, f, indent=2, ensure_ascii=False)

print("\n" + "="*70)
print("📊 РЕЗУЛЬТАТЫ:")
print(f"   Всего записей в датасете: {len(cleaned_dataset)}")
print(f"   Добавлено новых записей: {added_count}")
print(f"   Пропущено: {skipped_count}")
print("="*70)

if cleaned_dataset:
    print("\n📋 ПЕРВЫЕ 3 ЗАПИСИ:")
    for i, item in enumerate(cleaned_dataset[:3]):
        print(f"\n{i+1}. Модель: {item.get('model_name', 'N/A')}")
        print(f"   STL: {os.path.basename(item.get('stl_path', 'N/A'))}")
        print(f"   Углы: [{item.get('angle_x', 0)}°, {item.get('angle_y', 0)}°, {item.get('angle_z', 0)}°]")
        print(f"   Филамент: {item.get('filament_length_m', 0):.2f} м")
        print(f"   Время: {item.get('time_minutes', 0):.1f} мин")

print("\n🚀 Для обучения: python ai_orientation_predictor.py")
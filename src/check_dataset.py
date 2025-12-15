"""
Проверка созданной структуры датасета
"""

import json
from pathlib import Path

def check_dataset_structure(base_path="dataset"):
    """Проверяет структуру датасета"""
    
    base = Path(base_path)
    
    print("=" * 60)
    print("ПРОВЕРКА СТРУКТУРЫ ДАТАСЕТА")
    print("=" * 60)
    
    # 1. Проверяем папки
    required_folders = ["models", "orientations", "gcode_results"]
    
    for folder in required_folders:
        path = base / folder
        if path.exists():
            print(f"✅ {folder}/")
        else:
            print(f"❌ {folder}/ - отсутствует")
    
    # 2. Проверяем модели
    models = list((base / "models").glob("*.stl"))
    print(f"\n📦 Моделей найдено: {len(models)}")
    for model in models[:10]:  # покажем первые 10
        print(f"  • {model.name}")
    
    if len(models) > 10:
        print(f"  ... и еще {len(models) - 10}")
    
    # 3. Проверяем ориентации
    orientations_path = base / "orientations"
    if orientations_path.exists():
        model_folders = [f for f in orientations_path.iterdir() if f.is_dir()]
        print(f"\n🎯 Ориентаций по моделям: {len(model_folders)}")
        
        total_orientations = 0
        for model_folder in model_folders:
            orientations = [f for f in model_folder.iterdir() if f.is_dir()]
            total_orientations += len(orientations)
            
            if model_folders.index(model_folder) < 5:  # покажем первые 5
                print(f"  📁 {model_folder.name}: {len(orientations)} ориентаций")
                
                for orient in orientations[:3]:  # первые 3 ориентации
                    files = list(orient.glob("*"))
                    json_files = [f for f in files if f.suffix == '.json']
                    stl_files = [f for f in files if f.suffix == '.stl']
                    
                    print(f"    ↳ {orient.name}: {len(json_files)} JSON, {len(stl_files)} STL")
        
        print(f"\n📊 Всего ориентаций: {total_orientations}")
        print(f"📊 Среднее на модель: {total_orientations/len(model_folders):.1f}" if model_folders else "0")
    
    # 4. Проверяем G-code структуру
    gcode_path = base / "gcode_results"
    if gcode_path.exists():
        gcode_models = [f for f in gcode_path.iterdir() if f.is_dir()]
        print(f"\n🖨️  G-code структур: {len(gcode_models)}")
    
    # 5. Проверяем JSON файлы
    print(f"\n📄 Проверка JSON файлов:")
    
    json_files = list(base.rglob("*.json"))
    valid_json = 0
    invalid_json = 0
    
    for json_file in json_files[:20]:  # проверим первые 20
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            valid_json += 1
            if json_files.index(json_file) < 5:  # покажем первые 5
                print(f"  ✅ {json_file.relative_to(base)}")
        except Exception as e:
            invalid_json += 1
            print(f"  ❌ {json_file.relative_to(base)}: {e}")
    
    print(f"\n📊 JSON файлов: {valid_json} валидных, {invalid_json} с ошибками")
    
    print("\n" + "=" * 60)
    print("СТАТИСТИКА ДАТАСЕТА")
    print("=" * 60)
    
    stats = {
        "total_models": len(models),
        "total_orientations": total_orientations,
        "total_json_files": len(json_files),
        "dataset_size_gb": "N/A"  # можно добавить вычисление размера
    }
    
    for key, value in stats.items():
        print(f"{key.replace('_', ' ').title()}: {value}")
    
    print("\n" + "=" * 60)
    print("РЕКОМЕНДАЦИИ:")
    print("=" * 60)
    
    if len(models) < 10:
        print("⚠️  Мало моделей (<10). Добавьте больше STL файлов в dataset/models/")
    
    if total_orientations / max(1, len(models)) < 3:
        print("⚠️  Мало ориентаций на модель (<3). Запустите auto_analyze_full.py")
    
    if invalid_json > 0:
        print("⚠️  Есть поврежденные JSON файлы. Проверьте их вручную.")
    
    if len(models) >= 20 and total_orientations >= 60:
        print("✅ Датасет готов для передачи ML инженеру!")
        print("   Запустите: python src/prepare_ml_dataset.py")
    else:
        print("📈 Продолжайте сбор данных. Цель: 20+ моделей, 60+ ориентаций")
    
    print("=" * 60)

if __name__ == "__main__":
    check_dataset_structure()
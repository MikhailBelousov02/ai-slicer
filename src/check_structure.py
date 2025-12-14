import os
import json

def check_project_structure():
    """Проверяет созданную структуру проекта"""
    
    print("=" * 60)
    print("ПРОВЕРКА СТРУКТУРЫ ПРОЕКТА")
    print("=" * 60)
    
    # Проверяем основные папки
    folders = [
        "dataset/models",
        "dataset/orientations",
        "dataset/gcode_results",
        "src",
        "tests",
        "docs"
    ]
    
    for folder in folders:
        if os.path.exists(folder):
            print(f"✅ {folder}/")
        else:
            print(f"❌ {folder}/ - НЕ НАЙДЕНА!")
    
    print("\n" + "=" * 60)
    print("ПРОВЕРКА ДАТАСЕТА")
    print("=" * 60)
    
    # Проверяем модели
    models_path = "dataset/models"
    if os.path.exists(models_path):
        models = os.listdir(models_path)
        print(f"Моделей найдено: {len(models)}")
        for model in models:
            print(f"  📁 {model}")
    else:
        print("Папка models не найдена!")
    
    # Проверяем ориентации
    orientations_path = "dataset/orientations"
    if os.path.exists(orientations_path):
        for model_folder in os.listdir(orientations_path):
            model_path = os.path.join(orientations_path, model_folder)
            if os.path.isdir(model_path):
                print(f"\n📦 {model_folder}:")
                for orientation in os.listdir(model_path):
                    orientation_path = os.path.join(model_path, orientation)
                    if os.path.isdir(orientation_path):
                        files = os.listdir(orientation_path)
                        print(f"  ↳ {orientation} ({len(files)} файлов)")
                        
                        # Проверяем наличие ключевых файлов
                        required = ["model.stl", "orientation.json", "analysis.json"]
                        for req in required:
                            if req in files:
                                print(f"    ✅ {req}")
                            else:
                                print(f"    ❌ {req} - отсутствует")
    else:
        print("Папка orientations не найдена!")
    
    print("\n" + "=" * 60)
    print("ПРОВЕРКА JSON ФАЙЛОВ")
    print("=" * 60)
    
    # Проверяем валидность JSON файлов
    if os.path.exists(orientations_path):
        for root, dirs, files in os.walk(orientations_path):
            for file in files:
                if file.endswith('.json'):
                    filepath = os.path.join(root, file)
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        print(f"✅ {os.path.relpath(filepath, orientations_path)}")
                    except Exception as e:
                        print(f"❌ {os.path.relpath(filepath, orientations_path)}: {e}")
    else:
        print("Нет JSON файлов для проверки")
    
    print("\n" + "=" * 60)
    print("СТАТИСТИКА")
    print("=" * 60)
    
    # Считаем статистику
    total_models = len(models) if 'models' in locals() else 0
    total_orientations = 0
    
    if os.path.exists(orientations_path):
        for root, dirs, files in os.walk(orientations_path):
            # Считаем папки с ориентациями (исключаем папки моделей)
            if root != orientations_path and "orientation" in root:
                if any(f.endswith('.stl') for f in os.listdir(root)):
                    total_orientations += 1
    
    print(f"Всего моделей: {total_models}")
    print(f"Всего ориентаций: {total_orientations}")
    if total_models > 0:
        print(f"Среднее ориентаций на модель: {total_orientations/total_models:.1f}")
    else:
        print("Среднее ориентаций на модель: 0")
    
    print("\n" + "=" * 60)
    print("Готово! Проект успешно создан.")
    print("=" * 60)

if __name__ == "__main__":
    check_project_structure()
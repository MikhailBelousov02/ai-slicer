import os
import json
import pandas as pd
from pathlib import Path

def analyze_dataset():
    """Анализирует созданный датасет и создает сводную таблицу"""
    
    print("=" * 60)
    print("АНАЛИЗ ДАТАСЕТА")
    print("=" * 60)
    
    base_path = Path("dataset/orientations")
    data = []
    
    # Проходим по всем ориентациям
    for model_dir in base_path.iterdir():
        if model_dir.is_dir():
            for orientation_dir in model_dir.iterdir():
                if orientation_dir.is_dir():
                    # Читаем JSON файлы
                    orientation_file = orientation_dir / "orientation.json"
                    analysis_file = orientation_dir / "analysis.json"
                    
                    if orientation_file.exists() and analysis_file.exists():
                        try:
                            with open(orientation_file, 'r', encoding='utf-8') as f:
                                orientation_data = json.load(f)
                            
                            with open(analysis_file, 'r', encoding='utf-8') as f:
                                analysis_data = json.load(f)
                            
                            # Собираем данные
                            row = {
                                'model': model_dir.name,
                                'orientation': orientation_dir.name,
                                'rotation_x': orientation_data.get('rotation_angles', {}).get('x', 0),
                                'rotation_y': orientation_data.get('rotation_angles', {}).get('y', 0),
                                'rotation_z': orientation_data.get('rotation_angles', {}).get('z', 0),
                                'requires_supports': analysis_data.get('overhang_analysis', {}).get('requires_supports', False),
                                'max_overhang_angle': analysis_data.get('overhang_analysis', {}).get('max_overhang_angle', 0),
                                'stability_risk': analysis_data.get('stability_metrics', {}).get('stability_risk', 'unknown')
                            }
                            data.append(row)
                            
                        except Exception as e:
                            print(f"Ошибка чтения {orientation_dir}: {e}")
    
    # Создаем DataFrame
    if data:
        df = pd.DataFrame(data)
        print("\n📊 СВОДНАЯ ТАБЛИЦА ДАТАСЕТА:")
        print(df.to_string(index=False))
        
        # Сохраняем в CSV
        df.to_csv('dataset/dataset_summary.csv', index=False, encoding='utf-8')
        print(f"\n✅ Таблица сохранена: dataset/dataset_summary.csv")
        
        # Статистика
        print("\n📈 СТАТИСТИКА:")
        print(f"Всего моделей: {df['model'].nunique()}")
        print(f"Всего ориентаций: {len(df)}")
        print(f"Ориентаций с поддержками: {df['requires_supports'].sum()}")
        print(f"Ориентаций без поддержек: {len(df) - df['requires_supports'].sum()}")
        
    else:
        print("❌ Данные не найдены. Проверьте структуру папок.")
    
    return data

def check_stl_files():
    """Проверяет наличие STL файлов"""
    print("\n" + "=" * 60)
    print("ПРОВЕРКА STL ФАЙЛОВ")
    print("=" * 60)
    
    models_path = Path("dataset/models")
    orientations_path = Path("dataset/orientations")
    
    # Исходные модели
    print("\n📁 Исходные модели:")
    for stl_file in models_path.glob("*.stl"):
        size_kb = stl_file.stat().st_size / 1024
        print(f"  ✅ {stl_file.name} ({size_kb:.1f} KB)")
    
    # Ориентированные модели
    print("\n📁 Ориентированные модели:")
    stl_count = 0
    for stl_file in orientations_path.rglob("*.stl"):
        size_kb = stl_file.stat().st_size / 1024
        print(f"  ✅ {stl_file.relative_to(orientations_path)} ({size_kb:.1f} KB)")
        stl_count += 1
    
    print(f"\nВсего ориентированных STL: {stl_count}")

if __name__ == "__main__":
    analyze_dataset()
    check_stl_files()
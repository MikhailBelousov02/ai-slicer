"""
Создание шаблонов JSON файлов для ориентаций
"""

import json
from pathlib import Path
from datetime import datetime

def create_orientation_template(model_name, orientation_name, angles, author="Михаил"):
    """Создает шаблон orientation.json"""
    
    template = {
        "model_name": model_name,
        "orientation_name": orientation_name,
        "rotation_angles": {
            "x_degrees": angles[0],
            "y_degrees": angles[1], 
            "z_degrees": angles[2]
        },
        "creation_date": datetime.now().isoformat(),
        "author": author
    }
    
    return template

def create_print_info_template(orientation_used, estimated_time=0, estimated_material=0):
    """Создает шаблон print_info.json"""
    
    template = {
        "print_session": {
            "orientation_used": orientation_used,
            "print_date": datetime.now().strftime("%Y-%m-%d"),
            "printer_used": "Ender-3 V2"
        },
        "estimated_values": {
            "time_minutes": estimated_time,
            "material_g": estimated_material,
            "layer_count": 0
        },
        "success": False
    }
    
    return template

def setup_new_orientation(model_name, orientation_name, angles, output_dir=None):
    """
    Настраивает новую ориентацию: создает папку и шаблоны
    """
    
    if output_dir:
        base_dir = Path(output_dir)
    else:
        base_dir = Path("dataset/orientations") / model_name / orientation_name
    
    # Создаем папку
    base_dir.mkdir(parents=True, exist_ok=True)
    
    # Создаем orientation.json
    orientation_data = create_orientation_template(model_name, orientation_name, angles)
    orientation_file = base_dir / "orientation.json"
    
    with open(orientation_file, 'w', encoding='utf-8') as f:
        json.dump(orientation_data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Создан: {orientation_file}")
    
    # Создаем README
    readme_content = f"""# Ориентация: {orientation_name}

Модель: {model_name}
Углы поворота: X={angles[0]}°, Y={angles[1]}°, Z={angles[2]}°

## Инструкция:
1. Откройте {model_name}.stl в Cura
2. Поверните на указанные углы
3. Экспортируйте как model.stl в эту папку
4. Запустите анализ: python auto_analyze.py model.stl
"""
    
    readme_file = base_dir / "README.md"
    with open(readme_file, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    print(f"✅ Создан: {readme_file}")
    
    return base_dir

def main():
    """Интерактивное создание ориентаций"""
    
    print("Создание новой ориентации")
    print("-" * 40)
    
    model_name = input("Имя модели (без .stl): ").strip()
    orientation_name = input("Имя ориентации (default/flat/optimal): ").strip()
    
    print("Углы поворота (в градусах):")
    try:
        x = float(input("  X (наклон вперед/назад): ") or 0)
        y = float(input("  Y (поворот на столе): ") or 0) 
        z = float(input("  Z (редко используется): ") or 0)
    except ValueError:
        print("❌ Ошибка: введите числа")
        return
    
    # Создаем структуру
    folder = setup_new_orientation(model_name, orientation_name, [x, y, z])
    
    print(f"\n✅ Готово! Структура создана в: {folder}")
    print("\nДальнейшие шаги:")
    print("1. Откройте модель в Cura")
    print("2. Поверните на заданные углы")
    print(f"3. Экспортируйте как 'model.stl' в папку: {folder}")
    print("4. Запустите анализ: python auto_analyze.py")

if __name__ == "__main__":
    main()
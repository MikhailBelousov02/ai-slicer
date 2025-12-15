"""
Скрипт для создания структуры папок для одной или всех моделей
Автоматически создает папки и шаблоны JSON файлов
"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
import sys

class DatasetStructureCreator:
    def __init__(self, base_path="dataset"):
        self.base_path = Path(base_path)
        self.models_path = self.base_path / "models"
        self.orientations_path = self.base_path / "orientations"
        self.gcode_path = self.base_path / "gcode_results"
        
        # Стандартные ориентации (без experimental)
        self.standard_orientations = [
            ("default", [0, 0, 0], "Оригинальная ориентация"),
            ("flat", [90, 0, 0], "Модель лежит на боку"),
            ("optimal", [45, 30, 0], "Оптимальная ориентация")
        ]
        
        # Создаем корневые папки если нет
        self.models_path.mkdir(exist_ok=True, parents=True)
        self.orientations_path.mkdir(exist_ok=True, parents=True)
        self.gcode_path.mkdir(exist_ok=True, parents=True)
    
    def create_structure_for_model(self, model_name):
        """
        Создает структуру папок для конкретной модели
        
        Args:
            model_name: Имя модели (без .stl)
        """
        print(f"\n{'='*50}")
        print(f"СОЗДАНИЕ СТРУКТУРЫ ДЛЯ МОДЕЛИ: {model_name}")
        print(f"{'='*50}")
        
        # Проверяем есть ли исходная модель
        source_stl = self.models_path / f"{model_name}.stl"
        if not source_stl.exists():
            print(f"⚠️  Внимание: {source_stl.name} не найден в {self.models_path}")
            print("   Добавьте STL файл вручную или создайте позже")
        
        # Создаем папки для каждой ориентации
        for orient_name, angles, description in self.standard_orientations:
            self.create_orientation_structure(model_name, orient_name, angles, description, source_stl)
        
        # Создаем общие настройки Cura если нет
        self.create_global_cura_settings()
        
        print(f"\n✅ Структура создана для модели: {model_name}")
        print(f"   Создано ориентаций: {len(self.standard_orientations)}")
        print(f"   Путь: {self.orientations_path / model_name}")
    
    def create_orientation_structure(self, model_name, orient_name, angles, description, source_stl=None):
        """
        Создает полную структуру для одной ориентации
        
        Args:
            model_name: Имя модели
            orient_name: Имя ориентации (default/flat/optimal)
            angles: Углы поворота [x, y, z]
            description: Описание ориентации
            source_stl: Путь к исходному STL файлу (опционально)
        """
        # 1. Папка ориентации
        orient_dir = self.orientations_path / model_name / orient_name
        orient_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"\n📁 Создаю ориентацию: {model_name}/{orient_name}")
        print(f"   Углы: X={angles[0]}°, Y={angles[1]}°, Z={angles[2]}°")
        print(f"   Описание: {description}")
        
        # 2. Создаем README с инструкцией
        self.create_orientation_readme(orient_dir, model_name, orient_name, angles, description)
        
        # 3. Создаем orientation.json шаблон
        self.create_orientation_json(orient_dir, model_name, orient_name, angles, description)
        
        # 4. Создаем analysis.json шаблон (для ручного/автоматического заполнения)
        self.create_analysis_json_template(orient_dir, model_name)
        
        # 5. Если есть исходный STL, создаем пустой model.stl как напоминание
        if source_stl and source_stl.exists():
            placeholder_stl = orient_dir / "model.stl"
            if not placeholder_stl.exists():
                # Создаем пустой файл как напоминание
                with open(placeholder_stl, 'w') as f:
                    f.write(f"# Замените этот файл на повернутую версию модели\n")
                    f.write(f"# Исходный файл: {source_stl.name}\n")
                    f.write(f"# Углы поворота: X={angles[0]}°, Y={angles[1]}°, Z={angles[2]}°\n")
                print(f"   ✅ Создан placeholder для STL файла")
        
        # 6. Создаем структуру для G-code результатов
        self.create_gcode_structure(model_name, orient_name)
        
        print(f"   ✅ Ориентация {orient_name} создана")
    
    def create_orientation_readme(self, orient_dir, model_name, orient_name, angles, description):
        """Создает README файл с инструкцией для ориентации"""
        readme_content = f"""# Ориентация: {orient_name}

**Модель:** {model_name}
**Углы поворота:** X={angles[0]}°, Y={angles[1]}°, Z={angles[2]}°
**Описание:** {description}

## ИНСТРУКЦИЯ ДЛЯ РУЧНОГО ЗАПОЛНЕНИЯ:

### 1. Подготовка 3D модели:
1. Откройте файл `../models/{model_name}.stl` в Cura 5.11.0
2. Поверните модель на указанные углы:
   - Вращение X (наклон вперед/назад): {angles[0]}°
   - Вращение Y (поворот на столе): {angles[1]}°
   - Вращение Z: {angles[2]}°
3. Экспортируйте повернутую модель как `model.stl` в эту папку

### 2. Заполнение JSON файлов:

#### orientation.json - уже заполнен, проверьте:
- Углы поворота соответствуют действительности
- model_name указан верно

#### analysis.json - ЗАПОЛНИТЕ ВРУЧНУЮ или автоматически:
- Запустите скрипт: `python src/fill_analysis.py "{orient_dir}/model.stl"`
- Или заполните вручную:
  - `requires_supports`: нужны ли поддержки (true/false)
  - Ваша оценка качества (1-10)

### 3. Слайсинг и печать:
1. Откройте `model.stl` в Cura
2. Настройте параметры печати (используйте `dataset/cura_settings.json`)
3. Экспортируйте G-code как `output.gcode` в `../gcode_results/{model_name}/{orient_name}/`
4. После печати заполните `print_info.json` в папке G-code

## ФАЙЛЫ В ЭТОЙ ПАПКЕ:
- `model.stl` - повернутая 3D модель (создать вручную)
- `orientation.json` - метаданные ориентации (уже создан)
- `analysis.json` - анализ геометрии (шаблон, заполнить)
- `README.md` - эта инструкция

---
*Создано автоматически: {datetime.now().strftime("%Y-%m-%d %H:%M")}*
"""
        
        readme_file = orient_dir / "README.md"
        with open(readme_file, 'w', encoding='utf-8') as f:
            f.write(readme_content)
    
    def create_orientation_json(self, orient_dir, model_name, orient_name, angles, description):
        """Создает orientation.json файл"""
        orientation_data = {
            "model_name": model_name,
            "orientation_name": orient_name,
            "rotation_angles": {
                "x_degrees": float(angles[0]),
                "y_degrees": float(angles[1]),
                "z_degrees": float(angles[2])
            },
            "description": description,
            "created_date": datetime.now().isoformat(),
            "author": "structure_creator",
            "notes": "Заполните после подготовки модели"
        }
        
        orientation_file = orient_dir / "orientation.json"
        with open(orientation_file, 'w', encoding='utf-8') as f:
            json.dump(orientation_data, f, indent=2, ensure_ascii=False)
    
    def create_analysis_json_template(self, orient_dir, model_name):
        """Создает шаблон analysis.json для ручного заполнения"""
        analysis_template = {
            "automatic_analysis": {
                "bounding_box_mm": {
                    "width": 0.0,
                    "depth": 0.0,
                    "height": 0.0,
                    "note": "Заполните после анализа модели"
                },
                "volume_cm3": 0.0,
                "surface_area_cm2": 0.0,
                "center_of_mass_mm": [0.0, 0.0, 0.0],
                "status": "pending_analysis"
            },
            "support_analysis": {
                "requires_supports": False,
                "max_overhang_angle": 0.0,
                "overhang_area_mm2": 0.0,
                "support_volume_estimate_ml": 0.0,
                "note": "Определите нужны ли поддержки для этой ориентации"
            },
            "contact_area_mm2": 0.0,
            "user_assessment": {
                "quality_score": 0,
                "printability_score": 0,
                "notes": "Оцените после анализа: 1-10",
                "issues_found": []
            },
            "analysis_status": "not_analyzed",
            "last_updated": datetime.now().isoformat()
        }
        
        analysis_file = orient_dir / "analysis.json"
        with open(analysis_file, 'w', encoding='utf-8') as f:
            json.dump(analysis_template, f, indent=2, ensure_ascii=False)
    
    def create_gcode_structure(self, model_name, orient_name):
        """Создает структуру для результатов слайсинга"""
        gcode_dir = self.gcode_path / model_name / orient_name
        gcode_dir.mkdir(parents=True, exist_ok=True)
        
        # Создаем print_info.json шаблон
        print_info = {
            "print_session": {
                "model_name": model_name,
                "orientation_used": orient_name,
                "print_date": "",
                "printer_used": "Ender-3 V2",
                "operator": ""
            },
            "estimated_values": {
                "time_minutes": 0,
                "material_g": 0.0,
                "layer_count": 0,
                "filament_length_m": 0.0
            },
            "actual_results": {
                "time_minutes": 0,
                "material_used_g": 0.0,
                "success": False,
                "failed_reason": ""
            },
            "quality_assessment": {
                "overall_quality": 0,
                "dimensional_accuracy": 0,
                "surface_quality": 0,
                "notes": ""
            },
            "status": "not_printed",
            "created_date": datetime.now().isoformat()
        }
        
        print_info_file = gcode_dir / "print_info.json"
        with open(print_info_file, 'w', encoding='utf-8') as f:
            json.dump(print_info, f, indent=2, ensure_ascii=False)
        
        # Создаем README для G-code папки
        gcode_readme = f"""# Результаты печати

Модель: {model_name}
Ориентация: {orient_name}

## ФАЙЛЫ:
- `output.gcode` - G-code файл (создать в Cura после слайсинга)
- `print_info.json` - информация о печати (заполнить после печати)
- `cura_settings.json` - копия общих настроек

## ИНСТРУКЦИЯ:

### Перед печатью:
1. Убедитесь что в папке ориентации есть `model.stl`
2. Откройте его в Cura, настройте параметры
3. Экспортируйте G-code как `output.gcode` в эту папку

### После печати ЗАПОЛНИТЕ:
1. Фактическое время печати (минуты)
2. Использованный материал (граммы)
3. Успешность печати (true/false)
4. Оценку качества (1-10)
5. Заметки о проблемах

---
*Папка создана: {datetime.now().strftime("%Y-%m-%d %H:%M")}*
"""
        
        readme_file = gcode_dir / "README.md"
        with open(readme_file, 'w', encoding='utf-8') as f:
            f.write(gcode_readme)
        
        # Копируем общие настройки Cura если есть
        global_settings = self.base_path / "cura_settings.json"
        if global_settings.exists():
            shutil.copy(global_settings, gcode_dir / "cura_settings.json")
    
    def create_global_cura_settings(self):
        """Создает общий файл настроек Cura если его нет"""
        settings_file = self.base_path / "cura_settings.json"
        
        if not settings_file.exists():
            settings = {
                "profile_name": "Standard Quality 0.2mm",
                "quality_settings": {
                    "layer_height": 0.2,
                    "line_width": 0.4,
                    "wall_thickness": 0.8,
                    "top_bottom_thickness": 0.8
                },
                "infill_settings": {
                    "infill_density": 20,
                    "infill_pattern": "grid"
                },
                "material_settings": {
                    "material": "PLA",
                    "print_temperature": 210,
                    "bed_temperature": 60,
                    "print_speed": 50
                },
                "support_settings": {
                    "support_enabled": False,
                    "overhang_angle": 45
                },
                "adhesion_settings": {
                    "type": "none"
                },
                "printer_settings": {
                    "printer": "Creality Ender-3 V2",
                    "nozzle_size": 0.4
                },
                "notes": "Общие настройки для всего датасета. Можно скопировать и изменить для конкретной печати."
            }
            
            with open(settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Создан общий файл настроек: {settings_file}")
    
    def create_for_all_models(self):
        """Создает структуру для всех моделей в папке models"""
        stl_files = list(self.models_path.glob("*.stl"))
        
        if not stl_files:
            print("❌ Нет STL файлов в папке models/")
            print("   Добавьте STL файлы в: dataset/models/")
            return
        
        print(f"\n🔍 Найдено моделей: {len(stl_files)}")
        
        for stl_file in stl_files:
            model_name = stl_file.stem  # Без расширения
            self.create_structure_for_model(model_name)
        
        print(f"\n{'='*50}")
        print(f"✅ СТРУКТУРА СОЗДАНА ДЛЯ {len(stl_files)} МОДЕЛЕЙ")
        print(f"{'='*50}")
    
    def print_summary(self):
        """Выводит статистику созданной структуры"""
        print(f"\n{'='*50}")
        print("СТАТИСТИКА СОЗДАННОЙ СТРУКТУРЫ")
        print(f"{'='*50}")
        
        # Считаем модели
        models = list(self.orientations_path.iterdir())
        models = [m for m in models if m.is_dir()]
        
        print(f"📦 Моделей: {len(models)}")
        
        total_orientations = 0
        for model_dir in models:
            orientations = list(model_dir.iterdir())
            orientations = [o for o in orientations if o.is_dir()]
            total_orientations += len(orientations)
            
            if len(models) <= 10:  # Показываем детали если моделей немного
                print(f"  ├─ {model_dir.name}: {len(orientations)} ориентаций")
        
        print(f"🎯 Всего ориентаций: {total_orientations}")
        print(f"📊 Среднее на модель: {total_orientations/max(1, len(models)):.1f}")
        
        # Считаем JSON файлы
        json_files = list(self.orientations_path.rglob("*.json"))
        print(f"📄 JSON файлов создано: {len(json_files)}")
        
        print(f"\n📁 ПУТИ:")
        print(f"  Модели: {self.models_path}")
        print(f"  Ориентации: {self.orientations_path}")
        print(f"  G-code результаты: {self.gcode_path}")
        
        print(f"\n🎯 ДАЛЬНЕЙШИЕ ДЕЙСТВИЯ:")
        print(f"  1. Добавьте STL файлы в папки ориентаций")
        print(f"  2. Запустите скрипт для анализа геометрии")
        print(f"  3. Заполните analysis.json данными")
        print(f"  4. Загрузите JSON файлы на GitHub")
        print(f"{'='*50}")

def main():
    """Основная функция"""
    
    print("="*60)
    print("СОЗДАНИЕ СТРУКТУРЫ ПАПОК ДЛЯ ДАТАСЕТА")
    print("="*60)
    
    creator = DatasetStructureCreator()
    
    # Обработка аргументов командной строки
    if len(sys.argv) > 1:
        # Режим для одной модели
        model_name = sys.argv[1]
        if model_name.lower() == "all":
            creator.create_for_all_models()
        else:
            # Убираем расширение .stl если есть
            if model_name.lower().endswith('.stl'):
                model_name = model_name[:-4]
            creator.create_structure_for_model(model_name)
    else:
        # Интерактивный режим
        print("\n📋 ВЫБЕРИТЕ РЕЖИМ:")
        print("  1 - Создать структуру для всех моделей")
        print("  2 - Создать структуру для конкретной модели")
        
        choice = input("\nВаш выбор (1/2): ").strip()
        
        if choice == "1":
            creator.create_for_all_models()
        elif choice == "2":
            model_name = input("Введите имя модели (без .stl): ").strip()
            if model_name:
                creator.create_structure_for_model(model_name)
            else:
                print("❌ Имя модели не указано")
        else:
            print("❌ Неверный выбор")
    
    # Выводим статистику
    creator.print_summary()

if __name__ == "__main__":
    main()
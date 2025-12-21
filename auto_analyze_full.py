"""
auto_analyze_full.py - Минимальная структура датасета
Создает только: results/[model]/[orientation]/ с необходимыми файлами
"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
import sys

class MinimalStructureCreator:
    def __init__(self, base_path="dataset"):
        self.base_path = Path(base_path)
        self.models_path = self.base_path / "models"
        self.results_path = self.base_path / "results"
        
        # Стандартные ориентации
        self.standard_orientations = [
            ("default", [0, 0, 0], "Оригинальная ориентация"),
            ("flat", [90, 0, 0], "Модель лежит на боку"),
            ("optimal", [45, 30, 0], "Оптимальная ориентация")
        ]
        
        # Создаем корневые папки если нет
        self.models_path.mkdir(exist_ok=True, parents=True)
        self.results_path.mkdir(exist_ok=True, parents=True)
    
    def create_structure_for_model(self, model_name):
        """
        Создает структуру папок для конкретной модели в results/
        """
        print("\n" + "="*50)
        print(f"СОЗДАНИЕ СТРУКТУРЫ ДЛЯ МОДЕЛИ: {model_name}")
        print("="*50)
        
        # Проверяем есть ли исходная модель
        source_stl = self.models_path / f"{model_name}.stl"
        if not source_stl.exists():
            print(f"Внимание: {source_stl.name} не найден в {self.models_path}")
            print("   Добавьте STL файл вручную или создайте позже")
        
        # Создаем папки для каждой ориентации в results
        for orient_name, angles, description in self.standard_orientations:
            self.create_orientation_structure(model_name, orient_name, angles, description)
        
        print(f"\nСтруктура создана для модели: {model_name}")
        print(f"   Создано ориентаций: {len(self.standard_orientations)}")
        print(f"   Путь: {self.results_path / model_name}")
    
    def create_orientation_structure(self, model_name, orient_name, angles, description):
        """
        Создает полную структуру для одной ориентации в results/
        """
        # Папка ориентации в results
        orient_dir = self.results_path / model_name / orient_name
        orient_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"\nСоздаю ориентацию: {model_name}/{orient_name}")
        print(f"   Углы: X={angles[0]}°, Y={angles[1]}°, Z={angles[2]}°")
        
        # 1. Создаем placeholder model.stl
        self.create_stl_placeholder(orient_dir, model_name, orient_name, angles, description)
        
        # 2. Создаем print_info.json с ВСЕМИ данными
        self.create_print_info_json(orient_dir, model_name, orient_name, angles, description)
        
        # 3. Создаем пустой G-code файл
        self.create_gcode_file(orient_dir, model_name, orient_name, angles)
        
        print(f"   Ориентация {orient_name} создана")
    
    def create_stl_placeholder(self, orient_dir, model_name, orient_name, angles, description):
        """Создает placeholder для STL файла в results/"""
        placeholder_stl = orient_dir / "model.stl"
        
        if not placeholder_stl.exists():
            placeholder_content = f"""# Замените этот файл на повернутую версию модели
# Модель: {model_name}
# Ориентация: {orient_name}
# Углы поворота: X={angles[0]}°, Y={angles[1]}°, Z={angles[2]}°
# Описание: {description}
# Дата создания: {datetime.now().strftime("%Y-%m-%d %H:%M")}

ИНСТРУКЦИЯ:
1. Откройте {model_name}.stl из dataset/models/ в CAD-программе
2. Поверните модель на указанные углы:
   - X: {angles[0]}°
   - Y: {angles[1]}°
   - Z: {angles[2]}°
3. Сохраните повернутую модель как STL файл
4. Замените этот файл полученным STL
"""
            
            with open(placeholder_stl, 'w', encoding='utf-8') as f:
                f.write(placeholder_content)
            
            print(f"   Создан: model.stl ({placeholder_stl.stat().st_size} байт)")
    
    def create_print_info_json(self, orient_dir, model_name, orient_name, angles, description):
        """Создает print_info.json с ВСЕМИ данными (включая геометрию)"""
        print_info = {
            "model_name": model_name,
            "orientation_name": orient_name,
            "rotation_info": {
                "angles_degrees": {
                    "x": float(angles[0]),
                    "y": float(angles[1]),
                    "z": float(angles[2])
                },
                "description": description,
                "note": "Углы поворота относительно исходной ориентации"
            },
            "geometry_analysis": {
                "bounding_box_mm": {
                    "width": 0.0,
                    "depth": 0.0,
                    "height": 0.0,
                    "note": "Заполнить после анализа STL"
                },
                "volume_cm3": 0.0,
                "surface_area_cm2": 0.0,
                "analysis_date": "",
                "status": "pending_analysis"
            },
            "print_session": {
                "print_date": "",
                "printer_used": "Ender-3 V2",
                "operator": "",
                "status": "planned"
            },
            "estimated_values": {
                "time_minutes": 0,
                "material_g": 0.0,
                "layer_count": 0,
                "filament_length_m": 0.0,
                "note": "Заполнить после оценки Cura или печати"
            },
            "status": "not_printed",
            "created_date": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat()
        }
        
        print_info_file = orient_dir / "print_info.json"
        with open(print_info_file, 'w', encoding='utf-8') as f:
            json.dump(print_info, f, indent=2, ensure_ascii=False)
        
        print(f"   Создан: print_info.json (с геометрией и углами)")
    
    def create_gcode_file(self, orient_dir, model_name, orient_name, angles):
        """Создает пустой G-code файл"""
        gcode_file = orient_dir / "output.gcode"
        
        if not gcode_file.exists():
            gcode_content = f"""; CURA PROFILE FOR DATASET
; Model: {model_name}
; Orientation: {orient_name}
; Rotation angles: X={angles[0]}°, Y={angles[1]}°, Z={angles[2]}°
; Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
; Purpose: Empty template - replace with real G-code from Cura

; ============================================
; НАСТРОЙКИ ПЕЧАТИ:
; Принтер: Ender-3 V2
; Материал: PLA
; Высота слоя: 0.2mm
; Заполнение: 20%
; ============================================

M117 {model_name}/{orient_name}
G21 ; Set units to millimeters
G90 ; Absolute positioning
M82 ; Extruder absolute mode

; Нагрев
M140 S60 ; Bed temperature
M104 S210 ; Nozzle temperature
G28 ; Home all axes
M190 S60 ; Wait for bed
M109 S210 ; Wait for nozzle

; Начало печати
G1 Z0.2 F1200 ; Layer height
G1 X10 Y10 F6000 ; Start position
M117 Printing...

; ============================================
; ВНИМАНИЕ: Замените этот файл реальным G-code из Cura
; Инструкция:
; 1. Откройте model.stl из этой папки в Cura 5.11
; 2. Настройте параметры печати
; 3. Экспортируйте G-code в этот файл
; ============================================

; Завершение (placeholder)
G1 Z10 F6000 ; Move up
G28 X0 Y0 ; Home X and Y
M84 ; Disable motors
M104 S0 ; Hotend off
M140 S0 ; Bed off
M117 Print complete

; Информация для анализа
;TIME:0
;Filament used: 0.0m
;Layer count: 0
"""
            
            with open(gcode_file, 'w', encoding='utf-8') as f:
                f.write(gcode_content)
            
            print(f"   Создан: output.gcode ({gcode_file.stat().st_size} байт)")
    
    def create_for_all_models(self):
        """Создает структуру для всех моделей"""
        stl_files = list(self.models_path.glob("*.stl"))
        
        if not stl_files:
            print("Нет STL файлов в папке models/")
            print("   Добавьте STL файлы в: dataset/models/")
            return
        
        print(f"\nНайдено моделей: {len(stl_files)}")
        
        for stl_file in stl_files:
            model_name = stl_file.stem
            self.create_structure_for_model(model_name)
        
        print(f"\n" + "="*50)
        print(f"СТРУКТУРА СОЗДАНА ДЛЯ {len(stl_files)} МОДЕЛЕЙ")
        print("="*50)
    
    def print_summary(self):
        """Выводит статистику"""
        print(f"\n" + "="*50)
        print("СТАТИСТИКА СОЗДАННОЙ СТРУКТУРЫ")
        print("="*50)
        
        # Считаем модели в results
        models = list(self.results_path.iterdir())
        models = [m for m in models if m.is_dir()]
        
        print(f"Моделей: {len(models)}")
        
        total_orientations = 0
        for model_dir in models:
            orientations = list(model_dir.iterdir())
            orientations = [o for o in orientations if o.is_dir()]
            total_orientations += len(orientations)
            
            print(f"  |-- {model_dir.name}: {len(orientations)} ориентаций")
            for orient in orientations:
                # Проверяем файлы
                files = list(orient.glob("*"))
                file_list = ", ".join([f.name for f in files])
                print(f"  |    |-- {orient.name}: {file_list}")
        
        print(f"Всего ориентаций: {total_orientations}")
        
        # Считаем файлы
        json_files = list(self.results_path.rglob("*.json"))
        stl_files = list(self.results_path.rglob("*.stl"))
        gcode_files = list(self.results_path.rglob("*.gcode"))
        
        print(f"JSON файлов: {len(json_files)}")
        print(f"STL файлов: {len(stl_files)}")
        print(f"G-code файлов: {len(gcode_files)}")
        
        print(f"\nСТРУКТУРА:")
        print(f"  dataset/")
        print(f"  |-- models/                    # Исходные STL")
        print(f"  |    |-- [model_name].stl")
        print(f"  |-- results/                   # ВСЕ остальное")
        print(f"       |-- [model_name]/")
        print(f"           |-- default/")
        print(f"           |    |-- model.stl     # placeholder")
        print(f"           |    |-- print_info.json # все данные")
        print(f"           |    |-- output.gcode  # пустой")
        print(f"           |-- flat/")
        print(f"           |-- optimal/")
        
        print(f"\nПРИМЕР print_info.json:")
        print(f'''  {{
    "model_name": "1_16.12",
    "orientation_name": "default",
    "rotation_info": {{
      "angles_degrees": {{
        "x": 0.0,
        "y": 0.0,
        "z": 0.0
      }},
      "description": "Оригинальная ориентация"
    }},
    "geometry_analysis": {{
      "bounding_box_mm": {{
        "width": 0.0,
        "depth": 0.0,
        "height": 0.0
      }},
      "volume_cm3": 0.0,
      "surface_area_cm2": 0.0
    }},
    "estimated_values": {{
      "time_minutes": 0,
      "material_g": 0.0,
      "layer_count": 0,
      "filament_length_m": 0.0
    }},
    "status": "not_printed"
  }}''')
        
        print(f"\nДАЛЬНЕЙШИЕ ШАГИ:")
        print(f"  1. Замените placeholder model.stl реальными повернутыми моделями")
        print(f"  2. Запустите геометрический анализ для заполнения geometry_analysis")
        print(f"  3. Загрузите model.stl в Cura, замените output.gcode")
        print(f"  4. Заполните estimated_values из Cura")
        print("="*50)

def main():
    """Основная функция"""
    
    print("="*60)
    print("МИНИМАЛЬНАЯ СТРУКТУРА ДАТАСЕТА")
    print("="*60)
    print("Создает только results/[model]/[orientation]/")
    print("Включает: model.stl, print_info.json, output.gcode")
    print("="*60)
    
    creator = MinimalStructureCreator()
    
    # Обработка аргументов командной строки
    if len(sys.argv) > 1:
        model_name = sys.argv[1]
        if model_name.lower() == "all":
            creator.create_for_all_models()
        else:
            if model_name.lower().endswith('.stl'):
                model_name = model_name[:-4]
            creator.create_structure_for_model(model_name)
    else:
        print("\nВЫБЕРИТЕ РЕЖИМ:")
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
                print("Имя модели не указано")
        else:
            print("Неверный выбор")
    
    creator.print_summary()

if __name__ == "__main__":
    main()
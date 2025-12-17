"""
FINAL_ANALYZER.py - Финальный анализатор (только G-code данные)
Работает даже с placeholder STL файлами
"""

import json
import re
from pathlib import Path
from datetime import datetime
import sys

class FinalAnalyzer:
    def __init__(self, dataset_path="dataset"):
        self.dataset_path = Path(dataset_path).resolve()
        self.results_path = self.dataset_path / "results"
        
        print("="*70)
        print("FINAL DATASET ANALYZER - G-CODE ONLY")
        print("="*70)
        print("⚠️  ВНИМАНИЕ: STL файлы - placeholder, используем только G-code данные")
        print("="*70)
        print(f"📁 Dataset path: {self.dataset_path}")
        print(f"📂 Results path: {self.results_path}")
        print("="*70)
    
    def is_valid_stl(self, stl_path: Path):
        """Проверяет, является ли STL файл валидным (не placeholder)"""
        if not stl_path.exists():
            return False
        
        file_size = stl_path.stat().st_size
        if file_size < 1000:  # Меньше 1KB - вероятно placeholder
            return False
        
        # Проверяем первые несколько строк
        try:
            with open(stl_path, 'r', encoding='utf-8', errors='ignore') as f:
                first_line = f.readline().strip()
                # Если начинается с комментария - placeholder
                if first_line.startswith('#') or first_line.startswith(';'):
                    return False
        except:
            pass
        
        return True
    
    def extract_angles_from_name(self, orient_name: str):
        """Извлекает углы поворота из имени ориентации"""
        orient_name = orient_name.lower()
        
        # Стандартные ориентации
        if orient_name == "default":
            return {"x": 0.0, "y": 0.0, "z": 0.0}
        elif orient_name == "flat":
            return {"x": 90.0, "y": 0.0, "z": 0.0}
        elif orient_name == "optimal":
            return {"x": 45.0, "y": 30.0, "z": 0.0}
        else:
            return {"x": 0.0, "y": 0.0, "z": 0.0}
    
    def parse_gcode_comprehensive(self, gcode_path: Path):
        """Комплексный парсинг G-code файла"""
        print(f"   ⚙️  Анализ G-code...")
        
        if not gcode_path.exists():
            return self.get_empty_gcode_data("Файл не найден")
        
        file_size = gcode_path.stat().st_size
        if file_size < 100:
            return self.get_empty_gcode_data("Файл слишком мал")
        
        try:
            with open(gcode_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(50000)  # Читаем первые 50KB (достаточно для заголовка)
            
            estimations = {
                'time_minutes': 0,
                'material_g': 0.0,
                'layer_count': 0,
                'filament_length_m': 0.0,
                'success': False,
                'notes': []
            }
            
            lines = content.split('\n')
            
            for line in lines:
                line_stripped = line.strip()
                
                # Время печати - различные форматы
                if line_stripped.startswith(';TIME:'):
                    try:
                        time_str = line_stripped[6:].strip()
                        if ':' in time_str:  # Формат HH:MM:SS
                            parts = time_str.split(':')
                            if len(parts) == 3:
                                h, m, s = map(int, parts)
                                estimations['time_minutes'] = h * 60 + m + s/60
                                estimations['success'] = True
                                estimations['notes'].append("Время из TIME:HH:MM:SS")
                        else:  # Секунды
                            seconds = int(float(time_str))
                            estimations['time_minutes'] = seconds / 60
                            estimations['success'] = True
                            estimations['notes'].append("Время из TIME:секунды")
                    except:
                        pass
                
                # Филамент использованный
                elif ';Filament used:' in line_stripped:
                    # Ищем значение в метрах
                    match = re.search(r'([\d.]+)\s*m', line_stripped)
                    if match:
                        try:
                            filament_m = float(match.group(1))
                            estimations['filament_length_m'] = filament_m
                            
                            # Конвертация в граммы
                            filament_diameter = 1.75  # mm
                            density_pla = 1.25  # g/cm³
                            radius_cm = filament_diameter / 20  # в см
                            volume_cm3 = filament_m * 100 * 3.14159 * radius_cm**2
                            estimations['material_g'] = round(volume_cm3 * density_pla, 2)
                            estimations['success'] = True
                            estimations['notes'].append("Материал из Filament used")
                        except:
                            pass
                
                # Количество слоев
                elif ';LAYER_COUNT:' in line_stripped:
                    match = re.search(r'(\d+)', line_stripped)
                    if match:
                        try:
                            estimations['layer_count'] = int(match.group(1))
                            estimations['notes'].append("Слои из LAYER_COUNT")
                        except:
                            pass
                elif ';Layer count:' in line_stripped:
                    match = re.search(r'(\d+)', line_stripped)
                    if match:
                        try:
                            estimations['layer_count'] = int(match.group(1))
                            estimations['notes'].append("Слои из Layer count")
                        except:
                            pass
                
                # Альтернативный формат времени
                elif ';Print time:' in line_stripped:
                    # Пробуем разные форматы
                    # 1. В минутах
                    match = re.search(r'(\d+)\s*min', line_stripped, re.IGNORECASE)
                    if match:
                        try:
                            estimations['time_minutes'] = int(match.group(1))
                            estimations['success'] = True
                            estimations['notes'].append("Время из Print time:min")
                        except:
                            pass
                    
                    # 2. В часах и минутах
                    match = re.search(r'(\d+)\s*h.*?(\d+)\s*m', line_stripped, re.IGNORECASE)
                    if match:
                        try:
                            h, m = map(int, match.groups())
                            estimations['time_minutes'] = h * 60 + m
                            estimations['success'] = True
                            estimations['notes'].append("Время из Print time:h m")
                        except:
                            pass
                
                # Объем филамента в mm³
                elif ';Filament used:' in line_stl and 'mm' in line_stripped:
                    match = re.search(r'([\d.]+)\s*mm', line_stripped)
                    if match:
                        try:
                            mm3 = float(match.group(1))
                            estimations['material_g'] = mm3 * 0.00125  # PLA плотность
                            estimations['success'] = True
                            estimations['notes'].append("Материал из Filament used:mm³")
                        except:
                            pass
            
            if estimations['success']:
                print(f"     ✅ Время: {estimations['time_minutes']:.0f} мин")
                print(f"     ✅ Материал: {estimations['material_g']:.1f} г")
                if estimations['layer_count'] > 0:
                    print(f"     ✅ Слоев: {estimations['layer_count']}")
            else:
                print(f"     ⚠️  Не найдены оценки в G-code")
            
            return estimations
            
        except Exception as e:
            print(f"     ❌ Ошибка: {str(e)[:100]}")
            return self.get_empty_gcode_data(f"Ошибка: {str(e)[:50]}")
    
    def get_empty_gcode_data(self, reason=""):
        """Возвращает пустые данные с причиной"""
        return {
            'time_minutes': 0,
            'material_g': 0.0,
            'layer_count': 0,
            'filament_length_m': 0.0,
            'success': False,
            'notes': [reason] if reason else []
        }
    
    def update_print_info(self, print_info_path: Path, orient_name: str, gcode_data: dict):
        """Обновляет print_info.json данными из G-code"""
        try:
            with open(print_info_path, 'r', encoding='utf-8') as f:
                print_info = json.load(f)
        except Exception as e:
            print(f"   ❌ Ошибка чтения JSON: {e}")
            return False
        
        try:
            updated = False
            
            # 1. Добавляем/обновляем rotation_info
            angles = self.extract_angles_from_name(orient_name)
            
            if "rotation_info" not in print_info:
                print_info["rotation_info"] = {
                    "angles_degrees": angles,
                    "description": f"{orient_name} ориентация",
                    "updated_date": datetime.now().isoformat()
                }
                updated = True
            
            # 2. Добавляем/обновляем estimated_values из G-code
            if gcode_data['success']:
                new_estimations = {
                    "time_minutes": round(gcode_data['time_minutes']),
                    "material_g": round(gcode_data['material_g'], 2),
                    "layer_count": gcode_data['layer_count'],
                    "filament_length_m": round(gcode_data['filament_length_m'], 2),
                    "analysis_date": datetime.now().isoformat(),
                    "source": "gcode_analysis",
                    "notes": gcode_data.get('notes', [])
                }
                
                # Обновляем только если данные новые или лучше
                current_estimations = print_info.get("estimated_values", {})
                if (not current_estimations or 
                    current_estimations.get("time_minutes", 0) == 0 or
                    current_estimations.get("source") == "volume_based_estimation"):
                    
                    print_info["estimated_values"] = new_estimations
                    updated = True
            
            # 3. Добавляем note о STL placeholder
            if "geometry_analysis" in print_info:
                geometry = print_info["geometry_analysis"]
                if geometry.get("volume_cm3", 0) == 0:
                    print_info["geometry_analysis"]["note"] = "STL файл - placeholder, геометрия не анализирована"
                    updated = True
            else:
                print_info["geometry_analysis"] = {
                    "bounding_box_mm": {
                        "width": 0.0,
                        "depth": 0.0,
                        "height": 0.0
                    },
                    "volume_cm3": 0.0,
                    "surface_area_cm2": 0.0,
                    "analysis_date": datetime.now().isoformat(),
                    "status": "placeholder_stl",
                    "note": "STL файл - placeholder, геометрия не анализирована"
                }
                updated = True
            
            # 4. Обновляем общие поля
            print_info["last_updated"] = datetime.now().isoformat()
            
            if "print_session" in print_info:
                print_info["print_session"]["last_updated"] = datetime.now().isoformat()
                print_info["print_session"]["status"] = "gcode_analyzed"
            
            print_info["analysis_status"] = "gcode_only" if updated else "already_updated"
            
            # Сохраняем
            with open(print_info_path, 'w', encoding='utf-8') as f:
                json.dump(print_info, f, indent=2)
            
            if updated:
                print(f"   ✅ print_info.json обновлен (G-code данные)")
            else:
                print(f"   ℹ️  print_info.json уже актуален")
            
            return updated
            
        except Exception as e:
            print(f"   ❌ Ошибка обновления JSON: {type(e).__name__}: {str(e)[:100]}")
            return False
    
    def analyze_dataset(self):
        """Основной анализ датасета"""
        print("\n" + "="*70)
        print("АНАЛИЗ ДАТАСЕТА (ТОЛЬКО G-CODE)")
        print("="*70)
        
        # Находим все print_info.json файлы
        print_info_files = list(self.results_path.rglob("print_info.json"))
        
        if not print_info_files:
            print("❌ Не найдено print_info.json файлов")
            return
        
        print(f"🔍 Найдено ориентаций: {len(print_info_files)}")
        print("="*70)
        
        stats = {
            'total': len(print_info_files),
            'updated': 0,
            'already_updated': 0,
            'errors': 0,
            'gcode_success': 0
        }
        
        for i, print_info_path in enumerate(print_info_files, 1):
            try:
                orient_dir = print_info_path.parent
                
                # Получаем имена
                rel_path = orient_dir.relative_to(self.results_path)
                if len(rel_path.parts) >= 2:
                    model_name, orient_name = rel_path.parts[0], rel_path.parts[1]
                    
                    print(f"\n[{i}/{stats['total']}] {model_name}/{orient_name}")
                    
                    # Проверяем файлы
                    stl_path = orient_dir / "model.stl"
                    gcode_path = orient_dir / "output.gcode"
                    
                    # Проверяем STL файл
                    stl_valid = self.is_valid_stl(stl_path)
                    if not stl_valid:
                        stl_size = stl_path.stat().st_size if stl_path.exists() else 0
                        print(f"   📁 STL: placeholder ({stl_size} байт)")
                    
                    # Анализируем G-code
                    gcode_data = {}
                    if gcode_path.exists():
                        gcode_data = self.parse_gcode_comprehensive(gcode_path)
                        if gcode_data['success']:
                            stats['gcode_success'] += 1
                    else:
                        print(f"   ⚠️  G-code не найден")
                        gcode_data = self.get_empty_gcode_data("G-code файл не найден")
                    
                    # Обновляем print_info.json
                    if self.update_print_info(print_info_path, orient_name, gcode_data):
                        stats['updated'] += 1
                    else:
                        stats['already_updated'] += 1
                        
                else:
                    print(f"\n[{i}/{stats['total']}] ❌ Неверный путь: {rel_path}")
                    stats['errors'] += 1
                    
            except Exception as e:
                print(f"\n[{i}/{stats['total']}] ❌ Критическая ошибка: {e}")
                stats['errors'] += 1
        
        # Статистика
        print(f"\n{'='*70}")
        print("📊 ИТОГОВАЯ СТАТИСТИКА")
        print(f"{'='*70}")
        print(f"📁 Всего ориентаций: {stats['total']}")
        print(f"✅ Обновлено файлов: {stats['updated']}")
        print(f"ℹ️  Уже актуальны: {stats['already_updated']}")
        print(f"❌ Ошибки: {stats['errors']}")
        print(f"⚙️  G-code успешно проанализирован: {stats['gcode_success']}/{stats['total']}")
        print(f"{'='*70}")
        
        return stats
    
    def create_summary_report(self):
        """Создает сводный отчет по датасету"""
        print("\n" + "="*70)
        print("📋 СВОДНЫЙ ОТЧЕТ ПО ДАТАСЕТУ")
        print("="*70)
        
        # Собираем статистику по моделям
        models = {}
        
        for print_info_path in self.results_path.rglob("print_info.json"):
            try:
                with open(print_info_path, 'r') as f:
                    data = json.load(f)
                
                model_name = data.get("model_name", "unknown")
                orient_name = data.get("orientation_name", "unknown")
                
                if model_name not in models:
                    models[model_name] = {
                        'orientations': [],
                        'total_time': 0,
                        'total_material': 0,
                        'has_geometry': False
                    }
                
                # Собираем информацию об ориентации
                orient_info = {
                    'name': orient_name,
                    'time': data.get("estimated_values", {}).get("time_minutes", 0),
                    'material': data.get("estimated_values", {}).get("material_g", 0),
                    'has_geometry': data.get("geometry_analysis", {}).get("volume_cm3", 0) > 0
                }
                
                models[model_name]['orientations'].append(orient_info)
                models[model_name]['total_time'] += orient_info['time']
                models[model_name]['total_material'] += orient_info['material']
                if orient_info['has_geometry']:
                    models[model_name]['has_geometry'] = True
                    
            except:
                continue
        
        # Выводим отчет
        print(f"📦 Моделей: {len(models)}")
        print(f"🎯 Ориентаций всего: {sum(len(m['orientations']) for m in models.values())}")
        print(f"⏱️  Общее время печати: {sum(m['total_time'] for m in models.values()):.0f} мин")
        print(f"📊 Общий материал: {sum(m['total_material'] for m in models.values()):.1f} г")
        print(f"📐 Моделей с геометрией: {sum(1 for m in models.values() if m['has_geometry'])}")
        
        print(f"\n📋 ДЕТАЛИ ПО МОДЕЛЯМ:")
        for model_name, data in sorted(models.items()):
            print(f"\n  {model_name}:")
            print(f"    Ориентаций: {len(data['orientations'])}")
            print(f"    Время: {data['total_time']:.0f} мин")
            print(f"    Материал: {data['total_material']:.1f} г")
            print(f"    Геометрия: {'есть' if data['has_geometry'] else 'нет (placeholder)'}")
            
            for orient in data['orientations']:
                print(f"      - {orient['name']}: {orient['time']:.0f} мин, {orient['material']:.1f} г")

def main():
    """Основная функция"""
    
    print("\n" + "="*60)
    print("FINAL DATASET ANALYZER")
    print("="*60)
    print("Анализирует только G-code файлы (STL - placeholder)")
    print("="*60)
    
    analyzer = FinalAnalyzer()
    
    # Запускаем анализ
    stats = analyzer.analyze_dataset()
    
    # Создаем отчет
    if stats:
        analyzer.create_summary_report()
    
    print("\n🎯 АНАЛИЗ ЗАВЕРШЕН!")
    print("="*60)
    
    if stats and stats['gcode_success'] > 0:
        print(f"\n✅ УСПЕШНО: Проанализировано {stats['gcode_success']} G-code файлов")
        print(f"\n📋 ЧТО СДЕЛАНО:")
        print(f"   1. Проанализированы G-code файлы")
        print(f"   2. Извлечены оценки печати (время, материал, слои)")
        print(f"   3. Обновлены print_info.json файлы")
        print(f"   4. Добавлены углы поворота для каждой ориентации")
        print(f"   5. Отмечено, что STL файлы - placeholder")
        
        print(f"\n🔍 ПРОВЕРЬТЕ РЕЗУЛЬТАТ:")
        print(f'   python -c "')
        print(f'   import json')
        print(f'   f = open(\'dataset/results/1_16.12/default/print_info.json\')')
        print(f'   d = json.load(f)')
        print(f'   "')
    else:
        print("\n⚠️  Проблемы с анализом")
        print("   Проверьте, что G-code файлы содержат данные Cura")

if __name__ == "__main__":
    main()
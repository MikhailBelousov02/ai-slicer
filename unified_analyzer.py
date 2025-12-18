"""
UNIFIED_ANALYZER_FIXED.py - Исправленный анализатор с обработкой ошибок
"""

import trimesh
import numpy as np
import json
import re
from pathlib import Path
from datetime import datetime
import sys

class UnifiedAnalyzerFixed:
    def __init__(self, dataset_path="dataset"):
        self.dataset_path = Path(dataset_path).resolve()
        self.results_path = self.dataset_path / "results"
        
        print("="*70)
        print("UNIFIED DATASET ANALYZER - FIXED VERSION")
        print("="*70)
        print(f"📁 Dataset path: {self.dataset_path}")
        print(f"📂 Results path: {self.results_path}")
        print("="*70)
    
    def analyze_stl_geometry_fixed(self, stl_path: Path):
        """Анализирует геометрию STL файла с улучшенной обработкой ошибок"""
        print(f"   📐 Анализ геометрии...")
        
        try:
            # Проверяем размер файла
            file_size = stl_path.stat().st_size
            if file_size < 100:
                print(f"     ⚠️  Файл слишком мал ({file_size} байт), возможно placeholder")
                return None
            
            # Пробуем разные способы загрузки
            mesh = None
            try:
                mesh = trimesh.load(str(stl_path))
            except Exception as load_error:
                print(f"     ⚠️  Ошибка загрузки trimesh: {str(load_error)[:100]}")
                # Пробуем альтернативный метод
                try:
                    mesh = trimesh.load_mesh(str(stl_path))
                except:
                    pass
            
            if mesh is None:
                print(f"     ❌ Не удалось загрузить STL файл")
                return None
            
            # Проверяем, что mesh имеет нужные атрибуты
            if not hasattr(mesh, 'bounds') or mesh.bounds is None:
                print(f"     ❌ Нет данных bounds в mesh")
                return None
            
            # Получаем границы модели
            bounds = mesh.bounds
            if bounds is None or len(bounds) < 2:
                print(f"     ❌ Неверный формат bounds")
                return None
            
            dimensions = bounds[1] - bounds[0]
            
            # Проверяем расчеты
            volume_mm3 = mesh.volume if hasattr(mesh, 'volume') else 0
            area_mm2 = mesh.area if hasattr(mesh, 'area') else 0
            
            geometry_data = {
                "bounding_box_mm": {
                    "width": float(dimensions[0]),
                    "depth": float(dimensions[1]),
                    "height": float(dimensions[2])
                },
                "volume_cm3": float(volume_mm3 / 1000) if volume_mm3 > 0 else 0.0,
                "surface_area_cm2": float(area_mm2 / 100) if area_mm2 > 0 else 0.0,
                "analysis_date": datetime.now().isoformat(),
                "status": "analyzed"
            }
            
            print(f"     ✅ Размеры: {dimensions[0]:.1f}×{dimensions[1]:.1f}×{dimensions[2]:.1f} мм")
            if volume_mm3 > 0:
                print(f"     ✅ Объем: {volume_mm3/1000:.1f} см³")
            if area_mm2 > 0:
                print(f"     ✅ Площадь: {area_mm2/100:.1f} см²")
            
            return geometry_data
            
        except Exception as e:
            print(f"     ❌ Критическая ошибка: {type(e).__name__}: {str(e)[:100]}")
            return None
    
    def extract_angles_from_path(self, folder_path: Path):
        """Извлекает углы поворота из имени папки ориентации"""
        orient_name = folder_path.name.lower()
        
        # Определяем углы на основе имени ориентации
        if orient_name == "default":
            return {"x": 0.0, "y": 0.0, "z": 0.0}
        elif orient_name == "flat":
            return {"x": 90.0, "y": 0.0, "z": 0.0}
        elif orient_name == "optimal":
            return {"x": 45.0, "y": 30.0, "z": 0.0}
        else:
            # Пробуем извлечь из имени
            match = re.search(r'x([\d.-]+).*y([\d.-]+).*z([\d.-]+)', orient_name)
            if match:
                try:
                    return {
                        "x": float(match.group(1)),
                        "y": float(match.group(2)), 
                        "z": float(match.group(3))
                    }
                except:
                    pass
            return {"x": 0.0, "y": 0.0, "z": 0.0}
    
    def parse_gcode_file_fixed(self, gcode_path: Path):
        """Парсит G-code файл с улучшенной обработкой"""
        print(f"   ⚙️  Анализ G-code...")
        
        if not gcode_path.exists():
            print(f"     ⚠️  Файл не найден")
            return self.get_empty_gcode_data()
        
        try:
            file_size = gcode_path.stat().st_size
            if file_size < 50:
                print(f"     ⚠️  Файл слишком мал ({file_size} байт)")
                return self.get_empty_gcode_data()
            
            with open(gcode_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Проверяем, что это похоже на G-code
            if not any(keyword in content for keyword in ['G1', 'G0', 'G28', 'M104', 'M140']):
                print(f"     ⚠️  Файл не похож на G-code")
                return self.get_empty_gcode_data()
            
            estimations = self.extract_gcode_estimations(content)
            
            if estimations['success']:
                print(f"     ✅ Время: {estimations['time_minutes']:.0f} мин")
                print(f"     ✅ Материал: {estimations['material_g']:.1f} г")
                if estimations['layer_count'] > 0:
                    print(f"     ✅ Слоев: {estimations['layer_count']}")
            else:
                print(f"     ⚠️  Не найдены оценки в G-code")
            
            return estimations
            
        except Exception as e:
            print(f"     ❌ Ошибка чтения G-code: {str(e)[:100]}")
            return self.get_empty_gcode_data()
    
    def extract_gcode_estimations(self, content: str):
        """Извлекает оценки из содержимого G-code"""
        estimations = {
            'time_minutes': 0,
            'material_g': 0.0,
            'layer_count': 0,
            'filament_length_m': 0.0,
            'success': False
        }
        
        lines = content.split('\n')
        
        for line in lines:
            line_stripped = line.strip()
            
            # Время печати
            if line_stripped.startswith(';TIME:'):
                try:
                    time_str = line_stripped[6:].strip()
                    # Может быть в секундах или минутах
                    if ':' in time_str:  # Формат HH:MM:SS
                        parts = time_str.split(':')
                        if len(parts) == 3:
                            h, m, s = map(int, parts)
                            estimations['time_minutes'] = h * 60 + m + s/60
                            estimations['success'] = True
                    else:  # Просто секунды
                        seconds = int(time_str)
                        estimations['time_minutes'] = seconds / 60
                        estimations['success'] = True
                except:
                    pass
            
            # Филамент использованный
            elif ';Filament used:' in line_stripped:
                match = re.search(r'([\d.]+)\s*m', line_stripped)
                if match:
                    try:
                        filament_m = float(match.group(1))
                        estimations['filament_length_m'] = filament_m
                        
                        # Конвертируем в граммы
                        filament_diameter = 1.75  # mm
                        density_pla = 1.25  # g/cm³
                        radius_cm = filament_diameter / 20  # в см
                        volume_cm3 = filament_m * 100 * 3.14159 * radius_cm**2
                        estimations['material_g'] = volume_cm3 * density_pla
                        estimations['success'] = True
                    except:
                        pass
            
            # Количество слоев
            elif ';LAYER_COUNT:' in line_stripped or ';Layer count:' in line_stripped:
                match = re.search(r'(\d+)', line_stripped)
                if match:
                    try:
                        estimations['layer_count'] = int(match.group(1))
                    except:
                        pass
            
            # Альтернативный формат времени
            elif ';Print time:' in line_stripped:
                # Пытаемся извлечь время в минутах
                match = re.search(r'(\d+)\s*min', line_stripped, re.IGNORECASE)
                if match:
                    try:
                        estimations['time_minutes'] = int(match.group(1))
                        estimations['success'] = True
                    except:
                        pass
        
        return estimations
    
    def get_empty_gcode_data(self):
        """Возвращает пустые данные G-code"""
        return {
            'time_minutes': 0,
            'material_g': 0.0,
            'layer_count': 0,
            'filament_length_m': 0.0,
            'success': False
        }
    
    def process_orientation_fixed(self, orient_dir: Path, model_name: str, orient_name: str):
        """Обрабатывает одну ориентацию с улучшенной обработкой ошибок"""
        print(f"\n🔍 {model_name}/{orient_name}")
        
        # Пути к файлам
        stl_path = orient_dir / "model.stl"
        gcode_path = orient_dir / "output.gcode"
        print_info_path = orient_dir / "print_info.json"
        
        # Проверяем существование файлов
        files_exist = {
            'stl': stl_path.exists(),
            'gcode': gcode_path.exists() and gcode_path.stat().st_size > 100,
            'json': print_info_path.exists()
        }
        
        print(f"   📁 Файлы: ", end="")
        file_status = []
        if files_exist['stl']:
            stl_size = stl_path.stat().st_size
            file_status.append(f"STL({stl_size} байт)")
        else:
            file_status.append("STL(нет)")
            
        if files_exist['gcode']:
            gcode_size = gcode_path.stat().st_size
            file_status.append(f"G-code({gcode_size} байт)")
        else:
            file_status.append("G-code(нет)")
            
        if files_exist['json']:
            file_status.append("JSON(есть)")
        else:
            file_status.append("JSON(нет)")
        
        print(", ".join(file_status))
        
        if not files_exist['json']:
            print(f"   ❌ print_info.json не найден")
            return False
        
        # Загружаем существующий print_info.json
        try:
            with open(print_info_path, 'r', encoding='utf-8') as f:
                print_info = json.load(f)
        except Exception as e:
            print(f"   ❌ Ошибка чтения JSON: {e}")
            return False
        
        # 1. Извлекаем углы поворота
        angles = self.extract_angles_from_path(orient_dir)
        
        # 2. Анализируем геометрию STL (если файл существует)
        geometry_data = None
        if files_exist['stl']:
            geometry_data = self.analyze_stl_geometry_fixed(stl_path)
        
        # 3. Анализируем G-code (если файл существует)
        gcode_data = None
        if files_exist['gcode']:
            gcode_data = self.parse_gcode_file_fixed(gcode_path)
        
        # 4. Обновляем print_info.json
        try:
            updated = False
            
            # Обновляем rotation_info
            if "rotation_info" not in print_info or not print_info["rotation_info"]:
                print_info["rotation_info"] = {
                    "angles_degrees": angles,
                    "description": f"{orient_name} ориентация",
                    "updated_date": datetime.now().isoformat()
                }
                updated = True
            
            # Обновляем geometry_analysis если есть данные
            if geometry_data and ("geometry_analysis" not in print_info or 
                                print_info["geometry_analysis"].get("volume_cm3", 0) == 0):
                print_info["geometry_analysis"] = geometry_data
                updated = True
            
            # Обновляем estimated_values если есть данные из G-code
            if gcode_data and gcode_data['success'] and ("estimated_values" not in print_info or 
                                                       print_info["estimated_values"].get("time_minutes", 0) == 0):
                print_info["estimated_values"] = {
                    "time_minutes": round(gcode_data['time_minutes']),
                    "material_g": round(gcode_data['material_g'], 2),
                    "layer_count": gcode_data['layer_count'],
                    "filament_length_m": round(gcode_data['filament_length_m'], 2),
                    "analysis_date": datetime.now().isoformat(),
                    "source": "gcode_analysis"
                }
                updated = True
            
            # Если нет данных G-code, но есть геометрия, можем сделать примерные оценки
            elif geometry_data and ("estimated_values" not in print_info or 
                                  print_info["estimated_values"].get("time_minutes", 0) == 0):
                volume = geometry_data.get("volume_cm3", 0)
                if volume > 0:
                    # Примерные оценки на основе объема
                    print_info["estimated_values"] = {
                        "time_minutes": round(volume * 10),  # 10 мин на см³
                        "material_g": round(volume * 1.25, 2),  # PLA плотность
                        "layer_count": 0,
                        "filament_length_m": round(volume * 1.25 / 0.003, 2),
                        "analysis_date": datetime.now().isoformat(),
                        "source": "volume_based_estimation",
                        "note": "Оценка на основе объема"
                    }
                    updated = True
            
            # Обновляем даты
            print_info["last_updated"] = datetime.now().isoformat()
            if "print_session" in print_info:
                print_info["print_session"]["last_updated"] = datetime.now().isoformat()
                print_info["print_session"]["status"] = "analyzed"
            
            print_info["analysis_status"] = "completed" if updated else "no_changes"
            
            # Сохраняем обновленный файл
            with open(print_info_path, 'w', encoding='utf-8') as f:
                json.dump(print_info, f, indent=2)
            
            if updated:
                print(f"   ✅ print_info.json обновлен")
            else:
                print(f"   ℹ️  print_info.json уже актуален")
            return updated
            
        except Exception as e:
            print(f"   ❌ Ошибка обновления JSON: {type(e).__name__}: {str(e)[:100]}")
            return False
    
    def analyze_all_models_with_fallback(self):
        """Анализирует все модели с обработкой ошибок и fallback"""
        print("\n" + "="*70)
        print("ПОЛНЫЙ АНАЛИЗ ДАТАСЕТА С ОБРАБОТКОЙ ОШИБОК")
        print("="*70)
        
        # Находим все папки с print_info.json
        print_info_files = list(self.results_path.rglob("print_info.json"))
        
        if not print_info_files:
            print("❌ Не найдено print_info.json файлов")
            return 0, 0
        
        print(f"🔍 Найдено ориентаций: {len(print_info_files)}")
        
        results = {
            'total': len(print_info_files),
            'success': 0,
            'no_changes': 0,
            'errors': 0,
            'problem_files': []
        }
        
        for i, print_info_path in enumerate(print_info_files, 1):
            try:
                orient_dir = print_info_path.parent
                
                # Получаем имена модели и ориентации
                rel_path = orient_dir.relative_to(self.results_path)
                if len(rel_path.parts) >= 2:
                    model_name, orient_name = rel_path.parts[0], rel_path.parts[1]
                    
                    print(f"\n[{i}/{results['total']}] ", end="")
                    success = self.process_orientation_fixed(orient_dir, model_name, orient_name)
                    
                    if success:
                        results['success'] += 1
                    else:
                        # Проверяем, была ли это ошибка или просто нет изменений
                        try:
                            with open(print_info_path, 'r') as f:
                                data = json.load(f)
                            if data.get("analysis_status") == "no_changes":
                                results['no_changes'] += 1
                            else:
                                results['errors'] += 1
                                results['problem_files'].append(f"{model_name}/{orient_name}")
                        except:
                            results['errors'] += 1
                            results['problem_files'].append(f"{model_name}/{orient_name}")
                else:
                    print(f"\n[{i}/{results['total']}] ❌ Неверный путь: {rel_path}")
                    results['errors'] += 1
                    results['problem_files'].append(str(rel_path))
                    
            except Exception as e:
                print(f"\n[{i}/{results['total']}] ❌ Критическая ошибка: {e}")
                results['errors'] += 1
                results['problem_files'].append(str(print_info_path))
        
        # Статистика
        print(f"\n{'='*70}")
        print("📊 РЕЗУЛЬТАТЫ АНАЛИЗА")
        print(f"{'='*70}")
        print(f"📁 Всего ориентаций: {results['total']}")
        print(f"✅ Успешно обновлено: {results['success']}")
        print(f"ℹ️  Без изменений: {results['no_changes']}")
        print(f"❌ Ошибки: {results['errors']}")
        
        if results['problem_files']:
            print(f"\n📋 Проблемные файлы (первые 5):")
            for pf in results['problem_files'][:5]:
                print(f"   - {pf}")
            if len(results['problem_files']) > 5:
                print(f"   ... и еще {len(results['problem_files']) - 5}")
        
        return results
    
    def check_and_fix_files(self):
        """Проверяет и исправляет проблемные файлы"""
        print("\n" + "="*70)
        print("ПРОВЕРКА И ИСПРАВЛЕНИЕ ФАЙЛОВ")
        print("="*70)
        
        # Проверяем STL файлы
        stl_files = list(self.results_path.rglob("model.stl"))
        print(f"🔍 Найдено STL файлов: {len(stl_files)}")
        
        problem_stl = []
        for stl_path in stl_files:
            try:
                size = stl_path.stat().st_size
                if size < 100:
                    problem_stl.append((stl_path, f"{size} байт (возможно placeholder)"))
            except:
                problem_stl.append((stl_path, "ошибка доступа"))
        
        if problem_stl:
            print(f"⚠️  Проблемные STL файлы:")
            for path, issue in problem_stl[:3]:
                rel_path = path.relative_to(self.results_path)
                print(f"   - {rel_path}: {issue}")
            if len(problem_stl) > 3:
                print(f"   ... и еще {len(problem_stl) - 3}")
        
        # Проверяем G-code файлы
        gcode_files = list(self.results_path.rglob("output.gcode"))
        print(f"\n🔍 Найдено G-code файлов: {len(gcode_files)}")
        
        return len(stl_files), len(gcode_files)

def main():
    """Основная функция"""
    
    print("\n" + "="*60)
    print("UNIFIED DATASET ANALYZER - FIXED VERSION")
    print("="*60)
    
    analyzer = UnifiedAnalyzerFixed()
    
    # 1. Проверяем файлы
    stl_count, gcode_count = analyzer.check_and_fix_files()
    
    if stl_count == 0:
        print("\n❌ Нет STL файлов для анализа!")
        print("   Убедитесь, что заменили placeholder файлы реальными STL")
        return
    
    # 2. Запускаем анализ
    results = analyzer.analyze_all_models_with_fallback()
    
    print("\n🎯 АНАЛИЗ ЗАВЕРШЕН!")
    print("="*60)
    
    if results['success'] > 0:
        print(f"\n✅ ОБНОВЛЕНО: {results['success']} файлов")
        print(f"📊 ДАННЫЕ В print_info.json:")
        print(f"   • rotation_info - углы поворота")
        print(f"   • geometry_analysis - размеры и объем")
        print(f"   • estimated_values - оценки печати")
        
        # Показываем пример обновленного файла

if __name__ == "__main__":
    main()
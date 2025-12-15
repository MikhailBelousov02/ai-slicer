"""
Скрипт для заполнения analysis.json данными из STL файла
"""

import trimesh
import numpy as np
import json
import sys
from pathlib import Path
from datetime import datetime

def analyze_stl_and_update_json(stl_path):
    """
    Анализирует STL файл и обновляет analysis.json
    """
    print(f"🔍 Анализирую: {stl_path}")
    
    # Проверяем существует ли файл
    if not Path(stl_path).exists():
        print(f"❌ Файл не найден: {stl_path}")
        return False
    
    try:
        # Загружаем STL
        mesh = trimesh.load(stl_path)
        
        # Вычисляем базовые параметры
        bounds = mesh.bounds
        dimensions = bounds[1] - bounds[0]
        
        volume = mesh.volume  # мм³
        surface_area = mesh.area  # мм²
        
        # Центр масс
        if hasattr(mesh, 'center_mass'):
            center_of_mass = mesh.center_mass.tolist()
        else:
            center_of_mass = mesh.centroid.tolist()
        
        # Анализ overhang
        overhang_info = analyze_overhangs(mesh)
        
        # Площадь контакта
        contact_area = calculate_contact_area(mesh)
        
        # Определяем нужны ли поддержки
        requires_supports = determine_supports_needed(overhang_info)
        
        # Оценка объема поддержек
        support_volume = estimate_support_volume(overhang_info)
        
        # Находим analysis.json в той же папке
        stl_dir = Path(stl_path).parent
        analysis_file = stl_dir / "analysis.json"
        
        if not analysis_file.exists():
            print(f"❌ Файл analysis.json не найден в {stl_dir}")
            print(f"   Сначала создайте структуру с auto_analyze_full.py")
            return False
        
        # Загружаем существующий analysis.json
        with open(analysis_file, 'r', encoding='utf-8') as f:
            analysis_data = json.load(f)
        
        # Обновляем данные
        analysis_data["automatic_analysis"].update({
            "bounding_box_mm": {
                "width": float(dimensions[0]),
                "depth": float(dimensions[1]),
                "height": float(dimensions[2])
            },
            "volume_cm3": float(volume / 1000),  # в см³
            "surface_area_cm2": float(surface_area / 100),  # в см²
            "center_of_mass_mm": [float(center_of_mass[0]), 
                                 float(center_of_mass[1]), 
                                 float(center_of_mass[2])],
            "status": "analyzed",
            "analysis_date": datetime.now().isoformat()
        })
        
        analysis_data["support_analysis"].update({
            "requires_supports": requires_supports,
            "max_overhang_angle": float(overhang_info['max_angle']),
            "overhang_area_mm2": float(overhang_info['critical_area']),
            "support_volume_estimate_ml": float(support_volume),
            "note": "Автоматически проанализировано"
        })
        
        analysis_data["contact_area_mm2"] = float(contact_area)
        analysis_data["analysis_status"] = "auto_analyzed"
        analysis_data["last_updated"] = datetime.now().isoformat()
        
        # Сохраняем обновленный файл
        with open(analysis_file, 'w', encoding='utf-8') as f:
            json.dump(analysis_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ analysis.json обновлен: {analysis_file}")
        print(f"   Размеры: {dimensions[0]:.1f}×{dimensions[1]:.1f}×{dimensions[2]:.1f} мм")
        print(f"   Объем: {volume/1000:.1f} см³")
        print(f"   Поддержки: {'Нужны' if requires_supports else 'Не нужны'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка анализа: {e}")
        return False

def analyze_overhangs(mesh, critical_angle=45):
    """Анализирует углы нависания"""
    normals = mesh.face_normals
    vertical = np.array([0, 0, 1])
    
    angles = []
    critical_faces = []
    
    for i, normal in enumerate(normals):
        if np.linalg.norm(normal) > 0:
            cos_angle = np.dot(normal, vertical) / np.linalg.norm(normal)
            angle = np.degrees(np.arccos(np.clip(cos_angle, -1, 1)))
            effective_angle = min(angle, 180 - angle)
            angles.append(effective_angle)
            
            if effective_angle > critical_angle:
                critical_faces.append(i)
    
    if angles:
        max_angle = max(angles)
        critical_area = 0.0
        
        if critical_faces:
            areas = mesh.area_faces[critical_faces]
            critical_area = float(np.sum(areas))
    else:
        max_angle = 0.0
        critical_area = 0.0
    
    return {
        'max_angle': max_angle,
        'critical_area': critical_area,
        'critical_faces': len(critical_faces)
    }

def calculate_contact_area(mesh, tolerance=0.1):
    """Вычисляет площадь контакта со столом"""
    vertices = mesh.vertices
    min_z = vertices[:, 2].min()
    
    # Ищем грани близкие к минимальной Z
    contact_faces = []
    for i, face in enumerate(mesh.faces):
        face_vertices = vertices[face]
        if np.all(np.abs(face_vertices[:, 2] - min_z) < tolerance):
            contact_faces.append(i)
    
    if contact_faces:
        areas = mesh.area_faces[contact_faces]
        return float(np.sum(areas))
    
    return 0.0

def determine_supports_needed(overhang_info, angle_threshold=45, area_threshold=10):
    """Определяет нужны ли поддержки"""
    return (overhang_info['max_angle'] > angle_threshold and 
            overhang_info['critical_area'] > area_threshold)

def estimate_support_volume(overhang_info):
    """Оценивает объем поддержек"""
    base_volume = overhang_info['critical_area'] * 2  # 2мм высота
    multiplier = 1 + (overhang_info['critical_faces'] / 100)
    return base_volume * multiplier

def batch_analyze_all_models(base_path="dataset/orientations"):
    """Анализирует все STL файлы в датасете"""
    base_dir = Path(base_path)
    
    if not base_dir.exists():
        print(f"❌ Папка не найдена: {base_dir}")
        return
    
    stl_files = list(base_dir.rglob("model.stl"))
    
    print(f"🔍 Найдено STL файлов для анализа: {len(stl_files)}")
    
    success_count = 0
    for i, stl_file in enumerate(stl_files, 1):
        print(f"\n[{i}/{len(stl_files)}] ", end="")
        if analyze_stl_and_update_json(stl_file):
            success_count += 1
    
    print(f"\n{'='*50}")
    print(f"📊 РЕЗУЛЬТАТ: {success_count}/{len(stl_files)} файлов проанализировано")
    print(f"{'='*50}")

def main():
    """Основная функция"""
    
    print("="*60)
    print("АНАЛИЗ STL ФАЙЛОВ И ЗАПОЛНЕНИЕ ANALYSIS.JSON")
    print("="*60)
    
    if len(sys.argv) > 1:
        # Анализ конкретного файла
        stl_path = sys.argv[1]
        analyze_stl_and_update_json(stl_path)
    else:
        # Интерактивный режим
        print("\n📋 ВЫБЕРИТЕ РЕЖИМ:")
        print("  1 - Проанализировать все модели в датасете")
        print("  2 - Проанализировать конкретный STL файл")
        
        choice = input("\nВаш выбор (1/2): ").strip()
        
        if choice == "1":
            batch_analyze_all_models()
        elif choice == "2":
            stl_path = input("Введите путь к STL файлу: ").strip()
            if stl_path:
                analyze_stl_and_update_json(stl_path)
            else:
                print("❌ Путь не указан")
        else:
            print("❌ Неверный выбор")
    
    print(f"\nℹ️  Для создания структуры папок используйте:")
    print(f"   python src/auto_analyze_full.py [имя_модели|all]")
    print("="*60)

if __name__ == "__main__":
    main()
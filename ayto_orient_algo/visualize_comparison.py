import trimesh
import numpy as np
from auto_orient import rotation_matrix_from_angles, compute_overhang_area, get_faces_info

def compare_orientations(original_path, oriented_path, threshold_deg=45):
    """Сравнивает исходную и оптимизированную ориентации"""
    
    original = trimesh.load(original_path)
    oriented = trimesh.load(oriented_path)
    
    orig_normals, orig_areas = get_faces_info(original)
    ori_normals, ori_areas = get_faces_info(oriented)
    
    # Для исходной модели считаем площадь нависаний в текущей ориентации
    orig_overhang = compute_overhang_area(orig_normals, orig_areas, [0,0,0], threshold_deg)
    
    # Для оптимизированной — в её ориентации (уже повёрнута)
    ori_overhang = compute_overhang_area(ori_normals, ori_areas, [0,0,0], threshold_deg)
    
    total_orig = np.sum(orig_areas)
    total_ori = np.sum(ori_areas)
    
    print("\n" + "="*60)
    print("🔄 СРАВНЕНИЕ ОРИЕНТАЦИЙ")
    print("="*60)
    
    print(f"\n📊 Исходная модель:")
    print(f"   Высота (Z): {original.bounding_box.extents[2]:.1f} мм")
    print(f"   Площадь нависаний: {orig_overhang:.2f} / {total_orig:.2f} мм² ({orig_overhang/total_orig*100:.1f}%)")
    
    print(f"\n📊 Оптимизированная модель:")
    print(f"   Высота (Z): {oriented.bounding_box.extents[2]:.1f} мм")
    print(f"   Площадь нависаний: {ori_overhang:.2f} / {total_ori:.2f} мм² ({ori_overhang/total_ori*100:.1f}%)")
    
    improvement = (orig_overhang - ori_overhang) / orig_overhang * 100 if orig_overhang > 0 else 0
    height_change = (1 - oriented.bounding_box.extents[2] / original.bounding_box.extents[2]) * 100
    
    print(f"\n📈 Улучшения:")
    print(f"   Сокращение поддержек: {improvement:.1f}%")
    print(f"   Изменение высоты: {'↓' if height_change > 0 else '↑'} {abs(height_change):.1f}%")
    
    # Сохраняем отчёт
    report_path = "optimization_report.txt"
    with open(report_path, 'w') as f:
        f.write(f"Модель: {original_path}\n")
        f.write(f"Оптимальные углы из файла: {oriented_path}\n")
        f.write(f"Исходная площадь нависаний: {orig_overhang:.2f} мм²\n")
        f.write(f"Оптимизированная площадь нависаний: {ori_overhang:.2f} мм²\n")
        f.write(f"Улучшение: {improvement:.1f}%\n")
    
    print(f"\n📄 Отчёт сохранён: {report_path}")

# Запуск
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Использование: python visualize_comparison.py исходный.stl оптимизированный.stl")
    else:
        compare_orientations(sys.argv[1], sys.argv[2])
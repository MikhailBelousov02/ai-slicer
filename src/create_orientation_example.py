import trimesh
import numpy as np
import json
import os
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from PIL import Image

def calculate_bed_contact_area(mesh):
    """Оценивает площадь контакта со столом (простейший метод)"""
    # Находим вершины с минимальной Z (ближайшие к столу)
    vertices = mesh.vertices
    min_z = vertices[:, 2].min()
    
    # Все вершины вблизи минимальной Z (в пределах 0.1 мм)
    bed_vertices = vertices[vertices[:, 2] < min_z + 0.1]
    
    if len(bed_vertices) > 0:
        # Приблизительная площадь через выпуклую оболочку
        try:
            from scipy.spatial import ConvexHull
            # Берем только XY координаты
            xy_points = bed_vertices[:, :2]
            hull = ConvexHull(xy_points)
            return hull.volume  # Для 2D это площадь
        except:
            return 0.0
    return 0.0

def create_preview(mesh, folder):
    """Создает 2D превью модели"""
    try:
        # Создаем 3 вида с помощью matplotlib
        fig = plt.figure(figsize=(12, 4))
        
        # Вид сверху (XY)
        ax1 = fig.add_subplot(131, projection='3d')
        ax1.plot_trisurf(mesh.vertices[:, 0], mesh.vertices[:, 1], mesh.vertices[:, 2],
                        triangles=mesh.faces, alpha=0.8)
        ax1.view_init(elev=90, azim=-90)
        ax1.set_title('Вид сверху (XY)')
        ax1.set_axis_off()
        
        # Вид спереди (XZ)
        ax2 = fig.add_subplot(132, projection='3d')
        ax2.plot_trisurf(mesh.vertices[:, 0], mesh.vertices[:, 1], mesh.vertices[:, 2],
                        triangles=mesh.faces, alpha=0.8)
        ax2.view_init(elev=0, azim=-90)
        ax2.set_title('Вид спереди (XZ)')
        ax2.set_axis_off()
        
        # Вид сбоку (YZ)
        ax3 = fig.add_subplot(133, projection='3d')
        ax3.plot_trisurf(mesh.vertices[:, 0], mesh.vertices[:, 1], mesh.vertices[:, 2],
                        triangles=mesh.faces, alpha=0.8)
        ax3.view_init(elev=0, azim=0)
        ax3.set_title('Вид сбоку (YZ)')
        ax3.set_axis_off()
        
        plt.tight_layout()
        plt.savefig(os.path.join(folder, "preview_all.png"), dpi=100, bbox_inches='tight')
        plt.close()
        
    except Exception as e:
        print(f"Не удалось создать превью: {e}")
        # Создаем заглушку
        img = Image.new('RGB', (256, 256), color='gray')
        img.save(os.path.join(folder, "preview_all.png"))

def create_metadata(mesh, folder, original_path):
    """Создает JSON с метаданными ориентации"""
    metadata = {
        "model_name": os.path.basename(original_path).replace('.stl', ''),
        "original_file": original_path,
        "orientation_name": "0_0_0",
        "rotation_angles": {
            "x": 0,
            "y": 0, 
            "z": 0
        },
        "rotation_matrix": [
            [1, 0, 0],
            [0, 1, 0],
            [0, 0, 1]
        ],
        "applied_transforms": [
            "rotation_x: 0°",
            "rotation_y: 0°", 
            "rotation_z: 0°",
            "translation: none"
        ],
        "timestamp": "2024-01-15T10:30:00Z",
        "notes": "Исходная ориентация без изменений",
        "file_size_kb": os.path.getsize(original_path) / 1024
    }
    
    with open(os.path.join(folder, "orientation.json"), 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

def create_bounding_box_json(mesh, folder):
    """Создает JSON с размерами модели"""
    bounds = mesh.bounds
    
    bbox_data = {
        "bounding_box": {
            "min": bounds[0].tolist(),
            "max": bounds[1].tolist()
        },
        "dimensions": {
            "width_x": bounds[1][0] - bounds[0][0],
            "depth_y": bounds[1][1] - bounds[0][1],
            "height_z": bounds[1][2] - bounds[0][2]
        },
        "center_of_mass": mesh.center_mass.tolist() if hasattr(mesh, 'center_mass') else [0, 0, 0],
        "volume": float(mesh.volume),
        "surface_area": float(mesh.area),
        "bed_contact_area": calculate_bed_contact_area(mesh)
    }
    
    with open(os.path.join(folder, "bounding_box.json"), 'w', encoding='utf-8') as f:
        json.dump(bbox_data, f, indent=2, ensure_ascii=False)

def create_analysis_json(mesh, folder):
    """Создает JSON с анализом геометрии"""
    # Простейший анализ overhang
    normals = mesh.face_normals
    # Угол между нормалью и вертикалью (0,0,1)
    vertical = np.array([0, 0, 1])
    
    angles = []
    for normal in normals:
        if np.linalg.norm(normal) > 0:
            cos_angle = np.dot(normal, vertical) / (np.linalg.norm(normal))
            angle = np.degrees(np.arccos(np.clip(cos_angle, -1, 1)))
            angles.append(min(angle, 180 - angle))
    
    if angles:
        angles = np.array(angles)
        critical_angle = 45  # Угол, после которого нужны поддержки
        
        analysis = {
            "overhang_analysis": {
                "total_faces": len(normals),
                "faces_with_overhang": int(np.sum(angles > critical_angle)),
                "max_overhang_angle": float(np.max(angles)),
                "avg_overhang_angle": float(np.mean(angles)),
                "critical_overhang_faces": int(np.sum(angles > critical_angle)),
                "requires_supports": bool(np.any(angles > critical_angle))
            },
            "stability_metrics": {
                "center_of_mass_height": float(mesh.center_mass[2]) if hasattr(mesh, 'center_mass') else 0,
                "base_width": float(mesh.bounds[1][0] - mesh.bounds[0][0]),
                "base_depth": float(mesh.bounds[1][1] - mesh.bounds[0][1]),
                "aspect_ratio": float((mesh.bounds[1][2] - mesh.bounds[0][2]) / 
                                     max(mesh.bounds[1][0] - mesh.bounds[0][0], 
                                         mesh.bounds[1][1] - mesh.bounds[0][1])),
                "stability_risk": "low" if mesh.center_mass[2] < 30 else "medium"
            },
            "printability": {
                "is_watertight": mesh.is_watertight,
                "is_volume": mesh.is_volume,
                "is_convex": mesh.is_convex,
                "euler_number": int(mesh.euler_number) if hasattr(mesh, 'euler_number') else 0
            }
        }
    else:
        analysis = {
            "overhang_analysis": {
                "error": "could not calculate angles",
                "requires_supports": False
            }
        }
    
    with open(os.path.join(folder, "analysis.json"), 'w', encoding='utf-8') as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)

def create_orientation_example():
    """Создает пример папки с ориентацией"""
    
    # Загружаем модель
    model_path = "dataset/models/simple_cube.stl"
    if not os.path.exists(model_path):
        print(f"Модель не найдена: {model_path}")
        print("Сначала запустите create_sample_model.py")
        return
    
    mesh = trimesh.load(model_path)
    
    # Создаем папку для ориентации 0_0_0
    orientation_folder = "dataset/orientations/simple_cube/0_0_0"
    os.makedirs(orientation_folder, exist_ok=True)
    
    # 1. Сохраняем ориентированную модель (в данном случае оригинал)
    mesh.export(os.path.join(orientation_folder, "model.stl"))
    
    # 2. Создаем превью
    create_preview(mesh, orientation_folder)
    
    # 3. Создаем JSON с метаданными
    create_metadata(mesh, orientation_folder, model_path)
    
    # 4. Создаем bounding box JSON
    create_bounding_box_json(mesh, orientation_folder)
    
    # 5. Создаем analysis JSON
    create_analysis_json(mesh, orientation_folder)
    
    print(f"Пример ориентации создан в: {orientation_folder}")
    print(f"Созданы файлы:")
    print(f"  - model.stl")
    print(f"  - preview_all.png")
    print(f"  - orientation.json")
    print(f"  - bounding_box.json")
    print(f"  - analysis.json")

if __name__ == "__main__":
    create_orientation_example()
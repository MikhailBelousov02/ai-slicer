import trimesh
import numpy as np
import json
import os
from create_orientation_example import create_preview, create_bounding_box_json, create_analysis_json

def create_rotated_orientation():
    """Создает повернутую ориентацию модели"""
    
    # Загружаем модель
    model_path = "dataset/models/simple_cube.stl"
    if not os.path.exists(model_path):
        print(f"Модель не найдена: {model_path}")
        print("Сначала запустите create_sample_model.py")
        return
    
    mesh = trimesh.load(model_path)
    
    # Поворачиваем на 45 градусов вокруг X
    rotation = trimesh.transformations.rotation_matrix(
        np.radians(45),  # 45 градусов
        [1, 0, 0]        # вокруг оси X
    )
    
    mesh.apply_transform(rotation)
    
    # Создаем папку для ориентации 45_0_0
    orientation_folder = "dataset/orientations/simple_cube/45_0_0"
    os.makedirs(orientation_folder, exist_ok=True)
    
    # 1. Сохраняем повернутую модель
    mesh.export(os.path.join(orientation_folder, "model.stl"))
    
    # 2. Создаем превью
    create_preview(mesh, orientation_folder)
    
    # 3. Создаем метаданные с правильными углами
    metadata = {
        "model_name": "simple_cube",
        "original_file": model_path,
        "orientation_name": "45_0_0",
        "rotation_angles": {
            "x": 45,  # Важно: указываем реальный угол
            "y": 0, 
            "z": 0
        },
        "rotation_matrix": rotation.tolist(),
        "applied_transforms": [
            "rotation_x: 45°",
            "rotation_y: 0°", 
            "rotation_z: 0°",
            "translation: none"
        ],
        "timestamp": "2024-01-15T10:35:00Z",
        "notes": "Поворот на 45° вокруг оси X",
        "file_size_kb": os.path.getsize(model_path) / 1024
    }
    
    with open(os.path.join(orientation_folder, "orientation.json"), 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    # 4. Создаем bounding box JSON
    create_bounding_box_json(mesh, orientation_folder)
    
    # 5. Создаем analysis JSON
    create_analysis_json(mesh, orientation_folder)
    
    print(f"Повернутая ориентация создана в: {orientation_folder}")
    print("Также создана ориентация для сложной модели...")
    
    # Также создадим ориентацию для сложной модели
    create_complex_model_orientation()

def create_complex_model_orientation():
    """Создает ориентацию для сложной модели"""
    model_path = "dataset/models/complex_cylinder.stl"
    if not os.path.exists(model_path):
        print(f"Сложная модель не найдена: {model_path}")
        return
    
    mesh = trimesh.load(model_path)
    
    # Папка для горизонтальной ориентации
    orientation_folder = "dataset/orientations/complex_cylinder/horizontal"
    os.makedirs(orientation_folder, exist_ok=True)
    
    # Поворачиваем чтобы лежал на боку
    rotation = trimesh.transformations.rotation_matrix(
        np.radians(90),  # 90 градусов
        [1, 0, 0]        # вокруг оси X
    )
    
    mesh.apply_transform(rotation)
    mesh.export(os.path.join(orientation_folder, "model.stl"))
    
    # Создаем все файлы
    create_preview(mesh, orientation_folder)
    
    metadata = {
        "model_name": "complex_cylinder",
        "original_file": model_path,
        "orientation_name": "horizontal",
        "rotation_angles": {"x": 90, "y": 0, "z": 0},
        "rotation_matrix": rotation.tolist(),
        "notes": "Модель лежит на боку для минимизации поддержек",
        "timestamp": "2024-01-15T10:40:00Z"
    }
    
    with open(os.path.join(orientation_folder, "orientation.json"), 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    create_bounding_box_json(mesh, orientation_folder)
    create_analysis_json(mesh, orientation_folder)
    
    print(f"Ориентация сложной модели создана: {orientation_folder}")

if __name__ == "__main__":
    create_rotated_orientation()
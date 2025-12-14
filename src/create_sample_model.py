import trimesh
import numpy as np
import os

def create_cube(size=50):
    """Создает простой куб для тестирования"""
    # Создаем куб
    cube = trimesh.creation.box(extents=[size, size, size])
    
    # Создаем папку если нет
    os.makedirs('dataset/models', exist_ok=True)
    
    # Сохраняем
    cube.export('dataset/models/simple_cube.stl')
    print(f"Кубик создан: dataset/models/simple_cube.stl")
    
    # Также создаем более сложную модель (цилиндр с отверстием)
    cylinder = trimesh.creation.cylinder(radius=size/3, height=size*1.5)
    
    # Вырезаем отверстие
    small_cylinder = trimesh.creation.cylinder(radius=size/6, height=size*1.6)
    
    # Размещаем маленький цилиндр внутри большого
    small_cylinder.apply_translation([0, 0, -size*0.05])
    
    # Вычитаем (разность)
    complex_shape = cylinder.difference(small_cylinder)
    
    complex_shape.export('dataset/models/complex_cylinder.stl')
    print(f"Сложная модель создана: dataset/models/complex_cylinder.stl")
    
    return cube, complex_shape

if __name__ == "__main__":
    create_cube()
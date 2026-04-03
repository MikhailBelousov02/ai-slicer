import trimesh
import numpy as np
import random
import copy
import time
from datetime import datetime

def load_mesh(stl_path):
    """Загружает STL и возвращает mesh"""
    print(f"📂 Загрузка модели: {stl_path}")
    return trimesh.load(stl_path)

def get_faces_info(mesh):
    """
    Возвращает массив нормалей граней и массив площадей граней.
    Нормали нормализованы.
    """
    print("🔍 Анализ геометрии модели...")
    normals = mesh.face_normals
    areas = mesh.area_faces
    print(f"   ✅ Найдено граней: {len(areas)}")
    return normals, areas

def rotation_matrix_from_angles(angles_deg):
    """
    Создаёт матрицу поворота 3x3 для углов Эйлера (ZYX порядок).
    angles_deg: (rx, ry, rz) в градусах.
    """
    rx, ry, rz = np.radians(angles_deg)
    Rx = np.array([[1, 0, 0],
                   [0, np.cos(rx), -np.sin(rx)],
                   [0, np.sin(rx), np.cos(rx)]])
    Ry = np.array([[np.cos(ry), 0, np.sin(ry)],
                   [0, 1, 0],
                   [-np.sin(ry), 0, np.cos(ry)]])
    Rz = np.array([[np.cos(rz), -np.sin(rz), 0],
                   [np.sin(rz), np.cos(rz), 0],
                   [0, 0, 1]])
    return Rz @ Ry @ Rx

def compute_overhang_area(normals, areas, angles_deg, threshold_deg=45):
    """
    Вычисляет общую площадь граней, угол наклона которых превышает порог.
    """
    R = rotation_matrix_from_angles(angles_deg)
    rotated_normals = (R @ normals.T).T
    
    cos_theta = rotated_normals[:, 2]
    theta = np.degrees(np.arccos(np.clip(cos_theta, -1, 1)))
    
    overhang_mask = theta > threshold_deg
    overhang_area = np.sum(areas[overhang_mask])
    return overhang_area

def random_angle():
    return random.uniform(0, 360)

def mutate(angles, mutation_strength=10):
    """Мутация: добавляет нормальный шум к каждому углу"""
    new_angles = angles + np.random.normal(0, mutation_strength, 3)
    return np.mod(new_angles, 360)

def crossover(a, b):
    """Одноточечный кроссовер между двумя особями"""
    point = random.randint(0, 2)
    child = np.concatenate([a[:point], b[point:]])
    return child

def format_time(seconds):
    """Форматирует время в удобный вид"""
    if seconds < 60:
        return f"{seconds:.1f} сек"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f} мин"
    else:
        hours = seconds / 3600
        return f"{hours:.1f} ч"

def evolutionary_optimization(normals, areas,
                              pop_size=60,
                              generations=200,
                              mutation_strength=15,
                              crossover_prob=0.7,
                              mutation_prob=0.3,
                              elite_ratio=0.2,
                              threshold_deg=45):
    """
    Эволюционный поиск лучшей ориентации.
    Возвращает лучшие углы и историю fitness.
    """
    print(f"\n🧬 Запуск эволюционного алгоритма")
    print(f"   Параметры: поколений={generations}, популяция={pop_size}")
    print(f"   Всего итераций: {generations * pop_size}")
    print()
    
    start_time = time.time()
    
    # Инициализация популяции
    print("🌱 Создание начальной популяции...")
    population = [np.array([random_angle(), random_angle(), random_angle()]) 
                  for _ in range(pop_size)]
    
    best_fitness_history = []
    best_angles = None
    best_fitness = float('inf')
    
    # Для прогресс-бара
    bar_length = 40
    
    for gen in range(generations):
        gen_start = time.time()
        
        # Оценка приспособленности
        fitness = [compute_overhang_area(normals, areas, ind, threshold_deg) 
                   for ind in population]
        
        # Обновление лучшего решения
        min_idx = np.argmin(fitness)
        if fitness[min_idx] < best_fitness:
            best_fitness = fitness[min_idx]
            best_angles = population[min_idx].copy()
        best_fitness_history.append(best_fitness)
        
        # Прогресс-бар
        progress = (gen + 1) / generations
        filled = int(bar_length * progress)
        bar = '█' * filled + '░' * (bar_length - filled)
        
        elapsed = time.time() - start_time
        eta = (elapsed / (gen + 1)) * (generations - gen - 1)
        
        # Статусная строка
        print(f"\r🧬 Поколение {gen+1:3d}/{generations} [{bar}] "
              f"Лучшая площадь: {best_fitness:8.2f} мм² | "
              f"Прошло: {format_time(elapsed)} | "
              f"Осталось: {format_time(eta)}", end='', flush=True)
        
        # Отбор элиты
        elite_count = max(1, int(pop_size * elite_ratio))
        elite_indices = np.argsort(fitness)[:elite_count]
        elite = [population[i].copy() for i in elite_indices]
        
        # Создание нового поколения
        new_population = elite.copy()
        
        while len(new_population) < pop_size:
            # Турнирный отбор
            tournament = random.sample(range(pop_size), 3)
            parent1 = population[min(tournament, key=lambda i: fitness[i])]
            parent2 = population[min(tournament, key=lambda i: fitness[i])]
            
            # Кроссовер
            if random.random() < crossover_prob:
                child = crossover(parent1, parent2)
            else:
                child = parent1.copy() if random.random() < 0.5 else parent2.copy()
            
            # Мутация
            if random.random() < mutation_prob:
                child = mutate(child, mutation_strength)
            
            new_population.append(child)
        
        population = new_population
        mutation_strength *= 0.98
    
    print()  # Переход на новую строку
    elapsed = time.time() - start_time
    print(f"\n✅ Эволюция завершена за {format_time(elapsed)}")
    
    return best_angles, best_fitness_history

def main(stl_input_path, stl_output_path=None, threshold_deg=45):
    print("=" * 60)
    print("🔄 АВТОМАТИЧЕСКАЯ ОПТИМИЗАЦИЯ ОРИЕНТАЦИИ МОДЕЛИ")
    print("=" * 60)
    print(f"📁 Входной файл: {stl_input_path}")
    print(f"🎯 Критический угол: {threshold_deg}°")
    print()
    
    # Загрузка модели
    mesh = load_mesh(stl_input_path)
    normals, areas = get_faces_info(mesh)
    
    total_area = np.sum(areas)
    print(f"📏 Общая площадь поверхности: {total_area:.2f} мм²")
    print(f"📐 Количество граней: {len(areas):,}")
    print()
    
    # Запуск эволюционного поиска
    best_angles, history = evolutionary_optimization(
        normals, areas,
        pop_size=100,
        generations=1000,
        mutation_strength=15,
        threshold_deg=threshold_deg
    )
    
    # Результаты
    print("\n" + "=" * 60)
    print("📊 РЕЗУЛЬТАТЫ ОПТИМИЗАЦИИ")
    print("=" * 60)
    print(f"🎯 Оптимальные углы поворота:")
    print(f"   • Вращение по X (roll):  {best_angles[0]:6.1f}°")
    print(f"   • Вращение по Y (pitch): {best_angles[1]:6.1f}°")
    print(f"   • Вращение по Z (yaw):   {best_angles[2]:6.1f}°")
    print()
    
    best_area = compute_overhang_area(normals, areas, best_angles, threshold_deg)
    improvement = ((total_area - best_area) / total_area) * 100
    print(f"📉 Площадь нависаний: {best_area:.2f} мм² из {total_area:.2f} мм²")
    print(f"📈 Улучшение: {improvement:.1f}% (уменьшено на {total_area - best_area:.1f} мм²)")
    print()
    
    # Применяем поворот к mesh и сохраняем
    if stl_output_path is None:
        stl_output_path = stl_input_path.replace('.stl', '_oriented.stl')
    
    print("💾 Применение поворота к модели...")
    R = rotation_matrix_from_angles(best_angles)
    transform_matrix = np.eye(4)
    transform_matrix[:3, :3] = R
    
    oriented_mesh = mesh.copy()
    oriented_mesh.apply_transform(transform_matrix)
    oriented_mesh.export(stl_output_path)
    
    print(f"✅ Повёрнутая модель сохранена: {stl_output_path}")
    print()
    print("=" * 60)
    print("✨ ГОТОВО! Модель оптимизирована для печати")
    print("=" * 60)
    
    return best_angles, history

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Использование: python auto_orient.py model.stl [output.stl]")
        print()
        print("Примеры:")
        print("  python auto_orient.py test_cube.stl")
        print("  python auto_orient.py model.stl oriented.stl")
        print("  python auto_orient.py model.stl oriented.stl 50  # порог 50°")
    else:
        output = sys.argv[2] if len(sys.argv) > 2 else None
        threshold = float(sys.argv[3]) if len(sys.argv) > 3 else 45
        main(sys.argv[1], output, threshold)
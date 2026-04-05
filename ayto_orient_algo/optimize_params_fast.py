# optimize_params_fast.py
import os
import sys
import random
import time
import numpy as np
import trimesh
from deap import base, creator, tools, algorithms

# ------------------------------------------------------------
# 1. Предвычисление данных модели (один раз)
# ------------------------------------------------------------
class PrecomputedModel:
    def __init__(self, mesh):
        # mesh - уже Trimesh
        # Берём вершины граней (3 вершины на грань)
        self.vertices = mesh.vertices
        self.faces = mesh.faces
        # Нормали и площади граней
        self.normals = mesh.face_normals.astype(np.float64)
        self.areas = mesh.area_faces.astype(np.float64)
        # Удаляем грани с нулевой площадью
        valid = self.areas > 1e-8
        self.normals = self.normals[valid]
        self.areas = self.areas[valid]
        self.faces = self.faces[valid]
        # Предвычисляем вершины каждой грани (N x 3 x 3)
        self.face_vertices = self.vertices[self.faces]  # (N,3,3)
        # Нормализуем нормали (на всякий случай)
        lengths = np.linalg.norm(self.normals, axis=1, keepdims=True)
        self.normals = self.normals / lengths

    def evaluate_orientation(self, orientation, first_lay_h=0.0475, ascent=-0.0781, min_volume=False):
        """
        Быстрое вычисление bottom, overhang, contour для заданной ориентации.
        Возвращает (bottom, overhang, contour)
        """
        # Проекции вершин на ориентацию
        proj = np.inner(self.face_vertices, orientation)  # (N,3)
        min_proj = np.min(proj, axis=1)
        max_proj = np.max(proj, axis=1)
        med_proj = np.median(proj, axis=1)
        total_min = np.min(min_proj)

        # Bottom
        bottom_mask = max_proj < (total_min + first_lay_h)
        bottom = np.sum(self.areas[bottom_mask])

        # Overhang (угол между нормалью и ориентацией)
        dot = np.inner(self.normals, orientation)  # (N,)
        overhang_mask = (dot < ascent) & (~bottom_mask)
        if np.any(overhang_mask):
            if min_volume:
                heights = med_proj[overhang_mask] - total_min
                inner = dot[overhang_mask] - ascent
                # Упрощённая формула (без логарифмов для скорости)
                overhang = np.sum(self.areas[overhang_mask] * np.abs(inner * (inner < 0)) ** 2)
            else:
                inner = dot[overhang_mask] - ascent
                overhang = 2 * np.sum(self.areas[overhang_mask] * np.abs(inner * (inner < 0)) ** 2)
        else:
            overhang = 0.0

        # Contour (упрощённо: периметр квадрата по площади bottom)
        contour = 4 * np.sqrt(bottom) if bottom > 0 else 0.0
        return bottom, overhang, contour

# ------------------------------------------------------------
# 2. Загрузка датасета с предвычислением
# ------------------------------------------------------------
def load_mesh_robust(stl_path):
    try:
        obj = trimesh.load(stl_path)
        if isinstance(obj, trimesh.Scene):
            meshes = [geom for geom in obj.geometry.values() if isinstance(geom, trimesh.Trimesh)]
            if not meshes:
                return None
            if len(meshes) == 1:
                return meshes[0]
            return trimesh.util.concatenate(meshes)
        return obj
    except Exception:
        return None

def load_dataset(dataset_root="results"):
    stl_files = []
    for root, dirs, files in os.walk(dataset_root):
        if "optimal" in root and "model.stl" in files:
            stl_files.append(os.path.join(root, "model.stl"))
    print(f"🔍 Найдено кандидатов: {len(stl_files)}")
    valid = []
    for p in stl_files:
        mesh = load_mesh_robust(p)
        if mesh is not None:
            # Преобразуем в предвычисленный формат
            valid.append(PrecomputedModel(mesh))
        else:
            print(f"⚠️ Пропущен: {p}")
    print(f"✅ Валидных моделей: {len(valid)}")
    return valid

# ------------------------------------------------------------
# 3. Целевая функция и утилиты
# ------------------------------------------------------------
def random_orientation():
    phi = random.uniform(0, 2*np.pi)
    costheta = random.uniform(-1, 1)
    theta = np.arccos(costheta)
    return np.array([np.sin(theta)*np.cos(phi), np.sin(theta)*np.sin(phi), np.cos(theta)])

def compute_unprintability(params, bottom, overhang, contour, min_volume=False):
    TAR_A, TAR_B, RELATIVE_F, TAR_C, TAR_D, CONTOUR_F, BOTTOM_F, TAR_E = params[:8]
    if min_volume:
        overhang /= 25
        return (TAR_A * (overhang + TAR_B) + RELATIVE_F * (overhang + TAR_C) /
                (TAR_D + CONTOUR_F * contour + BOTTOM_F * bottom + TAR_E * overhang))
    else:
        return (TAR_A * (overhang + TAR_B) + RELATIVE_F * (overhang + TAR_C) /
                (TAR_D + CONTOUR_F * contour + BOTTOM_F * bottom))

def fitness(params, dataset, num_random=5, min_volume=False):
    total_penalty = 0
    for model in dataset:
        # Оптимальная ориентация (вертикаль вниз)
        bottom_opt, overhang_opt, contour_opt = model.evaluate_orientation(np.array([0,0,-1]), min_volume=min_volume)
        unprint_opt = compute_unprintability(params, bottom_opt, overhang_opt, contour_opt, min_volume)

        for _ in range(num_random):
            rand_orient = random_orientation()
            bottom_r, overhang_r, contour_r = model.evaluate_orientation(rand_orient, min_volume=min_volume)
            unprint_r = compute_unprintability(params, bottom_r, overhang_r, contour_r, min_volume)
            if unprint_r < unprint_opt:
                total_penalty += 1
    return total_penalty,

# ------------------------------------------------------------
# 4. Генетический алгоритм с прогрессом
# ------------------------------------------------------------
def run_ga(dataset, min_volume=False, pop_size=20, ngen=30, num_random=5):
    print("\n🧬 ЗАПУСК ГЕНЕТИЧЕСКОГО АЛГОРИТМА")
    print(f"   Моделей: {len(dataset)}")
    print(f"   Популяция: {pop_size}, поколений: {ngen}")
    print(f"   Случайных ориентаций на модель: {num_random}")
    print("-" * 60)

    bounds = [
        (0.01, 0.03), (0.1, 0.2), (5.0, 12.0), (-0.02, 0.25),
        (0.6, 1.1), (0.1, 0.3), (1.0, 1.5), (0.01, 0.04)
    ]
    n_params = len(bounds)

    # DEAP setup
    if hasattr(creator, "FitnessMin"):
        del creator.FitnessMin
        del creator.Individual
    creator.create("FitnessMin", base.Fitness, weights=(-1.0,))
    creator.create("Individual", list, fitness=creator.FitnessMin)

    toolbox = base.Toolbox()
    def make_uniform(low, up):
        return lambda: random.uniform(low, up)
    attr_funcs = [make_uniform(low, up) for low, up in bounds]
    toolbox.register("individual", tools.initCycle, creator.Individual, attr_funcs, n=1)
    toolbox.register("population", tools.initRepeat, list, toolbox.individual)

    toolbox.register("evaluate", fitness, dataset=dataset, min_volume=min_volume, num_random=num_random)
    toolbox.register("mate", tools.cxBlend, alpha=0.5)
    toolbox.register("mutate", tools.mutGaussian, mu=0, sigma=0.1, indpb=0.2)
    toolbox.register("select", tools.selTournament, tournsize=3)

    pop = toolbox.population(n=pop_size)
    hof = tools.HallOfFame(1)
    stats = tools.Statistics(lambda ind: ind.fitness.values)
    stats.register("min", np.min)
    stats.register("avg", np.mean)

    print("🌱 Эволюция начата...\n")
    start_time = time.time()
    for gen in range(ngen):
        # Оценка всех особей
        fitnesses = []
        for i, ind in enumerate(pop):
            fit = toolbox.evaluate(ind)
            fitnesses.append(fit)
            ind.fitness.values = fit
            # Прогресс внутри поколения (опционально)
            # print(f"\r   Оценка особи {i+1}/{pop_size}", end="", flush=True)
        # print()  # перевод строки

        fits = [f[0] for f in fitnesses]
        best = min(fits)
        avg = sum(fits)/len(fits)
        elapsed = time.time() - start_time
        eta = (elapsed / (gen+1)) * (ngen - gen - 1) if gen+1 < ngen else 0
        print(f"🧬 Поколение {gen+1:3d}/{ngen} | Лучший штраф: {best:8.0f} | Средний: {avg:8.0f} | Прошло: {elapsed:5.1f}с | Осталось: {eta:5.1f}с")

        # Отбор, скрещивание, мутация
        offspring = toolbox.select(pop, len(pop))
        offspring = list(map(toolbox.clone, offspring))
        for child1, child2 in zip(offspring[::2], offspring[1::2]):
            if random.random() < 0.7:
                toolbox.mate(child1, child2)
                del child1.fitness.values
                del child2.fitness.values
        for mutant in offspring:
            if random.random() < 0.2:
                toolbox.mutate(mutant)
                del mutant.fitness.values
        pop[:] = offspring
        hof.update(pop)

    print("\n✅ Эволюция завершена!")
    best_params = hof[0]
    print(f"\n🏆 Лучшие параметры:\n   {[round(p,6) for p in best_params]}")
    return best_params

# ------------------------------------------------------------
# 5. Сохранение параметров
# ------------------------------------------------------------
def save_params(params, filename="my_parameters.py"):
    names = ["TAR_A", "TAR_B", "RELATIVE_F", "TAR_C", "TAR_D", "CONTOUR_F", "BOTTOM_F", "TAR_E"]
    with open(filename, "w") as f:
        f.write("# Generated parameters for AutoOrient\n")
        f.write(f"# Date: {time.ctime()}\n")
        f.write("PARAMETER = {\n")
        for name, val in zip(names, params):
            f.write(f"    '{name}': {val},\n")
        f.write("}\n")
    print(f"💾 Параметры сохранены в {filename}")

# ------------------------------------------------------------
# 6. Запуск
# ------------------------------------------------------------
if __name__ == "__main__":
    print("="*60)
    print("🧬 ОПТИМИЗАЦИЯ ПАРАМЕТРОВ (БЫСТРАЯ ВЕРСИЯ)")
    print("="*60)
    dataset = load_dataset("results")
    if not dataset:
        print("❌ Нет валидных моделей.")
        sys.exit(1)

    # Для быстрого теста можно взять первые 5 моделей
    # dataset = dataset[:5]
    # print(f"⚠️ Используется подвыборка из {len(dataset)} моделей")

# Быстрый тест на 10 моделях, 10 поколений, 3 случайные ориентации
    dataset = dataset[:30]
    best = run_ga(dataset, min_volume=False, pop_size=10, ngen=10, num_random=3)
    save_params(best, "my_standard_params.py")

    print("\n✨ Готово! Теперь используйте my_standard_params.py в auto_orient.py")
import os
import re
import math
import time
from collections import Counter
import numpy as np

PARAMETER = {
    "TAR_A": 0.027889,          # Вес линейной части: умножается на (overhang + TAR_B)
    "TAR_B": 0.110271,          # Сдвиг для линейной части (overhang + TAR_B)
    "RELATIVE_F": 6.079397,     # Вес дробной части: умножается на (overhang + TAR_C) / знаменатель
    "CONTOUR_F": 0.210296,      # Коэффициент при длине контура основания в знаменателе
    "BOTTOM_F": 1.214279,       # Коэффициент при площади основания в знаменателе
    "TAR_C": 0.235249,          # Сдвиг для числителя дробной части (overhang + TAR_C)
    "TAR_D": 0.623361,          # Свободный член в знаменателе
    "TAR_E": 0.019795,          # Коэффициент при overhang в знаменателе (только для min_volume=False)

    # Параметры предобработки и геометрии
    "FIRST_LAY_H": 0.04754881938390257,  # Толщина первого слоя (мм) – грани в пределах этой высоты от нижней точки считаются основанием
    "VECTOR_TOL": -0.0008385913582234466, # Допуск для сравнения векторов (близость к вертикали)
    "NEGL_FACE_SIZE": 0.4737309463791554, # Минимальная площадь грани (мм²) – меньшие грани отбрасываются для ускорения
    "ASCENT": -0.07809801382985776,       # Порог косинуса угла для определения нависаний: если dot(n, orientation) < ASCENT, то грань считается нависающей
    "PLAFOND_ADV": 0.059937025927212395,  # Поправка для "потолочных" граней (для extended_mode)
    "CONTOUR_AMOUNT": 0.018242751444131886, # Дополнительный штраф за количество граней в контуре (в extended_mode)

    # используются только при min_volume=True
    "OV_H": 2.574100894603089,      # Показатель степени для штрафа нависаний (влияет на нелинейность)
    "height_offset": 2.372824083342488,   # Сдвиг в формуле объёма поддержек
    "height_log": 0.04137517666768212,    # Коэффициент при логарифме высоты
    "height_log_k": 1.9325457851679673,   # Масштаб внутри логарифма
}

# Параметры для режима минимизации объёма поддержек (min_volume=True)
PARAMETER_VOL = {
    # Аналогичные коэффициенты, но настроенные на объём, а не на площадь
    "TAR_A": 0.012826785357111374,
    "TAR_B": 0.1774847296275851,
    "RELATIVE_F": 6.610621027964314,
    "CONTOUR_F": 0.23228623269775997,
    "BOTTOM_F": 1.167152017941474,
    "TAR_C": 0.24308070476924726,
    "TAR_D": 0.6284515508160871,
    "TAR_E": 0.032157292647062234,
    "FIRST_LAY_H": 0.029227991916155015,
    "VECTOR_TOL": -0.0011163303070972383,
    "NEGL_FACE_SIZE": 0.4928696161029859,
    "ASCENT": -0.23897449119622627,
    "PLAFOND_ADV": 0.04079208948120519,
    "CONTOUR_AMOUNT": 0.0101472219892684,
    "OV_H": 1.0370178217794535,
    "height_offset": 2.7417608343142073,
    "height_log": 0.06442030687034085,
    "height_log_k": 0.3933594673063997,
}


class AutoOrient:

    def __init__(self, mesh, min_volume=False, verbose=True):

        self.verbose = verbose
        self.min_volume = min_volume
        # Загружаем параметры
        params = PARAMETER_VOL if min_volume else PARAMETER
        for k, v in params.items():
            setattr(self, k, v)

        self.mesh = self._preprocess(mesh)
        if verbose:
            print(f"Граней после предобработки: {len(self.mesh)}")

        # Сбор кандидатов
        candidates = self._collect_candidates()
        if verbose:
            print(f"Найдено кандидатов: {len(candidates)}")

        # Оценка кандидатов
        results = []
        for orientation in candidates:
            bottom, overhang, contour = self._evaluate(orientation)
            unprint = self._target_function(bottom, overhang, contour)
            results.append([orientation, bottom, overhang, contour, unprint])
            if verbose:
                print(f"  {orientation} -> bottom={bottom:.1f} over={overhang:.1f} "
                      f"contour={contour:.1f} unprint={unprint:.4f}")

        # Выбираем лучший
        results.sort(key=lambda x: x[4])
        best = results[0]
        self.best_orientation = best[0]
        self.bottom_area = best[1]
        self.overhang_area = best[2]
        self.contour = best[3]
        self.unprintability = best[4]
        self.rotation_matrix = self._euler(self.best_orientation)

    def _preprocess(self, mesh):
        # Преобразуем в массив [нормаль, v0, v1, v2, доп.поля]
        # Берём вершины и грани
        vertices = mesh.vertices
        faces = mesh.faces
        # Нормали граней (уже есть в mesh)
        normals = mesh.face_normals
        areas = mesh.area_faces

        # Строим массив: для каждой грани [norm_x, norm_y, norm_z, v0_x, v0_y, v0_z, v1_x, v1_y, v1_z, v2_x, v2_y, v2_z]
        n_faces = len(faces)
        data = np.zeros((n_faces, 12))
        data[:, 0:3] = normals
        for i, face in enumerate(faces):
            data[i, 3:6] = vertices[face[0]]
            data[i, 6:9] = vertices[face[1]]
            data[i, 9:12] = vertices[face[2]]

        # Добавляем столбцы: площадь (удвоенная), max_z, median_z
        addendum = np.zeros((n_faces, 5))
        addendum[:, 0] = areas * 2          # удвоенная площадь
        addendum[:, 1] = np.max(data[:, [5, 8, 11]], axis=1)   # max z
        addendum[:, 2] = np.median(data[:, [5, 8, 11]], axis=1) # median z
        # Доп. поля для проекций (заполнятся позже)
        addendum[:, 3] = 0   # min_proj
        addendum[:, 4] = 0   # max_proj

        mesh_array = np.hstack((data, addendum))

        lengths = np.sqrt(np.sum(mesh_array[:, 0:3] ** 2, axis=1))
        mesh_array[:, 0:3] = mesh_array[:, 0:3] / lengths[:, np.newaxis]
        mesh_array[:, 12] /= 2

        # Удаляем слишком маленькие грани
        if self.NEGL_FACE_SIZE > 0:
            negl = self.NEGL_FACE_SIZE * 0.1  # как в оригинале
            mesh_array = mesh_array[mesh_array[:, 12] > negl]

        return mesh_array

    def _collect_candidates(self):
        # Собираем все ориентации
        cand = []
        # 1. Накопление нормалей
        cand += self._area_cumulation(12)
        # 2. Случайные грани
        cand += self._death_star(12)
        # 3. Дополнительные фиксированные направления
        cand += self._add_supplements()
        # Удаляем дубликаты
        cand = self._remove_duplicates(cand)
        return cand

    def _area_cumulation(self, best_n):
        # Поиск наиболее частых нормалей с весами площадей
        normals = self.mesh[:, 0:3]
        areas = self.mesh[:, 12]
        orient = Counter()
        for i in range(len(normals)):
            key = tuple(np.around(normals[i], decimals=6))
            orient[key] += areas[i]
        top = orient.most_common(best_n)
        # Преобразуем в список ориентаций (вектор, вес не нужен)
        return [list(v[0]) for v in top]

    def _death_star(self, best_n):
        # Генерация случайных граней через комбинации рёбер
        n = len(self.mesh)
        iterations = max(1, int(20000 / (n + 100)))
        vertices = self.mesh[:, 3:12].reshape(n, 3, 3)
        orientations = []
        for _ in range(iterations):
            # Выбираем два случайных индекса вершин из каждой грани
            idx = np.random.choice(3, 2, replace=False)
            v0 = vertices[:, idx[0], :]
            v1 = vertices[:, idx[1], :]
            # Третья вершина — случайная из другой грани
            other_idx = (np.arange(n) * 127 + 8191 + _) % n
            v2 = vertices[other_idx, np.random.randint(0, 3), :]
            normals = np.cross(v2 - v0, v1 - v0)
            lengths = np.sqrt(np.sum(normals ** 2, axis=1))
            with np.errstate(divide='ignore', invalid='ignore'):
                normals = normals / lengths[:, np.newaxis]
            # Округляем
            normals = np.around(normals, decimals=6)
            for norm in normals:
                orientations.append(tuple(norm))
        # Частотный анализ
        cnt = Counter(orientations)
        most = cnt.most_common(best_n)
        most = [list(v) for v, c in most if c >= 2]
        most += [[-v[0], -v[1], -v[2]] for v in most]
        return most

    @staticmethod
    def _add_supplements():
        # Базовые направления
        v = [
            [0, 0, -1], [0.70710678, 0, -0.70710678], [0, 0.70710678, -0.70710678],
            [-0.70710678, 0, -0.70710678], [0, -0.70710678, -0.70710678],
            [1, 0, 0], [0.70710678, 0.70710678, 0], [0, 1, 0], [-0.70710678, 0.70710678, 0],
            [-1, 0, 0], [-0.70710678, -0.70710678, 0], [0, -1, 0], [0.70710678, -0.70710678, 0],
            [0.70710678, 0, 0.70710678], [0, 0.70710678, 0.70710678],
            [-0.70710678, 0, 0.70710678], [0, -0.70710678, 0.70710678], [0, 0, 1]
        ]
        return v

    @staticmethod
    def _remove_duplicates(orients, tol_deg=5):
        tol = np.sin(np.radians(tol_deg))
        unique = []
        for o in orients:
            dup = False
            for u in unique:
                if np.allclose(o, u, atol=tol):
                    dup = True
                    break
            if not dup:
                unique.append(o)
        return unique

    def _evaluate(self, orientation):
        # Вычисляет bottom, overhang, contour
        # Проекции вершин на ориентацию
        verts = self.mesh[:, 3:12].reshape(-1, 3, 3)
        proj = np.inner(verts, orientation)  # (N, 3)
        min_proj = np.min(proj, axis=1)
        max_proj = np.max(proj, axis=1)
        med_proj = np.median(proj, axis=1)

        total_min = np.min(min_proj)

        # Bottom: грани, у которых max_proj < total_min + FIRST_LAY_H
        bottom_mask = max_proj < (total_min + self.FIRST_LAY_H)
        bottom = np.sum(self.mesh[bottom_mask, 12])

        # Overhang: грани с углом > ASCENT и не bottom
        # Угол между нормалью и ориентацией: cos = dot(n, orientation)
        # Нависание, если dot(n, orientation) < ASCENT (ASCENT отрицательный)
        normals = self.mesh[:, 0:3]
        dot = np.inner(normals, orientation)
        overhang_mask = (dot < self.ASCENT) & (~bottom_mask)
        overhang_faces = self.mesh[overhang_mask]
        if len(overhang_faces) > 0:
            if self.min_volume:
                # Высота над основанием
                heights = med_proj[overhang_mask] - total_min
                inner = dot[overhang_mask] - self.ASCENT
                # Формула объёма поддержек
                overhang = np.sum(
                    (self.height_offset + self.height_log * np.log(self.height_log_k * heights + 1)) *
                    overhang_faces[:, 12] * np.abs(inner * (inner < 0)) ** self.OV_H
                )
            else:
                inner = dot[overhang_mask] - self.ASCENT
                overhang = 2 * np.sum(overhang_faces[:, 12] * np.abs(inner * (inner < 0)) ** 2)
        else:
            overhang = 0

        # Contour (периметр основания)
        # Упрощённо: ищем грани, у которых median_z близок к основанию
        contour_faces = self.mesh[med_proj < (total_min + self.FIRST_LAY_H)]
        if len(contour_faces) > 0:
            # Грубая оценка: сумма длин рёбер, лежащих в основании (требует сложной геометрии)
            contour = 4 * np.sqrt(bottom)  # упрощённо, как в Tweaker
        else:
            contour = 0

        return bottom, overhang, contour

    def _target_function(self, bottom, overhang, contour):
        # Целевая функция unprintability
        if self.min_volume:
            overhang /= 25  # для объёма
            return (self.TAR_A * (overhang + self.TAR_B) +
                    self.RELATIVE_F * (overhang + self.TAR_C) /
                    (self.TAR_D + self.CONTOUR_F * contour + self.BOTTOM_F * bottom + self.TAR_E * overhang))
        else:
            return (self.TAR_A * (overhang + self.TAR_B) +
                    self.RELATIVE_F * (overhang + self.TAR_C) /
                    (self.TAR_D + self.CONTOUR_F * contour + self.BOTTOM_F * bottom))

    def _euler(self, orientation):
        # Вычисляет ось, угол и матрицу поворота, чтобы orientation стал вертикальным вниз
        target = np.array([0, 0, -1])
        if np.allclose(orientation, target, atol=abs(self.VECTOR_TOL)):
            phi = 0
            axis = [1, 0, 0]
        elif np.allclose(orientation, -target, atol=abs(self.VECTOR_TOL)):
            phi = np.pi
            axis = [1, 0, 0]
        else:
            phi = np.pi - np.arccos(-orientation[2])
            axis = [-orientation[1], orientation[0], 0]
            axis = axis / np.linalg.norm(axis)
        # Матрица поворота по формуле Родрига
        v = np.array(axis)
        c = math.cos(phi)
        s = math.sin(phi)
        R = np.array([
            [v[0]*v[0]*(1-c)+c, v[0]*v[1]*(1-c)-v[2]*s, v[0]*v[2]*(1-c)+v[1]*s],
            [v[1]*v[0]*(1-c)+v[2]*s, v[1]*v[1]*(1-c)+c, v[1]*v[2]*(1-c)-v[0]*s],
            [v[2]*v[0]*(1-c)-v[1]*s, v[2]*v[1]*(1-c)+v[0]*s, v[2]*v[2]*(1-c)+c]
        ])
        return R


def auto_orient(input_stl, output_stl, min_volume=False, verbose=True):
    import trimesh
    mesh = trimesh.load(input_stl)
    orienter = AutoOrient(mesh, min_volume=min_volume, verbose=verbose)
    # Преобразуем 3x3 → 4x4
    R = orienter.rotation_matrix
    transform = np.eye(4)
    transform[:3, :3] = R
    rotated = mesh.copy()
    rotated.apply_transform(transform)
    rotated.export(output_stl)
    if verbose:
        print(f"Результат сохранён: {output_stl}")
        print(f"Unprintability = {orienter.unprintability:.4f}")
        print(f"Площадь нависаний = {orienter.overhang_area:.1f} мм²")
        print(f"Площадь основания = {orienter.bottom_area:.1f} мм²")
    return transform


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Использование: python auto_orient.py input.stl output.stl [--volume]")
    else:
        vol = "--volume" in sys.argv
        auto_orient(sys.argv[1], sys.argv[2], min_volume=vol, verbose=True)
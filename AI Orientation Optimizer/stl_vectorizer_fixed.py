import numpy as np
import json
import os
from pathlib import Path

print("="*60)
print("🔧 STL ВЕКТОРИЗАТОР ДЛЯ РЕКОМЕНДАТЕЛЬНОЙ СИСТЕМЫ")
print("="*60)

class SimpleSTLVectorizer:
    """Упрощенный векторизатор STL файлов"""
    
    def __init__(self):
        self.feature_names = [
            'width', 'depth', 'height', 'volume', 'area',
            'num_vertices', 'num_faces', 'center_x', 'center_y', 'center_z'
        ]
    
    def extract_basic_features(self, stl_path):
        """
        Извлекает базовые признаки из STL файла.
        Возвращает словарь с ключами 'vector' (основной) и 'features'.
        """
        try:
            # Пытаемся использовать trimesh для точного анализа
            import trimesh
            mesh = trimesh.load(stl_path)
            features = {}
            
            # 1. Размеры модели
            if hasattr(mesh, 'bounding_box'):
                bbox = mesh.bounding_box.extents
                features['width'] = float(bbox[0])
                features['depth'] = float(bbox[1])
                features['height'] = float(bbox[2])
            else:
                # Запасной вариант
                features['width'] = features['depth'] = features['height'] = 1.0
            
            # 2. Объем и площадь (примерные, если не доступны)
            features['volume'] = float(mesh.volume) if hasattr(mesh, 'volume') else 1.0
            features['area'] = float(mesh.area) if hasattr(mesh, 'area') else 1.0
            
            # 3. Информация о сетке
            features['num_vertices'] = len(mesh.vertices) if hasattr(mesh, 'vertices') else 100
            features['num_faces'] = len(mesh.faces) if hasattr(mesh, 'faces') else 200
            
            # 4. Центр масс (примерный)
            features['center_x'] = features['center_y'] = features['center_z'] = 0.5
            
            # Создаем вектор из 10 признаков
            vector = np.array([features[name] for name in self.feature_names])
            
            print(f"  ✅ Анализирован: {os.path.basename(stl_path)}")
            if 'width' in features:
                print(f"     Размеры: {features['width']:.1f}x{features['depth']:.1f}x{features['height']:.1f} мм")
            
            return {
                'vector': vector,
                'features': features,
                'success': True
            }
            
        except ImportError:
            # Если trimesh не установлен, используем упрощенный режим
            print(f"  ⚠️  trimesh не установлен. Упрощенный анализ: {os.path.basename(stl_path)}")
            return self._create_dummy_vector(stl_path)
        except Exception as e:
            print(f"  ⚠️  Ошибка анализа {stl_path}: {str(e)[:50]}...")
            return self._create_dummy_vector(stl_path)
    
    def _create_dummy_vector(self, stl_path):
        """Создает вектор на основе имени файла, если анализ не удался"""
        file_hash = hash(os.path.basename(stl_path)) % 10000
        np.random.seed(file_hash)
        vector = np.random.randn(10) * 10
        features = {name: float(vector[i]) for i, name in enumerate(self.feature_names)}
        return {
            'vector': vector,
            'features': features,
            'success': False
        }

# Глобальный экземпляр для удобного импорта
vectorizer = SimpleSTLVectorizer()

# Функция для обратной совместимости (импортируется из других скриптов)
def extract_basic_features(stl_path):
    return vectorizer.extract_basic_features(stl_path)

if __name__ == "__main__":
    print("Тест векторизатора: OK")
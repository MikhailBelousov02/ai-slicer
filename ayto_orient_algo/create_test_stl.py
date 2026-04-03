import trimesh

# Создаём коробку 20x20x20 мм
box = trimesh.primitives.Box(extents=[20, 20, 20])
box.export('test_cube.stl')
print("Создан test_cube.stl")
import bpy

# Limpa a cena
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)

# Cria um cubo
bpy.ops.mesh.primitive_cube_add(location=(2, 0, 1))

cube = bpy.context.active_object
cube.name = "TestCube"

# Salva o resultado
output = r"D:\blender-ai\agent-test.blend"
bpy.ops.wm.save_as_mainfile(filepath=output)

print("=== BLENDER AGENT TEST ===")
print(f"Objeto criado: {cube.name}")
print(f"Localizacao: {tuple(cube.location)}")
print(f"Arquivo salvo: {output}")
print("=== SUCCESS ===")
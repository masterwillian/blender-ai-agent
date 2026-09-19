import bpy

for name in ["Verify_A", "Verify_B", "Verify_C"]:
    obj = bpy.data.objects.get(name)

    if obj:
        bpy.data.objects.remove(obj, do_unlink=True)

positions = {
    "Verify_A": (-4, 0, 1),
    "Verify_B": (0, 0, 1),
    "Verify_C": (4, 0, 1),
}

for name, location in positions.items():
    bpy.ops.mesh.primitive_cube_add(
        size=1,
        location=location
    )

    obj = bpy.context.active_object
    obj.name = name

result = {
    "created": list(positions.keys())
}
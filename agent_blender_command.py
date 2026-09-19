import bpy

# Create a collection
collection = bpy.data.collections.new('AgentTest')
bpy.context.collection.children.link(collection)

# Create a sphere
bpy.ops.mesh.primitive_uv_sphere_add(radius=1, location=(-3, 0, 1))
obj = bpy.context.active_object
obj.name = "RedSphere"
obj.scale = (1.5, 1.5, 1.5)

# Create a cube
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 1))
obj = bpy.context.active_object
obj.name = "CenterCube"
obj.scale = (1, 1, 1)

# Create a cylinder
bpy.ops.mesh.primitive_cylinder_add(radius=0.5, depth=2, location=(3, 0, 1))
obj = bpy.context.active_object
obj.name = "RightCylinder"
obj.scale = (1, 1, 2)
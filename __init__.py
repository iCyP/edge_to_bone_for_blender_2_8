import bpy,bmesh
import math
import os,re
bl_info = {
    "name":"make bones from selected edge",
    "author": "iCyP",
    "version": (0, 1),
    "blender": (2, 80, 0),
    "location": "Mesh Edit -> Ctrl + E",
    "description": "make bones from selected edge",
    "warning": "",
    "support": "TESTING",
    "wiki_url": "",
    "tracker_url": "",
    "category": "Object"
}


class ICYP_OT_edge_to_bone(bpy.types.Operator):
    bl_idname = "object.icyp_edge_to_bone"
    bl_label = "Bones from selected edges"
    bl_description = "-------"
    bl_options = {'REGISTER', 'UNDO'}
    
    reverse : bpy.props.BoolProperty(default = False)

    def execute(self,context):   
        mesh_obj = context.active_object
        bm = bmesh.from_edit_mesh(mesh_obj.data)
        #region fetch selected edge
        selected_edges = [edge for edge in bm.edges if edge.select]
        group_edges_list = []
        def edge_union(edge,edge_group):
            for i,vert in enumerate(edge.verts):
                for link_edge in vert.link_edges: 
                    if link_edge in selected_edges:
                        selected_edges.remove(link_edge)
                        if i == 0:
                            edge_group.insert(0,link_edge)
                        else:
                            edge_group.append(link_edge)
                        edge_union(link_edge,edge_group)
            return edge_group

        while len(selected_edges) > 0:
            base_edge = selected_edges.pop()
            group_edges_list.append(edge_union(base_edge,[base_edge]))

        edge_point_list = [[[vert.co for vert in edge.verts] for edge in group_edges] for group_edges in group_edges_list]

        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.add(type='ARMATURE', enter_editmode=True, location=mesh_obj.location,rotation=[xyz for xyz in mesh_obj.rotation_euler])
        armature = context.object
        armature.name = "bones"
        armature.show_in_front = True
        for edge_group in edge_point_list:
            last_bone = None
            isFirst = True
            while edge_group:
                edge = edge_group.pop()
                b = armature.data.edit_bones.new("bone")
                if self.reverse:
                    b.head = edge[0]
                    b.tail = edge[1]
                    if isFirst:
                        isFirst = False
                    else:
                        last_bone.parent = b
                    last_bone = b
                else:
                    b.head = edge[1]
                    b.tail = edge[0]
                    if isFirst:
                        isFirst = False
                    else:
                        b.parent = last_bone
                    last_bone = b
            
        context.scene.update()
        bpy.ops.object.mode_set(mode='OBJECT')
        armature.scale = mesh_obj.scale

        context.view_layer.objects.active = mesh_obj
        bpy.ops.object.mode_set(mode='EDIT')

        return {'FINISHED'}
    
# アドオン有効化時の処理
classes = [
    ICYP_OT_edge_to_bone
    ]
    
def add_button(self, context):
    if context.object.type == "MESH":
        self.layout.operator(ICYP_OT_edge_to_bone.bl_idname)
    
def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.VIEW3D_MT_edit_mesh_edges.append(add_button)
    
# アドオン無効化時の処理
def unregister():
    bpy.types.VIEW3D_MT_edit_mesh_edges.remove(add_button)
    for cls in classes:
        bpy.utils.unregister_class(cls)

if "__main__" == __name__:
    register()

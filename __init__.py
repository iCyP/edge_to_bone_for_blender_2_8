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
    
    by_ring_select : bpy.props.BoolProperty(default = False)
    reverse : bpy.props.BoolProperty(default = False)
    skip : bpy.props.IntProperty(default = 0)
    with_root_bone : bpy.props.BoolProperty(default = False)
    with_auto_weight : bpy.props.BoolProperty(default = False)
    def execute(self,context):   
        mesh_obj = context.active_object
        bm = bmesh.from_edit_mesh(mesh_obj.data)
        #region fetch selected edge
        selected_verts = [v for v in bm.verts if v.select]
        group_verts_list = []
        def vert_union(vert,vert_array,direction):
            selected_link_verts = [v for link_edge in vert.link_edges for v in link_edge.verts if v.index != vert.index and v in selected_verts]
            for sv in selected_link_verts:
                selected_verts.remove(sv)
            for i,v in enumerate(selected_link_verts):
                if direction is None:
                    if i == 0:
                        vert_array.insert(0,v)
                        vert_union(v,vert_array,True)
                    else:
                        vert_array.append(v)
                        vert_union(v,vert_array,False)  
                elif direction == True:
                    vert_array.insert(0,v)
                    vert_union(v,vert_array,direction)
                else:
                    vert_array.append(v)
                    vert_union(v,vert_array,direction)                   
            return vert_array

        while len(selected_verts) > 0:
            base_vert = selected_verts.pop()
            group_verts_list.append(vert_union(base_vert,[base_vert],None))
        #endregion fetch selected edge

        #test func
        def empty_test(loc):
            o = bpy.data.objects.new(name="",object_data = None)
            bpy.context.collection.objects.link(o)
            o.location = loc
            o.show_name = True

        edge_points_list = []
        #TODO 実装
        if self.by_ring_select:
            ring_to_points = []
            already_sampled_verts = []
            def next_vert(vert,isFirst):
                verts = []
                for link_edge in vert.link_edges:
                    for v in link_edge.verts:
                        if v not in already_sampled_verts:
                            already_sampled_verts.append(v)
                            if not isFirst:
                                return v
                            else:
                                verts.append(v)
                return verts if len(verts) != 0 else None

            points_list = []
            for group_verts in group_verts_list:
                rings = []
                already_sampled_verts += group_verts
                ring_a = []
                ring_b = []
                for vert in group_verts:
                    a = next_vert(vert,True)
                    if a is not None:
                        ring_a.append(a[0])
                        ring_b.append(a[1])

                rings.append(ring_b)
                rings.append(group_verts)
                rings.append(ring_a)
                
                #TODO 以下実装
                if len(ring_a)!=0:
                    sub_rings= [ring_a]
                    while sub_rings:
                        ring = []
                        for vert in sub_rings.pop():
                            if vert is not None:
                                v = next_vert(vert,False)
                                if v is not None :
                                    ring.append(v)
                        if len(ring):
                            sub_rings.append(ring)
                            rings.append(ring)

                if len(ring_b)!=0:
                    sub_rings = [ring_b]
                    while sub_rings:
                        ring = []
                        for vert in sub_rings.pop():
                            if vert is not None:
                                v = next_vert(vert,False)
                                if v is not None:
                                    ring.append(v)
                        if len(ring):
                            sub_rings.append(ring)
                            rings.insert(0,ring)
                points = [[],[]]
                for ring in rings :
                    average_loc = [0,0,0]
                    for vert in [v for v in ring if v is not None]:
                        average_loc = [average_loc[i]+vert.co[i] for i in range(3)]
                    sum_n = len(ring) if len(ring)!=0 else 1
                    average_loc = [average_loc[i]/sum_n for i in range(3)]
                    points[0].append(average_loc)
                    points[1] = [v.index for v in ring if v is not None]
                points_list.append(points)

            if self.reverse:
                for points in points_list:
                    points[0].reverse()
            edge_points_list = [[(point,points[1]) for point in points[0][0::self.skip+1]] for points in points_list]

        else:
            if self.reverse:
                for group_verts in group_verts_list:
                    group_verts.reverse()
            #coは参照になるからコピーしないと落ちる
            edge_points_list = [[(vert.co[:],(vert.index,))  for vert in group_verts[0::self.skip+1]] for group_verts in group_verts_list]

        
        #make armature
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.add(type='ARMATURE', enter_editmode=True, location=mesh_obj.location,rotation=[xyz for xyz in mesh_obj.rotation_euler])
        armature = bpy.context.object
        armature.name = "bones"
        armature.show_in_front = True
        vert_id_bone_name_unionflag_tuple_list = []
        
        if self.with_root_bone:
            root_bone = armature.data.edit_bones.new("root")
            root_bone.head = [0,0,0]
            root_bone.tail = [0,0,0.1]
        else :
            root_bone = None

        for point_pos_id_tuples in edge_points_list:
            last_bone = None
            head = point_pos_id_tuples.pop(0)
            isFirst = True
            vert_indexies = [id for _,ids in point_pos_id_tuples for id in ids]
            bone_names = []
            while len(point_pos_id_tuples)>=1:
                tail = point_pos_id_tuples.pop(0)
                b = armature.data.edit_bones.new("bone")
                bone_names.append(b.name)
                b.head = head[0]
                b.tail = tail[0]
                if isFirst:
                    isFirst = False
                    if self.with_root_bone:
                        b.parent = root_bone
                else:
                    b.parent = last_bone
                last_bone = b
                head = tail[:]
            vert_id_bone_name_unionflag_tuple_list.append([vert_indexies,bone_names,False])
            
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.context.object.update_from_editmode()
        armature.scale = mesh_obj.scale
        mesh_obj.modifiers.new("auto_arm","ARMATURE").object = armature
        

        #auto weight
        if self.with_auto_weight:
            mesh_obj = bpy.data.objects[mesh_obj.name]
            for i,vert_id_bone_name_tuple in enumerate(vert_id_bone_name_unionflag_tuple_list):
                vert_ids,bone_names,already_unioned = vert_id_bone_name_tuple
                #mesh select
                context.view_layer.objects.active = mesh_obj
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.select_all(action="DESELECT")
                if already_unioned:
                    continue
                for vid in vert_ids:
                    mesh_obj.data.vertices[vid].select = True
                bpy.ops.mesh.select_linked()
                selected_verts = [vert.index for vert in mesh_obj.data.vertices if vert.select]
                same_group = []
                for i,vibnt in enumerate(vert_id_bone_name_unionflag_tuple_list):
                    vids,bnames,already_union = vibnt
                    if already_union:
                        continue
                    for vid in vids:
                        if vid in selected_verts:
                            same_group.append((vids,bone_names))
                            vert_id_bone_name_unionflag_tuple_list[i][2] = True
                            break
                for vids,_ in same_group:
                    for vid in vids:
                        mesh_obj.data.vertices[vid].select = True
                bpy.ops.mesh.select_linked()
                #bone select
                bpy.ops.object.mode_set(mode='OBJECT')
                context.view_layer.objects.active = bpy.data.objects[armature.name]
                armature = bpy.data.objects[armature.name]
                bpy.ops.object.mode_set(mode='POSE')
                bpy.ops.pose.select_all(action = "DESELECT")
                for bone_name in bone_names:
                    armature.data.bones[bone_name].select = True
                for _,link_bone_names,_ in vert_id_bone_name_unionflag_tuple_list:       
                    for bone_name in link_bone_names:
                        armature.data.bones[bone_name].select = True
                if root_bone is not None:
                    armature.data.bones[root_bone.name].select = False
                #weight paint
                bpy.ops.object.mode_set(mode='OBJECT')
                bpy.context.scene.update()
                bpy.data.objects[armature.name].select_set(True)
                bpy.data.objects[mesh_obj.name].select_set(True)
                bpy.context.view_layer.objects.active = mesh_obj
                bpy.ops.object.mode_set(mode='WEIGHT_PAINT')
                bpy.ops.paint.weight_from_bones()
                bpy.ops.object.mode_set(mode='OBJECT')

        bpy.ops.object.mode_set(mode='OBJECT')
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

import bpy,bmesh
import math
import os,re
bl_info = {
    "name":"Edge to Bone for blender2.8",
    "author": "iCyP",
    "version": (0, 1),
    "blender": (2, 80, 0),
    "location": "Mesh Edit -> Ctrl + E",
    "description": "make bones from selected edge",
    "warning": "",
    "support": "TESTING",
    "wiki_url": "",
    "tracker_url": "",
    "category": "Rigging"
}

def get_armatures(scene,context):
    arms = [("empty_empty","empty","")]
    arms.extend([(obj.name,obj.name,"") for obj in bpy.data.objects if obj.type == "ARMATURE"])
    return arms

class ICYP_OT_edge_to_bone(bpy.types.Operator):
    bl_idname = "object.icyp_edge_to_bone"
    bl_label = "Bones from selected edges"
    bl_description = "-------"
    bl_options = {'REGISTER', 'UNDO'}
    
    

    def set_bone_enum(self,context):
        if self.target_armature not in (None,"") :
            bone_enum =  [(bone.name,bone.name,"") for bone in bpy.data.objects[self.target_armature].data.bones]
        else:
            bone_enum = [("example_ICYP_value","","")]
        return bone_enum
    by_ring_select : bpy.props.BoolProperty(default = False)
    reverse : bpy.props.BoolProperty(default = False)
    skip : bpy.props.IntProperty(default = 0,min = 0)
    with_root_bone: bpy.props.BoolProperty(default=False)
    target_armature : bpy.props.EnumProperty(
        name = "edge_to_bone_target_armature",
        description = "target_armature",
        items = get_armatures
        )
    target_root_bone : bpy.props.EnumProperty(
        name = "edge_to_bone_target_bone",
        description = "target_root_bone",
        items = set_bone_enum
        )
    add_leaf_bone : bpy.props.BoolProperty(default=False)
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

        #debug func
        def empty_test(loc,i=0):
            o = bpy.data.objects.new(name="",object_data = None)
            bpy.context.collection.objects.link(o)
            o.location = loc
            o.show_name = True
            o.empty_display_size = 0.1
            o.empty_display_type = ('PLAIN_AXES', 'ARROWS', 'SINGLE_ARROW', 'CIRCLE', 'CUBE', 'SPHERE', 'CONE', 'IMAGE')[i]


        edge_points_list = []
        if self.by_ring_select:
            
            def link_verts(vert):
                return [lv for le in vert.link_edges for lv in le.verts]

            already_sampled_verts = set()
            def get_next_ring(vert,already_sampled_verts):
                next_ring = []
                current_vert = None
                for v in link_verts(vert):
                    if v not in already_sampled_verts:
                        next_ring.append(v)
                        current_vert = v
                        break
                while current_vert is not None:
                    for v in link_verts(current_vert):
                        if v not in already_sampled_verts:
                            is_ring = False
                            if v not in next_ring:
                                for lv in link_verts(v):
                                    if lv in already_sampled_verts:
                                        next_ring.append(v)
                                        current_vert = v
                                        is_ring = True
                                        break
                            if not is_ring:
                                current_vert = None
                            else:
                                break

                already_sampled_verts = already_sampled_verts.union(next_ring)
                return (next_ring,already_sampled_verts) if len(next_ring)>0 else (None,already_sampled_verts)
                                    

            points_list = []
            for group_verts in group_verts_list:
                rings = []
                already_sampled_verts = already_sampled_verts.union(group_verts)
                ring_a,already_sampled_verts = get_next_ring(group_verts[0],already_sampled_verts)
                ring_b,already_sampled_verts = get_next_ring(group_verts[0],already_sampled_verts)
                if ring_a is not None:
                    rings.append(ring_b)
                rings.append(group_verts)
                if ring_b is not None:
                    rings.append(ring_a)

                if ring_a is not None:
                    sub_rings= [ring_a]
                    while sub_rings:
                        sub_ring = sub_rings.pop()
                        next_ring,already_sampled_verts = get_next_ring(sub_ring[0],already_sampled_verts) if len(sub_ring) else None
                        if next_ring is not None:
                            sub_rings.append(next_ring)
                            rings.append(next_ring)

                if ring_b is not None:
                    sub_rings = [ring_b]
                    while sub_rings:
                        sub_ring = sub_rings.pop()
                        next_ring,already_sampled_verts = get_next_ring(sub_ring[0],already_sampled_verts) if len(sub_ring) else None
                        if next_ring is not None:
                            sub_rings.append(next_ring)
                            rings.insert(0,next_ring)

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

            #sort by length from origin
            for points in points_list:
                head = points[0][0][0]** 2 + points[0][0][1]** 2 + points[0][0][2]** 2
                tail = points[0][-1][0]** 2 + points[0][-1][1]** 2 + points[0][-1][2]** 2
                if head > tail:
                    points[0].reverse()
            if self.reverse:
                for points in points_list:
                    points[0].reverse()
            edge_points_list = [[(point, points[1]) for point in points[0][0::self.skip + 1]] for points in points_list]
            for points,edge_points in zip(points_list,edge_points_list):
                if (len(points[0])-1) % (self.skip+1) != 0:
                    edge_points.append((points[0][-1],points[1]))
        else:
            #sort by length from origin
            for group_verts in group_verts_list:
                head = group_verts[0].co[0]**2+ group_verts[0].co[1]**2+ group_verts[0].co[2]**2
                tail = group_verts[-1].co[0]** 2 + group_verts[-1].co[1]** 2 + group_verts[-1].co[2]** 2
                if head > tail:
                    group_verts.reverse()
            if self.reverse:
                for group_verts in group_verts_list:
                    group_verts.reverse()
            #coは参照になるからコピーしないと落ちる
            edge_points_list = [[(vert.co[:], (vert.index,)) for vert in group_verts[0::self.skip + 1]] for group_verts in group_verts_list]
            for group_verts,edge_points in zip(group_verts_list,edge_points_list):
                if (len(group_verts)-1) % (self.skip+1) != 0:
                    edge_points.append((group_verts[-1].co[:],(group_verts[-1].index,)))
        
        #make armature
        if self.target_armature == "empty_empty":
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.add(type='ARMATURE', enter_editmode=True,\
                                location=mesh_obj.matrix_world.translation,\
                                rotation=mesh_obj.matrix_world.to_euler())
            armature = bpy.context.object
            armature.name = "bones"
            armature.show_in_front = True
        else:
            armature = bpy.data.objects[self.target_armature]
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.context.view_layer.objects.active = armature
            bpy.ops.object.mode_set(mode='EDIT')
        vert_id_bone_name_unionflag_tuple_list = []
        
        if self.with_root_bone:
            if self.target_armature != "empty_empty":
                root_bone = bpy.data.objects[self.target_armature].data.edit_bones[self.target_root_bone]
                root_bone_name = root_bone.name
            else:
                root_bone = armature.data.edit_bones.new("root")
                root_bone.head = [0,0,0]
                root_bone.tail = [0, 0, 0.1]
                root_bone_name = root_bone.name
        else :
            root_bone = None

        for point_pos_id_tuples in edge_points_list:
            last_bone = None
            head = point_pos_id_tuples.pop(0)
            isFirst = True
            vert_indexies = [_id for _,ids in point_pos_id_tuples for _id in ids]
            bone_names = []
            while len(point_pos_id_tuples)!=0:
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
            if self.add_leaf_bone:
                b = armature.data.edit_bones.new("bone")
                b.head = last_bone.tail
                b.tail = [last_bone.tail[n] + [last_bone.tail[i] - last_bone.head[i] for i in range(3)][n] for n in range(3)]
                b.parent = last_bone
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.context.object.update_from_editmode()
        armature.scale = mesh_obj.scale[:]
        mesh_obj.modifiers.new("auto_arm","ARMATURE").object = armature
        

        #auto weight
        if self.with_auto_weight:
            mesh_obj = bpy.data.objects[mesh_obj.name]
            for i,vert_id_bone_name_tuple in enumerate(vert_id_bone_name_unionflag_tuple_list):
                vert_ids, bone_names, already_unioned = vert_id_bone_name_tuple
                if already_unioned:
                    continue
                #mesh select
                context.view_layer.objects.active = mesh_obj  
                bpy.ops.object.mode_set(mode='OBJECT')
                bpy.ops.object.mode_set(mode='EDIT')        
                bpy.ops.mesh.select_all(action="DESELECT")
                bpy.ops.object.mode_set(mode='OBJECT')
                #data.verts[id].selectはobj modeでしか機能しない
                for vid in vert_ids:
                    mesh_obj.data.vertices[vid].select = True
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.select_linked() 
                bpy.ops.object.mode_set(mode='OBJECT')
                selected_verts = [vert.index for vert in mesh_obj.data.vertices if vert.select]
                same_group_bone_names = []
                for i,vibnt in enumerate(vert_id_bone_name_unionflag_tuple_list):
                    vids,sub_bone_names,already_union = vibnt
                    if already_union:
                        continue
                    for vid in vids:
                        if vid in selected_verts:
                            vert_id_bone_name_unionflag_tuple_list[i][2] = True
                            same_group_bone_names.extend(sub_bone_names)
                            break

                #bone select
                bpy.ops.object.mode_set(mode='OBJECT')
                context.view_layer.objects.active = bpy.data.objects[armature.name]
                armature = bpy.data.objects[armature.name]
                bpy.ops.object.mode_set(mode='POSE')
                bpy.ops.pose.select_all(action="DESELECT")
                for bone_name in bone_names:
                    armature.data.bones[bone_name].select = True
                for sgbn in same_group_bone_names:       
                    armature.data.bones[sgbn].select = True
                if root_bone is not None:
                    armature.data.bones[root_bone_name].select = False

                #weight paint
                bpy.ops.object.mode_set(mode='OBJECT')
                if "update" in dir(bpy.context.scene):
                    bpy.context.scene.update()
                else :
                    bpy.context.scene.view_layers.update()
                bpy.data.objects[armature.name].select_set(True)
                bpy.data.objects[mesh_obj.name].select_set(True)
                bpy.context.view_layer.objects.active = mesh_obj
                bpy.ops.object.mode_set(mode='WEIGHT_PAINT')
                bpy.context.object.data.use_paint_mask_vertex = True
                bpy.ops.paint.weight_from_bones()
                bpy.ops.object.mode_set(mode='OBJECT')

        bpy.ops.object.mode_set(mode='OBJECT')
        #bone消失対策
        context.view_layer.objects.active = armature
        bpy.ops.object.mode_set(mode='EDIT') 
        bpy.ops.object.mode_set(mode='OBJECT')
        #元に戻す
        context.view_layer.objects.active = mesh_obj
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action="DESELECT")

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
    bpy.types.VIEW3D_MT_edit_mesh_context_menu.append(add_button)
    
# アドオン無効化時の処理
def unregister():
    bpy.types.VIEW3D_MT_edit_mesh_context_menu.remove(add_button)
    for cls in classes:
        bpy.utils.unregister_class(cls)

if "__main__" == __name__:
    register()

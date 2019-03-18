import os
import json

TEMP_STORED_DATA_DIR = '{}/temp_stored_data/'.format(os.environ['MAYA_APP_DIR'])
WEIGHTS_LIST_FILENAME = '{}{}.json'.format(TEMP_STORED_DATA_DIR, 'copy_unlock_skins_tool_temp')

def saveUnlockedSkinJointsWeights(deformer_node=None):
    #Save selection
    pre_selection = cmds.ls(selection=True)
    
    #Store wigths dictionary
    deform_weights_dict = {}
    
    #Get deformer type
    deformer_node_type = cmds.nodeType(deformer_node)
    
    ## SKIN CLUSTES
    if deformer_node_type == 'skinCluster':
        #Get unlocked joints in skin.
        all_joints_in_skin = cmds.skinCluster(deformer_node, query=True, influence=True)
        unlocked_joints_in_skin = [x for x in all_joints_in_skin if not cmds.getAttr('{}.liw'.format(x))]
        
        #Get skin values.
        for unlocked_joint in unlocked_joints_in_skin:
            joints_weights_values = []
            
            #Get vertex with weights:
            cmds.select(clear=True)
            cmds.skinCluster(deformer_node, edit=True, selectInfluenceVerts=unlocked_joint)
            vertex_with_weights_list = cmds.ls(selection=True, flatten=True)
            vertex_with_weights_list = [x for x in vertex_with_weights_list if '.vtx' in x]
            cmds.select(clear=True)
            #Save weights values
            if vertex_with_weights_list:
                for vtx in vertex_with_weights_list:
                    vtx_weight_value = cmds.skinPercent(deformer_node, vtx, transform=unlocked_joint, query=True, value=True)
                    vtx_number = int(vtx.split('.vtx[')[1][:-1])
                    joints_weights_values.append([vtx_number, vtx_weight_value])
            else:
                joints_weights_values.append([0, 0])
            
            #Save joint data at dict
            if joints_weights_values:
                deform_weights_dict[unlocked_joint] = joints_weights_values
                
    # If not exits the path folder, create
    if not os.path.exists(TEMP_STORED_DATA_DIR):
        os.makedirs(TEMP_STORED_DATA_DIR)
    
    # Save the dict with weights info at temporary file
    with open(WEIGHTS_LIST_FILENAME, 'w') as f:
        json.dump(deform_weights_dict, f, indent=4)
    
    #Select the preSelection
    if pre_selection:
        cmds.select(pre_selection, replace=True)
        
    print 'Unlocked skin joints values stored.',


def getSkinsInGeometry(geometry=None):
    # Get clean input history in geometry
    input_history = cmds.listHistory(geometry, pruneDagObjects=True, interestLevel=2)
    if not input_history:
        cmds.warning('The geometry doesnt have a skinCluster.')
        return
        
    #Get skinClusters in the history
    skinClusters_in_history = [x for x in input_history if cmds.objectType(x) == 'skinCluster']
    if not skinClusters_in_history:
        cmds.warning('The geometry doesnt have a skinCluster.')
        return
    if len(skinClusters_in_history) > 1:
        cmds.warning('The geometry has more than one skinCluster.')
        return
    
    return skinClusters_in_history[0]

def pasteUnlockedSkinJointsWeights(deformer_node=None, geometry=None):
    #Save selection
    pre_selection = cmds.ls(selection=True)
        
    #Get deformer type
    deformer_node_type = cmds.nodeType(deformer_node)
    
    ## SKIN CLUSTES
    if deformer_node_type == 'skinCluster':
        #Store wigths dictionary
        deform_weights_dict = {}
        
        #Check if temp file exists.
        if not os.path.exists(WEIGHTS_LIST_FILENAME):
            cmds.error('Doesnt exists weights copy information.')
        
        #Read temporary file.
        with open(WEIGHTS_LIST_FILENAME, 'r') as f:
            deform_weights_dict = json.load(f)
        
        #Get unlocked joints in skin.
        all_joints_in_skin = cmds.skinCluster(deformer_node, query=True, influence=True)
        unlocked_joints_in_skin = [x for x in all_joints_in_skin if not cmds.getAttr('{}.liw'.format(x))]
        
        #Joints in temporary file
        joints_in_file = deform_weights_dict.keys()
        
        #Difference inlocked joints with joints in file
        dif_joints = [x for x in unlocked_joints_in_skin + joints_in_file 
                      if x not in unlocked_joints_in_skin or x not in joints_in_file] 
        if dif_joints:
            cmds.error('The joints unlocked between the copy and paste skins are different.')
            return
        
        #Send all weights to the first unlocked joint.
        geometry_vertex = cmds.ls('{}.vtx[*]'.format(geometry))[0]
        cmds.skinPercent(deformer_node, geometry_vertex, 
                         transformValue=(unlocked_joints_in_skin[0], 1))
        
        #Read the weights in that joint.
        vertex_base = []
        weights_base = []
        cmds.select(clear=True)
        cmds.skinCluster(deformer_node, edit=True, selectInfluenceVerts=unlocked_joints_in_skin[0])
        vertex_with_weights_list = cmds.ls(selection=True, flatten=True)
        vertex_with_weights_list = [x for x in vertex_with_weights_list if '.vtx' in x]
        cmds.select(clear=True)
        #Save weights values
        if vertex_with_weights_list:
            for vtx in vertex_with_weights_list:
                vtx_weight_value = cmds.skinPercent(deformer_node, vtx, transform=unlocked_joints_in_skin[0], query=True, value=True)
                vtx_number = int(vtx.split('.vtx[')[1][:-1])
                vertex_base.append(vtx_number)
                weights_base.append(vtx_weight_value)
        
        #Total weight to apply percentage
        vertex_total = []
        weights_total = []
        for paste_joint in unlocked_joints_in_skin:
            weight_joint_info = deform_weights_dict[paste_joint]
            vertex_to_paste = [x[0] for x in weight_joint_info]
            weights_to_paste = [x[1] for x in weight_joint_info]
            for i, vtx_to_paste in enumerate(vertex_to_paste):
                if vtx_to_paste not in vertex_total:
                    vertex_total.append(vtx_to_paste)
                    weights_total.append(weights_to_paste[i])
                else:
                    pos_vtx_total = vertex_total.index(vtx_to_paste)
                    weights_total[pos_vtx_total] = weights_total[pos_vtx_total] + weights_to_paste[i]
        
        #Calculate percentage procces
        joint_percentage = 100 / len(unlocked_joints_in_skin)
        
        #Apply paste weights by joint
        percentage_done = 0
        for paste_joint in unlocked_joints_in_skin:
            weight_joint_info = deform_weights_dict[paste_joint]
            vertex_to_paste = [x[0] for x in weight_joint_info]
            weights_to_paste = [x[1] for x in weight_joint_info]
            for i, vtx_to_modify in enumerate(vertex_base):
                if vtx_to_modify in vertex_to_paste:
                    # Get the free value
                    total_free_weight = weights_base[i]
                    weight_total = weights_total[i]
                    #Get the percentage value
                    pos_vtx_in_joint = vertex_to_paste.index(vtx_to_modify)
                    vtx_joint_weight = weights_to_paste[pos_vtx_in_joint]
                    
                    #Value to paste
                    final_joint_weight = total_free_weight * (weight_total * vtx_joint_weight)
                    cmds.skinPercent(deformer_node, '{}.vtx[{}]'.format(geometry, str(vtx_to_modify)),
                                     transformValue=[(paste_joint, final_joint_weight)])
                else:
                    cmds.skinPercent(deformer_node, '{}.vtx[{}]'.format(geometry, str(vtx_to_modify)),
                                     transformValue=[(paste_joint, 0)])
                    
            cmds.setAttr('{}.liw'.format(paste_joint), 1)
            percentage_done = percentage_done + joint_percentage
            print 'Paste procces at {}%'.format(str(percentage_done))
        
        #Unlock the joints
        for unlocked_joint in unlocked_joints_in_skin:
            cmds.setAttr('{}.liw'.format(unlocked_joint), 0)
        
        #Print end function
        print 'Pasted the copy weights values.',
                    
                    
                    
                    
### COPY PASTE     
geometries_list = cmds.ls(selection = True)
first_geometry_skin = getSkinsInGeometry(geometry=geometries_list[0])
second_geometry_skin = getSkinsInGeometry(geometry=geometries_list[1])
saveUnlockedSkinJointsWeights(deformer_node=first_geometry_skin)
pasteUnlockedSkinJointsWeights(deformer_node=second_geometry_skin, geometry=geometries_list[1])



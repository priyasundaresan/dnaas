import os
import numpy as np
import logging

import meshpy
from meshpy import ObjFile
from autolab_core import RigidTransform

import dexnet.database.mesh_processor as mp
import dexnet.grasping.grasp_sampler as gs
import dexnet.grasping.grasp_quality_config as gqc
import dexnet.grasping.grasp_quality_function as gqf
from dexnet.grasping import GraspableObject3D, ParametrizedParallelJawGripper, GraspCollisionChecker

import consts

PROCESS_NAME = None

def grasps_to_dicts(grasps, metrics):
    grasps_list = []
    for grasp, metric in sorted(zip(grasps, metrics), key=lambda x: -x[1]):
        grasps_list.append({'center' : list(grasp.center),
                            'axis' : list(grasp.axis),
                            'open_width' : grasp.max_grasp_width_,
                            'grasp_width' : grasp.jaw_width,
                            'metric_score' : metric})
    return grasps_list

def load_mesh(mesh_id):
    # set up filepath from mesh id (this is where the service dumps the mesh
    filepath = os.path.join(consts.MESH_CACHE_DIR, mesh_id) + '.obj'

    # Initialize mesh processor.
    mesh_processor = mp.MeshProcessor(filepath, consts.MESH_CACHE_DIR)

    # Process mesh
    mesh, sdf, stable_poses = mesh_processor.generate_graspable(consts.CONFIG)

    # Make graspable
    graspable = GraspableObject3D(sdf           = sdf,
                                  mesh          = mesh,
                                  key           = mesh_id,
                                  model_name    = mesh_processor.obj_filename,
                                  mass          = consts.CONFIG['default_mass'],
                                  convex_pieces = None)
                                  
    # resave mesh to the proc file because the new CoM thing translates the mesh
    ObjFile(os.path.join(consts.MESH_CACHE_DIR, mesh_id) + '_proc.obj').write(graspable.mesh)
    
    return graspable, stable_poses

def sample_grasps(graspable, gripper, config):
    """ Sample grasps and compute metrics for given object, gripper, and stable pose """
    # create grasp sampler)
    if config['grasp_sampler'] == 'antipodal':
        sampler = gs.AntipodalGraspSampler(gripper, config)
    elif config['grasp_sampler'] == 'mesh_antipodal':
        sampler = gs.MeshAntipodalGraspSampler(gripper, config)
    elif config['grasp_sampler'] == 'gaussian':
        sampler = gs.GaussianGraspSampler(gripper, config)
    elif config['grasp_sampler'] == 'uniform':
        sampler = gs.UniformGraspSampler(gripper, config)

    # sample grasps
    grasps = sampler.generate_grasps(graspable, max_iter=config['max_grasp_sampling_iters'])
    return grasps

def filter_grasps_generic(graspable, grasps, gripper, progress_reporter=lambda x: None):
    progress_reporter(0)

    collision_checker = GraspCollisionChecker(gripper)
    collision_checker.set_graspable_object(graspable)

    collision_free_grasps = []
    colliding_grasps = []

    for k, grasp in enumerate(grasps):
        progress_reporter(float(k) / len(grasps))
        collision_free = False
        for rot_idx in range(0, consts.GENERAL_COLLISION_CHECKING_NUM_OFFSETS):
            rotated_grasp = grasp.grasp_y_axis_offset(rot_idx * consts.GENERAL_COLLISION_CHECKING_PHI)
            collides = collision_checker.collides_along_approach(rotated_grasp,
                                                                 consts.APPROACH_DIST,
                                                                 consts.DELTA_APPROACH)
            if not collides:
                collision_free = True
                collision_free_grasps.append(grasp)
                break
        if not collision_free:
            colliding_grasps.append(grasp)
    return collision_free_grasps, colliding_grasps

def filter_grasps_stbp(graspable, grasps, gripper, stable_poses, progress_reporter=lambda x: None):
    progress_reporter(0)
    
    collision_checker = GraspCollisionChecker(gripper)
    collision_checker.set_graspable_object(graspable)

    stbp_grasps_indices = []
    stbp_grasps_aligned = []
    for k, stable_pose in enumerate(stable_poses):
        # set up collision checker with table
        T_obj_stp = RigidTransform(rotation=stable_pose.r, from_frame='obj', to_frame='stp')
        T_obj_table = graspable.mesh.get_T_surface_obj(T_obj_stp,
                                                       delta=consts.COLLISION_CONFIG['table_offset']).as_frames('obj', 'table')
        T_table_obj = T_obj_table.inverse()
        collision_checker.set_table(consts.COLLISION_CONFIG['table_mesh_filename'], T_table_obj)

        aligned_grasps = [grasp.perpendicular_table(stable_pose) for grasp in grasps]
        this_stbp_grasps_indices = []
        this_stbp_grasps_aligned = []
        for idx, aligned_grasp in enumerate(aligned_grasps):
            progress_reporter(float(idx) / (len(grasps) * len(stable_poses)) + float(k) / len(stable_poses))
            _, grasp_approach_table_angle, _ = aligned_grasp.grasp_angles_from_stp_z(stable_pose)
            perpendicular_table = (np.abs(grasp_approach_table_angle) < consts.MAX_GRASP_APPROACH_TABLE_ANGLE)
            if not perpendicular_table:
                continue
            # check whether any valid approach directions are collision free
            for phi_offset in consts.PHI_OFFSETS:
                rotated_grasp = aligned_grasp.grasp_y_axis_offset(phi_offset)
                collides = collision_checker.collides_along_approach(rotated_grasp, consts.APPROACH_DIST, consts.DELTA_APPROACH)
                if not collides:
                    this_stbp_grasps_indices.append(idx)
                    this_stbp_grasps_aligned.append(aligned_grasp)
                    break
        stbp_grasps_indices.append(this_stbp_grasps_indices)
        stbp_grasps_aligned.append(this_stbp_grasps_aligned)
    return stbp_grasps_indices, stbp_grasps_aligned

def compute_metrics(graspable, grasps, gripper, metric_spec, progress_reporter=lambda x: None):
    """ Ripped from API to compute only collision-free grasps and make progress logging easier """

    progress_reporter(0)

    # compute grasp metrics
    grasp_metrics = []
    # create metric
    metric_config = gqc.GraspQualityConfigFactory.create_config(metric_spec)

    # compute metric
    # add params from gripper (right now we don't want the gripper involved in quality computation)
    setattr(metric_config, 'force_limits', gripper.force_limit)
    setattr(metric_config, 'finger_radius', gripper.finger_radius)

    # create quality function
    quality_fn = gqf.GraspQualityFunctionFactory.create_quality_function(graspable, metric_config)

    # compute quality for each grasp
    for k, grasp in enumerate(grasps):
        progress_reporter(float(k) / len(grasps))
        q = quality_fn(grasp)
        grasp_metrics.append(q.quality)
    return grasp_metrics


def preprocess_mesh(mesh_id, gripper_params, progress_reporter_big=lambda x: None, progress_reporter_small=lambda x: None):
    progress_reporter_big('preprocessing')
    # Update gripper params with defaults
    for key in consts.GRIPPER_PARAM_DEFAULTS:
        if key not in gripper_params:
            gripper_params[key] = consts.GRIPPER_PARAM_DEFAULTS[key]

    graspable, stable_poses = load_mesh(mesh_id)

    # Load gripper
    gripper = ParametrizedParallelJawGripper.load('generic_{}'.format(PROCESS_NAME), gripper_dir=consts.GRIPPER_DIR)
    gripper.update(gripper_params['fingertip_x'],
                    gripper_params['fingertip_y'],
                    gripper_params['palm_depth'],
                    gripper_params['width'])

    progress_reporter_big('sampling grasps')

    grasps = sample_grasps(graspable, gripper, consts.CONFIG)

    progress_reporter_big('collision checking')
    collision_free_grasps, colliding_grasps = filter_grasps_generic(graspable, grasps, gripper, progress_reporter=progress_reporter_small)

    progress_reporter_big('collision checking for stable poses')
    stbp_grasps_indices, stbp_grasps_aligned = filter_grasps_stbp(graspable, collision_free_grasps, gripper, stable_poses, progress_reporter=progress_reporter_small)

    progress_reporter_big('computing metrics')
    metric_spec = consts.CONFIG['metrics'][consts.METRIC_USED]
    grasp_metrics = compute_metrics(graspable, collision_free_grasps, gripper, metric_spec, progress_reporter=progress_reporter_small)

    # Process transforms into a form usable by the web api and return them
    stbp_trans = {}
    stbp_grasp = {}
    for pose_num, (stable_pose, one_stbp_grasps_indices, one_stbp_grasps_aligned) in enumerate(zip(stable_poses, stbp_grasps_indices, stbp_grasps_aligned)):
        T_obj_stp = RigidTransform(rotation=stable_pose.r, from_frame='obj', to_frame='stp')
        T_obj_table = graspable.mesh.get_T_surface_obj(T_obj_stp) # T_obj_table without offset, save this to send to client
        transform_dict = {
            'translation' : list(T_obj_table.translation),
            'quaternion'  : list(T_obj_table.quaternion),
            'probablility' : float(stable_pose.p)
        }
        stbp_trans[str(pose_num)] = transform_dict
        stbp_grasp[str(pose_num)] = grasps_to_dicts(one_stbp_grasps_aligned, [grasp_metrics[idx] for idx in one_stbp_grasps_indices])

    grasps = grasps_to_dicts(collision_free_grasps + colliding_grasps, grasp_metrics + [-1] * len(colliding_grasps))

    return grasps, stbp_trans, stbp_grasp

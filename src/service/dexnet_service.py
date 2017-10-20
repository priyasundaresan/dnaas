import os
from threading import Thread
import multiprocessing
import time
import uuid
import pickle
import traceback
import warnings
import json
import shutil

from flask import Flask, request, jsonify, send_file, g
from flask_cors import CORS, cross_origin

import numpy as np

from dexnet.grasping import ParametrizedParallelJawGripper # For getting gripper model

import dexnet_worker, consts

app = Flask(__name__)
CORS(app)

# =================================================================================================
# pickle dumping with a dict-like interface (for persistent storage)
# =================================================================================================
class disk_dictlike(object):
    """ Implements dict-like interface for dumping/reading objects from disk (incomplete)
    Only accepts string keys

    Is thread-safe but not process-safe
    """
    def __init__(self, path):
        self.path = os.path.abspath(path)
        if not os.path.isdir(self.path):
            if os.path.isfile(path):
                raise RuntimeError("{} is a path to a file, cannot create disk dict".format(self.path))
            os.makedirs(path)
        self.lock = False
    def __setitem__(self, key, value):
        while self.lock:
            time.sleep(0.1)
        self.lock = True
        try:
            with open(os.path.join(self.path, key), 'w') as f:
                pickle.dump(value, f, protocol=2)
        except Exception:
            self.lock = False
            raise
        self.lock = False
    def __getitem__(self, key):
        while self.lock:
            time.sleep(0.1)
        self.lock = True
        try:
            with open(os.path.join(self.path, key), 'r') as f:
                out = pickle.load(f)
        except Exception:
            self.lock = False
            raise
        self.lock = False
        return out
    def __iter__(self):
        for key in self.keys():
            yield (key, self[key])
    def keys(self):
        return os.listdir(self.path)
# =================================================================================================
# END
# =================================================================================================

# =================================================================================================
# Main method (initializaiton) of server
# =================================================================================================
if True: #os.environ.get("WERKZEUG_RUN_MAIN") == "true":
    # Job queue and input arg storage
    # Non-persistent because we server restarts should wipe this.
    job_queue = []
    job_args = {}

    # Persistent storage dicts
    progress =          disk_dictlike(os.path.join(consts.CACHE_DIR, 'persistent_progress'))
    errors =            disk_dictlike(os.path.join(consts.CACHE_DIR, 'persistent_errors'))
    errors_handled =    disk_dictlike(os.path.join(consts.CACHE_DIR, 'persistent_errors_handled'))
    filtered_grasps =   disk_dictlike(os.path.join(consts.CACHE_DIR, 'filtered_grasps'))
    stbp_trans =        disk_dictlike(os.path.join(consts.CACHE_DIR, 'stbp_trans'))
    stbp_grasp =        disk_dictlike(os.path.join(consts.CACHE_DIR, 'stbp_grasps'))

    time_logging =      disk_dictlike(os.path.join(consts.CACHE_DIR, 'persistent_logging'))  # TODO: Replace this with better logging

    # Wipe progress (anything that's not done is error because the server got restarted)
    for key in progress.keys():
        try:
            if progress[key] not in ['error', 'done']:
                progress[key] = 'error'
        except Exception:
            progress[key] = 'error'

    # For convenient acess of persistent storage dicts
    storage_dicts = {'progress': progress,
                     'errors' : errors,
                     'errors_handled' : errors_handled,
                     'filtered_grasps' : filtered_grasps,
                     'stbp_trans' : stbp_trans,
                     'stbp_grasp' : stbp_grasp,
                     'time_logging' : time_logging}

    # Initialize workers with their own copies of
    workers = []
    jobs_done_by = {}
    for i in range(0, consts.NUM_WORKERS):
        jobs_done_by[str(i)] = []
        worker = dexnet_worker.DexNetWorker(i)
        workers.append(worker)

    # Process manager function (copies data to persistent dict-likes, sends jobs to workers)
    def process_manager_fn():
        while True:
            for i, worker in enumerate(workers):
                if not worker.alive:
                    warnings.warn('Worker {} died, restarting'.format(i)) # TODO: actually restart the worker
                    worker.restart()
                while worker.has_ret:
                    destination, data = worker.ret
                    mesh_id, data = data
                    if destination != 'time_logging':
                        storage_dicts[destination][mesh_id] = data
                    else:
                        time_logging_dict = time_logging[mesh_id] # TODO: Replace this with better logging
                        time_logging_dict[data[0]] = data[1]
                        time_logging[mesh_id] = time_logging_dict
            if len(job_queue) != 0:
                try:
                    name = job_queue[0]
                    for worker in workers:
                        if not worker.busy:
                            args = job_args[name]
                            if args[0] == 'upload_mesh':
                                progress[name] = 'computing SDF'
                                jobs_done_by[worker.process_name].append(name)
                                job_queue.pop(0)
                                worker.preprocess_mesh(name, gripper_params=args[1])
                                break
                            else:
                                errors['general'] = "Got function {} that doesn't exist".format(args[0])
                except Exception as e:
                    errors['general'] = traceback.format_exc()
    # Start process manager
    process_manager_thread = Thread(target=process_manager_fn)
    process_manager_thread.start()
# =================================================================================================
# END
# =================================================================================================


# =================================================================================================
# Flask endpoints
# =================================================================================================
@app.before_request
def before_request():
    g.request_start_time = time.time()

@app.after_request
def after_request(response):
    # Return early if we don't have the start time
    if not hasattr(g, 'request_start_time'):
        return response

    # Record request time, response time in logging dict TODO: Replace this with better logging
    # if 'upload-mesh' in request.path.split('/'):
    #     logging_dict = time_logging[g.obj_id]
    #     logging_dict['request finished'] = time.time()
    #     logging_dict['request recieved'] = g.request_start_time
    #     time_logging[g.obj_id] = logging_dict

    # Get elapsed time in milliseconds
    # elapsed = time.time() - g.request_start_time
    # elapsed = int(round(1000 * elapsed))



    # Collect request/response tags
    # tags = [
    #     'mesh_id:{mesh_id}'.format(mesh_id=request.args['mesh_id']),
    #     'endpoint:{endpoint}'.format(endpoint=request.endpoint),
    #     'request_method:{method}'.format(method=request.method.lower()),
    #     'status_code:{status_code}'.format(status_code=response.status_code),
    # ]

    # if 'progress' in request.rule:
    #   tags.append('progress:{progress}'.format(progress=response['state']))

    # Record our response time metric
    # warnings.warn('flask.response.time', elapsed, tags=g.request_tags + tags) # Note: this doesn't actually work, just throws an error

    # Return the original unmodified response
    return response

@app.route('/upload-mesh', methods=['POST'])
def upload_mesh():
    file = request.files['file']
    if 'gripper' in request.files:
        gripper_args = request.files['gripper'].read()
    elif 'gripper' in request.form:
        gripper_args = request.form['gripper']
    else:
        gripper_args = '{}'
    gripper_args = json.loads(gripper_args)

    obj_id = str(uuid.uuid4())

    time_logging[obj_id] = {} # TODO: Replace this with better logging
    g.obj_id = obj_id

    file.save(os.path.join(consts.MESH_CACHE_DIR, obj_id + '.obj'))
    job_args[obj_id] = ('upload_mesh', (gripper_args))
    job_queue.append(obj_id)
    return jsonify({'id' : obj_id, 'position' : len(job_queue)})

@app.route('/<mesh_id>/processing-progress', methods=['GET'])
def get_progress(mesh_id):
    mesh_id = mesh_id.encode('ascii', 'replace')
    if mesh_id not in progress.keys():
        if mesh_id in job_queue:
            return jsonify({'state' : 'in queue', 'position' : job_queue.index(mesh_id)})
        else:
            return 'mesh with given id ({}) not found\n'.format(mesh_id), 404
    state = progress[mesh_id]
    ret_dict = {'state' : state}
    if state == 'computing metrics':
        ret_dict['percent done'] = 0
        for worker in workers:
            if mesh_id in jobs_done_by[worker.process_name]:
                ret_dict['percent done'] = worker.progress
                break
    return jsonify(ret_dict)

@app.route('/<mesh_id>/kill-job', methods=['POST'])
def kill_job(mesh_id):
    mesh_id = mesh_id.encode('ascii', 'replace')
    if mesh_id not in job_queue:
        if mesh_id != current_job:
            return 'requested mesh not in queue'.format(mesh_id), 404
        else:
            return 'mesh {} has begun computation and cannot be killed'.format(mesh_id), 412
    else:
        job_queue.remove(mesh_id)
        return 'mesh {} removed from queue'.format(mesh_id)

@app.route('/<mesh_id>', methods=['GET'])
def get_rescaled_mesh(mesh_id):
    mesh_id = mesh_id.encode('ascii', 'replace')
    mesh_filename = os.path.join(consts.MESH_CACHE_DIR, mesh_id + '_proc.obj')
    if not os.path.isfile(mesh_filename):
        return 'mesh with given id ({}) not found\n'.format(mesh_id), 404
    return send_file(mesh_filename, attachment_filename=mesh_id + '.obj', as_attachment=True)

@app.route('/<mesh_id>/grasps', methods=['GET'])
def get_grasps(mesh_id):
    mesh_id = mesh_id.encode('ascii', 'replace')
    try:
        grasps = filtered_grasps[mesh_id]
    except KeyError:
        return 'mesh with given id ({}) not found\n'.format(mesh_id), 404
    return jsonify(grasps)

@app.route('/<mesh_id>/stable-poses', methods=['GET'])
def get_stable_pose_count(mesh_id):
    mesh_id = mesh_id.encode('ascii', 'replace')
    if mesh_id not in stbp_trans.keys():
        return 'mesh with given id ({}) not found\n'.format(mesh_id), 404
    return jsonify(stbp_trans[mesh_id])

@app.route('/<mesh_id>/stable-poses/<pose_id>/transform', methods=['GET'])
def get_stable_pose_transforms(mesh_id, pose_id):
    mesh_id = mesh_id.encode('ascii', 'replace')
    pose_id = pose_id.encode('ascii', 'replace')
    if mesh_id not in stbp_trans.keys():
        return 'mesh with given id ({}) not found\n'.format(mesh_id), 404
    transforms = stbp_trans[mesh_id]
    if pose_id not in transforms.keys():
        return 'pose {} not found for mesh {}\n'.format(pose_id, mesh_id), 404
    return jsonify(transforms[pose_id])

@app.route('/<mesh_id>/stable-poses/<pose_id>/filtered-grasps', methods=['GET'])
def get_filtered_grasps(mesh_id, pose_id):
    mesh_id = mesh_id.encode('ascii', 'replace')
    pose_id = pose_id.encode('ascii', 'replace')
    if mesh_id not in stbp_trans.keys():
        return 'mesh with given id ({}) not found\n'.format(mesh_id), 404
    grasps_filt = stbp_grasp[mesh_id]
    if pose_id not in grasps_filt.keys():
        return 'pose {} not found for mesh {}\n'.format(pose_id, mesh_id), 404
    return jsonify(grasps_filt[pose_id])

@app.route('/gripper-mesh', methods=['POST'])
def get_gripper_mesh():
    if 'gripper' in request.files:
        gripper_params = request.files['gripper'].read()
    elif 'gripper' in request.form:
        gripper_params = request.form['gripper']
    else:
        gripper_params = '{}'
    gripper_params = json.loads(gripper_params)

    for key in consts.GRIPPER_PARAM_DEFAULTS:
        if key not in gripper_params:
            gripper_params[key] = consts.GRIPPER_PARAM_DEFAULTS[key]

    gripper = ParametrizedParallelJawGripper.load('generic', gripper_dir=consts.GRIPPER_DIR)
    gripper.update(gripper_params['fingertip_x'],
                    gripper_params['fingertip_y'],
                    gripper_params['palm_depth'],
                    gripper_params['width'])
    return send_file(os.path.join(consts.GRIPPER_DIR, 'generic/gripper.obj'), attachment_filename='gripper.obj', as_attachment=True)

@app.route('/<mesh_id>/error', methods=['GET'])
def get_error(mesh_id):
    mesh_id = mesh_id.encode('ascii', 'replace')
    if mesh_id not in errors_handled.keys():
        return "Not found\n"
    return errors_handled[mesh_id]

# Debug endpoints (potential to expose code, should be turned off in production if serious about security)
if consts.DEBUG:
    @app.route('/<mesh_id>/error-trace', methods=['GET'])
    def get_trace(mesh_id):
        mesh_id = mesh_id.encode('ascii', 'replace')
        if mesh_id not in errors.keys():
            return "Not found\n"
        return '<div style="font-family:monospace"> {} </div>'.format(
            errors[mesh_id].replace('\n', '<br>').replace(' ', '&nbsp;'))
# =================================================================================================
# END
# =================================================================================================

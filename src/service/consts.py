import numpy as np
import os
from autolab_core import YamlConfig

DEXNET_API_ROOT    = '/var/www/html/dexnet-api'
DEXNET_ROOT        = os.path.join(DEXNET_API_ROOT, 'dexnet/dex-net')
DNAAS_SERVICE_ROOT = os.path.join(DEXNET_API_ROOT, 'dnaas/src/service')
CACHE_DIR          = os.path.join(DEXNET_API_ROOT, 'webcache')
MESH_CACHE_DIR     = os.path.join(CACHE_DIR, 'mp_cache')

# DEXNET_API_ROOT = '/mnt/c/Users/alanp/Documents/CollegeNonclass/AUTOLAB/dnaas_refactor'
# DEXNET_ROOT     = os.path.join(DEXNET_API_ROOT, 'dex-net')
# CACHE_DIR       = os.path.join(DEXNET_API_ROOT, 'webcache')
# MESH_CACHE_DIR  = os.path.join(CACHE_DIR, 'mp_cache')

DEBUG = True
NUM_WORKERS = 2

SERVICE_DEFAULTS_FILE = os.path.join(DNAAS_SERVICE_ROOT, 'defaults.yaml')
GLOBAL_DEFAULTS_FILE  = os.path.join(DEXNET_ROOT, 'cfg/api_defaults.yaml')
GRIPPER_DIR = os.path.join(DNAAS_SERVICE_ROOT, 'grippers')

from collections import Mapping
def _deep_update_config(config, updates):
    """ Deep updates a config dict """
    for key, value in updates.iteritems():
        if isinstance(value, Mapping):
            try:
                base = config[key]
            except KeyError:
                base = {}
            config[key] = _deep_update_config(base, value)
        else:
            config[key] = value
    return config
CONFIG = _deep_update_config(YamlConfig(GLOBAL_DEFAULTS_FILE), YamlConfig(SERVICE_DEFAULTS_FILE))
CONFIG['cache_dir'] = MESH_CACHE_DIR


METRIC_USED = 'robust_ferrari_canny'
APPROACH_DIST = 0.1
DELTA_APPROACH = 0.005

GENERAL_COLLISION_CHECKING_NUM_OFFSETS = 100
GENERAL_COLLISION_CHECKING_PHI = 2 * np.pi / GENERAL_COLLISION_CHECKING_NUM_OFFSETS

COLLISION_CONFIG = {'table_offset' : 0.005,
                    'table_mesh_filename' : os.path.join(DEXNET_ROOT, 'data/meshes/table.obj'),
                    'approach_dist' : 0.1,
                    'delta_approach' : 0.005}
TABLE_ALIGNEMNT_PARAMS = {'max_approach_offset'         : 10,
                          'max_approach_table_angle'    : 10,
                          'num_approach_offset_samples' : 5}

MIN_GRASP_APPROACH_OFFSET = -np.deg2rad(TABLE_ALIGNEMNT_PARAMS['max_approach_offset'])
MAX_GRASP_APPROACH_OFFSET = np.deg2rad(TABLE_ALIGNEMNT_PARAMS['max_approach_offset'])
MAX_GRASP_APPROACH_TABLE_ANGLE = np.deg2rad(TABLE_ALIGNEMNT_PARAMS['max_approach_table_angle'])
NUM_GRASP_APPROACH_SAMPLES = TABLE_ALIGNEMNT_PARAMS['num_approach_offset_samples']

# This should probably be removed and defaults served from UI
GRIPPER_PARAM_DEFAULTS = {'fingertip_x' : 0.01,
                            'fingertip_y' : 0.01,
                            'palm_depth' : 0.2,
                            'width' : 0.05,
                            'gripper_offset' : 0.01}

# Set up grasp approach offsets
PHI_OFFSETS = []
if MAX_GRASP_APPROACH_OFFSET == MIN_GRASP_APPROACH_OFFSET:
    phi_inc = 1
elif NUM_GRASP_APPROACH_SAMPLES == 1:
    phi_inc = MAX_GRASP_APPROACH_OFFSET - MIN_GRASP_APPROACH_OFFSET + 1
else:
    phi_inc = (MAX_GRASP_APPROACH_OFFSET - MIN_GRASP_APPROACH_OFFSET) / (NUM_GRASP_APPROACH_SAMPLES - 1)
phi = MIN_GRASP_APPROACH_OFFSET
while phi <= MAX_GRASP_APPROACH_OFFSET:
    PHI_OFFSETS.append(phi)
    phi += phi_inc

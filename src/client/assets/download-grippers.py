import requests
import argparse
import json
import os
import glob
import time
import sys
import shutil


BASE_URL = 'http://automation.berkeley.edu/dex-net-api/'
if __name__ == "__main__":
    min_w  = 0.01
    max_w  = 0.105
    step_w = 0.005
    gripper_params = {'fingertip_x' : 0.01,
                      'fingertip_y' : 0.01,
                      'palm_depth' : 0.05,
                      'width' : 0,
                      'gripper_offset' : 0.01}
    
    os.mkdir('grippers')
    w = min_w
    while w < max_w:
        gripper_params['width'] = w
        files = {'gripper' : json.dumps(gripper_params)}
        r = requests.post(BASE_URL + 'gripper-mesh', files=files)
        with open('grippers/gripper_{}'.format(w * 100).replace('.', '_') + '.obj', 'w') as f:
            f.write(r.content)
        print(w)
        w += step_w

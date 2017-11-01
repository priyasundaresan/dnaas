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
    names = {}
    dones = {}
    for filepath in glob.glob('mini_dexnet/*.obj'):
        name, _ = os.path.splitext(os.path.basename(filepath))
        
        files = {'file' : open(filepath, 'rb'), 'gripper' : json.dumps({'width' : 0.05})}
        r = requests.post(BASE_URL + 'upload-mesh', files=files)
        print(name + ' requested')
        print(r.text)
        sys.stdout.flush()
        
        names[name] = r.json()['id']
        dones[name] = False
    
    tick = 0
    while not all(dones.values()):
        for name in names.keys():
            r = requests.get(BASE_URL + names[name] + '/processing-progress')
            if not dones[name] and r.json()['state'] != 'done':
                if r.json()['state'] == 'error':
                    print('Retrying {}'.format(name))
                    files = {'file' : open('mini_dexnet/{}.obj'.format(name), 'rb'), 'gripper' : json.dumps({'width' : 0.06})}
                    r = requests.post(BASE_URL + 'upload-mesh', files=files)
                    print(name + ' requested')
                    print(r.text)
                    sys.stdout.flush()
                    names[name] = r.json()['id']
                    dones[name] = False
                print(name.ljust(18) + ': ' + str(r.json()))
            else:
                print(name.ljust(18) + ' done')
                if not dones[name]:
                    print('first time {} is done, writing...'.format(name))
                    
                    base_url_obj = BASE_URL + names[name]
                    
                    shutil.rmtree('./' + name, ignore_errors=True)
                    os.mkdir('./' + name)
                    
                    r = requests.get(base_url_obj)
                    with open('./{0}/{0}.obj'.format(name), 'wb') as f:
                        f.write(r.content)
                    r = requests.get(base_url_obj + '/grasps')
                    with open('./{0}/grasps'.format(name), 'wb') as f:
                        f.write(r.content)

                    os.mkdir('./' + name + '/stable-poses')

                    r = requests.get(base_url_obj + '/stable-poses')
                    num_stable_poses = len(json.loads(r.content.decode('utf-8')))
                    with open('./{0}/stable-poses/index.html'.format(name), 'wb') as f:
                        f.write(r.content)


                    for i in range(0, num_stable_poses):
                        os.mkdir('./{0}/stable-poses/{1}'.format(name, i))
                        r = requests.get(base_url_obj + '/stable-poses/{0}/filtered-grasps'.format(i))
                        with open('./{0}/stable-poses/{1}/filtered-grasps'.format(name, i), 'wb') as f:
                            f.write(r.content)
                        r = requests.get(base_url_obj + '/stable-poses/{}/transform'.format(i))
                        with open('./{0}/stable-poses/{1}/transform'.format(name, i), 'wb') as f:
                            f.write(r.content)
                    print(name + ' written')
                    sys.stdout.flush()
                dones[name] = True
        sys.stdout.flush()
        time.sleep(1)
        print('\ntick' + str(tick))
        tick += 1

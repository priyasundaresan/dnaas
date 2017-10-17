'''
CLI example using DNaaS to compute grasps on mesh files
Author: Bill DeRose
'''
import json
import time
import optparse
import requests

API_URL = "http://automation.berkeley.edu/dex-net-api/"
UPLOAD_MESH_ENDPOINT = "upload-mesh"
PROGRESS_ENDPOINT = "{0}/processing-progress"
GRASPS_ENDPOINT = "/grasps"
FILTERED_STABLE_POSES_ENDPOINT = "filtered-grasps-exp"
MESH_FILE = "/your/path/to/mesh/file"
RESCALED_MESH_FILE = "mesh_rescaled.obj"
GRIPPER = {
    "fingertip_x" : 0.01,
    "fingertip_y" : 0.01,
    "palm_depth" : 0.2,
    "width" : 0.07
}

if __name__ == "__main__":
    opt_parser = optparse.OptionParser()
    opt_parser.add_option('--mesh_file', '-m',
                          default=MESH_FILE,
                          help="Mesh file location on disk")
    options, arguments = opt_parser.parse_args()
    print 'Computing grasps on object located at: %s' % options.mesh_file

    with open(options.mesh_file, "rb") as mesh:
        upload_response = requests.post("{0}{1}".format(API_URL, UPLOAD_MESH_ENDPOINT),
                                        files={
                                            'gripper': json.dumps(GRIPPER),
                                            'file': mesh,
                                        })
        upload_response = json.loads(upload_response.content)
        mesh_id = upload_response['id']
        print upload_response

        done_processing = False
        mesh_progress_endpoint = PROGRESS_ENDPOINT.format(mesh_id)
        while not done_processing:
            progress_report = requests.get("{0}{1}".format(API_URL, mesh_progress_endpoint))
            processing_state = json.loads(progress_report.content)['state']
            done_processing = processing_state == "done"
            print progress_report.content
            time.sleep(5)

        grasps_response = requests.get("{0}{1}{2}".format(API_URL, mesh_id, GRASPS_ENDPOINT))
        print json.loads(grasps_response.content)
        rescaled_mesh_response = requests.get("{0}{1}".format(API_URL, mesh_id))
        print rescaled_mesh_response.content
        with open(RESCALED_MESH_FILE, 'w+') as rescaled_mesh:
            rescaled_mesh.write(rescaled_mesh_response.content) # write rescaled mesh to disk
        stable_poses_response = requests.get("{0}{1}/stable-poses".format(API_URL, mesh_id))
        print stable_poses_response.content
        stable_pose_grasps_response = requests.get("{0}{1}/stable-poses/0/{2}".format(API_URL, mesh_id, FILTERED_STABLE_POSES_ENDPOINT))
        print stable_pose_grasps_response.content

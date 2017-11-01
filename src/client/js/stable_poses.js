var STABLE = {
    active: false,
    base_url: null,
    current_pose: 0,
    ground_plane: new THREE.Mesh(
        new THREE.PlaneGeometry(0.12, 0.12),
        new THREE.MeshBasicMaterial({
            color: 0x184da3, 
            side : THREE.DoubleSide,
        })
    ),
    num_poses: 0,
};

// Assumes you've already called addModelFile and there's a loaded mesh
STABLE.showStablePose = function(grasps_url, transform_url) {
    return $.ajax({
        url: transform_url,
        dataType: "json",
        timeout: 2000,
    }).then(function(data) {
        GLOBAL.render = false;
        return Promise.all([
            MESH.addModelFile(MESH.mesh_main_file, data['translation'], data['quaternion']),
            AXES.loadGraspAxes(grasps_url, data['translation'], data['quaternion']),
        ]);
    }).then(function() {
        STABLE.clearGroundPlane();
        STABLE.setGroundPlane();
        GLOBAL.camera.reset();
        GLOBAL.camera.lockRotation(true);
        GLOBAL.render = true;
        $( "#stable-pose-id" ).val((STABLE.current_pose + 1) + " / " + STABLE.num_poses);
    }).catch(function(...args) {
        console.error(...args);
        throw new Error(...args);
    });
}

STABLE.clearGroundPlane = function() {
    GLOBAL.world.remove(STABLE.ground_plane)
}

STABLE.setGroundPlane = function() {
    STABLE.clearGroundPlane();
    var dim = GLOBAL.world.extent * 2.1;
    var geom = new THREE.PlaneGeometry(dim, dim);
    
    STABLE.ground_plane = new THREE.Mesh( geom, new THREE.MeshBasicMaterial({color: 0x184da3, side : THREE.DoubleSide}) );
    GLOBAL.world.add(STABLE.ground_plane)
}

STABLE.increment_pose = function() {
    if (!STABLE.active) {
        return;
    }
    if (STABLE.current_pose === STABLE.num_poses - 1) {
        STABLE.current_pose = STABLE.num_poses - 1;
    } else {
        STABLE.current_pose += 1
        $('#stable-pose-nav-button-left').attr('disabled', false);
        if (STABLE.current_pose === STABLE.num_poses - 1) {
            $('#stable-pose-nav-button-right').attr('disabled', true);
        }   
        STABLE.showStablePose(
            STABLE.base_url + "/stable-poses/" + String(STABLE.current_pose) + "/filtered-grasps",
            STABLE.base_url + "/stable-poses/" + String(STABLE.current_pose) + "/transform"
        ).catch(err => console.error(err));
    }
}

STABLE.decrement_pose = function() {
    if (!STABLE.active) {
        return;
    }
    if (STABLE.current_pose === 0) {
        STABLE.current_pose = 0
    } else {
        STABLE.current_pose -= 1
        $('#stable-pose-nav-button-right').attr('disabled', false);
        if (STABLE.current_pose <= 0){
            $('#stable-pose-nav-button-left').attr('disabled', true);
        }
        STABLE.showStablePose(
            STABLE.base_url + "/stable-poses/" + String(STABLE.current_pose) + "/filtered-grasps",
            STABLE.base_url + "/stable-poses/" + String(STABLE.current_pose) + "/transform")
        .catch(err => console.error(err));
    }
}

STABLE.initialize = function() {
    STABLE.current_pose = 0;
    return $.ajax({
        url: STABLE.base_url + "/stable-poses",
        dataType: "json",
        timeout: 2000
    })
    .then(function(stable_poses) {
        STABLE.num_poses = Object.keys(stable_poses).length;
        if (STABLE.num_poses != 0) {            
            GLOBAL.camera.lockRotation(true);
            return STABLE.showStablePose(
                STABLE.base_url + "/stable-poses/0/filtered-grasps",
                STABLE.base_url + "/stable-poses/0/transform"
            );
        } else {
            $( "#stable-pose-id" ).val("N/A");
        }
    })
    .then(function() {
        STABLE.active = true;
        if (STABLE.num_poses != 0){
            // Remove only right disable because we're starting at stable pose 0
            $('#stable-pose-nav-button-right')
                .attr('disabled', false);
        }
    })
    .catch(function(...args) {
        console.error('Unable to initialize stable pose', ...args);
        throw new Error(...args);
    });
}

STABLE.clear = function() {
    STABLE.clearGroundPlane();
    GLOBAL.camera.lockRotation(false);
    STABLE.active = false;
    $('#stable-pose-nav-button-right, #stable-pose-nav-button-left')
        .attr('disabled', true);
    $("#stable-pose-button")
        .prop('checked', false);
    $('#stable-pose-id')
        .val(null);
}

STABLE.disengage = function() {
    STABLE.clear();
    if (MODE.mode === "grasp") {
        GLOBAL.render = false;
        Promise.all([
            MESH.addModelFile(MESH.mesh_main_file),
            AXES.loadGraspAxes(STABLE.base_url + "/grasps")
        ]).then(() => {
                GLOBAL.render = true;
            });

    }
}

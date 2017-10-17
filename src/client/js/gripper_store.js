var GRIPPER = {
    params : {
        fingertip_x : 0.01,
        fingertip_y : 0.01,
        palm_depth : 0.05,
        width : 0.05,
        gripper_offset : 0.01
    },
    model : undefined,
    material_main : new THREE.MeshLambertMaterial({color : 0x505050}),
    render_gripper : true
};
GRIPPER.material_main.side = THREE.DoubleSide;
GRIPPER.update = function() {
    if (GRIPPER.render_gripper) {
        return new Promise(function(resolve, reject) {
            var xhr = new XMLHttpRequest();
            xhr.onload = function() {
                if (xhr.status === 200) {
                    mesh_file = new File([xhr.response], MESH.id + ".obj");
                    var reader = new FileReader();
                    reader.onloadend = function(event){
                        var objectLoader = new THREE.OBJLoader();
                        objectLoader.load(event.target.result, function (object) {
                            object.traverse( function (child) {
                                if (child instanceof THREE.Mesh) {
                                    child.material = GRIPPER.material_main
                                }
                            });
                            object.name = "gripper"
                            GRIPPER.purge();                            
                            GLOBAL.world.position.x = 0
                            GLOBAL.world.position.y = 0
                            GLOBAL.world.position.z = 0
                            GLOBAL.world.scale.set(1, 1, 1)
                            world_bbox = new THREE.Box3().setFromObject(GLOBAL.world)
                            deltaz = world_bbox.max.z + GRIPPER.params.palm_depth + GRIPPER.params.gripper_offset
                            GLOBAL.world.add(object);
                            GRIPPER.model = object;
                            object.position.z += deltaz
                            object.applyQuaternion(new THREE.Quaternion(1, 0, 0, 0));
                        });
                        resolve();
                    }
                    reader.onerror = function() {
                        reject(Error("Mesh is invalid"));
                    };
                    reader.readAsDataURL(mesh_file);
                } else {
                    reject(Error(xhr));
                }
            };
            xhr.onerror = function(...args) {
                reject(Error("Network Error: " + args.toString()));
            };
            var formData = new FormData();
            formData.set("gripper", JSON.stringify(GRIPPER.params));
            xhr.open('POST', 'http://automation.berkeley.edu/dex-net-api/gripper-mesh', true);
            xhr.responseType = 'blob';
            xhr.send(formData);
        });
    } else {
        GLOBAL.world.remove(GRIPPER.model)
        return new Promise((resolve, reject) => {resolve();});
    }
}

GRIPPER.set_render = function(render) {
    GRIPPER.render_gripper = render
    GRIPPER.update()
}

GRIPPER.purge = function() {
    to_remove = GLOBAL.world.getObjectByName("gripper")
    while (to_remove != undefined){
        GLOBAL.world.remove(to_remove);
        to_remove = GLOBAL.world.getObjectByName("gripper");
    }
}
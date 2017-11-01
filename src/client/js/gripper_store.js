var GRIPPER = {
    params : {
        fingertip_x : 0.01,
        fingertip_y : 0.01,
        palm_depth : 0.05,
        width : 0.06,
        gripper_offset : 0.01
    },
    model : undefined,
    material_main : new THREE.MeshLambertMaterial({color : 0x505050}),
    render_gripper : true,
    offset : 0
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
                            object.applyQuaternion(new THREE.Quaternion(1, 0, 0, 0));
                            gbb = new THREE.Box3().setFromObject(object)
                            GRIPPER.offset = -gbb.getCenter().z + gbb.getSize().z / 2.0
                            object.scale.copy(GLOBAL.world.scale)
                            GLOBAL.scene.add(object);
                            GRIPPER.model = object;
                            if (STABLE.active){
                                world_bbox = new THREE.Box3().setFromObject(GLOBAL.world)
                                deltaz = world_bbox.max.z + (GRIPPER.offset + 0.01) * GLOBAL.world.scale.x
                                object.position.set(0, 0, deltaz)
                            } else{
                                object.position.copy(GLOBAL.camera.up.normalize().multiplyScalar((GLOBAL.world.extent + GRIPPER.offset) * GLOBAL.world.scale.x))
                            }
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
        GLOBAL.scene.remove(GRIPPER.model)
        return new Promise((resolve, reject) => {resolve();});
    }
}

GRIPPER.set_render = function(render) {
    GRIPPER.render_gripper = render
    GRIPPER.update()
}

GRIPPER.purge = function() {
    to_remove = GLOBAL.scene.getObjectByName("gripper")
    while (to_remove != undefined){
        GLOBAL.scene.remove(to_remove);
        to_remove = GLOBAL.scene.getObjectByName("gripper");
    }
}
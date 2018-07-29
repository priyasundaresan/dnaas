var MESH = {
    material_main: new THREE.MeshLambertMaterial({color : 0xa0a0a0}),
    mesh_main: null,
    mesh_main_file: undefined,
    id: undefined,
    autoscale: true,
    face_count_limit: 50000
};
MESH.material_main.side = THREE.DoubleSide;
MESH.addModelUrl = function(url, trans=null, rot=null) {
    return new Promise(function(resolve, reject) {
        var xhr = new XMLHttpRequest();
        xhr.open('GET', url, true);
        xhr.responseType = 'blob';
        xhr.onload = function() {
            if (xhr.status !== 200) {
                reject(Error(xhr))
            }
            MESH.mesh_main_file = new File([xhr.response], MESH.id + ".obj");
            resolve(MESH.addModelFile(MESH.mesh_main_file, trans, rot));
        };
        xhr.onerror = function(...args) {
            reject(Error("Network Error: " + args.toString()));
        };
        xhr.send();
    });
}

MESH.addModelFile = function(file, trans=null, rot=null) {
    return new Promise(function(resolve, reject) {
        var reader = new FileReader();
        reader.onloadend = function(event){
            var objLoader = new THREE.OBJLoader();
            objLoader.onerror = function() {
                reject(Error("Mesh is invalid"));
            };
            objLoader.load(event.target.result, function (object) {
                object.traverse( function (child) {
                    if (child instanceof THREE.Mesh) {
                        child.material = MESH.material_main;
                    }
                });
                MESH.clear();
                GLOBAL.world.add(object);
                MESH.mesh_main = object;
                if (trans !== null) {
                    object.position.x += trans[0];
                    object.position.y += trans[1];
                    object.position.z += trans[2];
                }
                if (rot !== null) {
                    // We give quaternions in wxyz but THREE wants xyzw
                    object.applyQuaternion(new THREE.Quaternion(rot[1], rot[2], rot[3], rot[0]));
                }
                GLOBAL.camera.reset();
                $('#wireframe-switch, #autoscale-switch') // only enable wireframe when mesh is loaded.
                    .attr('disabled', false);
                GRIPPER.update(); // Update gripper so that it doesn't collide
                resolve();
            });
            objLoader.onerror = function(){
                reject(Error("Mesh is invalid"));
            };
        };
        reader.onerror = function() {
            reject(Error("Mesh is invalid"));
        };
        reader.readAsDataURL(file);
        MESH.mesh_main_file = file;
    });
}

MESH.download_mesh = function() {
    // From js/third_party/download.js
    download(MESH.mesh_main_file, 'mesh_scaled.obj', 'application/octet-stream');
}

MESH.set_wireframe = function(value){
    MESH.material_main.wireframe = value;
}

MESH.set_autoscale = function(value){
    MESH.autoscale = value;
}

MESH.clear = function() {
    $('#wireframe-switch, #autoscale-switch') // disable mesh and stable pose when no mesh is loaded
        .attr('disabled', true);
    GLOBAL.world.remove(MESH.mesh_main);
}

MESH.fvcount = function() {
    facecount = 0;
    vertexcount = 0;
    MESH.mesh_main.traverse( function (child) {
        if (child instanceof THREE.Mesh) {
            geometry = new THREE.Geometry();
            geometry.fromBufferGeometry(child.geometry);
            facecount += geometry.faces.length;
            vertexcount += geometry.vertices.length;
        }
    });
    return [facecount, vertexcount];
}

MESH.validate = function() {
    var fv = MESH.fvcount();
    var under_face_limit = fv[0] <= MESH.face_count_limit;
    return under_face_limit;
}

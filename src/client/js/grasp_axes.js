var AXES = {
    grasp_axes_json: undefined,
    grasp_axes: undefined,
    num_grasps: undefined,
    num_grasps_rendered: null,
    slider: undefined,
    trans: undefined,
    rot: undefined,
    min_displayed: 0,
    max_displayed: Infinity,
    relative_colors: false,
    grasp_axes_thickness : 0.001
};

AXES.loadGraspAxes = function (url, trans=null, rot=null) {
    return $.ajax({
            url: url,
            dataType: "json",
            timeout: 2000,
        }).then(function(data) {
            AXES.trans = trans;
            AXES.rot = rot;
            data_processed = []
            for (i = 0; i < data.length; i++){ // quick fix for -1 (in collision) grasps breaking things
                if (data[i]['metric_score'] != -1){
                    data_processed.push(data[i])
                }
            }
            if (data_processed.length === 0) {
                $('#infoMessage').show();
            }
            AXES.grasp_axes_json = data_processed
            AXES.grasp_axes_json.sort(function(a, b) {
                return a.metric_score - b.metric_score;
            });
            return AXES.set_slider(AXES.relative_colors);
        }).catch(function(...args) {
            console.error("Unable to load grasp axes", ...args);
            throw new Error(...args);
        });
}

AXES.addGraspAxes = function(min_metric, max_metric, trans=null, rot=null) {
    GLOBAL.world.remove(AXES.grasp_axes);
    AXES.trans = trans;
    AXES.rot = rot;
    AXES.min_displayed = min_metric;
    AXES.max_displayed = max_metric;
    AXES.grasp_axes = new THREE.Object3D();
    if(AXES.grasp_axes_json.length != 0) {
        var lower_idx = 0;
        var upper_idx = AXES.grasp_axes_json.length - 1;
        if (AXES.grasp_axes_json[upper_idx]['metric_score'] < min_metric || AXES.grasp_axes_json[lower_idx]['metric_score'] > max_metric) {
            upper_idx = 0; // Given that we normalize to the grasps this should never actually happen, but might as well check to make sure.
        } else {
            for (; AXES.grasp_axes_json[lower_idx]['metric_score'] < min_metric; lower_idx++){}
            for (; AXES.grasp_axes_json[upper_idx]['metric_score'] > max_metric; upper_idx--){}

            var low_color, high_color;
            if (AXES.relative_colors) {
                low_color = AXES.grasp_axes_json[lower_idx]['metric_score']
                high_color = AXES.grasp_axes_json[upper_idx]['metric_score']
            } else {
                low_color = AXES.grasp_axes_json[0]['metric_score']
                high_color = AXES.grasp_axes_json[AXES.grasp_axes_json.length - 1]['metric_score']
            }
            var getHexColor = function(score){
                if (low_color === high_color){
                    return new THREE.Color(0, 1, 0)
                }
                score = (score - low_color) / (high_color - low_color)
                if (score < 0.5) {
                    return new THREE.Color(1, score * 2, 0)
                } else {
                    return new THREE.Color(1 - (score - 0.5) * 2, 1, 0)
                }
            }

            for (var i = lower_idx; i <= upper_idx; i++){
                axis = AXES.getGraspAxis(AXES.grasp_axes_json[i]['center'],
                                        AXES.grasp_axes_json[i]['axis'],
                                        AXES.grasp_axes_json[i]['open_width'],
                                        getHexColor(AXES.grasp_axes_json[i]['metric_score']));
                AXES.grasp_axes.add(axis);
            }   
        }
    }
    GLOBAL.world.add(AXES.grasp_axes);
    if (AXES.grasp_axes_json.length != 0) {
        AXES.num_grasps_rendered = upper_idx - lower_idx + 1
        $( "#rendered-count" ).val( AXES.num_grasps_rendered + " grasps rendered" );
    } else {
        $( "#rendered-count" ).val( "No grasps available" );
    }
    if (trans !== null) {
        AXES.grasp_axes.position.x += trans[0]
        AXES.grasp_axes.position.y += trans[1]
        AXES.grasp_axes.position.z += trans[2]
    }
    if (rot !== null) {
        // We give quaternions in wxyz but THREE wants xyzw
        AXES.grasp_axes.applyQuaternion( new THREE.Quaternion(rot[1], rot[2], rot[3], rot[0]))
    }
}

AXES.set_slider = function(relative) {
    AXES.relative_colors = relative;
    AXES.slider.slider({
        values: [ 10, 100 ],
        stop: function(event, ui) {
            if (AXES.grasp_axes_json.length != 0){
                min = AXES.grasp_axes_json[0]['metric_score'];
                max = AXES.grasp_axes_json[AXES.grasp_axes_json.length - 1]['metric_score'];
                slider_left = $( "#slider-range" ).slider( "values", 0 )
                slider_right = $( "#slider-range" ).slider( "values", 1 )
                min_metric = min + slider_left * (max - min) / 100
                max_metric = min + slider_right * (max - min) / 100
                AXES.addGraspAxes(min_metric , max_metric, AXES.trans, AXES.rot);
            }
        }
    });
    if (AXES.grasp_axes_json.length != 0){
        min = AXES.grasp_axes_json[0]['metric_score'];
        max = AXES.grasp_axes_json[AXES.grasp_axes_json.length - 1]['metric_score'];
        slider_left = $( "#slider-range" ).slider( "values", 0 )
        slider_right = $( "#slider-range" ).slider( "values", 1 )
        min_metric = min + slider_left * (max - min) / 100
        max_metric = min + slider_right * (max - min) / 100
        return AXES.addGraspAxes(min_metric , max_metric, AXES.trans, AXES.rot);
    } else {
        AXES.addGraspAxes(0, 0, AXES.trans, AXES.rot);
    }
}

AXES.download_grasps = function(){
    download(JSON.stringify(AXES.grasp_axes_json, null, 4), 'grasps.json', 'application/octet-stream')
}

AXES.clear = function(){
    GLOBAL.world.remove(AXES.grasp_axes);
}

AXES.getGraspAxis = function(center, axis, width, color) {
    center = new THREE.Vector3().fromArray(center)
    axis = new THREE.Vector3().fromArray(axis)
    var axis_scaled = axis.clone().multiplyScalar(width / 2.0)
    ep1 = center.clone().sub(axis_scaled)
    ep2 = center.clone().add(axis_scaled)

    material = new THREE.MeshLambertMaterial({color : color})
    material.side = THREE.DoubleSide

    var radiusSegments = 16
    var radius = AXES.grasp_axes_thickness
    var capsule = new THREE.Object3D();
    var cylinderGeom = new THREE.CylinderGeometry (radius, radius, width, radiusSegments, 1, true); // open-ended
    var cylinderMesh = new THREE.Mesh (cylinderGeom, material);

    // pass in the cylinder itself, its desired axis, and the place to move the center.
    AXES.makeLengthAngleAxisTransform (cylinderMesh, axis, center);
    capsule.add (cylinderMesh);

    // instance geometry
    var hemisphGeom = new THREE.SphereGeometry (radius, radiusSegments, radiusSegments/2, 0, 2*Math.PI, 0, Math.PI/2);

    // make a cap instance of hemisphGeom around 'center', looking into some 'direction'
    var makeHemiCapMesh = function (direction, center)
    {
        var cap = new THREE.Mesh (hemisphGeom, material);
        AXES.makeLengthAngleAxisTransform(cap, direction, center);
        return cap;
    };
    capsule.add(makeHemiCapMesh (axis, ep2));

    // reverse the axis so that the hemiCaps would look the other way
    axis.negate();

    capsule.add (makeHemiCapMesh (axis, ep1));

    return capsule;
}

// Transform object to align with given axis and then move to center
AXES.makeLengthAngleAxisTransform = function(obj, align_axis, center) {
    obj.matrixAutoUpdate = false;

    // From left to right using frames: translate, then rotate; TR.
    // So translate is first.
    obj.matrix.makeTranslation(center.x, center.y, center.z);

    // take cross product of axis and up vector to get axis of rotation
    var yAxis = new THREE.Vector3 (0, 1, 0);

    // Needed later for dot product, just do it now;
    var axis = new THREE.Vector3();
    axis.copy(align_axis);
    axis.normalize();

    var rotationAxis = new THREE.Vector3();
    rotationAxis.crossVectors(axis, yAxis);
    if  (rotationAxis.length() < 0.000001) {
        // Special case: if rotationAxis is just about zero, set to X axis,
        // so that the angle can be given as 0 or PI. AXES works ONLY
        // because we know one of the two axes is +Y.
        rotationAxis.set (1, 0, 0);
    }
    rotationAxis.normalize();

    // take dot product of axis and up vector to get cosine of angle of rotation
    var theta = -Math.acos(axis.dot (yAxis));
    var rotMatrix = new THREE.Matrix4();
    rotMatrix.makeRotationAxis(rotationAxis, theta);
    obj.matrix.multiply(rotMatrix);
}

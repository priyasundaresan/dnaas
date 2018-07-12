var REMOTE = {
    updateDelay : 3
}

/* Upload current model to server */
REMOTE.uploadMesh = function() {
    $("#stable-pose-button").prop('checked', false).change();
    MODE.enter_pbar_mode();
    REMOTE.set_pbar(0, "Working...", 0)
    $('.progress-estimated-wait').hide();
    var reader = new FileReader();
    var xhr = new XMLHttpRequest();
    this.xhr = xhr;
    var self = this;
    this.xhr.upload.addEventListener("progress", function(e) {
        if (e.lengthComputable) {
            var percentage = Math.round((e.loaded * 100) / e.total);
            REMOTE.set_pbar(2.5 * percentage / 100, "Uploading file")
        }
    }, false);
    xhr.upload.addEventListener("load", function(e){
        REMOTE.set_pbar(10, "Uploading file")
    }, false);
    xhr.onload = function() {
        var response = JSON.parse(xhr.responseText)
        MESH.id = response["id"];
        REMOTE.followProgress();
    }
    var formData = new FormData();
    formData.set("file", MESH.mesh_main_file);
    formData.set("params", JSON.stringify({
        "metric" : "robust_ferrari_canny",
        "config" : {},
        "gripper" : GRIPPER.params,
        "rescale_mesh" : MESH.autoscale
    }));
    xhr.open("POST", "http://automation.berkeley.edu/dex-net-api/upload-mesh");
    xhr.setRequestHeader('Accept', 'application/json');
    xhr.setRequestHeader('Content-Type', 'application/json');
    xhr.send(formData);
}

/* Update progress bar as things get finished */
REMOTE.followProgress = function(success, fail) {
    var url_base = "http://automation.berkeley.edu/dex-net-api/" + MESH.id
    var url = url_base + "/processing-progress"
    $.getJSON(url, function(data) {
        if (data['state'] === 'in queue'){
            $('.progress-estimated-wait').hide();
            var position = data['position']
            REMOTE.set_pbar(2.5 + 17.5 / Math.sqrt(position + 2), "Waiting in queue (position " + position + ")", 120)
        } else {
            $('.progress-estimated-wait').show();
        }
        
        if (data['state'] === 'preprocessing') {
            REMOTE.set_pbar(20, "Preprocessing mesh")
        } else if (data['state'] === 'sampling grasps') {
            REMOTE.set_pbar(25, "Sampling grasps")
        } else if (data['state'] === 'collision checking') {
            REMOTE.set_pbar(35 + 10 * data['percent done'], "Computing grasp reachability")
        } else if (data['state'] === 'collision checking for stable poses') {
            REMOTE.set_pbar(45 + 15 * data['percent done'], "Filtering grasps by stable pose")
        } else if (data['state'] === 'computing metrics') {
            REMOTE.set_pbar(60 + 40 * data['percent done'], "Performing perturbation analysis")
        }
        
        if (data['state'] === 'done') {
            REMOTE.set_pbar(100, "Done!", 0)
            GLOBAL.render = false;
            Promise.all([MESH.addModelUrl(url_base), AXES.loadGraspAxes(url_base + "/grasps")])
                .then(() => {
                    STABLE.base_url = url_base
                    GLOBAL.render = true;
                    MODE.enter_grasp_mode();
                    REMOTE.set_pbar(0, "Working...", 0)
                    $('.progress-estimated-wait').hide();
                    if (MESH.autoscale) {
                        $('#autoscale-switch').attr('disabled', true);
                    }
                })
                .catch((e) => {
                    console.error(e);
                    MODE.enter_upload_mode();
                });
        } else if (data['state'] === 'error') {
            MODE.enter_upload_mode();
            REMOTE.set_pbar(0, "Working...", 0)
            $('.progress-estimated-wait').hide();
            $.ajax({
                url : url_base + "/error",
                success : function(result){
                    if (result == "MemoryError"){
                        ERROR.showDialog("You got a MemoryError, either the server is overloaded or your mesh contains too many triangluar faces. " +
                        "Try reducing the complexity of your mesh by reducing the number of triangular faces and uploading the simplified .obj file to DNaaS.")
                    }
                }
            });
        } else {
            setTimeout(REMOTE.followProgress, REMOTE.updateDelay * 1000); // recursively call function again
        }
    })
}

REMOTE.set_pbar = function(percent, text="Working...", wait){
    if (wait == undefined){
        wait = REMOTE.updateDelay * 10
    }
    
    $("#progress-bar").css({
        "width": percent.toString() + "%",
        "transition-duration": wait + "s",
        "transition-timing-function": "cubic-bezier(0.3, 1, .17, .87)",
    });
    $("#progress-text").html(text);
}

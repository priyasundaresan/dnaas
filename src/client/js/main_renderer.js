if (!Detector.webgl) {
    Detector.addGetWebGLMessage();
}
var GLOBAL = {
    camera: null,
    scene: null,
    world: null,
    render: true,
};
var controls, renderer, wireframe, ambient, keyLight, fillLight, wasPageCleanedUp = false;

init();
animate();

function init() {
    var container = $('#canvas-container');
    /* Camera */
    GLOBAL.camera = new THREE.PerspectiveCamera(20, container.innerWidth() / container.innerHeight(), 1, 1000);
    GLOBAL.camera.setViewOffset ( container.innerWidth(),
                                  container.innerHeight(),
                                  0,
                                  container.innerHeight() * -0.12,
                                  container.innerWidth(),
                                  container.innerHeight());
    GLOBAL.camera.position.x = 0;
    GLOBAL.camera.position.z = 1;
	GLOBAL.camera.position.y = 3;
    GLOBAL.camera.up = new THREE.Vector3(0, 0, 1);
    GLOBAL.camera.reset = function(){
        GLOBAL.camera.position.x = 0;
        GLOBAL.camera.position.z = 1;
        GLOBAL.camera.position.y = 3;
        GLOBAL.camera.up = new THREE.Vector3(0, 0, 1);
        controls.forceIdle();
    }
    GLOBAL.camera.lockRotation = function(value){
        controls.fixedIdleRotation = value;
    }
    

    /* Scene */
    GLOBAL.scene = new THREE.Scene();
    wireframe = false;

    ambient = new THREE.AmbientLight(0xffffff, 0.25);
    GLOBAL.scene.add(ambient);

    keyLight = new THREE.DirectionalLight(0xffffff, 1.0);
    keyLight.position.set(-100, 0, 100);

    fillLight = new THREE.DirectionalLight(0xffffff, 0.75);
    fillLight.position.set(100, 0, 100);

    GLOBAL.camera.add(keyLight);
    GLOBAL.camera.add(fillLight);

    GLOBAL.scene.add(GLOBAL.camera);

    GLOBAL.world = new WORLD.world();
    GLOBAL.scene.add(GLOBAL.world);

    /* Renderer */
    renderer = new THREE.WebGLRenderer({ canvas: $('#canvas').get(0) });
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.setClearColor(new THREE.Color(0xffffff));
    renderer.setSize(container.innerWidth(), container.innerHeight());

    /* Controls */
    controls = new THREE.TrackballControls(GLOBAL.camera, renderer.domElement);
    controls.staticMoving = false;
    controls.rotateSpeed = 3.0;
	controls.dynamicDampingFactor = 0.2;
    controls.enableZoom = true;
	controls.minDistance = 1.5;
	controls.maxDistance = 10;
	controls.noPan = true;

    /* Events */
    window.addEventListener('resize', onWindowResize, false);

    /* Setting jquery stuff */
    {
        $("#mesh-file-field").change(function() {
            STABLE.clear();
            AXES.clear();
            MESH.addModelFile(this.files[0])
                .catch(error => console.error(error));
            MODE.enter_upload_mode();
            $("#slider-range" )
                .slider('option', 'values', [0, 100]);
            $('#metric-limits').val('0 - 100');
            $("#rendered-count").val( "(" + 0 + " grasps rendered)");

            $('#mesh-select').val('default').selectmenu("refresh");
            $(this).val(null); // null-out value of input so change event is trigger-able twice
        });

        /* Grasp slider setup */
        $( "#slider-range" ).slider({
            range: true,
            min: 0,
            max: 100,
            values: [ 0, 100 ],
            step: 0.5,
            slide: function(event, ui) {
                $("#metric-limits").val( ui.values[ 0 ] + " – " + ui.values[ 1 ] );
            }
        });
        AXES.slider = $( "#slider-range" );
        /* Grasp slider display fields */
        $( "#metric-limits" ).val( $( "#slider-range" ).slider( "values", 0 ) + " – " + $( "#slider-range" ).slider( "values", 1 ) );
        
        /* Gripper slider setup */
        $("#gripper-width-slider").slider({
            range: false,
            min: 1,
            max: 10,
            value:  parseInt(GRIPPER.params.width * 100),
            step: 0.5,
            slide: function(event, ui) {
                $("#gripper-width").val(ui.value + " cm");
                GRIPPER.params.width = ui.value / 100;
                $('#upload-confirm').attr('disabled', false);
            },
            stop: function(event, ui) {
                GRIPPER.update();
            }
        });
        $("#gripper-width").val(parseInt(GRIPPER.params.width * 100) + " cm");
        
        /* Stable pose toggle button */
        $( "#stable-pose-button" ).change(function() {
            if (this.checked) {
                STABLE.initialize()
                    .catch(err => console.error(err));
            } else {
                STABLE.disengage();
            }
        });

        /* Wireframe toggle setup */
        $("#wireframe-switch").change(function() {
            MESH.set_wireframe(event.target.checked);
        });
        
        /* Gripper render toggle setup */
        $("#gripper-switch").change(function() {
            GRIPPER.set_render(!event.target.checked)
        });

        $(window).on('beforeunload', function() {
            // this will work only for Chrome
            pageCleanup();
        });

        $(window).on("unload", function() {
            // this will work for other browsers
            pageCleanup();
        });
    }

    /* Initialize default mesh, grasps */
    Promise.all([
        MESH.addModelUrl('assets/spray/spray.obj'),
        AXES.loadGraspAxes('assets/spray/grasps')
    ]).then(() => {
            STABLE.base_url = 'assets/spray'
            MODE.enter_grasp_mode();
            GRIPPER.update();
        })
        .catch(function(error) { console.error(error); });
        
}

function onWindowResize() {
    var container = $('#canvas-container');
    GLOBAL.camera.aspect = container.innerWidth() / container.innerHeight();
    GLOBAL.camera.setViewOffset ( container.innerWidth(),
                              container.innerHeight(),
                              0,
                              container.innerHeight() * -0.12,
                              container.innerWidth(),
                              container.innerHeight() );
    GLOBAL.camera.updateProjectionMatrix();
    renderer.setSize(container.innerWidth(), container.innerHeight());
}

function animate() {
    requestAnimationFrame(animate);
    controls.update();
    render();
}

function render() {
    if (GLOBAL.render) {
        renderer.render(GLOBAL.scene, GLOBAL.camera);
    }
}

// See SO: https://stackoverflow.com/questions/4945932/window-onbeforeunload-ajax-request-in-chrome
function pageCleanup() {
    if (!wasPageCleanedUp) {
        // $.ajax({
        //     type: 'GET',
        //     async: false,
        //     url: '/kill',
        // })
        // .then(() => wasPageCleanedUp = true);
    }
}

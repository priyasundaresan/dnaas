var MODE = {}

MODE.mode = "grasp"

MODE.enter_grasp_mode = function() {
    MODE.mode = "grasp";
    $('#upload-confirm').attr('disabled', true);
    $('#stable-pose-button').attr('disabled', false);
    $('#download-mesh, #download-grasps').attr('disabled', false);
    $('.progress-container').hide();
    var $slider = $( "#slider-range" );
    $slider.slider('enable');
    $("#metric-limits")
        .val($slider.slider( "values", 0 ) + " – " + $slider.slider( "values", 1 ) );
}

MODE.enter_upload_mode = function() {
    MODE.mode = "upload"
    $('#upload-confirm').attr('disabled', false);
    $('#stable-pose-button').attr('disabled', true);
    $('#download-mesh, #download-grasps').attr('disabled', true);
    $('.progress-container').hide();
    $("#slider-range").slider('disable');
}

MODE.enter_pbar_mode = function() {
    MODE.mode = "pbar"
    $('#upload-confirm').attr('disabled', true);
    $('#stable-pose-button').attr('disabled', true);
    $('#download-mesh, #download-grasps').attr('disabled', true);
    $('.progress-container').show();
    $("#slider-range").slider('disable');
    $('#autoscale-switch').attr('disabled', true);
}
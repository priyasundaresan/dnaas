var ERROR = {
};

ERROR.showDialog = function(message){   
    var em = $('#errorMessage');
    if (MESH.id != undefined){
        em[0].lastElementChild.previousElementSibling.innerText = "Please include your mesh id " + MESH.id + " in your report. "
    } else{
        em[0].lastElementChild.previousElementSibling.innerText = ""
    }
    if (message != undefined){
        em[0].lastElementChild.innerText = message
    } else {
        em[0].lastElementChild.innerText = ""
    }
    em.show();
}


window.addEventListener('error', function(error) {
    console.log(error);
    ERROR.showDialog("Error message from " + error.filename + " ---- " + error.message);
});
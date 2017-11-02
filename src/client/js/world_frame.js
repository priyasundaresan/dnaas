/* World frame group with auto-rescaling */
var WORLD = {
    extent : 0
};

WORLD.world = function() {
    THREE.Group.call(this);
}
WORLD.world.prototype = Object.create(THREE.Group.prototype);
WORLD.world.prototype.add = function(to_add) {
    this.position.set(0, 0, 0)
    this.scale.set(1, 1, 1)
    Object.getPrototypeOf(WORLD.world.prototype).add.call(this, to_add)
    var bBox = new THREE.Box3().setFromObject(this)
    var bBoxCenter = bBox.getCenter();
    this.extent = bBox.getBoundingSphere().radius
    scale = 0.42 / this.extent;
    this.scale.set(scale, scale, scale)
    this.position.x = -bBoxCenter.x * scale;
    this.position.y = -bBoxCenter.y * scale;
    this.position.z = -bBoxCenter.z * scale;
    if (GRIPPER.model != undefined){
        GRIPPER.model.scale.copy(GLOBAL.world.scale)
    }
}
WORLD.world.prototype.remove = function(to_remove) {
    this.position.set(0, 0, 0)
    this.scale.set(1, 1, 1)
    Object.getPrototypeOf(WORLD.world.prototype).remove.call(this, to_remove)
    var bBox = new THREE.Box3().setFromObject(this)
    var bBoxCenter = bBox.getCenter();
    this.extent = bBox.getBoundingSphere().radius
    scale = 0.42 / this.extent;
    this.scale.set(scale, scale, scale)
    this.position.x = -bBoxCenter.x * scale;
    this.position.y = -bBoxCenter.y * scale;
    this.position.z = -bBoxCenter.z * scale;
    if (GRIPPER.model != undefined){
        GRIPPER.model.scale.copy(GLOBAL.world.scale)
    }
}

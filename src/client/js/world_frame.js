/* World frame group with auto-rescaling */
var WORLD = {};

WORLD.world = function() {
    THREE.Group.call(this);
    z_offset = 0;
}
WORLD.world.prototype = Object.create(THREE.Group.prototype);
WORLD.world.prototype.add = function(to_add) {
    this.position.x = 0
    this.position.y = 0
    this.position.z = 0
    this.scale.set(1, 1, 1)
    Object.getPrototypeOf(WORLD.world.prototype).add.call(this, to_add)
    var bBox = new THREE.Box3().setFromObject(this)
    var bBoxSize = bBox.getSize();
    var bBoxCenter = bBox.getCenter();
    scale = 0.42 / Math.max(bBoxSize.y, bBoxSize.x, bBoxSize.z);
    this.scale.set(scale, scale, scale)
    this.position.x = -bBoxCenter.x * scale;
    this.position.y = -bBoxCenter.y * scale;
    this.position.z = -bBoxCenter.z * scale - z_offset;
}
WORLD.world.prototype.remove = function(to_remove) {
    this.position.x = 0
    this.position.y = 0
    this.position.z = 0
    this.scale.set(1, 1, 1)
    Object.getPrototypeOf(WORLD.world.prototype).remove.call(this, to_remove)
    var bBox = new THREE.Box3().setFromObject(this)
    var bBoxSize = bBox.getSize();
    var bBoxCenter = bBox.getCenter();
    scale = 0.36 / Math.max(bBoxSize.y, bBoxSize.x, bBoxSize.z);
    this.scale.set(scale, scale, scale)
    this.position.x = -bBoxCenter.x * scale;
    this.position.y = -bBoxCenter.y * scale;
    this.position.z = -bBoxCenter.z * scale - z_offset;
}
WORLD.world.prototype.z_offset = function(offset){
    this.z_offset = 0;
}
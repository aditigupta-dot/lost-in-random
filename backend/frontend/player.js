export function createPlayer(scene){
    const geo = new THREE.BoxGeometry();
    const mat = new THREE.MeshStandardMaterial({color: 0x00ff00});

    const cube = new THREE.Mesh(geo, mat);
    cube.position.set(0,0.5,0);

    scene.add(cube);
    return cube;
}
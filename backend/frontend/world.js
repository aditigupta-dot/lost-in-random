export function createWorld(scene){
    for(let i=0;i<10;i++){
        for(let j=0;j<10;j++){
            const geo = new THREE.BoxGeometry(1,0.1,1);
            const mat = new THREE.MeshStandardMaterial({
                color: Math.random()*0xffffff
            });

            const tile = new THREE.Mesh(geo, mat);
            tile.position.set(i,0,j);
            scene.add(tile);
        }
    }
}
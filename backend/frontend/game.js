import { createWorld } from "./world.js";
import { createPlayer } from "./player.js";
import { missions } from "./storyline.js";
import { sendPosition, listenPlayers } from "./multiplayer.js";

let scene, camera, renderer, player;
let playerId = Math.random().toString(36).substring(7);

export function initGame() {
    scene = new THREE.Scene();

    camera = new THREE.PerspectiveCamera(75, window.innerWidth/window.innerHeight, 0.1, 1000);
    camera.position.set(5,10,10);
    camera.lookAt(0,0,0);

    renderer = new THREE.WebGLRenderer({canvas: document.getElementById("gameCanvas")});
    renderer.setSize(window.innerWidth, window.innerHeight);

    const light = new THREE.DirectionalLight(0xffffff, 1);
    light.position.set(5,10,7);
    scene.add(light);

    createWorld(scene);
    player = createPlayer(scene);

    document.addEventListener("keydown", move);

    updateMission(1);

    listenPlayers(players => console.log(players));

    animate();
}

function move(e) {
    if(e.key==="w") player.position.z -=1;
    if(e.key==="s") player.position.z +=1;
    if(e.key==="a") player.position.x -=1;
    if(e.key==="d") player.position.x +=1;

    sendPosition(playerId, player.position);
}

function updateMission(level){
    const m = missions.find(x=>x.level===level);
    if(m) document.getElementById("missionBox").innerText = m.text;
}

function animate(){
    requestAnimationFrame(animate);
    renderer.render(scene, camera);
}
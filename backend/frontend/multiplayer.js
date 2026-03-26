import { io } from "https://cdn.socket.io/4.0.0/socket.io.esm.min.js";

const socket = io("http://localhost:5001");

export function sendPosition(id, pos){
    socket.emit("move", {id, pos});
}

export function listenPlayers(cb){
    socket.on("update", cb);
}
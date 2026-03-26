from flask import request, jsonify
import jwt

SECRET = "secret"
users = {}

def register():
    data = request.json
    users[data["username"]] = data["password"]
    return jsonify({"msg": "registered"})

def login():
    data = request.json
    if users.get(data["username"]) == data["password"]:
        token = jwt.encode({"user": data["username"]}, SECRET, algorithm="HS256")
        return jsonify({"token": token})
    return jsonify({"msg": "invalid"})
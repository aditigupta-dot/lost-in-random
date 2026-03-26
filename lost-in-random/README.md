# Lost in Random — Backend Setup

## Quick Start

1. Make sure MongoDB is installed and running:
   ```bash
   mongod --dbpath ./data
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Create your `.env` file:
   ```bash
   cp .env.example .env
   # Edit .env and set JWT_SECRET to something long and random
   ```

4. Start the server:
   ```bash
   npm start
   ```

5. Open `game_fixed.html` in your browser
   - On the login screen, enter your server URL: `http://localhost:5000`
   - Click **Set** to save it
   - Now register/login and all progress is saved to MongoDB!

## MongoDB Atlas (Cloud — Free)

1. Go to https://cloud.mongodb.com and create a free account
2. Create a free M0 cluster
3. Get your connection string (looks like: `mongodb+srv://user:pass@cluster.mongodb.net/lost_in_random`)
4. Set it in `.env`:
   ```
   MONGO_URI=mongodb+srv://user:pass@cluster.mongodb.net/lost_in_random
   ```

## What's Stored in MongoDB

Each user document contains:
- `username` — unique username
- `passwordHash` — bcrypt-hashed password (never plain text)
- `score` — highest score ever
- `cleared` — array of world IDs completed
- `levelCleared` — object mapping world ID → array of cleared level numbers
- `trUnlocked` / `trCompleted` — treasure hunt realm progress
- `trFound` — total diamonds found
- `createdAt` / `lastLogin` — timestamps

## Why Your Login Data Seems Gone

The game previously saved data to `localStorage` in your browser. This data is still there!
When you log in with the same username/password you used before, your progress will load from localStorage.

With the MongoDB server running, all new progress is automatically synced to the database,
so you can log in from any device/browser.

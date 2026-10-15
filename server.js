const express = require('express');
const { spawn } = require('child_process');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 10000;

app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true, limit: '10mb' }));

// Serve static files from the root directory
app.use(express.static(path.join(__dirname)));

// Explicit route to serve index.html at the root URL
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'index.html'));
});

app.post('/api/process', (req, res) => {
    console.log("[API] Hit /api/process endpoint!");
    const scriptPayload = req.body.data || req.body.script;

    if (!scriptPayload) {
        console.log("[API ERROR] No payload provided.");
        return res.status(400).json({ success: false, error: 'No script provided' });
    }

    console.log("[API] Spawning python3 core_extractor.py...");
    const pythonProcess = spawn('python3', ['core_extractor.py', scriptPayload]);

    let pythonOutput = '';
    let pythonError = '';

    pythonProcess.stdout.on('data', (data) => {
        const msg = data.toString();
        pythonOutput += msg;
        console.log(`[Python] ${msg.trim()}`);
    });

    pythonProcess.stderr.on('data', (data) => {
        const msg = data.toString();
        pythonError += msg;
        console.error(`[Python Error] ${msg.trim()}`);
    });

    pythonProcess.on('close', (code) => {
        console.log(`[API] Python process finished with code ${code}`);
        res.json({ success: true, code, output: pythonOutput, error: pythonError });
    });
});

app.listen(PORT, '0.0.0.0', () => {
    console.log(`Server running on port ${PORT}`);
});

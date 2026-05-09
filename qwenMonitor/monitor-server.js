const http = require('http');

const server = http.createServer((req, res) => {
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

    if (req.method === 'OPTIONS') { res.writeHead(204); res.end(); return; }

    if (req.method === 'POST' && req.url === '/intercept') {
        let body = '';
        req.on('data', chunk => body += chunk);
        req.on('end', () => {
            // Broadcaster via SSE à la page HTML
            clients.forEach(c => c.res.write(`data: ${body}\n\n`));
            res.writeHead(200);
            res.end('ok');
        });
        return;
    }

    if (req.method === 'GET' && req.url === '/events') {
        res.writeHead(200, {
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*'
        });
        const id = Date.now();
        clients.push({ id, res });
        req.on('close', () => {
            clients = clients.filter(c => c.id !== id);
        });
        return;
    }

    res.writeHead(404); res.end();
});

let clients = [];
server.listen(9999, () => console.log('Monitor server listening on :9999'));
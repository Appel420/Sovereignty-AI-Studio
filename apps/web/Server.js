// apps/frontend/server.js
const http = require('http');
const { spawn } = require('child_process');

const PORT = parseInt(process.env.WEB_APP_PORT || '9898', 10);

const server = http.createServer((req, res) => {
  if (req.url === '/intent') {
    const py = spawn('python3', );
    let data = '';
    py.stdout.on('data', (chunk) => data += chunk);
    py.on('close', () => {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(data);  // JSON from Python → straight to client
    });
  } else {
    res.end('Sovereignty live.');
  }
});

server.listen(PORT, () => {
  console.log(`Node frontend on ${PORT} → talks to Python sovereign core`);
});

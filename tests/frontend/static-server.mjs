import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const projectRoot = resolve(fileURLToPath(new URL('../..', import.meta.url)));
const assets = new Map([
    ['/', ['index.html', 'text/html; charset=utf-8']],
    ['/index.html', ['index.html', 'text/html; charset=utf-8']],
    ['/css/style.css', ['css/style.css', 'text/css; charset=utf-8']],
    ['/js/app.js', ['js/app.js', 'text/javascript; charset=utf-8']],
    ['/js/backend-logs.js', ['js/backend-logs.js', 'text/javascript; charset=utf-8']],
    ['/js/operations.js', ['js/operations.js', 'text/javascript; charset=utf-8']],
    ['/js/system-monitor.js', ['js/system-monitor.js', 'text/javascript; charset=utf-8']],
    ['/js/ui-preferences.js', ['js/ui-preferences.js', 'text/javascript; charset=utf-8']],
]);

const server = createServer(async (request, response) => {
    const pathname = new URL(request.url, 'http://127.0.0.1').pathname;
    const asset = assets.get(pathname);
    if (!asset) {
        response.writeHead(404).end();
        return;
    }

    try {
        const content = await readFile(resolve(projectRoot, asset[0]));
        response.writeHead(200, {
            'Content-Type': asset[1],
            'Cache-Control': 'no-store',
            'X-Content-Type-Options': 'nosniff',
        });
        response.end(content);
    } catch (error) {
        console.error(`Failed to serve ${pathname}:`, error);
        response.writeHead(500).end();
    }
});

server.listen(4173, '127.0.0.1');

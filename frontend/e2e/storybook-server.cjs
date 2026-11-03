const http = require("http");
const fs = require("fs");
const path = require("path");
const root = path.resolve(__dirname, "../storybook-static");
http
  .createServer((req, res) => {
    const pathname = new URL(req.url, "http://localhost").pathname;
    const file = path.resolve(
      root,
      "." + decodeURIComponent(pathname === "/" ? "/index.html" : pathname),
    );
    if (
      !file.startsWith(root + path.sep) ||
      !fs.existsSync(file) ||
      fs.statSync(file).isDirectory()
    ) {
      res.writeHead(404);
      res.end();
      return;
    }
    res.setHeader(
      "Content-Type",
      {
        ".html": "text/html",
        ".js": "application/javascript",
        ".json": "application/json",
        ".css": "text/css",
        ".svg": "image/svg+xml",
        ".woff2": "font/woff2",
      }[path.extname(file)] || "application/octet-stream",
    );
    fs.createReadStream(file).pipe(res);
  })
  .listen(6106, "127.0.0.1");

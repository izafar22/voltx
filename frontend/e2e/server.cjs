const http = require("http");
const fs = require("fs");
const path = require("path");
const root = path.resolve(__dirname, "../build");
http
  .createServer((req, res) => {
    const pathname = new URL(req.url, "http://localhost").pathname;
    let file = path.resolve(root, "." + decodeURIComponent(pathname));
    if (
      !file.startsWith(root + path.sep) ||
      !fs.existsSync(file) ||
      fs.statSync(file).isDirectory()
    )
      file = path.join(root, "index.html");
    const types = {
      ".html": "text/html",
      ".js": "application/javascript",
      ".css": "text/css",
      ".svg": "image/svg+xml",
      ".png": "image/png",
      ".woff2": "font/woff2",
    };
    res.setHeader(
      "Content-Type",
      types[path.extname(file)] || "application/octet-stream",
    );
    fs.createReadStream(file).pipe(res);
  })
  .listen(3100, "127.0.0.1");

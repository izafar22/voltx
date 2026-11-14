const { createProxyMiddleware } = require("http-proxy-middleware");

module.exports = function (app) {
  app.use(
    createProxyMiddleware("/api", {
      target: "http://localhost:8002",

      // Important:
      // preserve Origin: http://localhost:3000
      changeOrigin: false,

      secure: false,
      xfwd: true,
    })
  );
};
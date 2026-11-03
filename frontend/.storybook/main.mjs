import path from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
export default {
  stories: ["../src/design-system/**/*.stories.jsx"],
  framework: { name: "@storybook/react-webpack5", options: {} },
  addons: [
    "@storybook/addon-webpack5-compiler-swc",
    "@storybook/addon-docs",
    "@storybook/addon-a11y",
  ],
  core: { disableTelemetry: true },
  typescript: { reactDocgen: false },
  webpackFinal: async (config) => {
    config.resolve.alias = {
      ...config.resolve.alias,
      "@": path.join(root, "src"),
    };
    config.module.rules = config.module.rules.filter(
      (rule) => !(rule.test instanceof RegExp && rule.test.test("styles.css")),
    );
    config.module.rules.push({
      test: /\.css$/,
      use: [
        require.resolve("style-loader"),
        {
          loader: require.resolve("css-loader"),
          options: { importLoaders: 1 },
        },
        {
          loader: require.resolve("postcss-loader"),
          options: {
            postcssOptions: {
              plugins: [
                require("tailwindcss")(path.join(root, "tailwind.config.js")),
                require("autoprefixer"),
              ],
            },
          },
        },
      ],
    });
    return config;
  },
};

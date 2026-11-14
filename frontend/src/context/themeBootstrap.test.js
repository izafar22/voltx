import fs from "fs";
import path from "path";
import vm from "vm";
const script = fs.readFileSync(
  path.join(process.cwd(), "public/theme-init.js"),
  "utf8",
);
test.each([
  ["dark", false, "dark"],
  ["light", true, "light"],
  [null, true, "dark"],
  ["invalid", false, "light"],
])(
  "pre-paint theme %s / system dark %s matches ThemeContext contract",
  (stored, systemDark, expected) => {
    const root = { classList: { toggle: jest.fn() }, style: {} };
    vm.runInNewContext(script, {
      document: { documentElement: root },
      window: {
        localStorage: { getItem: () => stored },
        matchMedia: () => ({ matches: systemDark }),
      },
    });
    expect(root.classList.toggle).toHaveBeenCalledWith(
      "dark",
      expected === "dark",
    );
    expect(root.style.colorScheme).toBe(expected);
  },
);
test("pre-paint theme tolerates blocked storage", () => {
  const root = { classList: { toggle: jest.fn() }, style: {} };
  vm.runInNewContext(script, {
    document: { documentElement: root },
    window: {
      localStorage: {
        getItem: () => {
          throw Error("blocked");
        },
      },
      matchMedia: () => ({ matches: true }),
    },
  });
  expect(root.style.colorScheme).toBe("dark");
});

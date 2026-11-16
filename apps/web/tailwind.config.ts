import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        ink: "#101114",
        panel: "#181a20",
        muted: "#9296a3",
        accent: "#9b87f5"
      }
    }
  },
  plugins: []
};

export default config;

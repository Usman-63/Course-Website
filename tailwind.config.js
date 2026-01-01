/** @type {import('tailwindcss').Config} */

export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: {
        "2xl": "1400px",
      },
    },
    extend: {
      colors: {
        navy: {
          DEFAULT: "#1a2332",
          light: "#2a3546",
        },
        yellow: {
          DEFAULT: "#ffd700",
          hover: "#e6c200",
        },
      },
    },
  },
  plugins: [],
};
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        app: {
          bg: "#1C2130",
          card: "#252B3A",
          soft: "#31384A",
          cyan: "#22D3EE",
          green: "#22C55E",
          orange: "#F97316",
          red: "#EF4444"
        }
      },
      boxShadow: {
        glow: "0 0 24px rgba(34, 211, 238, 0.18)"
      }
    }
  },
  plugins: []
};

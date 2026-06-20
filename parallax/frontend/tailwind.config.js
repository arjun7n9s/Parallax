/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        // Bauhaus Brutalist Editorial palette
        bone: {
          DEFAULT: "#F4F1EA",
          50: "#FBFAF6",
          100: "#F4F1EA",
          200: "#EAE6DC",
          300: "#DAD3C2",
          400: "#B6AC92",
        },
        ink: {
          DEFAULT: "#0A0A0A",
          50: "#1A1A1A",
          100: "#121212",
          200: "#0E0E0E",
          300: "#0A0A0A",
          400: "#050505",
        },
        oxblood: {
          DEFAULT: "#7C1F2D",
          50: "#F5E7E9",
          100: "#E8C0C5",
          200: "#C9808A",
          300: "#A84754",
          400: "#7C1F2D",
          500: "#5E1620",
        },
        acid: {
          DEFAULT: "#9FE870",
          50: "#EEFAE0",
          100: "#D9F4BB",
          200: "#B9E97F",
          300: "#9FE870",
          400: "#7FCC4A",
        },
        ochre: "#C9923A",
        cobalt: "#1E3F8A",
        // For data viz
        ok: "#3F8A4A",
        warn: "#C9923A",
        danger: "#7C1F2D",
      },
      fontFamily: {
        display: ['"Instrument Serif"', "ui-serif", "Georgia", "serif"],
        sans: ['"Geist"', "system-ui", "sans-serif"],
        mono: ['"Geist Mono"', "ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
      fontSize: {
        // Editorial display scale
        "display-2xl": ["clamp(4rem, 12vw, 11rem)", { lineHeight: "0.9", letterSpacing: "-0.04em" }],
        "display-xl": ["clamp(3rem, 8vw, 7rem)", { lineHeight: "0.92", letterSpacing: "-0.03em" }],
        "display-lg": ["clamp(2.25rem, 5vw, 4.5rem)", { lineHeight: "0.95", letterSpacing: "-0.025em" }],
        "display-md": ["clamp(1.75rem, 3vw, 2.75rem)", { lineHeight: "1.05", letterSpacing: "-0.02em" }],
        "eyebrow": ["0.6875rem", { lineHeight: "1", letterSpacing: "0.18em" }],
      },
      spacing: {
        // 8px grid baseline
        0.5: "0.125rem",
        1: "0.25rem",
        1.5: "0.375rem",
        2: "0.5rem",
        2.5: "0.625rem",
        3: "0.75rem",
        4: "1rem",
        5: "1.25rem",
        6: "1.5rem",
        7: "1.75rem",
        8: "2rem",
        10: "2.5rem",
        12: "3rem",
        14: "3.5rem",
        16: "4rem",
        20: "5rem",
        24: "6rem",
        32: "8rem",
      },
      borderRadius: {
        // Editorial, not soft and friendly
        none: "0",
        sm: "2px",
        DEFAULT: "4px",
        md: "6px",
        lg: "8px",
      },
      opacity: {
        // Allow non-standard opacity values like /3, /4, /12, /85
        3: "0.03",
        4: "0.04",
        12: "0.12",
        15: "0.15",
        18: "0.18",
        22: "0.22",
        35: "0.35",
        45: "0.45",
        55: "0.55",
        65: "0.65",
        85: "0.85",
      },
      boxShadow: {
        // No soft shadows - this is brutalist
        none: "none",
        "brutal-sm": "2px 2px 0 0 rgba(10,10,10,1)",
        "brutal": "4px 4px 0 0 rgba(10,10,10,1)",
        "brutal-lg": "8px 8px 0 0 rgba(10,10,10,1)",
        "brutal-oxblood": "4px 4px 0 0 #7C1F2D",
        "brutal-acid": "4px 4px 0 0 #9FE870",
        "inset-bone": "inset 0 0 0 1px #DAD3C2",
        "inset-ink": "inset 0 0 0 1px rgba(255,255,255,0.08)",
      },
      transitionTimingFunction: {
        editorial: "cubic-bezier(0.2, 0.8, 0.2, 1)",
        brut: "cubic-bezier(0.4, 0, 0.2, 1)",
      },
      keyframes: {
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "fade-in": {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        ticker: {
          "0%": { transform: "translateX(0)" },
          "100%": { transform: "translateX(-50%)" },
        },
        "blink-dot": {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.3" },
        },
      },
      animation: {
        "fade-up": "fade-up 0.6s cubic-bezier(0.2, 0.8, 0.2, 1) both",
        "fade-in": "fade-in 0.4s ease-out both",
        ticker: "ticker 60s linear infinite",
        "blink-dot": "blink-dot 1.4s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};

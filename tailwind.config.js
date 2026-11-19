/** @type {import('tailwindcss').Config} */
module.exports = {
  // web/*.html (not web/**): web/node_modules holds the old build tools
  content: [
    "./web/*.html",
    "./web/js/**/*.js"
  ],
  theme: {
    extend: {
      colors: {
        // Follows the theme chosen in Configuration: applyThemeColors() (common.js)
        // sets --primary-accent-rgb, so primary-accent/10 etc. work in every theme.
        // [var(--primary-accent)]/10 cannot work: Tailwind 3 cannot add opacity
        // to a color it only knows as var().
        'primary-accent': 'rgb(var(--primary-accent-rgb) / <alpha-value>)',
        'bg-dark': '#05070a',
      },
      opacity: {
        // used as white/8 and white/12 (the default scale goes in steps of 5)
        '8': '0.08',
        '12': '0.12',
      },
      fontFamily: {
        'orbitron': ['Orbitron', 'sans-serif'],
        'rajdhani': ['Rajdhani', 'sans-serif'],
      }
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
  ],
}

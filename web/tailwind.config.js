/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./*.html",
    "./fonts/**/*.{html,js}"
  ],
  theme: {
    extend: {
      colors: {
        'primary-accent': '#FF6600',
        'bg-dark': '#05070a',
        'panel-bg': 'rgba(18, 20, 24, 0.9)',
      },
      fontFamily: {
        orbitron: ['Orbitron', 'sans-serif'],
        rajdhani: ['Rajdhani', 'sans-serif'],
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms')
  ],
}

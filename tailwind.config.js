/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./web/**/*.html",
    "./web/js/**/*.js"
  ],
  theme: {
    extend: {
      colors: {
        'primary-accent': '#FF6600',
        'bg-dark': '#05070a',
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

/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{html,ts}",
  ],
  theme: {
    extend: {
      colors: {
        // Surfaces
        surface: '#f7faf5',
        'surface-dim': '#d8dbd6',
        'surface-bright': '#f7faf5',
        'surface-container-lowest': '#ffffff',
        'surface-container-low': '#f1f4ef',
        'surface-container': '#ecefea',
        'surface-container-high': '#e6e9e4',
        'surface-container-highest': '#e0e3df',

        // On Surface
        'on-surface': '#191c1a',
        'on-surface-variant': '#424844',
        'inverse-surface': '#2d312e',
        'inverse-on-surface': '#eff2ed',

        // Outlines
        outline: '#737974',
        'outline-variant': '#c2c8c2',
        'surface-tint': '#4d6357',

        // Primary (Pine)
        primary: '#23382d',
        'on-primary': '#ffffff',
        'primary-container': '#394f43',
        'on-primary-container': '#a7c0b1',
        'inverse-primary': '#b4ccbd',
        'primary-fixed': '#cfe9d8',
        'primary-fixed-dim': '#b4ccbd',
        'on-primary-fixed': '#0a2016',
        'on-primary-fixed-variant': '#364b40',

        // Secondary (Sage)
        secondary: '#4d6355',
        'on-secondary': '#ffffff',
        'secondary-container': '#cde6d4',
        'on-secondary-container': '#51685a',
        'secondary-fixed': '#d0e9d7',
        'secondary-fixed-dim': '#b4ccbb',
        'on-secondary-fixed': '#0a2015',
        'on-secondary-fixed-variant': '#364c3e',

        // Tertiary (Mountain Herb)
        tertiary: '#183b25',
        'on-tertiary': '#ffffff',
        'tertiary-container': '#2f523a',
        'on-tertiary-container': '#9dc4a6',
        'tertiary-fixed': '#c4eccc',
        'tertiary-fixed-dim': '#a9d0b1',
        'on-tertiary-fixed': '#00210e',
        'on-tertiary-fixed-variant': '#2b4e37',

        // Error
        error: '#ba1a1a',
        'on-error': '#ffffff',
        'error-container': '#ffdad6',
        'on-error-container': '#93000a',

        // Background
        background: '#f7faf5',
        'on-background': '#191c1a',

        // Semaphore Colors
        favorable: '#72977b',
        vulnerable: '#d9ae65',
        'high-risk': '#c97973',
        pending: '#9a9d98',
      },
      fontFamily: {
        // Headlines & Display
        'display-lg': ['Plus Jakarta Sans'],
        'display-lg-mobile': ['Plus Jakarta Sans'],
        'headline-lg': ['Plus Jakarta Sans'],
        'headline-lg-mobile': ['Plus Jakarta Sans'],
        'headline-md': ['Plus Jakarta Sans'],
        'headline-sm': ['Plus Jakarta Sans'],

        // Body
        'body-lg': ['Inter'],
        'body-md': ['Inter'],
        'body-sm': ['Inter'],

        // Labels & Metrics
        'label-md': ['Inter'],
        'label-sm': ['Inter'],
        'metric-lg': ['Inter'],
        'metric-md': ['Inter'],
      },
      fontSize: {
        'display-lg': ['36px', {
          lineHeight: '44px',
          letterSpacing: '-0.025em',
          fontWeight: '600',
        }],
        'display-lg-mobile': ['28px', {
          lineHeight: '36px',
          letterSpacing: '-0.02em',
          fontWeight: '600',
        }],
        'headline-lg': ['28px', {
          lineHeight: '36px',
          letterSpacing: '-0.02em',
          fontWeight: '600',
        }],
        'headline-lg-mobile': ['22px', {
          lineHeight: '30px',
          letterSpacing: '-0.015em',
          fontWeight: '600',
        }],
        'headline-md': ['20px', {
          lineHeight: '28px',
          letterSpacing: '-0.015em',
          fontWeight: '600',
        }],
        'headline-sm': ['16px', {
          lineHeight: '24px',
          letterSpacing: '-0.01em',
          fontWeight: '600',
        }],
        'body-lg': ['16px', {
          lineHeight: '26px',
          letterSpacing: '-0.005em',
          fontWeight: '400',
        }],
        'body-md': ['14px', {
          lineHeight: '22px',
          fontWeight: '400',
        }],
        'body-sm': ['13px', {
          lineHeight: '18px',
          fontWeight: '400',
        }],
        'label-md': ['12px', {
          lineHeight: '16px',
          letterSpacing: '0.02em',
          fontWeight: '500',
        }],
        'label-sm': ['11px', {
          lineHeight: '14px',
          letterSpacing: '0.04em',
          fontWeight: '600',
        }],
        'metric-lg': ['30px', {
          lineHeight: '36px',
          letterSpacing: '-0.02em',
          fontWeight: '600',
        }],
        'metric-md': ['22px', {
          lineHeight: '28px',
          letterSpacing: '-0.01em',
          fontWeight: '600',
        }],
      },
      borderRadius: {
        DEFAULT: '0.25rem',
        lg: '0.5rem',
        xl: '0.75rem',
        full: '9999px',
      },
      spacing: {
        'space-xs': '0.25rem',
        'space-sm': '0.5rem',
        'space-md': '1rem',
        'space-lg': '1.5rem',
        'space-xl': '2rem',
        gutter: '1rem',
        'gutter-desktop': '1.5rem',
        margin: '1rem',
        'margin-tablet': '1.5rem',
        'margin-desktop': '2rem',
      },
      boxShadow: {
        sm: '0 1px 3px 0 rgba(41, 45, 42, 0.02), 0 0 1px 0 rgba(41, 45, 42, 0.04)',
        md: '0 4px 16px -2px rgba(41, 45, 42, 0.04), 0 1px 3px 0 rgba(41, 45, 42, 0.02)',
        lg: '0 12px 32px -4px rgba(41, 45, 42, 0.08)',
      },
    },
  },
  plugins: [],
}

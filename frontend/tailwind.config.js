/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./src/**/*.{html,ts}'],
  theme: {
    extend: {
      colors: {
        // Surfaces
        surface: '#f7f9fc',
        'surface-dim': '#d8dfe8',
        'surface-bright': '#f7f9fc',
        'surface-container-lowest': '#ffffff',
        'surface-container-low': '#f0f4f9',
        'surface-container': '#e9eff6',
        'surface-container-high': '#e2eaf3',
        'surface-container-highest': '#dbe4ef',

        // On Surface
        'on-surface': '#191c20',
        'on-surface-variant': '#424b56',
        'inverse-surface': '#2e3136',
        'inverse-on-surface': '#eff1f5',

        // Outlines
        outline: '#737d89',
        'outline-variant': '#c3cbd5',
        'surface-tint': '#1f62a9',

        // Primary (Blue)
        primary: '#1f62a9',
        'on-primary': '#ffffff',
        'primary-container': '#174a80',
        'on-primary-container': '#d4e5ff',
        'inverse-primary': '#a5c9f8',
        'primary-fixed': '#d4e5ff',
        'primary-fixed-dim': '#a5c9f8',
        'on-primary-fixed': '#001c38',
        'on-primary-fixed-variant': '#174a80',

        // Secondary (Slate Blue)
        secondary: '#4b637d',
        'on-secondary': '#ffffff',
        'secondary-container': '#d1e4f8',
        'on-secondary-container': '#17324a',
        'secondary-fixed': '#d1e4f8',
        'secondary-fixed-dim': '#b5c8dc',
        'on-secondary-fixed': '#0c1e30',
        'on-secondary-fixed-variant': '#344b62',

        // Tertiary (Deep Cyan)
        tertiary: '#285f73',
        'on-tertiary': '#ffffff',
        'tertiary-container': '#164d61',
        'on-tertiary-container': '#c2eafa',
        'tertiary-fixed': '#c2eafa',
        'tertiary-fixed-dim': '#a7cddd',
        'on-tertiary-fixed': '#001f2b',
        'on-tertiary-fixed-variant': '#164d61',

        // Error
        error: '#ba1a1a',
        'on-error': '#ffffff',
        'error-container': '#ffdad6',
        'on-error-container': '#93000a',

        // Background
        background: '#f7f9fc',
        'on-background': '#191c20',

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
        'display-lg': [
          '36px',
          {
            lineHeight: '44px',
            letterSpacing: '-0.025em',
            fontWeight: '600',
          },
        ],
        'display-lg-mobile': [
          '28px',
          {
            lineHeight: '36px',
            letterSpacing: '-0.02em',
            fontWeight: '600',
          },
        ],
        'headline-lg': [
          '28px',
          {
            lineHeight: '36px',
            letterSpacing: '-0.02em',
            fontWeight: '600',
          },
        ],
        'headline-lg-mobile': [
          '22px',
          {
            lineHeight: '30px',
            letterSpacing: '-0.015em',
            fontWeight: '600',
          },
        ],
        'headline-md': [
          '20px',
          {
            lineHeight: '28px',
            letterSpacing: '-0.015em',
            fontWeight: '600',
          },
        ],
        'headline-sm': [
          '16px',
          {
            lineHeight: '24px',
            letterSpacing: '-0.01em',
            fontWeight: '600',
          },
        ],
        'body-lg': [
          '16px',
          {
            lineHeight: '26px',
            letterSpacing: '-0.005em',
            fontWeight: '400',
          },
        ],
        'body-md': [
          '14px',
          {
            lineHeight: '22px',
            fontWeight: '400',
          },
        ],
        'body-sm': [
          '13px',
          {
            lineHeight: '18px',
            fontWeight: '400',
          },
        ],
        'label-md': [
          '12px',
          {
            lineHeight: '16px',
            letterSpacing: '0.02em',
            fontWeight: '500',
          },
        ],
        'label-sm': [
          '11px',
          {
            lineHeight: '14px',
            letterSpacing: '0.04em',
            fontWeight: '600',
          },
        ],
        'metric-lg': [
          '30px',
          {
            lineHeight: '36px',
            letterSpacing: '-0.02em',
            fontWeight: '600',
          },
        ],
        'metric-md': [
          '22px',
          {
            lineHeight: '28px',
            letterSpacing: '-0.01em',
            fontWeight: '600',
          },
        ],
      },
      borderRadius: {
        DEFAULT: '0.25rem',
        lg: '0.5rem',
        xl: '0.75rem',
        full: '9999px',
      },
      spacing: {
        xs: '0.25rem',
        sm: '0.5rem',
        md: '1rem',
        lg: '1.5rem',
        xl: '2rem',
        gutter: '1rem',
        'gutter-desktop': '1.5rem',
      },
      boxShadow: {
        sm: '0 1px 3px 0 rgba(41, 45, 42, 0.02), 0 0 1px 0 rgba(41, 45, 42, 0.04)',
        md: '0 4px 16px -2px rgba(41, 45, 42, 0.04), 0 1px 3px 0 rgba(41, 45, 42, 0.02)',
        lg: '0 12px 32px -4px rgba(41, 45, 42, 0.08)',
      },
    },
  },
  plugins: [],
};

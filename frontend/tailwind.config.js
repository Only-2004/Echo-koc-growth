/** @type {import('tailwindcss').Config} */
// Beacon · Tailwind 配置
// 全部 tokens 移植自 frontend_design/prototype/styles/tokens.css
// 同时 styles/tokens.css 提供 :root CSS variables，便于动态切 accent 等

export default {
  content: ['./index.html', './src/**/*.{ts,tsx,js,jsx}'],
  theme: {
    extend: {
      colors: {
        bg: {
          0: '#faf9f6',
          1: '#ffffff',
          2: '#f3f1ec',
          3: '#e8e5dd',
          inset: '#f7f5f0',
        },
        fg: {
          0: '#1a1814',
          1: '#46433c',
          2: '#807c72',
          3: '#b3afa5',
          4: '#d9d5cb',
        },
        line: {
          0: 'rgba(26,24,20,0.06)',
          1: 'rgba(26,24,20,0.10)',
          2: 'rgba(26,24,20,0.18)',
        },
        accent: {
          DEFAULT: '#5d7a1a',
          ink: '#ffffff',
          soft: 'rgba(93,122,26,0.10)',
          line: 'rgba(93,122,26,0.32)',
        },
        pillar: {
          confirm: '#3d8a3a',
          person: '#b87a1a',
          explore: '#7a4ec4',
        },
        pos: { DEFAULT: '#3d8a3a', soft: 'rgba(61,138,58,0.10)' },
        neg: { DEFAULT: '#c44a3a', soft: 'rgba(196,74,58,0.10)' },
        warn: { DEFAULT: '#b87a1a', soft: 'rgba(184,122,26,0.12)' },
        info: { DEFAULT: '#2d6cb4', soft: 'rgba(45,108,180,0.10)' },
      },
      fontFamily: {
        sans: ['Inter', '"PingFang SC"', '"Hiragino Sans GB"', '"Microsoft YaHei"', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', '"SF Mono"', 'ui-monospace', 'monospace'],
        serif: ['"Source Serif 4"', '"Songti SC"', '"Noto Serif SC"', 'Georgia', 'serif'],
      },
      fontSize: {
        kicker: ['12px', { letterSpacing: '0.08em', textTransform: 'uppercase' }],
      },
      borderRadius: {
        sm: '6px',
        md: '10px',
        lg: '14px',
        xl: '20px',
        '2xl': '28px',
        pill: '999px',
      },
      spacing: {
        1: '4px',
        2: '8px',
        3: '12px',
        4: '16px',
        5: '20px',
        6: '24px',
        7: '32px',
        8: '40px',
        9: '56px',
        10: '72px',
      },
      boxShadow: {
        sm: '0 1px 2px rgba(0,0,0,0.06)',
        md: '0 8px 24px rgba(0,0,0,0.08)',
        lg: '0 24px 60px rgba(0,0,0,0.10)',
      },
      backdropBlur: {
        topbar: '12px',
      },
      transitionDuration: {
        chat: '250ms',
      },
    },
  },
  plugins: [],
}

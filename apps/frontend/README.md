# Dogwalker Frontend

Simple, modern Next.js landing page for Dogwalker.

## Overview

This is a lightweight landing page built with Next.js 15, React 19, TypeScript, and Tailwind CSS v4. It follows modern best practices with server components and optimized performance.

## Features

- **Next.js 15** - Latest App Router with React Server Components
- **TypeScript** - Type-safe development with strict mode
- **Tailwind CSS v4** - Modern utility-first CSS with OKLCH colors
- **Responsive design** - Works on desktop, tablet, and mobile
- **Fast loading** - Optimized for performance with Next.js
- **Modern styling** - Clean, professional design with smooth animations
- **SEO-friendly** - Proper meta tags and semantic structure

## Tech Stack

- **Framework:** Next.js 15.2.4
- **UI:** React 19
- **Styling:** Tailwind CSS v4.1.9
- **Icons:** Lucide React
- **Language:** TypeScript 5

## Local Development

### Prerequisites

- Node.js 20.17.0 or higher
- npm or yarn

### Setup

```bash
# Install dependencies
npm install

# Run development server
npm run dev

# Open http://localhost:3000 in your browser
```

### Available Scripts

```bash
npm run dev      # Start development server
npm run build    # Build for production
npm run start    # Start production server
npm run lint     # Run ESLint
```

## Deployment

### Vercel (Recommended)

```bash
cd apps/frontend
vercel
```

Or connect your GitHub repo to Vercel for automatic deployments.

### Netlify

```bash
# Build command
npm run build

# Publish directory
.next
```

### Docker

```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build
CMD ["npm", "start"]
```

## Structure

```
frontend/
├── app/
│   ├── layout.tsx       # Root layout with metadata
│   ├── page.tsx         # Home page
│   └── globals.css      # Global styles with Tailwind
├── lib/
│   └── utils.ts         # Utility functions (cn helper)
├── package.json         # Dependencies and scripts
├── tsconfig.json        # TypeScript configuration
├── next.config.ts       # Next.js configuration
├── postcss.config.mjs   # PostCSS/Tailwind config
└── README.md            # This file
```

## Customization

### Colors

Edit CSS variables in `app/globals.css`:

```css
:root {
  --primary: oklch(0.6 0.18 142);  /* Bright grass green */
  --accent: oklch(0.7 0.15 60);    /* Warm amber orange */
  /* ... */
}
```

### Content

Edit `app/page.tsx` to update sections:
- Hero (title, subtitle, CTA)
- How It Works (4-step process)
- Features (6 feature cards)
- Tech Stack (technology grid)
- CTA (final call-to-action)
- Footer (links and copyright)

### Metadata

Update SEO metadata in `app/layout.tsx`:

```typescript
export const metadata: Metadata = {
  title: "Your App Name",
  description: "Your description",
  // ...
}
```

## Performance

- **Next.js optimizations** - Automatic code splitting, image optimization
- **Server Components** - Reduced client-side JavaScript
- **Tailwind CSS v4** - Modern CSS with smaller bundle size
- **Type safety** - TypeScript prevents runtime errors

## Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- Mobile browsers (iOS Safari, Chrome Mobile)

## License

MIT License - Same as parent project

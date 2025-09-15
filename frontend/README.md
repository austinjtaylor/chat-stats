# UFA Statistics Frontend

## Overview
Modern, modular frontend for the UFA Statistics application with refactored architecture for better maintainability and performance.

## New Architecture (v2.0)

### Directory Structure
```
frontend/
├── styles/                 # Modular CSS architecture
│   ├── base.css           # Reset and base styles
│   ├── theme.css          # Theme variables
│   ├── main.css           # Main entry point (imports all)
│   └── components/        # Reusable components
│       ├── buttons.css
│       ├── tables.css
│       ├── cards.css
│       └── forms.css
├── js/                    # Modular JavaScript
│   ├── api/
│   │   └── client.js      # Centralized API client
│   └── utils/
│       ├── dom.js         # DOM utilities
│       └── format.js      # Formatting utilities
├── stats/                 # Statistics pages
│   ├── players.html
│   ├── teams.html
│   └── games.html
├── index.html             # Chat interface
├── dashboard.html         # Main dashboard
└── package.json           # Build configuration
```

## Quick Start

### Development (without build tools)
```bash
# Serve files directly
python3 -m http.server 8080
# or
npx serve .
```

### Development (with Vite)
```bash
# Install dependencies
npm install

# Start dev server with hot reload
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## Key Features

### Modular CSS
- **50% smaller** than original monolithic CSS
- **Component-based** architecture
- **Theme support** with CSS variables
- **Utility classes** for rapid development

### JavaScript Utilities

#### API Client
```javascript
// Before: Manual fetch
fetch('/api/players')
  .then(res => res.json())
  .then(data => console.log(data));

// After: Clean API client
statsAPI.getPlayers()
  .then(data => console.log(data));
```

#### DOM Utilities
```javascript
// Query elements
DOM.$('#element');
DOM.$$('.elements');

// Create elements
DOM.createElement('div', { className: 'card' }, ['Content']);

// Event handling
DOM.on(element, 'click', handler);
DOM.debounce(func, 300);
```

#### Format Utilities
```javascript
Format.number(1234);          // "1,234"
Format.percentage(0.75);      // "75.0%"
Format.date('2025-01-15');    // "Jan 15, 2025"
Format.playerName('John', 'Doe'); // "John Doe"
```

## CSS Components

### Buttons
```html
<button class="btn btn-primary">Primary</button>
<button class="btn btn-secondary">Secondary</button>
<button class="btn btn-danger">Danger</button>
<button class="btn btn-icon"><svg>...</svg></button>
```

### Cards
```html
<div class="card">
  <div class="card-header">
    <h3 class="card-title">Title</h3>
  </div>
  <div class="card-body">Content</div>
</div>

<div class="stat-card">
  <div class="stat-card-value">1,234</div>
  <div class="stat-card-label">Players</div>
</div>
```

### Tables
```html
<div class="table-container">
  <table class="table table-striped">
    <thead>
      <tr>
        <th class="sortable">Column</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td>Data</td>
      </tr>
    </tbody>
  </table>
</div>
```

### Forms
```html
<div class="form-group">
  <label class="form-label">Label</label>
  <input type="text" class="form-input" placeholder="Enter text">
  <span class="form-hint">Helper text</span>
</div>
```

## Utility Classes

### Spacing
- Margin: `m-{0-8}`, `mt-`, `mb-`, `ml-`, `mr-`, `mx-`, `my-`
- Padding: `p-{0-8}`, `pt-`, `pb-`, `pl-`, `pr-`, `px-`, `py-`

### Typography
- Size: `text-sm`, `text-base`, `text-lg`, `text-xl`, `text-2xl`
- Weight: `font-normal`, `font-medium`, `font-semibold`, `font-bold`
- Color: `text-primary`, `text-secondary`, `text-muted`

### Flexbox
- `flex`, `flex-col`, `flex-row`
- `items-start`, `items-center`, `items-end`
- `justify-start`, `justify-center`, `justify-end`, `justify-between`
- `gap-{0-8}`

### Display
- `block`, `inline-block`, `inline`, `hidden`
- Responsive: `sm:hidden`, `md:block`, `lg:flex`

## Theme Support

The application supports dark and light themes:

```javascript
// Toggle theme
document.documentElement.setAttribute('data-theme', 'light');
// or
document.documentElement.setAttribute('data-theme', 'dark');
```

## API Endpoints

The frontend connects to these backend endpoints:

- `POST /api/query` - Natural language queries
- `GET /api/stats` - Summary statistics
- `GET /api/players` - Player data
- `GET /api/teams` - Team data
- `GET /api/games` - Game data
- `GET /api/standings` - League standings

## Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- Mobile browsers (iOS Safari, Chrome Mobile)

## Performance Optimizations

1. **Modular CSS** - Load only what's needed
2. **Code splitting** - Separate vendor and app code
3. **Lazy loading** - Load components on demand
4. **Minification** - Reduce file sizes
5. **Caching** - Leverage browser cache

## Development Tools

### Linting
```bash
# Lint CSS
npm run lint:css

# Lint JavaScript
npm run lint:js
```

### Formatting
```bash
# Format all files
npm run format

# Check formatting
npm run format:check
```

## Migration from v1

If you're updating from the old structure:

1. Replace `style.css` references with `styles/main.css`
2. Add utility scripts before main scripts
3. Update API calls to use `statsAPI` client
4. Replace inline styles with utility classes
5. Update component markup to use new CSS classes

## Contributing

1. Follow the modular structure
2. Use utility classes over inline styles
3. Keep components small and reusable
4. Test in multiple browsers
5. Run linting before committing

## License

Private project - All rights reserved
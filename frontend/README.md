# Chat with Stats - Frontend Documentation

## Overview
Modern TypeScript-based frontend for the Chat with Stats application, featuring a modular architecture with strict type safety for better maintainability, reliability, and developer experience.

## TypeScript Architecture (v3.0)

### Directory Structure
```
frontend/
├── src/                    # TypeScript source files
│   ├── api/
│   │   └── client.ts       # Centralized API client with types
│   ├── components/
│   │   ├── nav.ts          # Navigation component
│   │   └── dropdown.ts     # Dropdown component
│   └── utils/
│       ├── dom.ts          # DOM utilities with type safety
│       └── format.ts       # Formatting utilities
├── stats/                  # Statistics pages (TypeScript)
│   ├── players.ts
│   ├── teams.ts
│   └── games.ts
├── types/                  # TypeScript type definitions
│   ├── api.ts              # API response types
│   └── models.ts           # Data model types
├── styles/                 # Modular CSS architecture
│   ├── base.css           # Reset and base styles
│   ├── theme.css          # Theme variables
│   ├── main.css           # Main entry point
│   └── components/        # Component styles
├── index.html             # Chat interface
├── tsconfig.json          # TypeScript configuration
└── package.json           # Build configuration
```

## Quick Start

### Development with TypeScript
```bash
# Install dependencies
npm install

# Start dev server with TypeScript compilation and hot reload
npm run dev

# Run TypeScript type checking
npm run typecheck

# Build for production (with type checking)
npm run build

# Preview production build
npm run preview
```

## TypeScript Features

### Strict Type Safety
The project uses TypeScript with **strict mode enabled** for maximum type safety:
- No implicit `any` types
- Strict null checks
- Strict function types
- No unused locals or parameters

### Path Aliases
Configured aliases for cleaner imports:
```typescript
import { StatsAPI } from '@api/client';
import { DOM } from '@utils/dom';
import { Format } from '@utils/format';
import type { QueryResponse } from '@types/api';
```

### Type Definitions
All API responses and data models are fully typed:
```typescript
interface QueryResponse {
  answer: string;
  data?: any;
  session_id: string;
  error?: string;
}

interface Player {
  player_id: number;
  first_name: string;
  last_name: string;
  team_id?: number;
  position?: string;
  // ... more fields
}
```

## Key Features

### Modular Architecture
- **Component-based** structure with TypeScript modules
- **Type-safe** API client and utilities
- **Reusable** typed components
- **50% smaller CSS** with modular architecture

### TypeScript API Client
```typescript
import statsAPI from '@api/client';
import type { Player, Team, Game } from '@types/models';

// Type-safe API calls
const players: Player[] = await statsAPI.getPlayers();
const team: Team = await statsAPI.getTeam(teamId);
const games: Game[] = await statsAPI.getRecentGames();

// Query with type safety
const response = await statsAPI.query('Who are the top scorers?', sessionId);
console.log(response.answer); // TypeScript knows this is a string
```

### DOM Utilities with Type Safety
```typescript
import { DOM } from '@utils/dom';

// Type-safe element queries
const button = DOM.$<HTMLButtonElement>('#sendButton');
const inputs = DOM.$$<HTMLInputElement>('.form-input');

// Create elements with proper types
const div = DOM.createElement('div',
  { className: 'card', dataset: { id: '123' } },
  ['Content']
);

// Type-safe event handling
DOM.on(button, 'click', (e: MouseEvent) => {
  console.log('Clicked!');
});

// Utility functions with proper types
const debounced = DOM.debounce((value: string) => {
  console.log(value);
}, 300);
```

### Format Utilities with Type Safety
```typescript
import { Format } from '@utils/format';

// All methods are properly typed
const formatted = Format.number(1234);          // "1,234"
const percent = Format.percentage(0.75);        // "75.0%"
const date = Format.date('2025-01-15');        // "Jan 15, 2025"
const name = Format.playerName('John', 'Doe'); // "John Doe"

// Type checking prevents errors
Format.percentage('not a number'); // TypeScript error!
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

The application supports dark and light themes with TypeScript:

```typescript
// Toggle theme with type safety
type Theme = 'light' | 'dark';

function setTheme(theme: Theme): void {
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem('theme', theme);
}

// Get current theme
function getTheme(): Theme {
  return (localStorage.getItem('theme') as Theme) || 'dark';
}
```

## API Integration

The frontend connects to these typed backend endpoints:

```typescript
interface APIEndpoints {
  query: 'POST /api/query';           // Natural language queries
  stats: 'GET /api/stats';           // Summary statistics
  players: 'GET /api/players';       // Player data
  teams: 'GET /api/teams';           // Team data
  games: 'GET /api/games';           // Game data
  standings: 'GET /api/standings';   // League standings
}
```

## Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- Mobile browsers (iOS Safari, Chrome Mobile)

## Performance Optimizations

1. **TypeScript Tree-shaking** - Remove unused code at build time
2. **Type-safe code splitting** - Separate vendor and app code
3. **Lazy loading** - Load components on demand with proper types
4. **Minification** - Reduce file sizes
5. **Type caching** - Faster subsequent builds

## Development Tools

### TypeScript Commands
```bash
# Type checking
npm run typecheck

# Build with type checking
npm run build

# Development with type checking
npm run dev
```

### Linting
```bash
# Lint TypeScript and JavaScript
npm run lint:js

# Lint CSS
npm run lint:css

# Lint everything
npm run lint
```

### Formatting
```bash
# Format all files (including TypeScript)
npm run format

# Check formatting
npm run format:check
```

## Migration from JavaScript (v2 → v3)

If you're updating from the JavaScript version:

1. **Update imports**: Change `js/` to `src/` in all imports
2. **Add type annotations**: Gradually add types to existing code
3. **Use type definitions**: Import types from `@types/*`
4. **Enable strict mode**: Start with loose config, then enable strict
5. **Update build scripts**: Use TypeScript compiler in build process

### Example Migration
```javascript
// Before (JavaScript)
import { DOM } from '../js/utils/dom';
const element = DOM.$('#myElement');

// After (TypeScript)
import { DOM } from '@utils/dom';
const element = DOM.$<HTMLDivElement>('#myElement');
```

## TypeScript Best Practices

1. **Always use strict mode** for maximum type safety
2. **Define interfaces** for all data structures
3. **Use type guards** for runtime type checking
4. **Avoid `any`** - use `unknown` if type is truly unknown
5. **Export types separately** from implementations
6. **Use const assertions** for literal types
7. **Leverage discriminated unions** for complex state

## Contributing

1. **Write TypeScript** - All new code must be TypeScript
2. **Add types** - No implicit `any` types allowed
3. **Run type checking** - `npm run typecheck` before committing
4. **Follow conventions** - Use existing patterns and styles
5. **Test types** - Ensure types match runtime behavior
6. **Document types** - Add JSDoc comments for complex types

## Troubleshooting

### Common TypeScript Issues

**Issue**: "Cannot find module '@utils/dom'"
**Solution**: Check `tsconfig.json` paths configuration

**Issue**: "Type 'X' is not assignable to type 'Y'"
**Solution**: Verify your types match the expected interface

**Issue**: "Object is possibly 'null'"
**Solution**: Add null checks or use optional chaining (`?.`)

## License

Private project - All rights reserved
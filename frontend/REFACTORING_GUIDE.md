# Frontend Refactoring Guide

## Overview
This guide documents the refactoring of the frontend codebase from monolithic CSS/JS files to a modular, maintainable architecture.

## Problems Addressed

### CSS Issues (style.css with 1010 lines)
- **Too large**: Single file with mixed concerns
- **Hard to maintain**: Finding specific styles was difficult
- **Duplication**: Same styles repeated across multiple files
- **No clear structure**: Base styles mixed with components and utilities
- **Global scope pollution**: All styles globally available

### JavaScript Issues
- **No module system**: Everything in global scope
- **Code duplication**: Similar API calls repeated across files
- **Large files**: dashboard.js (447 lines), players.js (411 lines)
- **No centralized API client**: Each file had its own fetch logic
- **Missing utilities**: Common operations repeated everywhere

## New Structure

### CSS Architecture
```
frontend/
├── styles/
│   ├── base.css           # Reset, typography, base elements
│   ├── theme.css          # CSS variables for theming
│   ├── main.css           # Imports all modules
│   └── components/
│       ├── buttons.css    # Button styles and variants
│       ├── tables.css     # Table component styles
│       ├── cards.css      # Card component styles
│       └── forms.css      # Form elements and inputs
```

### JavaScript Architecture
```
frontend/
├── js/
│   ├── api/
│   │   └── client.js      # Centralized API client
│   ├── utils/
│   │   ├── dom.js         # DOM manipulation utilities
│   │   └── format.js      # Data formatting utilities
│   └── components/        # Reusable UI components (future)
```

## Key Improvements

### 1. Modular CSS (~150-200 lines per file)
- **base.css**: CSS reset and typography
- **theme.css**: All color and theme variables
- **components/**: Reusable UI components
- **Utility classes**: Consistent spacing, display, flexbox utilities

### 2. Centralized API Client
```javascript
// Before: Repeated in every file
fetch('/api/players', { method: 'GET' })
  .then(res => res.json())
  .then(data => { /* handle */ })
  .catch(err => { /* handle */ });

// After: Clean, reusable
statsAPI.getPlayers()
  .then(data => { /* handle */ })
  .catch(error => { /* handle */ });
```

### 3. Utility Functions
```javascript
// DOM utilities
DOM.$('#element');                    // querySelector
DOM.on(element, 'click', handler);    // addEventListener
DOM.createElement('div', {}, []);      // Create elements

// Format utilities
Format.number(1234);                   // "1,234"
Format.percentage(0.75);               // "75.0%"
Format.date('2025-01-15');            // "Jan 15, 2025"
```

## Migration Steps

### Step 1: Update HTML Files
Replace old stylesheets:
```html
<!-- Old -->
<link rel="stylesheet" href="style.css">

<!-- New -->
<link rel="stylesheet" href="styles/main.css">
```

### Step 2: Include JavaScript Utilities
```html
<!-- Add before your main script -->
<script src="js/api/client.js"></script>
<script src="js/utils/dom.js"></script>
<script src="js/utils/format.js"></script>
```

### Step 3: Update JavaScript Code
```javascript
// Old: Direct fetch
fetch('/api/query', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ query: message })
});

// New: API client
statsAPI.query(message, sessionId);
```

### Step 4: Use New CSS Classes
```html
<!-- Old custom styles -->
<button style="background: #2563eb; color: white; padding: 10px 20px;">

<!-- New component classes -->
<button class="btn btn-primary">
```

## Benefits

### Performance
- **Smaller files**: Faster parsing and caching
- **Modular loading**: Load only what you need
- **Better caching**: Unchanged modules stay cached

### Maintainability
- **Easy to find**: Know exactly where styles/code live
- **No duplication**: Shared utilities and components
- **Clear separation**: Components, layouts, utilities separated

### Scalability
- **Easy to extend**: Add new components without affecting others
- **Consistent patterns**: Follow established structure
- **Reusable code**: Use utilities across all pages

## Component Examples

### Buttons
```html
<button class="btn btn-primary">Primary</button>
<button class="btn btn-secondary">Secondary</button>
<button class="btn btn-ghost">Ghost</button>
<button class="btn btn-danger">Danger</button>
<button class="btn btn-primary btn-lg">Large</button>
<button class="btn btn-icon"><svg>...</svg></button>
```

### Cards
```html
<div class="card">
  <div class="card-header">
    <h3 class="card-title">Title</h3>
  </div>
  <div class="card-body">Content</div>
  <div class="card-footer">Footer</div>
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

<select class="form-select">
  <option>Option 1</option>
</select>

<textarea class="form-textarea"></textarea>
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
- Display: `flex`, `inline-flex`
- Direction: `flex-row`, `flex-col`
- Align: `items-start`, `items-center`, `items-end`
- Justify: `justify-start`, `justify-center`, `justify-end`, `justify-between`
- Gap: `gap-{0-8}`

### Display
- `block`, `inline-block`, `inline`, `hidden`
- Responsive: `sm:hidden`, `md:block`, `lg:flex`

## Next Steps

### Immediate Actions
1. Test all pages with new structure
2. Update remaining HTML files to use new CSS
3. Replace inline styles with utility classes
4. Convert remaining API calls to use client

### Future Improvements
1. Add build system (Vite/esbuild) for bundling
2. Implement CSS purging to remove unused styles
3. Create more reusable JavaScript components
4. Add TypeScript for better type safety
5. Implement CSS-in-JS or CSS Modules for scoping

## File Size Comparison

| File | Before | After | Reduction |
|------|---------|--------|-----------|
| style.css | 1010 lines | Split into 8 files | ~150 lines each |
| Total CSS | ~2950 lines | ~1200 lines | 59% reduction |
| script.js | 405 lines | Split into modules | Modular |
| dashboard.js | 447 lines | Uses shared utilities | ~200 lines |

## Conclusion

This refactoring provides a solid foundation for maintaining and scaling the frontend. The modular structure makes it easy to:
- Find and update styles
- Add new features
- Fix bugs
- Onboard new developers
- Optimize performance

The investment in refactoring will pay dividends in reduced development time and fewer bugs going forward.
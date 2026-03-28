# Vue Frontend for pkts_capture

Modern Vue 3 + Vite frontend for the Claude Code Capture dashboard.

## Architecture

```
web-vue/
├── src/
│   ├── components/        # Reusable Vue components
│   │   ├── Sidebar.vue   # Navigation sidebar
│   │   └── TopHeader.vue # Page header
│   ├── views/            # Page-level components
│   │   ├── Dashboard.vue    # Statistics dashboard with charts
│   │   ├── Sessions.vue     # Session list with filters
│   │   ├── SessionDetail.vue # Session timeline view
│   │   ├── RequestDetail.vue # Request detail view
│   │   └── Analysis.vue     # Token and tool analysis
│   ├── stores/           # Pinia state management
│   │   ├── statistics.js  # Dashboard stats
│   │   ├── sessions.js    # Sessions data
│   │   └── charts.js      # Chart data
│   ├── router/           # Vue Router configuration
│   │   └── index.js
│   ├── utils/            # Helper utilities
│   │   └── formatters.js  # Number/date formatting
│   ├── App.vue           # Root component
│   ├── main.js           # Entry point
│   └── style.css         # Global styles
├── index.html
├── package.json
└── vite.config.js
```

## Technology Stack

- **Vue 3** - Progressive JavaScript framework
- **Vue Router 4** - Client-side routing
- **Pinia** - State management
- **Vite** - Build tool
- **Chart.js** - Data visualization
- **Bootstrap Icons** - Icon font

## Features Preserved

All original functionality is maintained:

1. **Dashboard** (`/`)
   - Statistics cards with real-time updates
   - Request volume timeline chart
   - Model distribution pie chart
   - Top tools list
   - Recent sessions list
   - Time range filter

2. **Sessions** (`/sessions`)
   - Paginated session list
   - Filters: Session ID, Model, Date range
   - Sort by started time

3. **Session Detail** (`/sessions/:id`)
   - Session information card
   - Message timeline (user/assistant)
   - Tool call summaries
   - Pagination

4. **Request Detail** (`/requests/:id`)
   - Token usage metrics
   - Request/response messages
   - Tool call details
   - Metadata panel

5. **Analysis** (`/analysis`)
   - Token usage by model
   - Tool usage statistics
   - Cost breakdown

## Styling

- CSS variables matching the original design
- LangSmith-inspired color scheme
- Responsive grid layouts
- Consistent with original visual style

## Development

```bash
# Install dependencies
cd web-vue
npm install

# Run development server
npm run dev

# Build for production
npm run build
```

## Flask Integration

The Flask backend can serve the Vue app in two modes:

### Mode 1: Jinja2 Templates (Default)
Original template-based rendering.

### Mode 2: Vue SPA
Serve the built Vue app:

```bash
# Build Vue app
cd web-vue
npm run build

# Start Flask with Vue mode
export USE_VUE=true
python web/app.py
```

Or modify `scripts/run.py` to set `USE_VUE=true`.

## API Endpoints Used

- `GET /api/statistics/summary` - Dashboard stats
- `GET /api/statistics/timeline` - Timeline data
- `GET /api/statistics/models` - Model distribution
- `GET /api/statistics/tools` - Tool usage
- `GET /api/sessions` - Session list
- `GET /api/sessions/:id` - Session detail
- `GET /api/requests/:id` - Request detail
- `GET /api/analysis/tokens` - Token analysis
- `GET /api/analysis/tools` - Tool analysis

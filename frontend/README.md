# Re-Habitar PoC - Frontend

Territorial intelligence dashboard for demographic risk analysis in Madrid's Sierra Norte region. Built with **Angular 22** + **Tailwind CSS v3** + **TypeScript**.

Displays WLC (Weighted Linear Combination) viability scores, emergency healthcare accessibility, and intelligent public funding opportunities from BDNS/Reto Demográfico.

## Quick Start

```bash
npm start
```

Application runs at `http://localhost:4200/`

### API y datos de prueba

En desarrollo, `/api` se redirige a `http://localhost:8000` mediante
`proxy.conf.json`; inicia el backend en ese puerto o modifica el destino del
proxy. Las respuestas fallidas se muestran en la interfaz.

Para probar sin backend, abre `http://localhost:4200/?mock=1`. El modo mock
permanece activo durante la sesión de la pestaña; usa `?mock=0` para volver
al backend. Los datos son ficticios e incluyen un municipio pendiente,
una ficha con ruta y convocatorias abiertas y cerradas. Los mocks implementan
los filtros visibles, pero no recalculan el WLC con pesos personalizados ni
persisten la ingesta.

## Project Structure

```
src/app/
├── pages/                 # Route-based components
│   ├── dashboard/        # 5 KPI cards + WLC map + municipality ranking
│   ├── municipio-detail/ # Detailed municipality viability breakdown
│   ├── convocatorias/    # Public funding catalog & filtering
│   └── not-found/        # 404 page
│
├── shared/components/    # Reusable UI components
│   ├── navbar/          # Fixed navigation bar
│   ├── kpi-card/        # KPI metric cards
│   ├── territorio-map/  # Interactive territory map
│   └── rango-municipal/ # WLC ranking table
│
├── core/
│   ├── services/        # MunicipioService (API client)
│   └── models/          # TypeScript interfaces
│
└── app.*                # Root component & routing
```

## Architecture

- **Standalone Components**: Modern Angular pattern (no NgModules)
- **Change Detection**: OnPush strategy for performance
- **Reactive**: RxJS Subjects & takeUntil for cleanup
- **Styling**: Tailwind v3 + 43-color Sierra Norte design system
- **State**: Local component state (service-backed where needed)

## Key Components

| Component | Purpose |
|-----------|---------|
| **Dashboard** | 5 KPIs + WLC map + municipality ranking by viability score |
| **Municipio Detail** | Full WLC breakdown (5 criteria), demographics, infrastructure |
| **Convocatorias** | Searchable funding catalog filtered by applicability |
| **KPI Card** | Metric display with status badges (favorable/warning/critical) |
| **Rango Municipal** | Sortable, searchable table of municipalities ranked by WLC |

## Data Models

- **Municipio**: Core geographic unit with WLC scores, demographics, infrastructure
- **WLCBreakdown**: 5-component viability assessment (road access, healthcare proximity, digital connectivity, water access, demographic inertia)
- **Convocatoria**: Public funding opportunities with applicability rules (by municipality, population, region)
- **KPISummary**: Dashboard aggregates (total analyzed, risk levels, pending)

## Available Commands

```bash
npm start        # Dev server + watch mode (port 4200)
npm run build    # Production build → dist/
npm test         # Unit tests (Vitest)
ng generate component path/name  # Scaffold component
```

## Design System

- **Colors**: Primary (Sierra blue), Secondary, Tertiary, Error, Surfaces (43 tokens)
- **Typography**: Plus Jakarta Sans (headings) + Inter (body, tabular numbers)
- **Spacing**: 8pt system (xs, sm, md, lg, xl, xl-2xl)
- **Components**: Buttons, inputs, cards, badges, tables with consistent styling
- **Icons**: Material Symbols (Outlined variant via CDN)

## Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 15+

## Dependencies

- **Angular 22.3.0** - Framework
- **Tailwind CSS v3.4.1** - Styling
- **TypeScript 5.6** - Type safety
- **RxJS 7** - Reactive programming

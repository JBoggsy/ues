# UES Web UI

Browser-based user interface for the User Environment Simulator (UES).

## Tech Stack

- **React 18** - UI framework
- **TypeScript** - Type-safe development
- **Vite** - Build tooling
- **Tailwind CSS** - Styling
- **shadcn/ui** - Component library
- **TanStack Query** - Server state management
- **React Router** - Client-side routing

## Development

### Prerequisites

- Node.js 18+
- UES backend running on `http://localhost:8000`

### Setup

```bash
# Install dependencies
npm install

# Start development server
npm run dev
```

The UI will be available at `http://localhost:5173`.

### Environment Variables

Copy `.env.example` to `.env.local` and configure:

```env
VITE_API_BASE_URL=http://localhost:8000
```

## Project Structure

```
src/
├── api/           # API client and hooks
├── components/    # Reusable UI components
│   ├── ui/        # shadcn/ui components
│   ├── layout/    # Layout components
│   └── simulation/# Simulation controls
├── pages/         # Page components
├── lib/           # Utilities
└── types/         # TypeScript types
```

## Building for Production

```bash
npm run build
```

Output will be in the `dist/` directory.

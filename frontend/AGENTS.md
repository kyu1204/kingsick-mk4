# Frontend AGENTS.md

Next.js 14 App Router + TypeScript + Tailwind CSS + shadcn/ui.

## Structure

```
frontend/
├── app/              # App Router pages
│   ├── (auth)/       # Route group: login, register
│   ├── dashboard/    # Main dashboard
│   ├── watchlist/    # Stock watchlist
│   ├── settings/     # User settings
│   └── layout.tsx    # Root layout
├── components/       # See components/AGENTS.md
├── lib/              # See lib/AGENTS.md
├── types/            # TypeScript interfaces
├── __tests__/        # Vitest tests
└── public/           # Static assets
```

## Commands

```bash
# Dev
npm run dev

# Test
npm run test -- --run                        # All once
npm run test -- __tests__/lib/utils.test.ts --run  # Single file
npm run test:coverage                        # Coverage

# Lint & Type
npm run lint
npx tsc --noEmit
```

## Conventions

### Import Order
```typescript
import * as React from 'react';              // React first
import { Slot } from '@radix-ui/react-slot';  // External libs
import { cn } from '@/lib/utils';             // Internal (@/ alias)
import type { ButtonProps } from './types';   // Types last
```

### Path Alias
Always use `@/` for internal imports:
```typescript
import { Button } from '@/components/ui';
import { apiClient } from '@/lib/api';
import { User } from '@/types';
```

### Component Pattern
```typescript
const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, ...props }, ref) => {
    return (
      <button
        className={cn(buttonVariants({ variant }), className)}
        ref={ref}
        {...props}
      />
    );
  }
);
Button.displayName = 'Button';
```

### Styling
- Tailwind utility classes only
- Use `cn()` for conditional classes
- Never inline `style={{}}` objects
- Custom colors: `profit` (green), `loss` (red)

## State Management

- **Auth**: React Context (`lib/auth/index.tsx`)
- **Complex state**: Zustand (available, use when needed)
- **Local state**: `useState`, `useReducer`
- **Server state**: Direct API calls (no React Query yet)

## API Integration

1. Check backend router first
2. Use `lib/api/` client functions
3. Handle `ApiError` properly

```typescript
import { watchlistApi } from '@/lib/api';

try {
  const items = await watchlistApi.getItems();
} catch (error) {
  if (error instanceof ApiError) {
    // Handle based on status
  }
}
```

## Testing

- Framework: Vitest + React Testing Library
- Location: `__tests__/` (mirrors source structure)
- Setup: `vitest.setup.ts` (Next.js mocks included)

## Anti-Patterns

- Never use `as any` or `@ts-ignore`
- Never hardcode API paths (use lib/api)
- Never skip `displayName` on forwardRef components
- Never use CSS-in-JS or inline styles

# Components AGENTS.md

shadcn/ui based component library with domain-specific extensions.

## Structure

```
components/
├── ui/              # Base components (shadcn/ui pattern)
│   ├── button.tsx
│   ├── input.tsx
│   ├── dialog.tsx
│   ├── card.tsx
│   └── index.ts     # Barrel export
├── layout/          # App-wide layout
│   ├── main-layout.tsx
│   ├── header.tsx
│   ├── sidebar.tsx
│   └── index.ts
├── charts/          # Trading charts
│   ├── StockChart.tsx
│   ├── PortfolioChart.tsx
│   └── index.ts
├── watchlist/       # Watchlist domain
│   ├── watchlist-table.tsx
│   ├── add-stock-modal.tsx
│   └── index.ts
├── settings/        # Settings domain
│   ├── api-key-settings.tsx
│   ├── TelegramSettings.tsx
│   └── index.ts
├── auth/            # Auth domain
│   ├── protected-route.tsx
│   └── index.ts
├── admin/           # Admin domain
│   ├── invitation-manager.tsx
│   └── index.ts
└── providers/       # Context providers
    └── theme-provider.tsx
```

## UI Component Pattern (shadcn/ui)

```typescript
import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const buttonVariants = cva(
  'inline-flex items-center justify-center rounded-md text-sm font-medium',
  {
    variants: {
      variant: {
        default: 'bg-primary text-primary-foreground',
        destructive: 'bg-destructive text-destructive-foreground',
        profit: 'bg-profit text-profit-foreground',  // Custom
        loss: 'bg-loss text-loss-foreground',        // Custom
      },
      size: {
        default: 'h-10 px-4 py-2',
        sm: 'h-9 px-3',
        lg: 'h-11 px-8',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(...);
Button.displayName = 'Button';

export { Button, buttonVariants };
```

## Domain Component Pattern

```typescript
// watchlist/watchlist-table.tsx
import { Table, TableBody, TableCell } from '@/components/ui';
import { WatchlistItem } from '@/types';

interface WatchlistTableProps {
  items: WatchlistItem[];
  onEdit: (item: WatchlistItem) => void;
  onDelete: (id: string) => void;
}

export function WatchlistTable({ items, onEdit, onDelete }: WatchlistTableProps) {
  return (
    <Table>
      {/* Implementation */}
    </Table>
  );
}
```

## Styling Rules

1. **Tailwind only** - No CSS modules, no styled-components
2. **cn() utility** - For conditional/merged classes
3. **Custom colors** - Use `profit`, `loss` for trading UI
4. **Responsive** - Mobile-first with Tailwind breakpoints

## Imports

Always use barrel exports:
```typescript
// Good
import { Button, Input, Dialog } from '@/components/ui';

// Bad
import { Button } from '@/components/ui/button';
```

## Adding New Components

1. **UI component**: Add to `ui/`, follow shadcn pattern
2. **Domain component**: Create folder, add `index.ts`
3. **Update barrel**: Export from `index.ts`

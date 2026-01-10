# Lib AGENTS.md

Shared utilities, API client, and auth context.

## Structure

```
lib/
├── api/              # API client layer
│   ├── client.ts     # Axios singleton with interceptors
│   ├── index.ts      # Barrel export
│   ├── watchlist.ts  # Watchlist API functions
│   ├── trading.ts    # Trading API functions
│   ├── telegram.ts   # Telegram API functions
│   └── ...
├── auth/
│   └── index.tsx     # AuthContext + useAuth hook
├── utils.ts          # Utility functions
└── websocket.ts      # WebSocket client (future)
```

## API Client

### Base Client (client.ts)

```typescript
import axios from 'axios';

export class ApiError extends Error {
  public readonly status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

export const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  headers: { 'Content-Type': 'application/json' },
});

// Auto-inject JWT token
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('kingsick_access_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Convert errors to ApiError
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const { status, data } = error.response || {};
    throw new ApiError(status || 500, data?.detail || error.message);
  }
);
```

### Domain API Functions

```typescript
// api/watchlist.ts
import { apiClient } from './client';
import { WatchlistItem, WatchlistItemCreate } from '@/types';

export const watchlistApi = {
  getItems: async (): Promise<WatchlistItem[]> => {
    const { data } = await apiClient.get('/api/v1/watchlist');
    return data;
  },
  
  addItem: async (item: WatchlistItemCreate): Promise<WatchlistItem> => {
    const { data } = await apiClient.post('/api/v1/watchlist', item);
    return data;
  },
  
  deleteItem: async (id: string): Promise<void> => {
    await apiClient.delete(`/api/v1/watchlist/${id}`);
  },
};
```

## Auth Context

```typescript
// auth/index.tsx
import { createContext, useContext } from 'react';

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be within AuthProvider');
  return context;
}
```

## Utilities (utils.ts)

```typescript
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

// Class name merger
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// Format Korean Won
export function formatKRW(value: number): string {
  return new Intl.NumberFormat('ko-KR', {
    style: 'currency',
    currency: 'KRW',
  }).format(value);
}

// Format percentage with sign
export function formatPercent(value: number, decimals = 2): string {
  const sign = value >= 0 ? '+' : '';
  return `${sign}${value.toFixed(decimals)}%`;
}
```

## Before Adding API Calls

1. Check backend router in `backend/app/api/*.py`
2. Verify path at `http://localhost:8000/docs`
3. Add types in `types/api.ts` or `types/index.ts`
4. Create/update domain API file in `lib/api/`

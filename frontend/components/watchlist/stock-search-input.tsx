'use client';

import { useState, useEffect, useRef } from 'react';
import { Input } from '@/components/ui/input';
import { stocksApi, type StockInfo } from '@/lib/api';
import { Search, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

interface StockSearchInputProps {
  onSelect: (stock: StockInfo) => void;
  placeholder?: string;
  disabled?: boolean;
}

export function StockSearchInput({
  onSelect,
  placeholder = '종목명 또는 코드 검색...',
  disabled = false,
}: StockSearchInputProps) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<StockInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const inputRef = useRef<HTMLInputElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Debounced search
  useEffect(() => {
    if (query.length < 2) {
      setResults([]);
      setIsOpen(false);
      return;
    }

    const timer = setTimeout(async () => {
      setLoading(true);
      try {
        const response = await stocksApi.searchStocks(query, 10);
        setResults(response.stocks);
        setIsOpen(response.stocks.length > 0);
        setSelectedIndex(-1);
      } catch {
        setResults([]);
      } finally {
        setLoading(false);
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [query]);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node) &&
        inputRef.current &&
        !inputRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSelect = (stock: StockInfo) => {
    onSelect(stock);
    setQuery('');
    setResults([]);
    setIsOpen(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!isOpen) return;

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setSelectedIndex((prev) => Math.min(prev + 1, results.length - 1));
        break;
      case 'ArrowUp':
        e.preventDefault();
        setSelectedIndex((prev) => Math.max(prev - 1, 0));
        break;
      case 'Enter':
        e.preventDefault();
        if (selectedIndex >= 0 && results[selectedIndex]) {
          handleSelect(results[selectedIndex]);
        }
        break;
      case 'Escape':
        setIsOpen(false);
        break;
    }
  };

  return (
    <div className="relative">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={() => results.length > 0 && setIsOpen(true)}
          placeholder={placeholder}
          disabled={disabled}
          className="pl-9"
        />
        {loading && (
          <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 animate-spin text-muted-foreground" />
        )}
      </div>

      {isOpen && results.length > 0 && (
        <div
          ref={dropdownRef}
          className="absolute z-50 mt-1 w-full rounded-md border bg-popover shadow-lg"
        >
          <ul className="py-1 max-h-60 overflow-auto">
            {results.map((stock, index) => (
              <li
                key={stock.code}
                className={cn(
                  'flex items-center justify-between px-3 py-2 cursor-pointer transition-colors',
                  index === selectedIndex
                    ? 'bg-accent text-accent-foreground'
                    : 'hover:bg-accent/50'
                )}
                onClick={() => handleSelect(stock)}
                onMouseEnter={() => setSelectedIndex(index)}
              >
                <div>
                  <span className="font-medium">{stock.name}</span>
                  <span className="ml-2 text-sm text-muted-foreground font-mono">
                    {stock.code}
                  </span>
                </div>
                <span className="text-xs text-muted-foreground">{stock.market}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

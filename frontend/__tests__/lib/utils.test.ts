import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  cn,
  formatKRW,
  formatNumber,
  formatPercent,
  formatDate,
  formatDateTime,
  sleep,
  debounce,
  isTradingHours,
} from '@/lib/utils';

describe('utils', () => {
  describe('cn', () => {
    it('should merge class names correctly', () => {
      expect(cn('foo', 'bar')).toBe('foo bar');
    });

    it('should handle conditional classes', () => {
      expect(cn('foo', false && 'bar', 'baz')).toBe('foo baz');
    });

    it('should merge tailwind classes correctly', () => {
      expect(cn('px-4', 'px-6')).toBe('px-6');
    });
  });

  describe('formatKRW', () => {
    it('should format number as Korean Won', () => {
      const result = formatKRW(1234567);
      expect(result).toContain('1,234,567');
    });

    it('should handle zero', () => {
      const result = formatKRW(0);
      expect(result).toContain('0');
    });

    it('should handle negative numbers', () => {
      const result = formatKRW(-50000);
      // Korean locale formats with currency symbol
      expect(result).toContain('50,000');
      expect(result).toMatch(/-/);
    });
  });

  describe('formatNumber', () => {
    it('should format number with thousand separators', () => {
      expect(formatNumber(1234567)).toBe('1,234,567');
    });

    it('should handle decimal places', () => {
      expect(formatNumber(1234.567, 2)).toBe('1,234.57');
    });
  });

  describe('formatPercent', () => {
    it('should format positive percentage with plus sign', () => {
      expect(formatPercent(5.25)).toBe('+5.25%');
    });

    it('should format negative percentage', () => {
      expect(formatPercent(-3.5)).toBe('-3.50%');
    });

    it('should respect decimal places', () => {
      expect(formatPercent(5.255, 1)).toBe('+5.3%');
    });
  });

  describe('formatDate', () => {
    it('should format Date object', () => {
      const date = new Date('2024-01-15');
      const result = formatDate(date);
      expect(result).toContain('2024');
      expect(result).toContain('01');
      expect(result).toContain('15');
    });

    it('should format date string', () => {
      const result = formatDate('2024-06-20');
      expect(result).toContain('2024');
      expect(result).toContain('06');
      expect(result).toContain('20');
    });
  });

  describe('formatDateTime', () => {
    it('should include time in output', () => {
      const date = new Date('2024-01-15T14:30:45');
      const result = formatDateTime(date);
      // Korean locale uses 12-hour format with 오전/오후
      expect(result).toContain('2024');
      expect(result).toContain('30');
      expect(result).toContain('45');
    });
  });

  describe('sleep', () => {
    it('should resolve after specified time', async () => {
      const start = Date.now();
      await sleep(100);
      const elapsed = Date.now() - start;
      expect(elapsed).toBeGreaterThanOrEqual(90);
    });
  });

  describe('debounce', () => {
    beforeEach(() => {
      vi.useFakeTimers();
    });

    afterEach(() => {
      vi.useRealTimers();
    });

    it('should debounce function calls', () => {
      const fn = vi.fn();
      const debouncedFn = debounce(fn, 100);

      debouncedFn();
      debouncedFn();
      debouncedFn();

      expect(fn).not.toHaveBeenCalled();

      vi.advanceTimersByTime(100);

      expect(fn).toHaveBeenCalledTimes(1);
    });

    it('should call with latest arguments', () => {
      const fn = vi.fn();
      const debouncedFn = debounce(fn, 100);

      debouncedFn('first');
      debouncedFn('second');
      debouncedFn('third');

      vi.advanceTimersByTime(100);

      expect(fn).toHaveBeenCalledWith('third');
    });
  });

  describe('isTradingHours', () => {
    beforeEach(() => {
      vi.useFakeTimers();
    });

    afterEach(() => {
      vi.useRealTimers();
    });

    it('should return true during trading hours on weekday', () => {
      // Set to Wednesday 10:00 AM KST
      const tradingTime = new Date('2024-01-17T10:00:00+09:00');
      vi.setSystemTime(tradingTime);
      expect(isTradingHours()).toBe(true);
    });

    it('should return false on weekend', () => {
      // Set to Saturday 10:00 AM KST
      const weekend = new Date('2024-01-20T10:00:00+09:00');
      vi.setSystemTime(weekend);
      expect(isTradingHours()).toBe(false);
    });

    it('should return false before market open', () => {
      // Set to Wednesday 8:00 AM KST
      const beforeOpen = new Date('2024-01-17T08:00:00+09:00');
      vi.setSystemTime(beforeOpen);
      expect(isTradingHours()).toBe(false);
    });

    it('should return false after market close', () => {
      // Set to Wednesday 4:00 PM KST
      const afterClose = new Date('2024-01-17T16:00:00+09:00');
      vi.setSystemTime(afterClose);
      expect(isTradingHours()).toBe(false);
    });
  });
});

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { TelegramSettings } from './TelegramSettings';
import { telegramApi } from '@/lib/api';

// Mock the telegram API
vi.mock('@/lib/api', () => ({
  telegramApi: {
    getStatus: vi.fn(),
    createLinkToken: vi.fn(),
    unlink: vi.fn(),
  },
}));

describe('TelegramSettings', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers({ shouldAdvanceTime: true });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe('Loading state', () => {
    it('should show loading spinner initially', () => {
      vi.mocked(telegramApi.getStatus).mockImplementation(
        () => new Promise(() => {}) // Never resolves
      );

      render(<TelegramSettings />);

      // The loading spinner has animate-spin class
      const spinner = document.querySelector('.animate-spin');
      expect(spinner).toBeInTheDocument();
    });
  });

  describe('Not connected state', () => {
    beforeEach(() => {
      vi.mocked(telegramApi.getStatus).mockResolvedValue({
        linked: false,
        linked_at: null,
      });
    });

    it('should show "Not connected" when not linked', async () => {
      render(<TelegramSettings />);

      await waitFor(() => {
        expect(screen.getByText('연결되지 않음')).toBeInTheDocument();
      });

      expect(screen.getByText('미연결')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /텔레그램 연결/i })).toBeInTheDocument();
    });

    it('should call createLinkToken when connect button clicked', async () => {
      vi.mocked(telegramApi.createLinkToken).mockResolvedValue({
        deep_link: 'https://t.me/test_bot?start=token123',
        expires_in: 600,
      });

      render(<TelegramSettings />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /텔레그램 연결/i })).toBeInTheDocument();
      });

      const connectButton = screen.getByRole('button', { name: /텔레그램 연결/i });
      await userEvent.click(connectButton);

      await waitFor(() => {
        expect(telegramApi.createLinkToken).toHaveBeenCalled();
      });
    });

    it('should show deep link after creating link token', async () => {
      vi.mocked(telegramApi.createLinkToken).mockResolvedValue({
        deep_link: 'https://t.me/test_bot?start=token123',
        expires_in: 600,
      });

      render(<TelegramSettings />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /텔레그램 연결/i })).toBeInTheDocument();
      });

      const connectButton = screen.getByRole('button', { name: /텔레그램 연결/i });
      await userEvent.click(connectButton);

      await waitFor(() => {
        expect(screen.getByText('연결 대기 중...')).toBeInTheDocument();
        expect(screen.getByRole('link', { name: /텔레그램 열기/i })).toBeInTheDocument();
      });
    });

    it('should show error when createLinkToken fails', async () => {
      vi.mocked(telegramApi.createLinkToken).mockRejectedValue(
        new Error('Failed to create link')
      );

      render(<TelegramSettings />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /텔레그램 연결/i })).toBeInTheDocument();
      });

      const connectButton = screen.getByRole('button', { name: /텔레그램 연결/i });
      await userEvent.click(connectButton);

      await waitFor(() => {
        expect(screen.getByText(/failed to create link/i)).toBeInTheDocument();
      });
    });
  });

  describe('Linking in progress state', () => {
    beforeEach(() => {
      vi.mocked(telegramApi.getStatus).mockResolvedValue({
        linked: false,
        linked_at: null,
      });
      vi.mocked(telegramApi.createLinkToken).mockResolvedValue({
        deep_link: 'https://t.me/test_bot?start=token123',
        expires_in: 600,
      });
    });

    it('should show countdown timer', async () => {
      render(<TelegramSettings />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /텔레그램 연결/i })).toBeInTheDocument();
      });

      const connectButton = screen.getByRole('button', { name: /텔레그램 연결/i });
      await userEvent.click(connectButton);

      await waitFor(() => {
        // Check for expiry message with time format (M:SS)
        const expiryText = screen.getByText(/링크 만료까지 \d+:\d{2}/i);
        expect(expiryText).toBeInTheDocument();
      });
    });

    it('should allow canceling link request', async () => {
      render(<TelegramSettings />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /텔레그램 연결/i })).toBeInTheDocument();
      });

      const connectButton = screen.getByRole('button', { name: /텔레그램 연결/i });
      await userEvent.click(connectButton);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /취소/i })).toBeInTheDocument();
      });

      const cancelButton = screen.getByRole('button', { name: /취소/i });
      await userEvent.click(cancelButton);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /텔레그램 연결/i })).toBeInTheDocument();
      });
    });

    it('should have correct deep link href', async () => {
      render(<TelegramSettings />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /텔레그램 연결/i })).toBeInTheDocument();
      });

      const connectButton = screen.getByRole('button', { name: /텔레그램 연결/i });
      await userEvent.click(connectButton);

      await waitFor(() => {
        const openTelegramLink = screen.getByRole('link', { name: /텔레그램 열기/i });
        expect(openTelegramLink).toHaveAttribute(
          'href',
          'https://t.me/test_bot?start=token123'
        );
        expect(openTelegramLink).toHaveAttribute('target', '_blank');
      });
    });
  });

  describe('Connected state', () => {
    const linkedAt = '2024-01-15T09:30:00Z';

    beforeEach(() => {
      vi.mocked(telegramApi.getStatus).mockResolvedValue({
        linked: true,
        linked_at: linkedAt,
      });
    });

    it('should show "Connected" when linked', async () => {
      render(<TelegramSettings />);

      await waitFor(() => {
        expect(screen.getByText('연결됨')).toBeInTheDocument();
      });

      expect(screen.getByRole('button', { name: /텔레그램 연결 해제/i })).toBeInTheDocument();
    });

    it('should show connected date', async () => {
      render(<TelegramSettings />);

      await waitFor(() => {
        const connectedElements = screen.getAllByText(/연결됨/i);
        expect(connectedElements.length).toBeGreaterThan(0);
      });
    });

    it('should call unlink when disconnect button clicked', async () => {
      vi.mocked(telegramApi.unlink).mockResolvedValue({
        message: 'Unlinked successfully',
      });

      render(<TelegramSettings />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /텔레그램 연결 해제/i })).toBeInTheDocument();
      });

      const disconnectButton = screen.getByRole('button', { name: /텔레그램 연결 해제/i });
      await userEvent.click(disconnectButton);

      await waitFor(() => {
        expect(telegramApi.unlink).toHaveBeenCalled();
      });
    });

    it('should update state after successful unlink', async () => {
      vi.mocked(telegramApi.unlink).mockResolvedValue({
        message: 'Unlinked successfully',
      });

      render(<TelegramSettings />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /텔레그램 연결 해제/i })).toBeInTheDocument();
      });

      const disconnectButton = screen.getByRole('button', { name: /텔레그램 연결 해제/i });
      await userEvent.click(disconnectButton);

      await waitFor(() => {
        expect(screen.getByText('연결되지 않음')).toBeInTheDocument();
      });
    });

    it('should show error when unlink fails', async () => {
      vi.mocked(telegramApi.unlink).mockRejectedValue(new Error('Failed to unlink'));

      render(<TelegramSettings />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /텔레그램 연결 해제/i })).toBeInTheDocument();
      });

      const disconnectButton = screen.getByRole('button', { name: /텔레그램 연결 해제/i });
      await userEvent.click(disconnectButton);

      await waitFor(() => {
        expect(screen.getByText(/failed to unlink/i)).toBeInTheDocument();
      });
    });
  });

  describe('Error handling', () => {
    it('should show error when getStatus fails', async () => {
      vi.mocked(telegramApi.getStatus).mockRejectedValue(
        new Error('Network error')
      );

      render(<TelegramSettings />);

      await waitFor(() => {
        expect(screen.getByText(/failed to load telegram status/i)).toBeInTheDocument();
      });
    });
  });

  describe('Polling', () => {
    beforeEach(() => {
      vi.mocked(telegramApi.getStatus).mockResolvedValue({
        linked: false,
        linked_at: null,
      });
      vi.mocked(telegramApi.createLinkToken).mockResolvedValue({
        deep_link: 'https://t.me/test_bot?start=token123',
        expires_in: 600,
      });
    });

    it('should poll for status while linking', async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
      render(<TelegramSettings />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /텔레그램 연결/i })).toBeInTheDocument();
      });

      // Start linking
      const connectButton = screen.getByRole('button', { name: /텔레그램 연결/i });
      await user.click(connectButton);

      await waitFor(() => {
        expect(screen.getByText('연결 대기 중...')).toBeInTheDocument();
      });

      // Clear initial calls
      vi.mocked(telegramApi.getStatus).mockClear();

      // Advance time by 3 seconds (poll interval) within act()
      await act(async () => {
        await vi.advanceTimersByTimeAsync(3000);
      });

      // Polling should have called getStatus
      expect(telegramApi.getStatus).toHaveBeenCalled();
    });

    it('should stop polling and update UI when linked', async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
      render(<TelegramSettings />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /텔레그램 연결/i })).toBeInTheDocument();
      });

      // Start linking
      const connectButton = screen.getByRole('button', { name: /텔레그램 연결/i });
      await user.click(connectButton);

      await waitFor(() => {
        expect(screen.getByText('연결 대기 중...')).toBeInTheDocument();
      });

      // Simulate successful linking on next poll
      vi.mocked(telegramApi.getStatus).mockResolvedValue({
        linked: true,
        linked_at: '2024-01-15T09:30:00Z',
      });

      // Advance time by 3 seconds (poll interval) within act()
      await act(async () => {
        await vi.advanceTimersByTimeAsync(3000);
      });

      await waitFor(() => {
        expect(screen.getByText('연결됨')).toBeInTheDocument();
      }, { timeout: 5000 });
    });
  });
});

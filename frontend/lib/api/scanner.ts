import { apiClient } from './client';
import { ScanResponse, StockUniverseResponse, ScanTypeEnum } from '@/types/api';

export const scannerApi = {
  scanMarket: async (
    scanType: ScanTypeEnum = 'BUY',
    minConfidence: number = 0.7,
    limit: number = 10
  ): Promise<ScanResponse> => {
    const { data } = await apiClient.get<ScanResponse>(
      `/api/v1/scan?scan_type=${scanType}&min_confidence=${minConfidence}&limit=${limit}`
    );
    return data;
  },

  getUniverse: async (): Promise<StockUniverseResponse> => {
    const { data } = await apiClient.get<StockUniverseResponse>('/api/v1/scan/universe');
    return data;
  },
};

import { apiClient } from './client';

export interface IndicatorScores {
  rsi_score: number;
  macd_score: number;
  volume_score: number;
  trend_score: number;
  bollinger_score: number;
}

export interface StockScoreResponse {
  stock_code: string;
  stock_name: string;
  current_price: number;
  change_pct: number;
  score: number;
  signal: "STRONG_BUY" | "BUY" | "HOLD" | "SELL" | "STRONG_SELL";
  indicator_scores: IndicatorScores;
  reasons: string[];
  analysis_date: string;
}

export const analysisApi = {
  getStockScore: async (stockCode: string): Promise<StockScoreResponse> => {
    const { data } = await apiClient.get(`/api/v1/analysis/stock/${stockCode}/score`);
    return data;
  },

  getRecommendations: async (topN: number = 10): Promise<{ recommendations: StockScoreResponse[]; total: number }> => {
    const { data } = await apiClient.get(`/api/v1/analysis/recommend`, {
      params: { top_n: topN }
    });
    return data;
  }
};

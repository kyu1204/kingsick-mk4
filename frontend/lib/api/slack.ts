import { apiClient } from './client';

export interface SlackStatusResponse {
  configured: boolean;
  webhook_url_masked: string | null;
}

export interface SlackWebhookRequest {
  webhook_url: string;
}

export interface SlackMessageResponse {
  success: boolean;
  message: string;
}

export const slackApi = {
  getStatus: async (): Promise<SlackStatusResponse> => {
    const response = await apiClient.get('/api/v1/settings/slack');
    return response.data;
  },

  saveWebhook: async (request: SlackWebhookRequest): Promise<SlackStatusResponse> => {
    const response = await apiClient.post('/api/v1/settings/slack', request);
    return response.data;
  },

  testWebhook: async (): Promise<SlackMessageResponse> => {
    const response = await apiClient.post('/api/v1/settings/slack/test', {});
    return response.data;
  },

  deleteWebhook: async (): Promise<SlackMessageResponse> => {
    const response = await apiClient.delete('/api/v1/settings/slack');
    return response.data;
  },
};

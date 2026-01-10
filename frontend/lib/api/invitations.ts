/**
 * Invitations API module.
 *
 * Handles invitation management for admin users.
 */

import { apiClient } from './client';

/**
 * Invitation schema from backend.
 */
export interface Invitation {
  id: string;
  code: string;
  invitation_url: string;
  used: boolean;
  used_by_user_id: string | null;
  expires_at: string;
  created_at: string;
  created_by_user_id: string;
}

/**
 * Request to create a new invitation.
 */
export interface CreateInvitationRequest {
  expires_in_days?: number;
}

/**
 * Response containing a list of invitations.
 */
export interface InvitationsResponse {
  invitations: Invitation[];
}

/**
 * Get authorization header from stored token.
 */
function getAuthHeader(): { Authorization: string } | Record<string, never> {
  if (typeof window === 'undefined') return {};
  const token = localStorage.getItem('kingsick_access_token');
  if (!token) return {};
  return { Authorization: `Bearer ${token}` };
}

/**
 * Create a new invitation.
 * Requires admin privileges.
 *
 * @param request - Invitation creation request with optional expiry days
 * @returns Created invitation
 */
export async function createInvitation(
  request: CreateInvitationRequest = {}
): Promise<Invitation> {
  const response = await apiClient.post<Invitation>(
    '/api/v1/invitations/',
    request,
    { headers: getAuthHeader() }
  );
  return response.data;
}

/**
 * List all invitations.
 * Requires admin privileges.
 *
 * @returns List of invitations
 */
export async function listInvitations(): Promise<InvitationsResponse> {
  const response = await apiClient.get<InvitationsResponse>(
    '/api/v1/invitations/',
    { headers: getAuthHeader() }
  );
  return response.data;
}

/**
 * Delete an invitation.
 * Requires admin privileges.
 *
 * @param invitationId - ID of the invitation to delete
 */
export async function deleteInvitation(invitationId: string): Promise<void> {
  await apiClient.delete(`/api/v1/invitations/${invitationId}`, {
    headers: getAuthHeader(),
  });
}

import { UserInterest } from '@/types/news';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

function getAuthHeaders(): HeadersInit {
  const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null;
  const headers: HeadersInit = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  return headers;
}

export const userInterestService = {
  /**
   * Get the current user's saved interests
   * IsAuthenticated endpoint
   */
  async getInterests(): Promise<UserInterest[]> {
    const response = await fetch(`${API_URL}/users/interests/`, {
      headers: getAuthHeaders(),
    });
    if (!response.ok) throw new Error('Failed to fetch interests');
    return response.json();
  },

  /**
   * Save (bulk upsert) a list of interests for the current user
   * IsAuthenticated endpoint
   * @param interests - Array of {interest_type, value, display_name}
   */
  async saveInterests(
    interests: Array<{ interest_type: string; value: string; display_name: string }>
  ) {
    const response = await fetch(`${API_URL}/users/interests/`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify({ interests }),
    });
    if (!response.ok) throw new Error('Failed to save interests');
    return response.json();
  },

  /**
   * Delete a single interest by its primary key
   * IsAuthenticated endpoint
   * @param id - UserInterest primary key
   */
  async deleteInterest(id: number): Promise<void> {
    const response = await fetch(`${API_URL}/users/interests/${id}/`, {
      method: 'DELETE',
      headers: getAuthHeaders(),
    });
    if (!response.ok) throw new Error('Failed to delete interest');
  },
};

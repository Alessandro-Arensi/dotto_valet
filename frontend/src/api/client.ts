import { useAuthStore } from '../stores/authStore';

const API_BASE = '/api';

interface FetchOptions extends RequestInit {
  skipAuth?: boolean;
}

class ApiError extends Error {
  status: number;
  detail: string;
  
  constructor(status: number, detail: string) {
    super(detail);
    this.status = status;
    this.detail = detail;
  }
}

async function fetchApi<T>(
  endpoint: string,
  options: FetchOptions = {}
): Promise<T> {
  const { skipAuth = false, ...fetchOptions } = options;
  
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...fetchOptions.headers,
  };
  
  // Add auth token if available and not skipped
  if (!skipAuth) {
    const token = useAuthStore.getState().token;
    if (token) {
      (headers as Record<string, string>)['Authorization'] = `Bearer ${token}`;
    }
  }
  
  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...fetchOptions,
    headers,
  });
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    
    // Handle unauthorized
    if (response.status === 401) {
      useAuthStore.getState().logout();
    }
    
    throw new ApiError(response.status, error.detail || 'Request failed');
  }
  
  return response.json();
}

// Auth API
export const authApi = {
  login: (phone: string, pin: string) =>
    fetchApi<{
      access_token: string;
      operator: { id: string; name: string; is_admin: boolean };
    }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ phone, pin }),
      skipAuth: true,
    }),
  
  getMe: () =>
    fetchApi<{ id: string; name: string; is_admin: boolean }>('/auth/me'),
};

// Events API
export const eventsApi = {
  list: () => fetchApi<Event[]>('/events'),
  
  getStats: (eventId: string) =>
    fetchApi<EventStats>(`/events/${eventId}/stats`),
  
  getNextSlot: (eventId: string) =>
    fetchApi<NextSlot>(`/events/${eventId}/next-slot`),
  
  // Public
  getAvailability: (slug: string) =>
    fetchApi<EventAvailability>(`/events/${slug}/availability`, { skipAuth: true }),

  // Public reservation (not yet wired in UI)
  reserve: (slug: string, data: PublicReservationRequest) =>
    fetchApi<PublicReservationResponse>(`/events/${slug}/reserve`, {
      method: 'POST',
      body: JSON.stringify({
        phone: data.phone,
        email: data.email,
        newsletter_opt_in: data.newsletter,
      }),
      skipAuth: true,
    }),

  // Walk-in reservation without contact data
  walkin: (slug: string) =>
    fetchApi<PublicReservationResponse>(`/events/${slug}/walkin`, {
      method: 'POST',
      skipAuth: true,
    }),
};

// Checkin API
export const checkinApi = {
  create: (data: CheckinRequest) =>
    fetchApi<CheckinResponse>('/checkin', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  
  checkout: (tokenCode: string) =>
    fetchApi<CheckoutResponse>('/checkout', {
      method: 'POST',
      body: JSON.stringify({ token_code: tokenCode }),
    }),
  
  list: (eventId: string, status: 'active' | 'all' = 'active') =>
    fetchApi<CheckinItem[]>(`/checkins/${eventId}?status=${status}`),
};

// Token API
export const tokenApi = {
  getInfo: (code: string) =>
    fetchApi<TokenInfo>(`/token/${code}`, { skipAuth: true }),
  
  recover: (phone: string, eventId?: string) =>
    fetchApi<TokenRecoverResponse>(
      `/token/recover?phone=${encodeURIComponent(phone)}${eventId ? `&event_id=${eventId}` : ''}`,
      { skipAuth: true }
    ),

  getWalletPass: (code: string) =>
    fetchApi<TokenWalletResponse>(`/token/${code}/wallet`, { skipAuth: true }),
};

// Types
export interface Event {
  id: string;
  name: string;
  slug: string;
  location: string | null;
  start_date: string;
  total_capacity: number;
  is_active: boolean;
}

export interface EventStats {
  event_id: string;
  total_capacity: number;
  checked_in: number;
  reserved: number;
  available: number;
  occupancy_percent: number;
  checkins_last_5min: number;
  suggest_fast_mode: boolean;
}

export interface NextSlot {
  rack_id: string;
  rack_number: number;
  slot_number: number;
  rack_label: string | null;
}

export interface EventAvailability {
  event: {
    name: string;
    slug: string;
    location: string | null;
    start_date: string;
    checkin_opens_at: string | null;
  };
  availability: {
    total: number;
    available: number;
    occupied: number;
    percent: number;
  };
  can_reserve: boolean;
  message: string | null;
}

export interface PublicReservationRequest {
  phone: string;
  email?: string;
  newsletter: boolean;
}

export interface PublicReservationResponse {
  success: boolean;
  token: {
    code: string;
    qr_url: string;
    wallet_url: string;
    /** Posto assegnato (es. "Rastrelliera 1, Slot 3") - presente per walk-in */
    position?: string | null;
  };
  reservation: {
    expires_at: string | null;
    checkin_opens_at: string | null;
  };
  message_sent?: boolean;
}

export interface CheckinRequest {
  token_code: string;
  create_token?: boolean;
  customer_phone?: string;
  customer_email?: string;
  newsletter_opt_in?: boolean;
  physical_token?: boolean;
  auto_position?: boolean;
  rack_id?: string;
  slot_number?: number;
  bike_photo_base64?: string;
}

export interface CheckinResponse {
  success: boolean;
  checkin_id: string;
  token: { code: string; type: string };
  position: {
    rack_number: number;
    slot_number: number;
    rack_label: string | null;
    auto_assigned: boolean;
  };
  customer: { phone_masked: string | null } | null;
  message_sent: boolean;
  warnings: string[];
}

export interface CheckoutResponse {
  success: boolean;
  checkin: {
    position: string;
    checked_in_at: string;
    bike_photo_url: string | null;
  };
  customer: { phone_masked: string | null } | null;
  token_type: string;
}

export interface CheckinItem {
  id: string;
  token_code: string;
  token_type: string;
  rack_number: number;
  rack_label: string | null;
  slot_number: number;
  checked_in_at: string;
  checked_out_at: string | null;
  bike_photo_url: string | null;
  customer_phone: string | null;
}

export interface TokenInfo {
  token: {
    code: string;
    status: string;
    type: string;
  };
  event: {
    name: string;
    location: string | null;
    date: string;
  } | null;
  checkin: {
    position: string;
    checked_in_at: string;
    photo_url: string | null;
  } | null;
}

export interface TokenWalletResponse {
  success: boolean;
  wallet_url?: string;
  message?: string;
}

export interface TokenRecoverResponse {
  success: boolean;
  tokens: Array<{
    code: string;
    qr_url: string;
    status: string;
    event_name: string | null;
  }>;
  message: string;
}



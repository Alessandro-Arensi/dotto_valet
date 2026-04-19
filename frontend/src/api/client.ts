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

  reserve: (slug: string, data: ReservationRequest) =>
    fetchApi<ReservationResponse>(`/events/${slug}/reserve`, {
      method: 'POST',
      body: JSON.stringify(data),
      skipAuth: true,
    }),

  walkin: (slug: string, data: WalkinRequest) =>
    fetchApi<WalkinResponse>(`/events/${slug}/walkin`, {
      method: 'POST',
      body: JSON.stringify(data),
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
};

// Admin API (requires is_admin)
export const adminApi = {
  createEvent: (data: EventCreate) =>
    fetchApi<Event>('/events', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  updateEvent: (id: string, data: EventUpdate) =>
    fetchApi<Event>(`/events/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  deleteEvent: (id: string) =>
    fetchApi<void>(`/events/${id}`, { method: 'DELETE' }),

  listRacks: (eventId: string) =>
    fetchApi<Rack[]>(`/events/${eventId}/racks`),

  createRack: (eventId: string, data: RackCreate) =>
    fetchApi<Rack>(`/events/${eventId}/racks`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  updateRack: (rackId: string, data: RackUpdate) =>
    fetchApi<Rack>(`/racks/${rackId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  deleteRack: (rackId: string) =>
    fetchApi<void>(`/racks/${rackId}`, { method: 'DELETE' }),

  listRacksDetail: (eventId: string) =>
    fetchApi<RackDetail[]>(`/events/${eventId}/racks/detail`),

  blockSlot: (rackId: string, slot_number: number, reason?: string) =>
    fetchApi<SlotBlockItem>(`/racks/${rackId}/blocks`, {
      method: 'POST',
      body: JSON.stringify({ slot_number, reason }),
    }),

  releaseSlot: (rackId: string, slot_number: number) =>
    fetchApi<void>(`/racks/${rackId}/blocks/${slot_number}`, { method: 'DELETE' }),

  reassignCheckin: (checkinId: string) =>
    fetchApi<{
      success: boolean;
      checkin_id: string;
      token_code: string;
      position: {
        rack_number: number;
        slot_number: number;
        rack_label: string | null;
        auto_assigned: boolean;
      };
    }>(`/checkins/${checkinId}/reassign`, { method: 'POST' }),

  listOperators: () => fetchApi<OperatorItem[]>('/operators'),

  createOperator: (data: OperatorCreate) =>
    fetchApi<OperatorItem>('/operators', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  updateOperator: (id: string, data: OperatorUpdate) =>
    fetchApi<OperatorItem>(`/operators/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  deleteOperator: (id: string) =>
    fetchApi<void>(`/operators/${id}`, { method: 'DELETE' }),
};

// Types
export interface Event {
  id: string;
  name: string;
  slug: string;
  location: string | null;
  description?: string | null;
  start_date: string;
  end_date?: string | null;
  checkin_opens_at?: string | null;
  total_capacity: number;
  fast_mode_threshold?: number;
  is_active: boolean;
}

export interface EventCreate {
  name: string;
  slug?: string;  // optional: backend derives from name if omitted
  description?: string;
  location?: string;
  start_date: string;
  end_date?: string;
  checkin_opens_at?: string;
  total_capacity: number;
  fast_mode_threshold?: number;
}

export interface EventUpdate extends Partial<EventCreate> {
  is_active?: boolean;
}

export interface Rack {
  id: string;
  event_id: string;
  rack_number: number;
  slots: number;
  label: string | null;
}

export interface RackCreate {
  rack_number: number;
  slots: number;
  label?: string;
}

export interface RackUpdate extends Partial<RackCreate> {}

export type SlotStatus = 'free' | 'checked_in' | 'blocked';

export interface SlotState {
  slot_number: number;
  status: SlotStatus;
  token_code: string | null;
  block_reason: string | null;
}

export interface RackDetail {
  id: string;
  event_id: string;
  rack_number: number;
  label: string | null;
  slots: number;
  states: SlotState[];
}

export interface SlotBlockItem {
  id: string;
  rack_id: string;
  slot_number: number;
  reason: string | null;
  created_at: string;
  released_at: string | null;
}

export interface OperatorItem {
  id: string;
  name: string;
  phone: string | null;
  email: string | null;
  is_admin: boolean;
  is_active: boolean;
  created_at: string;
}

export interface OperatorCreate {
  name: string;
  phone: string;
  email?: string;
  pin: string;
  is_admin?: boolean;
  is_active?: boolean;
}

export interface OperatorUpdate {
  name?: string;
  phone?: string;
  email?: string;
  pin?: string;
  is_admin?: boolean;
  is_active?: boolean;
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

export interface CheckinRequest {
  token_code: string;
  create_token?: boolean;
  customer_phone?: string;
  customer_email?: string;
  newsletter_opt_in?: boolean;
  event_id?: string;
  physical_token?: boolean;
  auto_position?: boolean;
  rack_id?: string;
  slot_number?: number;
  bike_description?: string;
}

export interface ReservationRequest {
  first_name: string;
  last_name: string;
  phone?: string;
  email?: string;
  newsletter_opt_in?: boolean;
}

export interface ReservationResponse {
  success: boolean;
  token: {
    code: string;
    qr_url: string;
  };
  reservation: {
    expires_at: string | null;
    checkin_opens_at: string | null;
    customer_name: string;
  };
}

export interface WalkinRequest {
  first_name: string;
  last_name: string;
}

export interface WalkinResponse {
  success: boolean;
  token: {
    code: string;
    qr_url: string;
  };
  position: {
    rack_id: string;
    rack_number: number;
    rack_label: string | null;
    slot_number: number;
  };
  customer_name: string;
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
    bike_description: string | null;
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
  bike_description: string | null;
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
    bike_description: string | null;
  } | null;
}

export interface TokenRecoverResponse {
  success: boolean;
  tokens: Array<{
    code: string;
    qr_url: string;
    status: string;
    event_name: string | null;
    customer_name: string | null;
    phone_masked: string | null;
    checked_in_at: string | null;
    position: {
      rack_number: number;
      rack_label: string | null;
      slot_number: number;
      display: string;
    } | null;
  }>;
  message: string;
  message_sent?: boolean;
}



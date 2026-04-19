import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface ActiveEventState {
  eventId: string | null;
  eventName: string | null;
  eventSlug: string | null;
  setActive: (id: string, name: string, slug: string) => void;
  clear: () => void;
}

/**
 * Which event the operator is currently working on.
 * Persisted in localStorage so refresh keeps the selection.
 */
export const useActiveEventStore = create<ActiveEventState>()(
  persist(
    (set) => ({
      eventId: null,
      eventName: null,
      eventSlug: null,
      setActive: (eventId, eventName, eventSlug) =>
        set({ eventId, eventName, eventSlug }),
      clear: () => set({ eventId: null, eventName: null, eventSlug: null }),
    }),
    { name: 'dotto-active-event' }
  )
);

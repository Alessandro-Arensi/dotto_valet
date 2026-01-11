import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface Operator {
  id: string;
  name: string;
  is_admin: boolean;
}

interface AuthState {
  token: string | null;
  operator: Operator | null;
  isAuthenticated: boolean;
  
  login: (token: string, operator: Operator) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      operator: null,
      isAuthenticated: false,
      
      login: (token, operator) => {
        set({
          token,
          operator,
          isAuthenticated: true,
        });
      },
      
      logout: () => {
        set({
          token: null,
          operator: null,
          isAuthenticated: false,
        });
      },
    }),
    {
      name: 'dotto-auth',
    }
  )
);



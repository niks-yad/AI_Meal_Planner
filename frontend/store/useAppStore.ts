'use client';

import { create } from 'zustand';
import axios from 'axios';

interface HealthDataPayload {
  heightFeet: number;
  heightInches: number;
  weight: number;
  activityLevel: string;
}

interface MealPlanData {
  meal_plan: Array<{
    day: string;
    breakfast: string;
    lunch: string;
    dinner: string;
    snacks: string;
  }>;
}

interface GroceryItem {
  item: string;
  quantity: string;
  category: string;
  link: string | null;
  protein: string;
  carbs: string;
  fats: string;
  cals: string;
}

interface AppState {
  mealPlan: MealPlanData | null;
  groceryList: GroceryItem[] | null;
  sessionId: string | null;
  loading: boolean;
  error: string | null;
  
  generateMealPlan: (healthData: HealthDataPayload) => Promise<void>;
  generateGroceryList: () => Promise<void>;
  clearGroceryList: () => Promise<void>;
  clearAll: () => void;
}

const API_BASE_URL = 'http://127.0.0.1:8000';

export const useAppStore = create<AppState>((set, get) => ({
  mealPlan: null,
  groceryList: null,
  sessionId: null,
  loading: false,
  error: null,

  generateMealPlan: async (healthData) => {
    set({ loading: true, error: null, mealPlan: null, groceryList: null, sessionId: null });
    try {
      const requestBody = {
        ...healthData,
        days: 7, // Default to 7 days
      };
      const response = await axios.post<MealPlanData>(`${API_BASE_URL}/mealplan`, requestBody);
      if (response.status === 200) {
        set({ mealPlan: response.data });
      } else {
        set({ error: `Failed to generate meal plan: ${response.statusText}` });
      }
    } catch (err: any) {
      console.error("Error generating meal plan:", err);
      let errorMessage = "An unexpected error occurred";
      if (err.response && err.response.data) {
        errorMessage = `Backend Error: ${JSON.stringify(err.response.data, null, 2)}`;
      } else if (err.message) {
        errorMessage = err.message;
      }
      set({ error: errorMessage });
    } finally {
      set({ loading: false });
    }
  },

  generateGroceryList: async () => {
    const currentMealPlan = get().mealPlan;
    if (!currentMealPlan) {
      set({ error: "No meal plan available to generate grocery list." });
      return;
    }

    set({ loading: true, error: null });
    try {
      const response = await axios.post<{ session_id: string; grocery_list: GroceryItem[] }>(`${API_BASE_URL}/grocery-list`, currentMealPlan);
      if (response.status === 200) {
        set({ groceryList: response.data.grocery_list, sessionId: response.data.session_id });
      } else {
        set({ error: `Failed to generate grocery list: ${response.statusText}` });
      }
    } catch (err: any) {
      console.error("Error generating grocery list:", err);
      set({ error: err.response?.data?.detail || err.message || "An unexpected error occurred" });
    } finally {
      set({ loading: false });
    }
  },

  clearGroceryList: async () => {
    const currentSessionId = get().sessionId;
    if (currentSessionId) {
      try {
        await axios.delete(`${API_BASE_URL}/grocery-list/${currentSessionId}`);
        console.log(`Grocery list for session ${currentSessionId} deleted from backend.`);
      } catch (err: any) {
        console.error("Error deleting grocery list from backend:", err);
        set({ error: err.response?.data?.detail || err.message || "Failed to clear grocery list from backend" });
      }
    }
    set({ groceryList: null, sessionId: null });
  },

  clearAll: () => {
    set({ mealPlan: null, groceryList: null, sessionId: null, error: null });
  },
}));
'use client';

import React from 'react';
import HealthForm from '../components/HealthForm';
import MealPlan from '../components/MealPlan';
import GroceryList from '../components/GroceryList';
import { useAppStore } from '../store/useAppStore';

export default function Home() {
  const { 
    mealPlan, 
    groceryList, 
    loading, 
    error, 
    generateMealPlan, 
    generateGroceryList, 
    clearGroceryList, 
    clearAll 
  } = useAppStore();

  return (
    <main className="flex min-h-screen flex-col items-center p-6 bg-gray-100 text-gray-800">
      <header className="w-full max-w-2xl text-center mb-8">
        <h1 className="text-4xl font-bold text-blue-600">Personal Meal Planner</h1>
      </header>

      <HealthForm onSubmit={generateMealPlan} isLoading={loading} />

      {loading && <p className="mt-4 text-lg font-semibold">Generating...</p>}
      {error && <p className="mt-4 text-red-600 font-semibold">Error: {error}</p>}

      {mealPlan && (
        <MealPlan 
          plan={mealPlan} 
          onGenerateGroceryList={generateGroceryList} 
          isLoadingGroceryList={loading} 
        />
      )}

      {groceryList && (
        <div className="w-full max-w-2xl mt-8">
          <GroceryList list={groceryList} />
          <div className="flex justify-center mt-4">
            <button 
              onClick={clearGroceryList} 
              className="bg-red-500 hover:bg-red-700 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline mr-2"
            >
              Clear Grocery List
            </button>
            <button 
              onClick={clearAll} 
              className="bg-gray-500 hover:bg-gray-700 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline"
            >
              Start Over
            </button>
          </div>
        </div>
      )}
    </main>
  );
}

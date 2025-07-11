'use client';

import React from 'react';

interface MealPlanProps {
  plan: { meal_plan: Array<{
    day: string;
    breakfast: string;
    lunch: string;
    dinner: string;
    snacks: string;
  }> };
  onGenerateGroceryList: () => void;
  isLoadingGroceryList: boolean;
}

const MealPlan: React.FC<MealPlanProps> = ({
  plan,
  onGenerateGroceryList,
  isLoadingGroceryList,
}) => {
  if (!plan || !plan.meal_plan || plan.meal_plan.length === 0) {
    return null;
  }

  return (
    <div className="bg-white p-6 rounded-lg shadow-md w-full max-w-2xl mx-auto mt-8">
      <h2 className="text-2xl font-bold mb-6 text-gray-800 text-center">Your 7-Day Meal Plan</h2>
      <div className="space-y-6">
        {plan.meal_plan.map((dayPlan, index) => (
          <div key={index} className="border border-gray-200 rounded-lg p-4">
            <h3 className="text-xl font-semibold mb-3 text-gray-700">{dayPlan.day}</h3>
            <ul className="list-disc list-inside text-gray-600 space-y-1">
              <li><strong>Breakfast:</strong> {dayPlan.breakfast}</li>
              <li><strong>Lunch:</strong> {dayPlan.lunch}</li>
              <li><strong>Dinner:</strong> {dayPlan.dinner}</li>
              <li><strong>Snacks:</strong> {dayPlan.snacks}</li>
            </ul>
          </div>
        ))}
      </div>
      <div className="flex justify-center mt-8">
        <button
          onClick={onGenerateGroceryList}
          disabled={isLoadingGroceryList}
          className="bg-green-500 hover:bg-green-700 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isLoadingGroceryList ? 'Generating Grocery List...' : 'Generate Grocery List'}
        </button>
      </div>
    </div>
  );
};

export default MealPlan;

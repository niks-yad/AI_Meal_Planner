import React from 'react';
import './MealPlan.css';

const MealPlan = ({ plan, onGenerateGroceryList }) => {
  if (!plan || !plan.meal_plan) {
    return null;
  }

  return (
    <div className="meal-plan-container">
      <h2>Your 7-Day Meal Plan</h2>
      <div className="meal-plan-grid">
        {plan.meal_plan.map((day, index) => (
          <div key={index} className="meal-plan-day">
            <h3>{day.day}</h3>
            <p><strong>Breakfast:</strong> {day.breakfast}</p>
            <p><strong>Lunch:</strong> {day.lunch}</p>
            <p><strong>Dinner:</strong> {day.dinner}</p>
            <p><strong>Snacks:</strong> {day.snacks}</p>
          </div>
        ))}
      </div>
      <button onClick={onGenerateGroceryList} className="generate-grocery-list-button">
        Generate Grocery List
      </button>
    </div>
  );
};

export default MealPlan;

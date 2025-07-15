"use client";
import React from "react";


export default function Form_Page_1() {
  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);

    // Build a plain object matching backend HealthData model
    const health_data = {
      heightFeet: Number(formData.get("heightFeet")),
      heightInches: Number(formData.get("heightInches")),
      weight: Number(formData.get("weight")),
      activityLevel: formData.get("activityLevel"),
    };
    const days = Number(formData.get("days"));
    const recipe_limit = Number(formData.get("recipe_limit"));

    await fetch("http://localhost:8000/mealplan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ health_data, days, recipe_limit }),
    });
  }

  return (
    <div>
      <div>
        <h2>Form Page 1</h2>
      </div>
      <form onSubmit={handleSubmit}>
        <div>
          <label htmlFor="heightFeet">Height (feet):</label>
          <input type="number" id="heightFeet" name="heightFeet" required min={0} defaultValue={5} />
        </div>
        <div>
          <label htmlFor="heightInches">Height (inches):</label>
          <input type="number" id="heightInches" name="heightInches" required min={0} max={11} defaultValue={10} />
        </div>
        <div>
          <label htmlFor="weight">Weight (lbs):</label>
          <input type="number" id="weight" name="weight" required min={0} defaultValue={150} />
        </div>
        <div>
          <label htmlFor="activityLevel">Activity Level:</label>
          <select id="activityLevel" name="activityLevel" required defaultValue="sedentary">
            <option value="sedentary">Sedentary</option>
            <option value="light">Lightly Active</option>
            <option value="moderate">Moderately Active</option>
            <option value="active">Active</option>
            <option value="very active">Very Active</option>
          </select>
        </div>
        <div>
          <label htmlFor="days">Number of Days:</label>
          <input type="number" id="days" name="days" required min={1} max={14} defaultValue={7} />
        </div>
        <div>
          <label htmlFor="recipe_limit">Recipe Limit:</label>
          <input type="number" id="recipe_limit" name="recipe_limit" required min={1} max={50} defaultValue={10} />
        </div>
        <button type="submit">Submit</button>
      </form>
    </div>
  );
}
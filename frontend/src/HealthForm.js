import React, { useState } from 'react';
import './HealthForm.css';

const HealthForm = ({ onMealPlanGenerated, onLoadingChange }) => {
  const [healthData, setHealthData] = useState({
    heightFeet: '',
    heightInches: '',
    weight: '',
    activityLevel: 'sedentary',
  });

  const handleChange = (e) => {
    const { name, value } = e.target;
    setHealthData({ ...healthData, [name]: value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    onLoadingChange(true);
    onMealPlanGenerated(null);

    const payload = {
      heightFeet: parseInt(healthData.heightFeet || '0', 10),
      heightInches: parseInt(healthData.heightInches || '0', 10),
      weight: parseInt(healthData.weight || '0', 10),
      activityLevel: healthData.activityLevel,
    };

    try {
      const response = await fetch('http://localhost:8001/mealplan', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      onMealPlanGenerated(result);
    } catch (error) {
      console.error('Error sending data to backend:', error);
      alert('Failed to generate meal plan.');
    } finally {
      onLoadingChange(false);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <h2>Your Health Profile</h2>
      <div>
        <label>Height</label>
        <input
          type="number"
          name="heightFeet"
          placeholder="Feet"
          value={healthData.heightFeet}
          onChange={handleChange}
          required
        />
        <input
          type="number"
          name="heightInches"
          placeholder="Inches"
          value={healthData.heightInches}
          onChange={handleChange}
          required
        />
      </div>
      <div>
        <label>Weight (lbs)</label>
        <input
          type="number"
          name="weight"
          placeholder="Pounds"
          value={healthData.weight}
          onChange={handleChange}
          required
        />
      </div>
      <div>
        <label>Activity Level</label>
        <select
          name="activityLevel"
          value={healthData.activityLevel}
          onChange={handleChange}
        >
          <option value="sedentary">Sedentary</option>
          <option value="lightly_active">Lightly Active</option>
          <option value="moderately_active">Moderately Active</option>
          <option value="very_active">Very Active</option>
          <option value="extra_active">Extra Active</option>
        </select>
      </div>
      <button type="submit">Generate Meal Plan</button>
    </form>
  );
};

export default HealthForm;


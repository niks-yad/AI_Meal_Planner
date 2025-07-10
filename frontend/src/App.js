import React, { useState } from 'react';
import HealthForm from './HealthForm';
import MealPlan from './MealPlan';
import GroceryList from './GroceryList'; // Import the new component
import './App.css';

function App() {
  const [mealPlan, setMealPlan] = useState(null);
  const [groceryList, setGroceryList] = useState(null); // New state for grocery list
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [sessionId, setSessionId] = useState(null); // New state for session ID

  const handleMealPlanGenerated = (plan) => {
    setMealPlan(plan);
    setGroceryList(null); // Clear grocery list when a new meal plan is generated
    setSessionId(null); // Clear session ID as well
  };

  const handleGenerateGroceryList = async () => {
    setLoading(true);
    setError(null);
    try {
      // Step 1: Request grocery list generation and get session ID
      const generateResponse = await fetch('http://localhost:8001/grocery-list', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(mealPlan),
      });
      if (!generateResponse.ok) {
        throw new Error(`HTTP error! status: ${generateResponse.status}`);
      }
      const generateData = await generateResponse.json();
      const newSessionId = generateData.session_id;
      setSessionId(newSessionId);

      // Step 2: Fetch the generated grocery list using the session ID
      const fetchResponse = await fetch(`http://localhost:8001/grocery-list/${newSessionId}`);
      if (!fetchResponse.ok) {
        throw new Error(`HTTP error! status: ${fetchResponse.status}`);
      }
      const fetchData = await fetchResponse.json();
      setGroceryList(fetchData.grocery_list);

    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleClearGroceryList = async () => {
    if (sessionId) {
      try {
        const response = await fetch(`http://localhost:8001/grocery-list/${sessionId}`, {
          method: 'DELETE',
        });
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        console.log(`Grocery list for session ${sessionId} deleted.`);
      } catch (e) {
        console.error("Error deleting grocery list:", e);
      }
    }
    setGroceryList(null);
    setSessionId(null);
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>Personal Meal Planner</h1>
      </header>
      <main>
        <HealthForm 
          onMealPlanGenerated={handleMealPlanGenerated} 
          onLoadingChange={setLoading} 
        />
        {loading && <p>Generating...</p>}
        {error && <p className="error-message">Error: {error}</p>}
        {mealPlan && (
          <MealPlan 
            plan={mealPlan} 
            onGenerateGroceryList={handleGenerateGroceryList} 
          />
        )}
        {groceryList && (
          <>
            <GroceryList list={groceryList} />
            <button onClick={handleClearGroceryList} className="clear-grocery-list-button">
              Clear Grocery List
            </button>
          </>
        )}
      </main>
    </div>
  );
}

export default App;
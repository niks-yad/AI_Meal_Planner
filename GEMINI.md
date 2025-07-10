# AI Meal Planner - Intended Workflow

This document outlines the intended user flow and data processing steps for the AI Meal Planner project.

## User Flow

1.  **User Inputs Basic Info:** The user provides their health data and preferences.
2.  **Get Recipes from Database:** The application attempts to retrieve existing recipes from a database (to be provided later) that match user preferences.
3.  **Create a Recipe using Gemini:** If suitable recipes are not found in the database, Gemini AI generates a custom recipe based on user input.
4.  **Extract JSON of All Products:** Gemini extracts a JSON list of all products used in the generated recipes, calculated for portioning and weekly requirements.
5.  **Send JSON to Gemini for Data Extraction:** The extracted JSON is sent to Gemini with a specific "data extraction prompt" (to be provided later) for further refinement.
6.  **Store Result in a Temporary Database:** The refined JSON result is stored in a temporary database.
7.  **Generate Grocery List Table:** The application uses the data from the temporary database to generate the grocery list table.
8.  **Populate the Grocery List Table:** The grocery list table is populated with the extracted and refined product information.
9.  **Delete the Temporary Database:** After the grocery list is displayed, the temporary database is deleted.
10. **Repeat for the Next Request:** The process is ready to repeat for subsequent user requests.

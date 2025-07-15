"""
Walmart Meal Planner API - A FastAPI application that generates personalized meal plans
and grocery lists using Google's Gemini AI model.

User Flow:
1. User submits health data (height, weight, activity level)
2. System generates personalized meal plan using AI
3. User can extract grocery list from meal plan
4. System stores grocery list with session ID for later retrieval
5. User can retrieve or delete stored grocery lists
"""

import json
import os
import logging
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
import threading

# Third-party imports
import google.generativeai as genai
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator

# Local imports
import database

# Load environment variables from .env file
load_dotenv()

# In-memory cache for recipes, thread-safe
global recipes_cache 
global recipes_cache_lock 
global session_id 
recipes_cache = {}
recipes_cache_lock = threading.Lock()
session_id = str(uuid.uuid4())


# Configure logging for debugging and monitoring
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# PYDANTIC MODELS - Define data structures for API requests/responses
# ============================================================================

class HealthData(BaseModel):
    """
    Model for user health information input.
    Used to calculate personalized meal plans based on user's physical characteristics.
    """
    heightFeet: int = Field(..., ge=3, le=8, description="Height in feet (3-8)")
    heightInches: int = Field(..., ge=0, le=11, description="Height in inches (0-11)")
    weight: int = Field(..., ge=50, le=500, description="Weight in pounds (50-500)")
    activityLevel: str = Field(..., description="Activity level: sedentary, lightly_active, moderately_active, very_active, extra_active")
    days: int = Field(7, ge=1, le=14, description="Number of days for meal plan")
    
    # unnecessary
    # @validator('activityLevel')
    # def validate_activity_level(cls, v):
    #     """Ensure activity level is one of the accepted values"""
    #     valid_levels = ['sedentary', 'lightly_active', 'moderately_active', 'very_active', 'extra_active']
    #     if v not in valid_levels:
    #         raise ValueError(f'Activity level must be one of: {", ".join(valid_levels)}')
    #     return v

class DayMeal(BaseModel):
    """Model for a single day's meal plan"""
    day: str = Field(..., description="Day of the week")
    breakfast: str = Field(..., description="Breakfast meal description")
    lunch: str = Field(..., description="Lunch meal description")
    dinner: str = Field(..., description="Dinner meal description")
    snacks: str = Field(..., description="Snacks description")

class MealPlanResponse(BaseModel):
    """Model for meal plan API response"""
    meal_plan: List[DayMeal] = Field(..., description="List of daily meal plans")
    generated_at: datetime = Field(default_factory=datetime.now, description="When the meal plan was generated")

class GroceryItem(BaseModel):
    """Model for individual grocery items"""
    item: str = Field(..., description="Name of the grocery item")
    quantity: str = Field(..., description="Quantity needed (e.g., '2 lbs', '3 items')")
    category: str = Field(..., description="Category (Produce, Protein, Dairy, etc.)")
    link: Optional[str] = Field(None, description="Store product link (if available)")
    protein: str = Field(..., description="Protein content in grams")
    carbs: str = Field(..., description="Carbohydrate content in grams")
    fats: str = Field(..., description="Fat content in grams")
    calories: str = Field(..., description="Calorie content")

class GroceryListResponse(BaseModel):
    """Model for grocery list API response"""
    grocery_list: List[GroceryItem] = Field(..., description="List of grocery items")
    session_id: str = Field(..., description="Unique session identifier")
    created_at: datetime = Field(default_factory=datetime.now, description="When the grocery list was created")

class MealPlanInput(BaseModel):
    """Model for accepting meal plan data to extract grocery list"""
    meal_plan: List[Dict[str, Any]] = Field(..., description="Meal plan data")
    
    class Config:
        extra = "allow"  # Allow additional fields that might be present

# ============================================================================
# UTILITY FUNCTIONS - Helper functions for AI integration and data processing
# ============================================================================

def get_gemini_model():
    """
    Initialize and return Google Gemini AI model instance.
    
    Returns:
        GenerativeModel: Configured Gemini model for text generation
        
    Raises:
        ValueError: If GEMINI_API_KEY environment variable is not set
    """
    # Retrieve API key from environment variables
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        logger.error("Gemini API key not found in environment variables")
        raise ValueError("Gemini API key not found. Please set the GEMINI_API_KEY environment variable.")
    
    # Configure the Gemini API with the provided key
    genai.configure(api_key=api_key)
    
    # Return the flash model (faster, suitable for meal planning tasks)
    return genai.GenerativeModel('gemini-1.5-flash')

def safe_json_parse(text: str, expected_key: str, max_retries: int = 2) -> dict:
    """
    Safely parse JSON from AI response with retry logic.
    
    Args:
        text: Raw text response from AI
        expected_key: The key that should be present in the JSON root
        max_retries: Maximum number of correction attempts
        
    Returns:
        dict: Parsed JSON object
        
    Raises:
        ValueError: If JSON parsing fails after all retries
    """
    # First attempt: Clean and parse the response
    cleaned_text = text.strip().replace('```json', '').replace('```', '')
    
    # Try to extract JSON object from the text
    json_start = cleaned_text.find('{')
    json_end = cleaned_text.rfind('}')
    
    if json_start != -1 and json_end != -1:
        json_text = cleaned_text[json_start:json_end + 1]
        
        try:
            # Attempt to parse the JSON
            parsed_json = json.loads(json_text)
            
            # Validate that expected key exists
            if expected_key in parsed_json:
                logger.info(f"Successfully parsed JSON with key '{expected_key}'")
                return parsed_json
            else:
                logger.warning(f"Expected key '{expected_key}' not found in JSON")
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed: {e}")
            
    # If we reach here, parsing failed
    raise ValueError(f"Failed to parse valid JSON with expected key '{expected_key}'")

def calculate_calories_needed(height_feet: int, height_inches: int, weight: int, activity_level: str) -> int:
    """
    Calculate estimated daily calorie needs using Mifflin-St Jeor equation.
    
    Args:
        height_feet: Height in feet
        height_inches: Height in inches  
        weight: Weight in pounds
        activity_level: Activity level string
        
    Returns:
        int: Estimated daily calories needed
    """
    # Convert height to total inches, then to centimeters
    total_inches = (height_feet * 12) + height_inches
    height_cm = total_inches * 2.54
    
    # Convert weight to kilograms
    weight_kg = weight * 0.453592
    
    # Assume average age of 30 and male for baseline calculation
    # BMR = 10 * weight(kg) + 6.25 * height(cm) - 5 * age + 5
    bmr = 10 * weight_kg + 6.25 * height_cm - 5 * 30 + 5
    
    # Activity level multipliers
    activity_multipliers = {
        'sedentary': 1.2,
        'lightly_active': 1.375,
        'moderately_active': 1.55,
        'very_active': 1.725,
        'extra_active': 1.9
    }
    
    # Calculate total daily energy expenditure
    multiplier = activity_multipliers.get(activity_level, 1.55)
    daily_calories = int(bmr * multiplier)
    
    logger.info(f"Calculated daily calories needed: {daily_calories}")
    return daily_calories

def get_mcp_completion(prompt: str, model: str = "gemini-1.5-flash", max_tokens: int = 1024) -> str:
    """
    Send a prompt to the local MCP server and return the generated text.
    """
    mcp_url = "http://localhost:8001/v1/completions"  # MCP server endpoint (adjust port if needed)
    payload = {
        "model": model,
        "prompt": prompt,
        "parameters": {"max_tokens": max_tokens}
    }
    try:
        response = requests.post(mcp_url, json=payload, timeout=60)
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["text"]
    except Exception as e:
        logger.error(f"MCP completion error: {e}")
        raise HTTPException(status_code=500, detail=f"MCP server error: {str(e)}")

# ============================================================================
# FASTAPI APPLICATION SETUP
# ============================================================================

# Initialize FastAPI application
app = FastAPI(
    title="Walmart Meal Planner API",
    description="Generate personalized meal plans and grocery lists using AI",
    version="1.0.0"
)

# Add CORS middleware to allow frontend connections
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React development server
    allow_credentials=True,  # Allow cookies and authorization headers
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

# ============================================================================
# DEPENDENCY INJECTION - Shared dependencies for endpoints
# ============================================================================

def get_ai_model():
    """Dependency to provide AI model instance to endpoints"""
    return get_gemini_model()

# ============================================================================
# API ENDPOINTS - Core application functionality
# ============================================================================

@app.get("/")
async def root():
    """
    Health check endpoint.
    Returns basic API information to verify service is running.
    """
    return {
        "message": "Walmart Meal Planner API",
        "version": "1.0.0",
        "status": "healthy"
    }

# @app.get("/health")
# async def health_check():
#     """
#     Detailed health check endpoint.
#     Verifies all system components are functioning.
#     """
#     try:
#         # Test database connection
#         database_status = "healthy"  # Assume healthy for now
        
#         # Test AI model initialization
#         model = get_gemini_model()
#         ai_status = "healthy" if model else "unhealthy"
        
#         return {
#             "status": "healthy",
#             "timestamp": datetime.now().isoformat(),
#             "components": {
#                 "database": database_status,
#                 "ai_model": ai_status
#             }
#         }
#     except Exception as e:
#         logger.error(f"Health check failed: {e}")
#         raise HTTPException(status_code=503, detail="Service unavailable")

@app.post("/mealplan", response_model=MealPlanResponse)
async def generate_meal_plan(
    data: HealthData
):
    logger.info(f"Generating meal plan for user: height={data.heightFeet}'{data.heightInches}", weight={data.weight}lbs, activity={data.activityLevel})
    
    try:
        # Calculate estimated daily calorie needs
        daily_calories = calculate_calories_needed(
            data.heightFeet,
            data.heightInches,
            data.weight,
            data.activityLevel
        )


        # Fetch recipes from the /recipes endpoint
        recipes_response = requests.get("http://localhost:8002/recipes?limit=50", timeout=10)
        recipes_response.raise_for_status()
        
        # recipes_data = recipes_response.json().get("recipes", [])
        recipes_data = [
            {
                "name": r.get("name"),
                "ingredients": r.get("ingredients"),
                "id": r.get("id")
            }
            for r in recipes_response.json().get("recipes", [])
        ]

        with recipes_cache_lock:
            recipes_cache[session_id] = recipes_data

        # Create detailed prompt for AI meal plan generation, including recipes
        prompt = f"""
        You are a meal planning assistant. Here is a list of available recipes:
        {json.dumps(recipes_data, indent=2)}

        Create a personalized {data.days}-day meal plan for a person with the following profile:
        - Height: {data.heightFeet} feet, {data.heightInches} inches
        - Weight: {data.weight} lbs
        - Activity Level: {data.activityLevel.replace('_', ' ')}
        - Estimated Daily Calories: {daily_calories}

        Guidelines:
        1. Use only the provided recipes.
        2. Ensure meals are balanced with proper macronutrients.
        3. Reuse ingredients across days to minimize waste and cost.
        4. Consider food expiration dates when planning.
        5. Include variety while being practical.

        Return ONLY a valid JSON object with this exact structure:
        {{
          "meal_plan": [
            {{
              "day": "Monday",
              "breakfast": "Recipe name or description from the provided list",
              "lunch": "Recipe name or description from the provided list", 
              "dinner": "Recipe name or description from the provided list",
              "snacks": "Healthy snack options"
            }}
          ]
        }}

        Do not include any markdown formatting, explanations, or text outside the JSON.
        """

        # Generate meal plan using MCP server
        logger.info("Requesting meal plan generation from MCP server")
        ai_response = get_mcp_completion(prompt)
        meal_plan_data = safe_json_parse(ai_response, "meal_plan")
        
        # Validate the structure and convert to Pydantic models
        daily_meals = [DayMeal(**day_data) for day_data in meal_plan_data["meal_plan"]]
        
        # Create response object
        meal_plan_response = MealPlanResponse(meal_plan=daily_meals)
        
        logger.info(f"Successfully generated {len(daily_meals)}-day meal plan")
        return meal_plan_response
        
    except Exception as e:
        logger.error(f"Error generating meal plan: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate meal plan: {str(e)}"
        )

@app.post("/grocery-list", response_model=GroceryListResponse)
async def create_grocery_list(
    meal_plan_input: MealPlanInput
):
    """
    Extract and organize grocery list from a meal plan.
    
    User Flow:
    1. User submits meal plan data
    2. AI analyzes meals and extracts ingredients
    3. System consolidates quantities and categorizes items
    4. System generates session ID and stores grocery list
    5. Returns organized grocery list with nutritional information
    
    Args:
        meal_plan_input: Meal plan data to extract groceries from
        model: AI model instance (injected dependency)
        
    Returns:
        GroceryListResponse: Organized grocery list with session ID
    """
    logger.info("Extracting grocery list from meal plan")
    
    try:
        # Convert meal plan to JSON string for AI processing
        meal_plan_json = json.dumps(meal_plan_input.meal_plan, indent=2)
                # Fetch recipes from the /recipes endpoint
        recipes_response = requests.get("http://localhost:8002/recipes?limit=50", timeout=10)
        recipes_response.raise_for_status()
        
        # recipes_data = recipes_response.json().get("recipes", [])
        recipes_data = [
            {
                "name": r.get("name"),
                "ingredients": r.get("ingredients"),
                "id": r.get("id")
            }
            for r in recipes_response.json().get("recipes", [])
        ]

        # Create detailed prompt for grocery list extraction
        prompt = f"""
        Analyze this meal plan and create a comprehensive grocery list:
        
        {recipes_data}
        
        Instructions:
        1. Extract all unique ingredients needed for the entire meal plan
        2. Consolidate quantities using standard US grocery units (lbs, oz, cups, items)
        3. Categorize items (Produce, Protein, Dairy & Alternatives, Pantry, Beverages)
        4. For each item, provide nutritional information per typical serving
        5. Do not include store links (they cannot be verified)
        
        Return ONLY a valid JSON object with this exact structure:
        {{
          "grocery_list": [
            {{
              "item": "Chicken Breast",
              "quantity": "2 lbs",
              "category": "Protein",
              "link": null,
              "protein": "25g",
              "carbs": "0g", 
              "fats": "3g",
              "calories": "165"
            }}
          ]
        }}
        
        Do not include any markdown formatting, explanations, or text outside the JSON.
        """
        
        logger.info("Requesting grocery list extraction from MCP server")
        ai_response = get_mcp_completion(prompt)
        grocery_data = safe_json_parse(ai_response, "grocery_list")
        
        # Validate and convert to Pydantic models
        grocery_items = [GroceryItem(**item_data) for item_data in grocery_data["grocery_list"]]
        
        # Generate unique session ID for storing the grocery list
        session_id = str(uuid.uuid4())
        
        # Store grocery list in database with session ID
        logger.info(f"Storing grocery list with session ID: {session_id}")
        database.insert_grocery_list(session_id, grocery_data)
        
        # Create response object
        grocery_response = GroceryListResponse(
            grocery_list=grocery_items,
            session_id=session_id
        )
        
        logger.info(f"Successfully created grocery list with {len(grocery_items)} items")
        return grocery_response
        
    except Exception as e:
        logger.error(f"Error creating grocery list: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create grocery list: {str(e)}"
        )

@app.get("/grocery-list/{session_id}")
async def get_grocery_list(session_id: str):
    """
    Retrieve a previously generated grocery list by session ID.
    
    User Flow:
    1. User provides session ID from previous grocery list creation
    2. System queries database for stored grocery list
    3. Returns grocery list data or 404 if not found
    
    Args:
        session_id: Unique identifier for the grocery list
        
    Returns:
        dict: Grocery list data with metadata
    """
    logger.info(f"Retrieving grocery list for session: {session_id}")
    
    try:
        # Query database for grocery list
        grocery_list = database.get_grocery_list(session_id)
        
        if not grocery_list:
            logger.warning(f"Grocery list not found for session: {session_id}")
            raise HTTPException(
                status_code=404,
                detail=f"Grocery list not found for session: {session_id}"
            )
        
        logger.info(f"Successfully retrieved grocery list for session: {session_id}")
        return {
            "session_id": session_id,
            "grocery_list": grocery_list,
            "retrieved_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error retrieving grocery list: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve grocery list: {str(e)}"
        )

@app.delete("/grocery-list/{session_id}")
async def delete_grocery_list(session_id: str):
    """
    Delete a stored grocery list by session ID.
    
    User Flow:
    1. User provides session ID of grocery list to delete
    2. System removes grocery list from database
    3. Returns confirmation message
    
    Args:
        session_id: Unique identifier for the grocery list to delete
        
    Returns:
        dict: Confirmation message
    """
    logger.info(f"Deleting grocery list for session: {session_id}")
    
    try:
        # Remove grocery list from database
        database.delete_grocery_list(session_id)
        
        logger.info(f"Successfully deleted grocery list for session: {session_id}")
        return {
            "message": f"Grocery list for session {session_id} has been deleted",
            "deleted_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error deleting grocery list: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete grocery list: {str(e)}"
        )

# ============================================================================
# APPLICATION STARTUP - Initialize services and dependencies
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """
    Initialize application services on startup.
    Verifies all dependencies are available.
    """
    logger.info("Starting Walmart Meal Planner API...")
    
    try:
        # Test AI model initialization
        model = get_gemini_model()
        logger.info("✓ AI model initialized successfully")
        
        # Test database connection (if applicable)
        # database.test_connection()
        logger.info("✓ Database connection verified")
        
        logger.info("🚀 Meal Planner API startup complete")
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """
    Cleanup resources on application shutdown.
    """
    logger.info("Shutting down Meal Planner API...")
    # Add any cleanup logic here
    logger.info("✓ Shutdown complete")

# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    # Run the application with uvicorn server
    uvicorn.run(
        "main:app",  # Module and app instance
        host="0.0.0.0",  # Listen on all interfaces
        port=8000,  # Default port
        reload=True,  # Auto-reload on code changes
        log_level="info"  # Logging level
    )
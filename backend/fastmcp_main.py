import os
import logging
import json
import re
from typing import List
from pydantic import BaseModel, Field
from fastmcp import FastMCP
from dotenv import load_dotenv
import psycopg2
import psycopg2.extras
import google.generativeai as genai
from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Load environment variables
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("MealPlannerMCP")

# Initialize FastMCP
mcp = FastMCP("MealPlannerMCP")

# Initialize FastAPI app
app = FastAPI(docs_url="/docs", redoc_url="/redoc", openapi_url="/openapi.json")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class HealthData(BaseModel):
    heightFeet: int = Field(..., ge=0)
    heightInches: int = Field(..., ge=0, le=11)
    weight: int = Field(..., ge=0)
    activityLevel: str  # e.g. "sedentary", "light", "moderate", "active"

class DayMeal(BaseModel):
    day: str
    breakfast: str
    lunch: str
    dinner: str
    snacks: str

class MealPlanResponse(BaseModel):
    meal_plan: List[DayMeal]

# Activity multipliers
activity_multipliers = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "active": 1.725,
    "very active": 1.9,
}

# --- Plain Python core functions ---

def calc_calories(heightFeet: int, heightInches: int, weight: int, activityLevel: str) -> int:
    logger.info(f"Calculating calories needed: {heightFeet}ft {heightInches}in, {weight}lbs, activity: {activityLevel}")
    height_cm = (heightFeet * 12 + heightInches) * 2.54
    weight_kg = weight * 0.453592
    bmr = 10 * weight_kg + 6.25 * height_cm - 5 * 30 + 5  # assuming male, age=30
    multiplier = activity_multipliers.get(activityLevel.lower(), 1.2)
    calories = int(bmr * multiplier)
    logger.info(f"Calculated calories: {calories}")
    return calories

def fetch_recipes(limit: int) -> List[dict]:
    logger.info(f"Fetching {limit} recipes from Postgres")
    PG_HOST = os.getenv("PG_HOST", "localhost")
    PG_PORT = os.getenv("PG_PORT", "5432")
    PG_DB = os.getenv("PG_DB", "recipes_beta_1")
    PG_USER = os.getenv("PG_USER", "niks")
    PG_PASS = os.getenv("PG_PASS", "NiksforAIMPDB*19")

    with psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        dbname=PG_DB,
        user=PG_USER,
        password=PG_PASS,
    ) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute("SELECT data FROM recipes LIMIT %s;", (limit,))
            rows = cursor.fetchall()
    recipes = [row["data"] for row in rows]
    logger.info(f"Fetched {len(recipes)} recipes")
    return recipes

def generate_meal_plan_plain(health_data: HealthData, days: int, recipes: List[dict]) -> MealPlanResponse:
    logger.info(f"Generating meal plan for {days} days with health data: {health_data}")
    calories = calc_calories(
        health_data.heightFeet,
        health_data.heightInches,
        health_data.weight,
        health_data.activityLevel,
    )

    prompt = f"""
You are a nutritionist AI. Create a balanced meal plan for {days} days.

User health data:
- Height: {health_data.heightFeet}ft {health_data.heightInches}in
- Weight: {health_data.weight} lbs
- Activity level: {health_data.activityLevel}
- Estimated daily calories: {calories}

Available recipes (JSON format):
{recipes}

Return JSON only, no markdown fencing, in this structure:
{{
  "meal_plan": [
    {{
      "day": "Monday",
      "breakfast": "...",
      "lunch": "...",
      "dinner": "...",
      "snacks": "..."
    }}
  ]
}}
"""

    logger.info("Calling Gemini generative AI for meal plan...")
    model = genai.GenerativeModel("gemini-2.5-pro")
    response = model.generate_content(prompt)
    content = response.text.strip()

    try:
        # Clean any backticks
        content_clean = re.sub(r"```(json)?", "", content).strip()
        plan_json = json.loads(content_clean)
        meal_plan_response = MealPlanResponse.parse_obj(plan_json)
        logger.info("Meal plan generated successfully")
        return meal_plan_response
    except Exception as e:
        logger.error(f"Failed to parse meal plan JSON: {e}")
        return MealPlanResponse(meal_plan=[])

# --- MCP decorated wrappers ---

@mcp.tool()
def calculate_calories_needed(heightFeet: int, heightInches: int, weight: int, activityLevel: str) -> int:
    return calc_calories(heightFeet, heightInches, weight, activityLevel)

@mcp.resource("recipes://{limit}")
def get_recipes(limit: int):
    return fetch_recipes(limit)

@mcp.prompt()
def generate_meal_plan(health_data: HealthData, days: int, recipes: List[dict]) -> MealPlanResponse:
    return generate_meal_plan_plain(health_data, days, recipes)

# MCP function to run whole flow (optional)
@mcp.tool()
def full_meal_plan_flow(health_data: HealthData, days: int, recipe_limit: int):
    calories = calculate_calories_needed(
        health_data.heightFeet,
        health_data.heightInches,
        health_data.weight,
        health_data.activityLevel,
    )
    recipes = get_recipes(recipe_limit)
    meal_plan = generate_meal_plan(health_data, days, recipes)
    return meal_plan

# --- FastAPI endpoints ---

from fastapi import HTTPException

@app.post("/mealplan")
async def mealplan_endpoint(
    heightFeet: int = Body(...),
    heightInches: int = Body(...),
    weight: int = Body(...),
    activityLevel: str = Body(...),
    days: int = Body(...),
    recipe_limit: int = Body(10),
):
    health_data = HealthData(
        heightFeet=heightFeet,
        heightInches=heightInches,
        weight=weight,
        activityLevel=activityLevel,
    )
    recipes = fetch_recipes(recipe_limit)
    result = generate_meal_plan_plain(health_data, days, recipes)
    return JSONResponse(content=result.dict())

@app.get("/recipes/{limit}")
async def recipes_endpoint(limit: int):
    recipes = fetch_recipes(limit)
    return JSONResponse(content={"recipes": recipes})

if __name__ == "__main__":
    logger.info("Starting MealPlannerMCP server...")
    mcp.run(app)

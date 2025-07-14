from fastapi import FastAPI, HTTPException
import psycopg2
import json
import requests
from pydantic import BaseModel

app = FastAPI()

DB_NAME = "recipes_beta_1"
DB_USER = "niks"
DB_PASS = "nikhil19"
DB_HOST = "localhost"  # or your remote IP if not local
DB_PORT = 5432

# Assuming mcp_server runs on port 8001
MCP_SERVER_URL = "http://localhost:8001/v1/completions"

class UserPreferences(BaseModel):
    dietary_restrictions: list[str] = []
    allergies: list[str] = []
    health_goals: str = ""
    favorite_foods: list[str] = []
    disliked_foods: list[str] = []
    meal_type: str = ""
    num_meals: int = 1

def get_db_connection():
    conn = psycopg2.connect(
        dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT
    )
    return conn

@app.get("/recipes")
def read_recipes(limit: int = 30):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT data FROM recipes LIMIT %s;", (limit,))
        rows = cur.fetchall()
        recipes = [row[0] for row in rows]
        return {"recipes": recipes}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

# @app.post("/generate_recipe_with_gemini")
# async def generate_recipe_with_gemini(preferences: UserPreferences):
#     try:
#         # Construct a prompt for Gemini based on user preferences
#         prompt = f"""Generate a {preferences.meal_type} recipe for {preferences.num_meals} serving(s) based on the following preferences:
# Dietary Restrictions: {', '.join(preferences.dietary_restrictions) if preferences.dietary_restrictions else 'None'}
# Allergies: {', '.join(preferences.allergies) if preferences.allergies else 'None'}
# Health Goals: {preferences.health_goals if preferences.health_goals else 'None'}
# Favorite Foods: {', '.join(preferences.favorite_foods) if preferences.favorite_foods else 'None'}
# Disliked Foods: {', '.join(preferences.disliked_foods) if preferences.disliked_foods else 'None'}

# Please provide a detailed recipe including ingredients and instructions. If no specific meal type is provided, generate a general recipe.
# """

#         # Send the prompt to the MCP server
#         mcp_response = requests.post(
#             MCP_SERVER_URL,
#             json={
#                 "model": "gemini-pro",  # Or another appropriate Gemini model
#                 "prompt": prompt,
#                 "parameters": {"max_tokens": 1024} # Example parameter
#             }
#         )
#         mcp_response.raise_for_status()  # Raise an exception for HTTP errors
#         gemini_output = mcp_response.json()

#         return {"generated_recipe": gemini_output.get("choices", [{}])[0].get("text", "No recipe generated.")}

#     except requests.exceptions.RequestException as e:
#         raise HTTPException(status_code=500, detail=f"Error communicating with MCP server: {e}")
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))


import os
import json
import logging
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def _get_gemini_model():
    """Initializes and returns the Gemini model."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("Gemini API key not found. Please set the GEMINI_API_KEY environment variable.")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel('gemini-1.5-flash')

def generate_meal_plan_from_ai(health_data):
    """
    Generates a 7-day meal plan using the Gemini API based on user health data.
    """
    logger.info(f"generate_meal_plan_from_ai called with: heightFeet={health_data.heightFeet}, heightInches={health_data.heightInches}, weight={health_data.weight}, activityLevel={health_data.activityLevel}")
    model = _get_gemini_model()
    prompt = f"""
    Based on the following health profile for a person in the USA, create a personalized 7-day meal plan:
    - Height: {health_data.heightFeet} feet, {health_data.heightInches} inches
    - Weight: {health_data.weight} lbs
    - Activity Level: {health_data.activityLevel.replace('_', ' ')}
    Your task is to generate a simple, healthy, and balanced meal plan with common American foods and standard portion sizes.
    Make sure to reuse groceries whever possible as we want to minimize waste and cost. Some foods expire withint days, so less is more but dont compromise on quality.
    The JSON object should have a single key \"meal_plan\" which is an array of 7 day objects.
    Each day object should have the following keys: \"day\", \"breakfast\", \"lunch\", \"dinner\", and \"snacks\".
    The value for breakfast, lunch, dinner, and snacks should be a string describing the meal.
    Ensure the entire output is a single, valid JSON object. Do not include any text or markdown formatting. The response string should be a valid JSON response, and nothing else. Make sure it is valid JSON.
    """
    try:
        logger.info("Sending prompt to Gemini for meal plan generation.")
        response = model.generate_content(prompt)
        logger.info(f"Raw Gemini response: {response.text}")
        cleaned_response = response.text.strip().replace('```json', '').replace('```', '')
        logger.info(f"Cleaned Gemini response: {cleaned_response}")
        # Validate JSON using a Gemini correction layer if needed
        try:
            meal_plan_json = json.loads(cleaned_response)
            logger.info("Successfully parsed meal plan JSON on first attempt.")
        except json.JSONDecodeError as e:
            logger.error(f"Initial meal plan JSON parsing failed: {e}. Attempting correction with Gemini.")
            correction_prompt = f"""
            The following text was intended to be a JSON object, but it failed to parse.\nPlease correct it to be a valid JSON object, ensuring it strictly follows the specified format for a meal_plan.\nDo not include any conversational text, markdown formatting (like ```json), or extra characters outside the JSON object.\n\nOriginal problematic text:\n{cleaned_response}\n\nExpected JSON format (root object with 'meal_plan' key, which is an array of 7 day objects):\n{{\n  \"meal_plan\": [\n    {{\n      \"day\": \"Monday\",\n      \"breakfast\": \"...\",\n      \"lunch\": \"...\",\n      \"dinner\": \"...\",\n      \"snacks\": \"...\"\n    }}\n  ]\n}}\n"""
            correction_response = model.generate_content(correction_prompt)
            logger.info(f"Gemini correction response: {correction_response.text}")
            corrected_response_text = correction_response.text.strip()
            json_start = corrected_response_text.find('{')
            json_end = corrected_response_text.rfind('}')
            if json_start != -1 and json_end != -1:
                final_cleaned_response = corrected_response_text[json_start : json_end + 1]
                logger.info(f"Final cleaned corrected response: {final_cleaned_response}")
            else:
                logger.error("Corrected AI response still does not contain a valid JSON object.")
                raise ValueError("Corrected AI response still does not contain a valid JSON object.")
            meal_plan_json = json.loads(final_cleaned_response)
        return meal_plan_json
    except Exception as e:
        logger.error(f"Error generating meal plan with Gemini: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None



def extract_grocery_list_from_ai(meal_plan_text):
    """
    Extracts a grocery list from a meal plan using the Gemini API, including Tesco Ireland links and macros.
    """
    model = _get_gemini_model()
    prompt = f"""
    Analyze the following 7-day meal plan and extract a consolidated grocery list.

    Meal Plan:
    {meal_plan_text}

    Your task is to:
    1. Identify all unique ingredients required for the entire week.
    2. Consolidate the quantities. Use standard US grocery units (e.g., lbs, oz, cups, or by item count like "2 apples").
    3. Categorize the items (e.g., "Produce", "Protein", "Dairy & Alternatives", "Pantry").
    4. For each item, search for it on "Tesco Ireland" and find a working product link on tesco.ie/groceries/product/.
    5. For each item, extract its protein, carbs, fats, and calories.
    6. Provide the output as a single, valid JSON object. The root object should have a single key "grocery_list" which is an array of item objects.
    7. Each item object must have the following keys: "item" (the name of the ingredient), "quantity" (a string with the amount and unit), "category", "link" (the Tesco product link, or null if not found), "protein" (in grams), "carbs" (in grams), "fats" (in grams), and "cals" (calories).

    Example format:
    {{
      "grocery_list": [
        {{
          "item": "Chicken Breast",
          "quantity": "2 lbs",
          "category": "Protein",
          "link": "https://www.tesco.ie/groceries/product/details/some-chicken-link",
          "protein": "50g",
          "carbs": "0g",
          "fats": "5g",
          "cals": "250"
        }},
        {{
          "item": "Apple",
          "quantity": "3",
          "category": "Produce",
          "link": "https://www.tesco.ie/groceries/product/details/some-apple-link",
          "protein": "0.5g",
          "carbs": "14g",
          "fats": "0.3g",
          "cals": "52"
        }}
      ]
    }}

    Ensure the entire output is a single, valid JSON object without any surrounding text or markdown.
    """
    try:
        logger.info("Sending prompt to Gemini for grocery list extraction.")
        response = model.generate_content(prompt)
        logger.info(f"Raw Gemini response: {response.text}")
        response_text = response.text.strip()

        try:
            # Attempt to parse the initial response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}')
            if json_start != -1 and json_end != -1:
                cleaned_response = response_text[json_start : json_end + 1]
                logger.info(f"Cleaned Gemini grocery response: {cleaned_response}")
            else:
                logger.error("No valid JSON object found in AI response.")
                raise ValueError("No valid JSON object found in AI response.")
            grocery_list_json = json.loads(cleaned_response)
            logger.info("Successfully parsed grocery list JSON on first attempt.")
        except json.JSONDecodeError as e:
            logger.error(f"Initial JSON parsing failed: {e}. Attempting correction with Gemini.")
            # If parsing fails, send a correction prompt to Gemini
            correction_prompt = f"""
            The following text was intended to be a JSON object, but it failed to parse.
            Please correct it to be a valid JSON object, ensuring it strictly follows the specified format for a grocery_list.
            Do not include any conversational text, markdown formatting (like ```json), or extra characters outside the JSON object.

            Original problematic text:
            {response_text}

            Expected JSON format (root object with "grocery_list" key, which is an array of item objects):
            {{
              "grocery_list": [
                {{
                  "item": "Chicken Breast",
                  "quantity": "2 lbs",
                  "category": "Protein",
                  "link": "https://www.tesco.ie/groceries/product/details/some-chicken-link",
                  "protein": "50g",
                  "carbs": "0g",
                  "fats": "5g",
                  "cals": "250"
                }},
                {{
                  "item": "Apple",
                  "quantity": "3",
                  "category": "Produce",
                  "link": "https://www.tesco.ie/groceries/product/details/some-apple-link",
                  "protein": "0.5g",
                  "carbs": "14g",
                  "fats": "0.3g",
                  "cals": "52"
                }}
              ]
            }}
            """
            correction_response = model.generate_content(correction_prompt)
            logger.info(f"Gemini correction response: {correction_response.text}")
            corrected_response_text = correction_response.text.strip()

            # Attempt to parse the corrected response
            json_start_corrected = corrected_response_text.find('{')
            json_end_corrected = corrected_response_text.rfind('}')
            if json_start_corrected != -1 and json_end_corrected != -1:
                final_cleaned_response = corrected_response_text[json_start_corrected : json_end_corrected + 1]
                logger.info(f"Final cleaned corrected grocery response: {final_cleaned_response}")
            else:
                logger.error("Corrected AI response still does not contain a valid JSON object.")
                raise ValueError("Corrected AI response still does not contain a valid JSON object.")
            grocery_list_json = json.loads(final_cleaned_response)
        return grocery_list_json
    except Exception as e:
        logger.error(f"Error extracting grocery list with Gemini: {e}")
        return None
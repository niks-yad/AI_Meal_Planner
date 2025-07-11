# Walmart Meal Planner - MCP Enhanced Tech Stack

## Updated Architecture Overview

### **Frontend**
- **Next.js 14** with App Router
- **TypeScript** for type safety
- **Tailwind CSS** for styling
- **React Hook Form** for form management
- **Zustand** for state management (lightweight alternative to Redux)

### **Backend**
- **FastAPI** (Python) - Main API server
- **FastMCP 2.0** - MCP Server implementation
- **PostgreSQL** - Primary database
- **Redis** - Caching and session management

### **AI Integration**
- **Google Generative AI** (Gemini) - Meal planning
- **MCP Client** - Standardized AI tool connectivity
- **MCP Server** - Expose meal planning tools to AI agents

## Simplified Dependencies

### **Python Backend (`requirements.txt`)**
```
# Core FastAPI
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
python-dotenv==1.0.0

# Database
asyncpg==0.29.0
sqlalchemy[asyncio]==2.0.23
alembic==1.12.1

# AI & MCP
google-generativeai==0.3.2
fastmcp==2.0.1
mcp==1.0.0

# Authentication & Security
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6

# Utilities
httpx==0.25.2
python-dateutil==2.8.2
```

### **Frontend (`package.json`)**
```json
{
  "dependencies": {
    "next": "14.0.3",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "typescript": "^5.3.0",
    "@types/react": "^18.2.0",
    "@types/node": "^20.9.0",
    "tailwindcss": "^3.3.0",
    "react-hook-form": "^7.47.0",
    "zustand": "^4.4.0",
    "axios": "^1.6.0"
  }
}
```

## MCP Implementation Strategy

### **1. MCP Server Setup (FastAPI)**
FastMCP 2.0 provides a complete toolkit for working with the MCP ecosystem and can be integrated natively with FastAPI. Here's the structure:

```python
# mcp_server.py
from fastmcp import FastMCP
from fastapi import FastAPI
import google.generativeai as genai

app = FastAPI()
mcp = FastMCP("walmart-meal-planner")

@mcp.tool()
async def generate_meal_plan(
    goal: str,
    lifestyle: str,
    dietary_requirements: str,
    days: int = 7
) -> dict:
    """Generate a personalized meal plan based on user preferences"""
    # AI meal planning logic here
    pass

@mcp.tool()
async def extract_grocery_list(meal_plan: dict) -> list:
    """Extract grocery items from a meal plan"""
    # Grocery extraction logic
    pass

@mcp.tool()
async def search_walmart_products(items: list) -> list:
    """Search for Walmart products based on grocery items"""
    # Walmart API integration
    pass

# Expose MCP tools alongside regular FastAPI endpoints
app.include_router(mcp.router)
```

### **2. Database Schema with MCP Context**
```sql
-- Enhanced schema for MCP integration
CREATE TABLE mcp_sessions (
    session_id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(user_id),
    context_data JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP
);

CREATE TABLE mcp_tool_calls (
    call_id UUID PRIMARY KEY,
    session_id UUID REFERENCES mcp_sessions(session_id),
    tool_name VARCHAR(100),
    parameters JSONB,
    result JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### **3. MCP Client Integration (Next.js)**
```typescript
// lib/mcp-client.ts
class MCPClient {
  private baseUrl: string;
  
  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  async generateMealPlan(preferences: UserPreferences) {
    const response = await fetch(`${this.baseUrl}/mcp/tools/generate_meal_plan`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(preferences)
    });
    return response.json();
  }

  async getGroceryList(mealPlan: MealPlan) {
    const response = await fetch(`${this.baseUrl}/mcp/tools/extract_grocery_list`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ meal_plan: mealPlan })
    });
    return response.json();
  }
}
```

## Key MCP Benefits for This Project

### **1. Standardized AI Tool Connectivity**
MCP provides a standardized way to connect AI models to external tools and data sources, making your meal planning system:
- **Interoperable**: Works with Claude, GPT, and other AI agents
- **Extensible**: Easy to add new tools and data sources
- **Maintainable**: Standard protocol reduces custom integration code

### **2. Enhanced Resume Value**
- **Cutting-edge Technology**: OpenAI officially adopted MCP in March 2025
- **Industry Standard**: Shows knowledge of latest AI integration patterns
- **Protocol Implementation**: Demonstrates ability to work with open standards

### **3. Walmart Integration Benefits**
```python
# Example: MCP tools for Walmart integration
@mcp.tool()
async def walmart_product_search(query: str, location: str) -> list:
    """Search Walmart products with location-based pricing"""
    pass

@mcp.tool()
async def walmart_cart_add(product_ids: list, quantities: list) -> dict:
    """Add items to Walmart cart"""
    pass

@mcp.tool()
async def walmart_nutrition_lookup(product_id: str) -> dict:
    """Get detailed nutrition information"""
    pass
```

## Development Phases

### **Phase 1: Core MCP Setup (Week 1-2)**
- [ ] FastAPI + FastMCP integration
- [ ] Basic MCP tools (meal planning, grocery extraction)
- [ ] PostgreSQL schema setup
- [ ] Next.js MCP client integration

### **Phase 2: AI Integration (Week 3-4)**
- [ ] Gemini API integration with MCP tools
- [ ] User preference handling
- [ ] Meal plan generation and storage
- [ ] Basic grocery list functionality

### **Phase 3: Walmart Integration (Week 5-6)**
- [ ] Mock Walmart API integration
- [ ] Product search and pricing
- [ ] Cart management
- [ ] Nutrition data integration

### **Phase 4: Production Ready (Week 7-8)**
- [ ] Authentication and authorization
- [ ] Error handling and logging
- [ ] Performance optimization
- [ ] Mobile responsiveness

## Project Structure
```
walmart-meal-planner/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   └── mcp/
│   │   ├── models/
│   │   ├── services/
│   │   └── core/
│   ├── mcp_server.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   ├── components/
│   │   ├── lib/
│   │   └── types/
│   ├── package.json
│   └── next.config.js
└── docs/
    └── mcp-integration.md
```

## Why This Stack Works

1. **Simplicity**: Minimal dependencies, focused on core functionality
2. **Scalability**: FastAPI + PostgreSQL handles growth well
3. **Modern**: MCP is like "USB for AI integrations" - industry standard
4. **Resume-Worthy**: Shows knowledge of latest AI integration patterns
5. **Walmart-Ready**: Easy to integrate with existing Walmart APIs

This approach positions your project as a modern, standardized AI application that can easily integrate with various AI agents and external systems through MCP.
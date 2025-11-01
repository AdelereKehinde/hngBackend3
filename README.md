🧠 Fifth Grade Students Optimizer API (A2A Agent)
🧩 Description

Fifth Grade Students Optimizer is an AI-powered text simplifier agent designed to help rewrite complex text into a clear, friendly, and easy-to-understand format for 5th-grade students.

It uses the A2A Protocol and can be integrated directly into the Telex platform.
When triggered, the agent receives a message, processes it using AI, and returns a simplified version of the text that children can easily understand.

⚙️ Core Features

✅ Simplifies any input text into a child-friendly version
✅ Built on FastAPI with A2A protocol compatibility
✅ Uses Gemini AI API for text optimization
✅ Returns results in JSON-RPC (A2A) format
✅ Health check endpoint for easy monitoring
✅ Clean modular structure (ready for Telex integration)

🧾 Example Use Case

Teachers can use it to explain difficult topics in simple language

EdTech platforms can integrate it to generate child-friendly study materials

AI chatbots can use it to adapt language levels automatically for young learners

📂 Project Structure
fifth_grade_optimizer/
│
├── main.py                # FastAPI entry point (A2A-compatible)
├── .env                   # Environment variables (Gemini API key, port)
├── models/
│   └── a2a.py             # A2A protocol data models
└── agents/
    └── optimizer_agent.py # Core AI logic for text simplification

🧩 Example Request (JSON-RPC)
{
  "jsonrpc": "2.0",
  "id": "001",
  "method": "message/send",
  "params": {
    "message": {
      "role": "user",
      "parts": [
        {"kind": "text", "text": "Explain how photosynthesis works in simple words."}
      ]
    }
  }
}

🧩 Example Response
{
  "jsonrpc": "2.0",
  "id": "001",
  "result": {
    "id": "task_001",
    "contextId": "ctx_123",
    "status": {
      "state": "completed",
      "message": {
        "role": "agent",
        "parts": [
          {"kind": "text", "text": "Photosynthesis is how plants make food using sunlight, water, and air."}
        ]
      }
    }
  }
}

🧠 How It Works

The user sends a message with a block of text.

The optimizer agent uses the Gemini AI API to rewrite it in a simpler way.

The agent responds using the A2A message format, ready for use by Telex or other A2A clients.

🧰 Installation

Clone the repository and install dependencies:

git clone https://github.com/yourusername/fifth-grade-optimizer.git
cd fifth-grade-optimizer
pip install -r requirements.txt


Or if using pyproject.toml:

pip install -e .

⚙️ Environment Setup (.env)
PORT=5001
GEMINI_API_KEY=your_free_gemini_api_key_here

🚀 Run the Server
uvicorn main:app --host 0.0.0.0 --port 5001

✅ Health Check

Visit:

GET /health


Response:

{"status": "healthy", "agent": "fifth_grade_optimizer"}

💡 Integration with Telex

The API endpoint:

POST /a2a/optimizer


Accepts A2A-compliant JSON-RPC requests and can be directly connected to the Telex platform for message-based AI interactions.

🧩 Example Prompt

“Explain gravity like you’re talking to a 10-year-old.”

🟢 Response:

“Gravity is what makes things fall down instead of floating away. It’s like Earth’s invisible magnet that pulls everything toward it.”

👨‍💻 Author

DevVoyager
AI Developer | Python & FastAPI Enthusiast

Slack Username : AdelereKehinde, @AdelereK

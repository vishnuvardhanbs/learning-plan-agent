from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from google import genai
import os
import json

app = FastAPI()

client = genai.Client(
    vertexai=True,
    project=os.getenv("GOOGLE_CLOUD_PROJECT"),
    location=os.getenv("GOOGLE_CLOUD_LOCATION")
)

class LearningRequest(BaseModel):
    topic: str = Field(..., example="Machine Learning")
    weekly_hours: int = Field(..., example=8)


def get_ui_html():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Learning Plan Agent</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 900px;
                margin: 40px auto;
                padding: 20px;
            }
            input, button {
                width: 100%;
                padding: 12px;
                margin: 10px 0;
                border-radius: 8px;
                border: 1px solid #ccc;
                font-size: 16px;
            }
            button {
                cursor: pointer;
                font-weight: bold;
            }
            .week-card {
                margin-top: 20px;
                padding: 20px;
                border: 1px solid #ddd;
                border-radius: 12px;
            }
            ul {
                margin-top: 5px;
            }
        </style>
    </head>
    <body>
        <h1>🚀 Learning Plan Agent</h1>

        <input id="topic" placeholder="Enter topic (e.g. Machine Learning)">
        <input id="hours" type="number" placeholder="Weekly hours">

        <button onclick="generatePlan()">Generate Plan</button>

        <div id="output"></div>

        <script>
        async function generatePlan() {
            const topic = document.getElementById("topic").value.trim();
            const hours = Number(document.getElementById("hours").value);

            if (!topic || !hours) {
                document.getElementById("output").innerHTML =
                    "<p>Please enter both topic and weekly hours.</p>";
                return;
            }

            document.getElementById("output").innerHTML = "<p>Generating plan...</p>";

            try {
                const response = await fetch("/plan", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        topic: topic,
                        weekly_hours: hours
                    })
                });

                const data = await response.json();

                let outputHtml = `
                    <h2>📚 ${data.topic} Learning Plan</h2>
                    <p><strong>Weekly Hours:</strong> ${data.weekly_hours}</p>
                `;

                const plan = data.learning_plan;

                if (!plan || typeof plan !== "object") {
                    outputHtml += "<p>Could not generate structured plan.</p>";
                } else {
                    for (const [week, details] of Object.entries(plan)) {
                        if (!details || typeof details !== "object") continue;

                        const goal = details.goal || "Not available";
                        const topics = Array.isArray(details.topics)
                            ? details.topics
                            : [];
                        const task = details.practical_task || "Not available";

                        outputHtml += `
                            <div class="week-card">
                                <h3>${week.replace("_", " ").toUpperCase()}</h3>
                                <p><strong>Goal:</strong> ${goal}</p>
                                <p><strong>Topics:</strong></p>
                                <ul>
                                    ${topics.map(t => `<li>${t}</li>`).join("")}
                                </ul>
                                <p><strong>Practical Task:</strong> ${task}</p>
                            </div>
                        `;
                    }
                }

                document.getElementById("output").innerHTML = outputHtml;

            } catch (error) {
                document.getElementById("output").innerHTML =
                    "<p>Error: " + error.message + "</p>";
            }
        }
        </script>
    </body>
    </html>
    """


@app.get("/", response_class=HTMLResponse)
def home():
    return get_ui_html()


@app.get("/ui", response_class=HTMLResponse)
def ui():
    return get_ui_html()


@app.post("/plan")
def create_plan(request: LearningRequest):
    prompt = f"""
    Create a 6-week learning roadmap in VALID JSON format only.

    Topic: {request.topic}
    Weekly study time: {request.weekly_hours} hours

    Return ONLY valid JSON in this exact format:

    {{
      "week_1": {{
        "goal": "...",
        "topics": ["...", "..."],
        "practical_task": "..."
      }},
      "week_2": {{
        "goal": "...",
        "topics": ["...", "..."],
        "practical_task": "..."
      }},
      "week_3": {{
        "goal": "...",
        "topics": ["...", "..."],
        "practical_task": "..."
      }},
      "week_4": {{
        "goal": "...",
        "topics": ["...", "..."],
        "practical_task": "..."
      }},
      "week_5": {{
        "goal": "...",
        "topics": ["...", "..."],
        "practical_task": "..."
      }},
      "week_6": {{
        "goal": "...",
        "topics": ["...", "..."],
        "practical_task": "..."
      }}
    }}

    No markdown, no explanation, JSON only.
    """

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    try:
        cleaned_text = response.text.strip()

        if cleaned_text.startswith("```json"):
            cleaned_text = cleaned_text.replace("```json", "", 1)
        if cleaned_text.startswith("```"):
            cleaned_text = cleaned_text.replace("```", "", 1)
        if cleaned_text.endswith("```"):
            cleaned_text = cleaned_text[:-3]

        cleaned_text = cleaned_text.strip()
        plan_json = json.loads(cleaned_text)

    except Exception as e:
        plan_json = {
            "error": str(e),
            "raw_output": response.text
        }

    return {
        "topic": request.topic,
        "weekly_hours": request.weekly_hours,
        "learning_plan": plan_json
    }
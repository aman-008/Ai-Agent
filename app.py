import os
import json
import requests
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
import streamlit as st
import streamlit.components.v1 as components

load_dotenv()
client = OpenAI()



# --- Available tool functions ---

def get_weather(city: str):
    url = f"https://wttr.in/{city}?format=%C+%t"
    response = requests.get(url)
    if response.status_code == 200:
        return f"The weather in {city} is {response.text}."
    return "Something went wrong"


def run_command(command: str):
    import subprocess
    try:
        result = subprocess.run(command, shell=True,
                                capture_output=True, text=True, timeout=10)
        return result.stdout.strip() or result.stderr.strip()
    except Exception as e:
        return f"Error running command: {e}"


available_tools = {
    "get_weather": get_weather,
    "run_command": run_command
}

# --- SYSTEM PROMPT guiding the AI ---
SYSTEM_PROMPT = """
You are an AI assistant specialized in building simple web apps like todo lists, calculators, and others.
You will follow the start, plan, action, observe steps.
You can generate code files: index.html, styles.css, app.js as needed.
You must output JSON with the format:

{
  "step": "plan" | "action" | "observe" | "output",
  "content": "string",
  "function": "function_name_if_action",
  "input": "input_param_if_action"
}

Available tools:
- get_weather(city): returns weather info.
- run_command(cmd): runs shell command and returns output.

Also, you can generate the full files content in the "output" step as a JSON dictionary like:
{
  "step": "output",
  "content": "Here is your app code.",
  "files": {
    "index.html": "...",
    "styles.css": "...",
    "app.js": "..."
  }
}

After files are generated, display the app code and preview it inline.
"""

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

st.title("🧠 Web Apps Builder Devta")

user_input = st.text_input("Ask me to build a simple web app or query:")


def process_agent_query(query):
    st.session_state.messages.append({"role": "user", "content": query})

    while True:
        response = client.chat.completions.create(
            model="gpt-4o",
            response_format={"type": "json_object"},
            messages=st.session_state.messages
        )
        content = response.choices[0].message.content
        st.session_state.messages.append(
            {"role": "assistant", "content": content})

        parsed = json.loads(content)
        step = parsed.get("step")

        if step == "plan":
            st.info(f"🧠 PLAN: {parsed.get('content')}")
            continue

        elif step == "action":
            func = parsed.get("function")
            inp = parsed.get("input")
            st.info(f"🛠️ ACTION: Calling {func} with input: {inp}")
            if func in available_tools:
                output = available_tools[func](inp)
                st.success(f"🛠️ OUTPUT: {output}")
                st.session_state.messages.append(
                    {"role": "user", "content": json.dumps({"step": "observe", "output": output})})
            else:
                st.error(f"⚠️ Unknown tool requested: {func}")
            continue

        elif step == "output":
            st.success(f"🤖 OUTPUT: {parsed.get('content')}\n")
            files = parsed.get("files")
            if files:
                st.write("### Generated Files:")
                for fname, fcontent in files.items():
                    st.code(fcontent, language="html" if fname.endswith(
                        ".html") else "css" if fname.endswith(".css") else "javascript")

                # If index.html exists, attempt inline preview:
                html = files.get("index.html", "")
                css = files.get("styles.css", "")
                js = files.get("app.js", "")

                # Combine all for inline preview
                combined_html = f"""
                <html>
                <head>
                <style>{css}</style>
                </head>
                <body>
                {html}
                <script>{js}</script>
                </body>
                </html>
                """
                st.write("### App Preview:")
                components.html(combined_html, height=600, scrolling=True)

            break

        else:
            st.warning("⚠️ Unhandled step or format.")
            break


if user_input:
    process_agent_query(user_input)

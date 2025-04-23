import streamlit as st
import anthropic
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()ZZ

# Init API

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),  # ← vervang dit met jouw DeepSeek sleutel
    base_url="https://api.deepseek.com/v1"  # ← belangrijk!
)
# Claude Agent functies
def agent_1(prompt):
    user_input = f"""Je bent een product owner en schrijf een user story vanuit eindgebruikersperspectief. Geef een eerste voorstel gebaseerd op de volgende input.

Input:
{prompt}
"""
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": user_input}],
        max_tokens=1000,
        temperature=0.7,
    )
    return response.choices[0].message.content

def agent_2(prompt, agent1_output):
    user_input = f"""Je bent een senior developer en evalueert en verbetert de user story vanuit technisch perspectief. Geef feedback op het voorstel van de product owner waar nodig.

Input:
{prompt}

Voorstel van Agent 1:
{agent1_output}
"""
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": user_input}],
        max_tokens=1000,
        temperature=0.7,
    )
    return response.choices[0].message.content

def agent_3_arbiter(prompt, agent1_output, agent2_output):
    user_input = f"""Je bent een software tester , Vergelijk het originele voorstel van Agent 1 met de verbeterde versie van Agent 2.

- Beoordeel de versie van de product owner en die van de senior developer en voeg testscenario's en strategie toe.
- Geef een duidelijke eindversie gebaseerd input van de product owner en de senior developer.
- Geef een score van 1-10 voor de kwaliteit van de eindversie.
Input:
{prompt}

Voorstel van Agent 1:
{agent1_output}

Verbetering door Agent 2:
{agent2_output}
"""
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": user_input}],
        max_tokens=1000,
        temperature=0.7,
    )
    return response.choices[0].message.content

# 🧩 Scrum Master functie: splits user story in subtaken
def split_story(story_output):
    user_input = f"""
Je bent een ervaren Scrum Master. Hier is een uitgewerkte user story met testscenario's:

\"\"\"{story_output}\"\"\"

Splits deze user story op in overzichtelijke, logische subtaken, stories of epics. Geef duidelijke taakomschrijvingen in een genummerde lijst.
"""
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": user_input}],
        max_tokens=1000,
        temperature=0.7,
    )
    return response.choices[0].message.content

# Streamlit UI
st.set_page_config(page_title="AI Scrum refinement Demo", layout="wide")
st.title("🤖 Ai Scrum team in Gesprek")
st.write("Voer een prompt in en zie hoe drie DeepSeek scrum AI agenten samenwerken.")

user_prompt = st.text_area("✍️ Jouw prompt:", height=150)

if st.button("Start samenwerking"):
    if not user_prompt.strip():
        st.warning("⚠️ Voer eerst een prompt in.")
    else:
        # Agent 1
        with st.spinner("De productowner genereert een eerste voorstel..."):
            agent1_response = agent_1(user_prompt)

        # Agent 2
        with st.spinner("De senior developer evalueert en verbetert..."):
            agent2_response = agent_2(user_prompt, agent1_response)

        # Agent 3 (Arbiter)
        with st.spinner("De software tester evalueert en vult aan..."):
            arbiter_response = agent_3_arbiter(user_prompt, agent1_response, agent2_response)
        
        with st.spinner("De Scrummaster splitst de story op in subtaken..."):
            subtasks_response = split_story(arbiter_response)

        # UI-opbouw
        st.subheader("🧠 Resultaten van de Teamleden")

        st.divider()
        st.subheader("### 🧩 Product owner Voorstel")
        st.markdown(agent1_response)

        st.divider()
        st.subheader("### 🔧 Senior developer Verbetering")
        st.markdown(agent2_response)

        st.divider()
        st.subheader("⚖️ Eindvoorstel en evaluatie door software tester")
        st.markdown(arbiter_response)

        # Subtasks knop en output
        st.divider()
        st.subheader("📌 Subtaken gegenereerd door de Scrum Master")


        st.markdown(subtasks_response)

        # Downloadknop
        data = "Product owner Voorstel\n\n" + agent1_response + "\n\n\n\nSenior developer Verbetering\n\n" + agent2_response + "\n\n\n\nEindvoorstel en evaluatie door software tester\n\n" + arbiter_response + "\n\n\n\nOpsplitsing in subtaken door de Scrummaster\n\n" +  subtasks_response

        if arbiter_response:
            st.download_button(
                label="Download eindversie",
                data=data,
                file_name="eindversie_ai-team.txt",
                mime="text/plain"
            )
#commit

import streamlit as st
import os
import graphviz
from openai import OpenAI
from dotenv import load_dotenv

# Laden van API sleutel
load_dotenv()
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com/v1"
)

# Claude/DeepSeek Teamlid functies
def teamlid_1(prompt):
    user_input = f"""Je bent een product owner en schrijft een user story vanuit eindgebruikersperspectief.
    Geef een eerste voorstel gebaseerd op de volgende input:

    Input:
    {prompt}
    """
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": user_input}],
        max_tokens=1000
    )
    return response.choices[0].message.content

def teamlid_2(prompt, teamlid1_output):
    user_input = f"""Je bent een senior developer en evalueert en verbetert de user story vanuit technisch perspectief.
    Geef feedback op het voorstel van de product owner waar nodig.

    Input:
    {prompt}

    Voorstel van Teamlid 1:
    {teamlid1_output}
    """
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": user_input}],
        max_tokens=1000
    )
    return response.choices[0].message.content

def teamlid_3_arbiter(prompt, teamlid1_output, teamlid2_output):
    user_input = f"""Je bent een software tester. Vergelijk het originele voorstel van Teamlid 1 met de verbeterde versie van Teamlid 2.

    - Beoordeel beide versies
    - Voeg testscenario's en strategie toe
    - Geef een duidelijke eindversie
    - Geef een score van 1-10 voor de kwaliteit

    Input:
    {prompt}

    Teamlid 1:
    {teamlid1_output}

    Teamlid 2:
    {teamlid2_output}
    """
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": user_input}],
        max_tokens=2000
    )
    return response.choices[0].message.content

def split_story(final_story):
    user_input = f"""Splits de volgende user story in losse subtaken:

{final_story}"""
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": user_input}],
        max_tokens=800
    )
    return response.choices[0].message.content

def chat_with_teamlid(role, vraag):
    instructies = {
        "Product Owner": "Je bent een product owner. Beantwoord de volgende vraag vanuit eindgebruikersperspectief.",
        "Senior Developer": "Je bent een senior developer. Beantwoord vanuit technisch perspectief.",
        "Tester": "Je bent een software tester. Richt je op kwaliteit, validatie en risico's."
    }
    user_input = f"{instructies[role]}\n\nVraag: {vraag}"
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": user_input}],
        max_tokens=800
    )
    return response.choices[0].message.content

def build_story_map(story, subtasks):
    dot = graphviz.Digraph()
    dot.node("User Story", story[:50] + "...")
    for idx, taak in enumerate(subtasks.split('\n')):
        if taak.strip():
            dot.node(f"taak{idx}", taak.strip())
            dot.edge("User Story", f"taak{idx}")
    return dot

# Init session state
if "teamlid1_response" not in st.session_state:
    st.session_state.teamlid1_response = ""
if "teamlid2_response" not in st.session_state:
    st.session_state.teamlid2_response = ""
if "arbiter_response" not in st.session_state:
    st.session_state.arbiter_response = ""
if "subtaken_response" not in st.session_state:
    st.session_state.subtaken_response = ""

# Streamlit UI
st.set_page_config(page_title="AI Scrum refinement Tool", layout="wide")
st.title("🤖 AI Scrum Team Assistent")

# Sidebar Sprint info
st.sidebar.header("📂 Sprintplanning")
sprint_nummer = st.sidebar.selectbox("Sprint:", [1, 2, 3, 4, 5])
storypoints = st.sidebar.slider("Story Points:", 1, 13, 5)
velocity = st.sidebar.slider("Team Velocity (points/sprint):", 5, 30, 20)

# Prompt invoer
st.write("Voer een prompt in en zie hoe de Scrum AI teamleden samenwerken.")
user_prompt = st.text_area("✍️ Jouw prompt:", height=150)

# Chat met individuele teamlid
st.subheader("💬 Gesprek met 1 teamlid")
teamlid_role = st.selectbox("Kies een teamlid:", ["Product Owner", "Senior Developer", "Tester"])
custom_question = st.text_input("Stel een vraag aan dit teamlid:")
if custom_question:
    antwoord = chat_with_teamlid(teamlid_role, custom_question)
    st.info(f"**Antwoord van {teamlid_role}:**\n\n{antwoord}")

# Hoofdverwerking
if st.button("Start samenwerking"):
    if not user_prompt.strip():
        st.warning("⚠️ Voer eerst een prompt in.")
    else:
        with st.spinner("De product owner genereert een voorstel..."):
            st.session_state.teamlid1_response = teamlid_1(user_prompt)

        with st.spinner("De senior developer evalueert..."):
            st.session_state.teamlid2_response = teamlid_2(user_prompt, st.session_state.teamlid1_response)

        with st.spinner("De tester evalueert en vult aan..."):
            st.session_state.arbiter_response = teamlid_3_arbiter(user_prompt, st.session_state.teamlid1_response, st.session_state.teamlid2_response)

# Toon resultaten
if st.session_state.arbiter_response:
    st.subheader("🧠 Resultaten van het Team")
    st.markdown("### 🧩 Product owner Voorstel")
    st.markdown(st.session_state.teamlid1_response)
    st.markdown("### 🔧 Senior developer Verbetering")
    st.markdown(st.session_state.teamlid2_response)
    st.markdown("### ⚖️ Tester Eindversie en evaluatie")
    st.markdown(st.session_state.arbiter_response)

    st.subheader("🗞️ Sprintplanning")
    st.markdown(f"""
    - **Sprint:** {sprint_nummer}  
    - **Story Points:** {storypoints}  
    - **Geschatte doorlooptijd:** {round(storypoints / velocity * 7, 1)} dagen
    """)

    if st.button("🔍 Splits user story op in subtaken"):
        with st.spinner("Splitsen in subtaken..."):
            st.session_state.subtaken_response = split_story(st.session_state.arbiter_response)
        st.subheader("📌 Opgesplitste Subtaken")
        st.markdown(st.session_state.subtaken_response)
        st.graphviz_chart(build_story_map(user_prompt, st.session_state.subtaken_response))

    # Downloadknoppen
    download_txt = f"Product Owner:\n{st.session_state.teamlid1_response}\n\nSenior Developer:\n{st.session_state.teamlid2_response}\n\nTester:\n{st.session_state.arbiter_response}"
    st.download_button("Download eindversie", download_txt, file_name="eindversie.txt")

    if st.session_state.subtaken_response:
        testscript_txt = f"Testscenario's en Subtaken:\n\n{st.session_state.subtaken_response}"
        st.download_button("Download testscript", testscript_txt, file_name="testscript.txt")

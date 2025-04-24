import streamlit as st
import os
import graphviz
from openai import OpenAI
from dotenv import load_dotenv
import datetime

# Laden van API sleutel
load_dotenv()
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com/v1"
)

# DeepSeek Teamlid functies
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
    user_input = f"{instructies.get(role, f'Je bent een {role}.')}\nVraag: {vraag}"
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

def analyse_acceptatiecriteria(final_story):
    user_input = f"""Geef voor de volgende user story de acceptatiecriteria in Gherkin-formaat:

{final_story}"""
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": user_input}],
        max_tokens=800
    )
    return response.choices[0].message.content

# Init session state
if "history" not in st.session_state:
    st.session_state.history = []
    
if "current_responses" not in st.session_state:
    st.session_state.current_responses = {
        "teamlid1": "",
        "teamlid2": "",
        "arbiter": "",
        "subtaken": "",
        "acceptatie": ""
    }
    
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Streamlit UI configuratie
st.set_page_config(page_title="AI Scrum refinement Tool", layout="wide")
st.title("🤖 AI Scrum Team Assistent")

# --- Verbeterde Geschiedenis Sidebar ---
with st.sidebar:
    st.subheader("📚 Geschiedenis")
    
    if not st.session_state.history:
        st.write("Nog geen geschiedenis")
    else:
        for idx, item in enumerate(st.session_state.history):
            with st.expander(f"📝 {item['timestamp']}", expanded=False):
                st.markdown(f"**Prompt:**")
                st.text(item['prompt'][:200] + ("..." if len(item['prompt']) > 200 else ""))
                
                col1, col2 = st.columns([3,1])
                with col1:
                    if st.button("Laad", key=f"load_{idx}"):
                        st.session_state.current_responses = item["responses"]
                        st.rerun()
                with col2:
                    if st.button("❌", key=f"delete_{idx}"):
                        del st.session_state.history[idx]
                        st.rerun()

# --- Hoofdcontent ---
tab_main, tab_chat = st.tabs(["🏠 Hoofdpagina", "💬 Chat met Teamlid"])

with tab_main:
    # Prompt invoer
    st.write("Voer een prompt in en zie hoe de Scrum AI teamleden samenwerken.")
    user_prompt = st.text_area("✍️ Jouw prompt:", height=150, key="main_prompt")

    # Progress bar
    progress_bar = st.progress(0, text="Wacht op input...")

    if st.button("Start samenwerking"):
        if not user_prompt.strip():
            st.warning("⚠️ Voer eerst een prompt in.")
            progress_bar.empty()
        else:
            try:
                # Voeg direct toe aan geschiedenis (voor laden)
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                st.session_state.history.append({
                    "timestamp": timestamp,
                    "prompt": user_prompt,
                    "responses": {
                        "teamlid1": "",
                        "teamlid2": "",
                        "arbiter": "",
                        "subtaken": "",
                        "acceptatie": ""
                    }
                })
                
                # Verwerk de prompt
                progress_bar.progress(20, text="Product owner aan het werk...")
                st.session_state.current_responses["teamlid1"] = teamlid_1(user_prompt)

                progress_bar.progress(50, text="Developer geeft feedback...")
                st.session_state.current_responses["teamlid2"] = teamlid_2(user_prompt, st.session_state.current_responses["teamlid1"])

                progress_bar.progress(80, text="Tester evalueert...")
                st.session_state.current_responses["arbiter"] = teamlid_3_arbiter(
                    user_prompt, 
                    st.session_state.current_responses["teamlid1"], 
                    st.session_state.current_responses["teamlid2"]
                )

                # Update de geschiedenis met resultaten
                st.session_state.history[-1]["responses"] = st.session_state.current_responses.copy()
                
                progress_bar.progress(100, text="Klaar!")
                st.success("✅ Samenwerking voltooid!")
                st.balloons()
                
            except Exception as e:
                st.error(f"Er ging iets mis: {str(e)}")
                # Verwijder de incomplete geschiedenis entry bij fout
                if st.session_state.history and not st.session_state.history[-1]["responses"]["teamlid1"]:
                    st.session_state.history.pop()
                progress_bar.empty()

    # Toon resultaten in tabs
    if st.session_state.current_responses["arbiter"]:
        st.subheader("🧠 Resultaten van het Team")
        
        tab_po, tab_dev, tab_test = st.tabs(["🧩 Product Owner", "🔧 Developer", "⚖️ Tester"])
        
        with tab_po:
            st.markdown(st.session_state.current_responses["teamlid1"])
        
        with tab_dev:
            st.markdown(st.session_state.current_responses["teamlid2"])
        
        with tab_test:
            st.markdown(st.session_state.current_responses["arbiter"])

        # Actieknoppen onder resultaten
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔍 Splits user story op in subtaken"):
                with st.spinner("Splitsen in subtaken..."):
                    st.session_state.current_responses["subtaken"] = split_story(st.session_state.current_responses["arbiter"])
                st.subheader("📌 Opgesplitste Subtaken")
                st.markdown(st.session_state.current_responses["subtaken"])
                st.graphviz_chart(build_story_map(user_prompt, st.session_state.current_responses["subtaken"]))
        
        with col2:
            if st.button("📜 Genereer acceptatiecriteria in Gherkin-formaat"):
                with st.spinner("Genereren van acceptatiecriteria..."):
                    st.session_state.current_responses["acceptatie"] = analyse_acceptatiecriteria(st.session_state.current_responses["arbiter"])
                st.subheader("✅ Acceptatiecriteria")
                st.code(st.session_state.current_responses["acceptatie"], language="gherkin")

        # Download knoppen
        st.divider()
        st.subheader("📥 Download Resultaten")
        
        download_col1, download_col2, download_col3 = st.columns(3)
        
        with download_col1:
            download_txt = f"Product Owner:\n{st.session_state.current_responses['teamlid1']}\n\nSenior Developer:\n{st.session_state.current_responses['teamlid2']}\n\nTester:\n{st.session_state.current_responses['arbiter']}"
            st.download_button("Download eindversie", download_txt, file_name="eindversie.txt")
        
        with download_col2:
            if st.session_state.current_responses["subtaken"]:
                testscript_txt = f"Testscenario's en Subtaken:\n\n{st.session_state.current_responses['subtaken']}"
                st.download_button("Download testscript", testscript_txt, file_name="testscript.txt")
        
        with download_col3:
            if st.session_state.current_responses["acceptatie"]:
                st.download_button("Download acceptatiecriteria", st.session_state.current_responses["acceptatie"], file_name="acceptatiecriteria.feature")

with tab_chat:
    # Chat met individuele teamlid
    st.subheader("💬 Gesprek met Teamlid")
    teamlid_role = st.selectbox("Kies een teamlid:", ["Product Owner", "Senior Developer", "Tester"], key="chat_role")
    custom_question = st.text_input("Stel een vraag aan dit teamlid:", key="chat_question")
    
    if custom_question:
        with st.spinner(f"{teamlid_role} denkt na..."):
            try:
                antwoord = chat_with_teamlid(teamlid_role, custom_question)
                st.info(f"**Antwoord van {teamlid_role}:**\n\n{antwoord}")

                # Voeg chat toe aan geschiedenis
                st.session_state.chat_history.append({
                    "role": teamlid_role,
                    "vraag": custom_question,
                    "antwoord": antwoord,
                    "timestamp": datetime.datetime.now().strftime("%H:%M")
                })
            except Exception as e:
                st.error(f"Fout bij chat: {str(e)}")

        # Toon chat geschiedenis
        with st.expander("📜 Chat Geschiedenis"):
            if st.session_state.chat_history:
                for chat in reversed(st.session_state.chat_history):
                    st.markdown(f"**{chat['role']} ({chat['timestamp']}):** {chat['vraag']}")
                    st.markdown(f"*Antwoord:* {chat['antwoord']}")
                    st.divider()
            else:
                st.write("Nog geen chat geschiedenis")
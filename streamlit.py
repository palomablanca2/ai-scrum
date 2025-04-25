import streamlit as st
import os
import graphviz
from openai import OpenAI
from dotenv import load_dotenv
import datetime
import json
import pandas as pd
from io import StringIO

# Laden van API sleutel
load_dotenv()
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com/v1"
)

# --- Verbeterde Teamlid Functies ---
def generate_response(model, messages, max_tokens=5000):
    """Gecentraliseerde functie voor API calls met error handling"""
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=0.7  # Meer creativiteit toestaan
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"API Fout: {str(e)}")
        return None

def teamlid_1(prompt):
    messages = [
        {"role": "system", "content": "Je bent een ervaren product owner. Schrijf duidelijke user stories volgens INVEST criteria."},
        {"role": "user", "content": f"""Schrijf een user story gebaseerd op:
        {prompt}
        
        Volg dit format:
        Als een [type gebruiker]
        Wil ik [doel/wens]
        Zodat [waarde/business doel]
        
        Acceptatiecriteria:
        - [Meetbaar criterium 1]
        - [Meetbaar criterium 2]"""}
    ]
    return generate_response("deepseek-chat", messages)

def teamlid_2(prompt, teamlid1_output):
    messages = [
        {"role": "system", "content": "Je bent een senior developer. Geef technische feedback en verbeter user stories."},
        {"role": "user", "content": f"""Geef technische feedback op deze user story:
        Originele prompt: {prompt}
        
        User story:
        {teamlid1_output}
        
        Richtlijnen:
        1. Identificeer ontbrekende technische vereisten
        2. Controleer op ambiguïteit
        3. Voeg implementatie details toe waar nodig
        4. Behoud de business waarde"""}
    ]
    return generate_response("deepseek-chat", messages)

def teamlid_3_arbiter(prompt, teamlid1_output, teamlid2_output):
    messages = [
        {"role": "system", "content": "Je bent een QA engineer. Evalueer user stories en voeg testscenario's toe."},
        {"role": "user", "content": f"""Evalueer deze user story versies:
        Originele prompt: {prompt}
        
        Product Owner versie:
        {teamlid1_output}
        
        Developer feedback:
        {teamlid2_output}
        
        Geef:
        1. Een samengevoegde, verbeterde versie
        2. Testscenario's (happy path + edge cases)
        3. Kwaliteitsscore (1-10) met motivatie
        4. Risicoanalyse"""}
    ]
    return generate_response("deepseek-chat", messages)

def split_story(final_story):
    messages = [
        {"role": "system", "content": "Je bent een agile coach. Splits user stories in kleine, uitvoerbare taken."},
        {"role": "user", "content": f"""Splits deze user story:
        {final_story}
        
        Volg dit format:
        ## Epics
        - [Epic 1]
        - [Epic 2]
        
        ## User Stories
        - [US 1]
        - [US 2]
        
        ## Technische Taken
        - [Taak 1]
        - [Taak 2]"""}
    ]
    return generate_response("deepseek-chat", messages)

def chat_with_teamlid(role, vraag):
    instructies = {
        "Product Owner": "Je bent een product owner. Beantwoord vragen vanuit business perspectief.",
        "Senior Developer": "Je bent een senior developer. Beantwoord vanuit technisch perspectief.",
        "Tester": "Je bent een QA engineer. Richt je op testbaarheid en kwaliteit."
    }
    messages = [
        {"role": "system", "content": instructies.get(role, f"Je bent een {role}")},
        {"role": "user", "content": vraag}
    ]
    return generate_response("deepseek-chat", messages)

def verfijn_user_story(final_story, verfijnings_prompt):
    messages = [
        {"role": "system", "content": "Je bent een agile coach. Verfijn user stories op basis van feedback."},
        {"role": "user", "content": f"""Verfijn deze user story:
        {final_story}
        
        Verfijningsinstructies:
        {verfijnings_prompt}
        
        Behoud het INVEST format:
        - Independent
        - Negotiable
        - Valuable
        - Estimable
        - Small
        - Testable"""}
    ]
    return generate_response("deepseek-chat", messages)

def generate_jira_import(story_data):
    """Genereer CSV voor Jira import"""
    data = {
        "Summary": [story_data["title"]],
        "Description": [story_data["description"]],
        "Acceptance Criteria": [story_data["acceptance"]],
        "Story Points": [story_data["points"]],
        "Component": ["Backend"],
        "Labels": ["generated"]
    }
    return pd.DataFrame(data)



# --- UI Configuratie ---
st.set_page_config(page_title="AI Scrum Tool PRO", layout="wide", initial_sidebar_state="expanded")
st.title("🚀 AI Scrum Team Assistent PRO")

# --- Session State Management ---
class SessionState:
    def __init__(self):
        self.history = []
        self.current_responses = {
            "teamlid1": "", "teamlid2": "", "arbiter": "",
            "subtaken": "", "acceptatie": "", "verfijnd": "",
            "story_points": "", "risico_analyse": ""
        }
        self.chat_history = []
        self.settings = {
            "ai_temperature": 0.7,
            "max_tokens": 5000
        }

if "app_state" not in st.session_state:
    st.session_state.app_state = SessionState()

# --- Sidebar met Geschiedenis en Instellingen ---
with st.sidebar:
    st.header("⚙️ Instellingen")
    st.session_state.app_state.settings["ai_temperature"] = st.slider(
        "AI Creativiteit", 0.0, 1.0, 0.7, 0.1,
        help="Hoger = creatiever, Lager = voorspelbaarder"
    )
    
    st.divider()
    st.header("📚 Geschiedenis")
    
    if not st.session_state.app_state.history:
        st.info("Geen geschiedenis beschikbaar")
    else:
        for idx, item in enumerate(st.session_state.app_state.history):
            with st.expander(f"📌 {item['timestamp']}", expanded=False):
                st.caption(f"Prompt: {item['prompt'][:100]}...")
                
                if item['responses'].get('verfijnd'):
                    st.success("✓ Verfijnd")
                
                cols = st.columns([3,1])
                with cols[0]:
                    if st.button("Laden", key=f"load_{idx}"):
                        st.session_state.app_state.current_responses = item["responses"]
                        st.rerun()
                with cols[1]:
                    if st.button("❌", key=f"del_{idx}"):
                        st.session_state.app_state.history.pop(idx)
                        st.rerun()

# --- Hoofdcontent ---
tab_main, tab_chat, tab_export = st.tabs(["🏠 Refinement", "💬 Team Chat", "📤 Export"])

with tab_main:
    # Prompt Sectie
    with st.container(border=True):
        prompt = st.text_area(
            "✍️ User Story Input:", 
            height=150,
            placeholder="Beschrijf je feature of verbetering..."
        )
        
        if st.button("🚀 Start Refinement", use_container_width=True):
            if not prompt.strip():
                st.warning("Voer een prompt in")
            else:
                with st.status("🔍 AI Team aan het werk...", expanded=True) as status:
                    st.write("Product Owner schrijft user story...")
                    st.session_state.app_state.current_responses["teamlid1"] = teamlid_1(prompt)
                    
                    st.write("Developer geeft feedback...")
                    st.session_state.app_state.current_responses["teamlid2"] = teamlid_2(
                        prompt, 
                        st.session_state.app_state.current_responses["teamlid1"]
                    )
                    
                    st.write("Tester evalueert...")
                    st.session_state.app_state.current_responses["arbiter"] = teamlid_3_arbiter(
                        prompt,
                        st.session_state.app_state.current_responses["teamlid1"],
                        st.session_state.app_state.current_responses["teamlid2"]
                    )
                    
                    # Update history
                    st.session_state.app_state.history.append({
                        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "prompt": prompt,
                        "responses": st.session_state.app_state.current_responses.copy()
                    })
                    
                    status.update(label="✅ Refinement voltooid!", state="complete")
                    st.balloons()

    # Resultaten Sectie
    if st.session_state.app_state.current_responses["arbiter"]:
        with st.container(border=True):
            tab1, tab2, tab3, tab4 = st.tabs([
                "🧩 User Story", 
                "🔧 Technisch", 
                "⚖️ Testen", 
                "✨ Verfijnen"
            ])
            
            with tab1:
                st.markdown(st.session_state.app_state.current_responses["teamlid1"])
                
            with tab2:
                st.markdown(st.session_state.app_state.current_responses["teamlid2"])
                
            with tab3:
                st.markdown(st.session_state.app_state.current_responses["arbiter"])
                
                # Story Points schatting
                if not st.session_state.app_state.current_responses["story_points"]:
                    with st.spinner("Schatting story points..."):
                        response = chat_with_teamlid(
                            "Senior Developer",
                            f"Geef een Fibonacci story point schatting (1,2,3,5,8,13) voor:\n{st.session_state.app_state.current_responses['arbiter']}\n\nMotivatie:"
                        )
                        st.session_state.app_state.current_responses["story_points"] = response
                st.divider()
                st.subheader("📊 Story Points Schatting")
                st.markdown(st.session_state.app_state.current_responses["story_points"])
                
            with tab4:
                verfijn_prompt = st.text_area(
                    "Hoe moet de user story verfijnd worden?",
                    height=100,
                    placeholder="Bijv: meer details over authenticatie, performance eisen, etc."
                )
                
                if st.button("🔄 Verfijn", use_container_width=True):
                    if verfijn_prompt:
                        with st.spinner("User story verfijnen..."):
                            refined = verfijn_user_story(
                                st.session_state.app_state.current_responses["arbiter"],
                                verfijn_prompt
                            )
                            st.session_state.app_state.current_responses["verfijnd"] = refined
                            st.success("✅ User story verfijnd!")
                            st.markdown(refined)
                    else:
                        st.warning("Voer verfijningsinstructies in")

        # Acties Sectie
        with st.container(border=True):
            st.subheader("🔨 Acties")
            
            cols = st.columns(3)
            with cols[0]:
                if st.button("📝 Splits in taken", help="Breek af in kleinere items"):
                    story_to_split = st.session_state.app_state.current_responses.get("verfijnd") or st.session_state.app_state.current_responses["arbiter"]
                    with st.spinner("Splitsen..."):
                        st.session_state.app_state.current_responses["subtaken"] = split_story(story_to_split)
                    st.markdown(st.session_state.app_state.current_responses["subtaken"])
                    
            with cols[1]:
                if st.button("✅ Acceptatiecriteria", help="Genereer Gherkin scenarios"):
                    story_for_criteria = st.session_state.app_state.current_responses.get("verfijnd") or st.session_state.app_state.current_responses["arbiter"]
                    with st.spinner("Genereren..."):
                        st.session_state.app_state.current_responses["acceptatie"] = analyse_acceptatiecriteria(story_for_criteria)
                    st.code(st.session_state.app_state.current_responses["acceptatie"], language="gherkin")
                    
            with cols[2]:
                if st.button("⚠️ Risico Analyse", help="Identificeer potentiële risico's"):
                    if not st.session_state.app_state.current_responses["risico_analyse"]:
                        with st.spinner("Analyse..."):
                            response = chat_with_teamlid(
                                "Tester",
                                f"Geef een risicoanalyse voor:\n{st.session_state.app_state.current_responses['arbiter']}\n\nCategoriseer in: Technisch, Organisatorisch, Planning"
                            )
                            st.session_state.app_state.current_responses["risico_analyse"] = response
                    st.markdown(st.session_state.app_state.current_responses["risico_analyse"])

with tab_chat:
    # Chat Interface
    with st.container(border=True):
        col1, col2 = st.columns([1,3])
        with col1:
            role = st.selectbox("Teamlid", ["Product Owner", "Senior Developer", "Tester"])
        with col2:
            question = st.text_input("Stel je vraag", placeholder="Typ je vraag hier...")
            
        if question:
            with st.spinner(f"{role} denkt na..."):
                answer = chat_with_teamlid(role, question)
                st.session_state.app_state.chat_history.append({
                    "role": role,
                    "question": question,
                    "answer": answer,
                    "time": datetime.datetime.now().strftime("%H:%M")
                })
                
            st.markdown(f"**{role}:** {answer}")
            
    # Chat Geschiedenis
    if st.session_state.app_state.chat_history:
        with st.expander("📜 Chat Geschiedenis", expanded=True):
            for msg in reversed(st.session_state.app_state.chat_history):
                st.markdown(f"**{msg['role']} ({msg['time']}):** {msg['question']}")
                st.markdown(f"{msg['answer']}")
                st.divider()

with tab_export:
    # Export Functionaliteiten
    if st.session_state.app_state.current_responses.get("arbiter"):
        with st.container(border=True):
            st.subheader("📤 Export Opties")
            
            # Jira Export
            with st.expander("🔄 Jira Import"):
                jira_data = {
                    "title": "User Story: " + (st.session_state.app_state.current_responses.get("verfijnd") or st.session_state.app_state.current_responses["arbiter"]).split("\n")[0][:100],
                    "description": st.session_state.app_state.current_responses["arbiter"],
                    "acceptance": st.session_state.app_state.current_responses.get("acceptatie", ""),
                    "points": "3"  # Placeholder
                }
                
                df = generate_jira_import(jira_data)
                st.dataframe(df)
                
                csv = df.to_csv(index=False)
                st.download_button(
                    label="📥 Download CSV voor Jira",
                    data=csv,
                    file_name="jira_import.csv",
                    mime="text/csv"
                )
            
            # Markdown Export
            with st.expander("📝 Markdown"):
                markdown_content = f"""# User Story\n\n{st.session_state.app_state.current_responses["arbiter"]}\n\n"""
                if st.session_state.app_state.current_responses.get("verfijnd"):
                    markdown_content += f"## Verfijnde Versie\n\n{st.session_state.app_state.current_responses['verfijnd']}\n\n"
                if st.session_state.app_state.current_responses.get("acceptatie"):
                    markdown_content += f"## Acceptatiecriteria\n\n```gherkin\n{st.session_state.app_state.current_responses['acceptatie']}\n```\n\n"
                if st.session_state.app_state.current_responses.get("subtaken"):
                    markdown_content += f"## Opgesplitste Taken\n\n{st.session_state.app_state.current_responses['subtaken']}\n\n"
                
                st.download_button(
                    label="📥 Download Markdown",
                    data=markdown_content,
                    file_name="user_story.md",
                    mime="text/markdown"
                )
            
            # JSON Export
            with st.expander("📦 Volledige Export (JSON)"):
                full_data = {
                    "metadata": {
                        "generated_at": datetime.datetime.now().isoformat(),
                        "version": "1.0"
                    },
                    "user_story": st.session_state.app_state.current_responses["arbiter"],
                    "refined_version": st.session_state.app_state.current_responses.get("verfijnd", ""),
                    "acceptance_criteria": st.session_state.app_state.current_responses.get("acceptatie", ""),
                    "tasks": st.session_state.app_state.current_responses.get("subtaken", ""),
                    "story_points": st.session_state.app_state.current_responses.get("story_points", ""),
                    "risk_analysis": st.session_state.app_state.current_responses.get("risico_analyse", "")
                }
                
                json_str = json.dumps(full_data, indent=2, ensure_ascii=False)
                st.download_button(
                    label="📥 Download JSON",
                    data=json_str,
                    file_name="user_story_export.json",
                    mime="application/json"
                )
    else:
        st.info("Voer eerst een refinement uit om export opties te zien")

# --- Einde van de App
# ---- Extended version
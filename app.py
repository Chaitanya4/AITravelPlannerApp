import os
import re
import json
import streamlit as st
from google import genai
from google.genai import types

# -------------------------------------------------------------
# Security & Input Validation Core Logic
# -------------------------------------------------------------

def sanitize_text(text: str, max_length: int = 200) -> str:
    """
    Sanitizes string inputs by stripping HTML-like tag sequences,
    stripping extra whitespace, and cropping to a safe maximum length.
    """
    if not isinstance(text, str):
        return ""
    # Strip HTML tags
    cleaned = re.sub(r'<[^>]*>', '', text)
    # Remove leading/trailing whitespaces
    cleaned = cleaned.strip()
    # Crop to safe limit
    return cleaned[:max_length]

def clean_destination_name(dest: str) -> str:
    """
    Ensures destination names only contain clean alpha-numeric, space, 
    comma, period, or hyphen characters to prevent injection.
    """
    if not dest:
        return ""
    sanitized = sanitize_text(dest, max_length=80)
    # Filter to only allow safe alphanumeric + basic punctuation
    cleaned = re.sub(r'[^\w\s,\.-]', '', sanitized)
    return cleaned.strip()

def validate_days_count(days: int) -> int:
    """
    Validates and clamps duration of stay to a safe limit [1, 10] days.
    """
    try:
        val = int(days)
        return max(1, min(10, val))
    except (ValueError, TypeError):
        return 3

# -------------------------------------------------------------
# Gemini AI Curation Wrappers (Secure & Testable)
# -------------------------------------------------------------

def generate_itinerary_json(client, destination: str, days_count: int, interests: str, traveler_type: str) -> dict:
    """
    Requests a structured vacation plan from Gemini in strict JSON format.
    """
    if not client:
        raise ValueError("AI Client is not initialized.")

    clean_dest = clean_destination_name(destination)
    if not clean_dest:
        raise ValueError("A valid, non-empty destination is required.")

    clean_ints = sanitize_text(interests, max_length=300) or "General sightseeing, local cuisine"
    clean_style = sanitize_text(traveler_type, max_length=80) or "Solo Explorer"
    duration = validate_days_count(days_count)

    prompt = f"""
    Generate a highly personalized, structured {duration}-day travel itinerary for {clean_dest}.
    Traveler Details:
    - Interests: {clean_ints}
    - Traveler Type: {clean_style}

    Provide deep local recommendations across attractions, culinary delights, artisan shops, and traditional cultural experiences. Ensure each day has morning, afternoon, and evening recommendations with expert tips.
    """

    # Structured Schema for output validation
    response_schema = {
        "type": "OBJECT",
        "properties": {
            "destination": {"type": "STRING"},
            "overview": {"type": "STRING"},
            "expertTips": {
                "type": "ARRAY",
                "items": {"type": "STRING"}
            },
            "days": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "dayNumber": {"type": "INTEGER"},
                        "title": {"type": "STRING"},
                        "activities": {
                            "type": "ARRAY",
                            "items": {
                                "type": "OBJECT",
                                "properties": {
                                    "time": {"type": "STRING"},
                                    "title": {"type": "STRING"},
                                    "description": {"type": "STRING"},
                                    "category": {"type": "STRING"},
                                    "locationName": {"type": "STRING"},
                                    "expertTip": {"type": "STRING"}
                                },
                                "required": ["time", "title", "description", "category", "locationName", "expertTip"]
                            }
                        }
                    },
                    "required": ["dayNumber", "title", "activities"]
                }
            }
        },
        "required": ["destination", "overview", "expertTips", "days"]
    }

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction="You are an elite travel concierge. Generate hyper-detailed plans strictly in JSON format matching the schema.",
            response_mime_type="application/json",
            response_schema=response_schema,
            temperature=0.2
        )
    )

    if not response or not response.text:
        raise RuntimeError("No response text received from the AI model.")

    return json.loads(response.text)

def generate_chat_response(client, destination: str, expert_instruction: str, user_message: str, history: list) -> str:
    """
    Sends a query to a specific specialized travel expert while passing conversation history.
    """
    if not client:
        raise ValueError("AI Client is not initialized.")

    clean_dest = clean_destination_name(destination)
    if not clean_dest:
        raise ValueError("Please provide a destination city or country before talking to experts.")

    clean_msg = sanitize_text(user_message, max_length=1000)
    if not clean_msg:
        return "I didn't receive a message. Please type something so I can help!"

    # Cap past log interactions to 12 history turns to maintain strict memory safety
    recent_history = history[-12:] if history else []

    contents = []
    for m in recent_history:
        contents.append({
            "role": "user" if m.get("role") == "user" else "model",
            "parts": [{"text": sanitize_text(m.get("content", ""), max_length=1000)}]
        })
    # Add final message
    contents.append({
        "role": "user",
        "parts": [{"text": clean_msg}]
    })

    system_instruction = f"Destination: {clean_dest}.\n{expert_instruction}\nRespond warmly, concisely, and support your insights with specific neighborhood locations."

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.7
        )
    )

    if not response or not response.text:
        return "I am sorry, I couldn't connect to my knowledge base right now. Let's try again!"

    return response.text

# -------------------------------------------------------------
# Static Travel Expert Personas
# -------------------------------------------------------------
LOCAL_EXPERTS = {
    "general": {
        "name": "Kai",
        "title": "Local Explorer",
        "bio": "Expert in daily route optimization, transit hacks, and finding secret panoramic views.",
        "icon": "🧭",
        "system_instruction": "You are Kai, an experienced Local Explorer. Help travelers optimize routes, find hidden views, and understand local transit. Speak warmly, concisely, and with insider passion."
    },
    "foodie": {
        "name": "Chef Mei",
        "title": "Culinary Expert",
        "bio": "Street food champion, restaurant critic, and recipe keeper. She knows every hidden back-alley bistro.",
        "icon": "🍜",
        "system_instruction": "You are Chef Mei, an enthusiastic local foodie. Recommend mouth-watering street food stalls, markets, and regional delicacies. Provide dining etiquette tips."
    },
    "cultural": {
        "name": "Siddharth",
        "title": "Cultural Historian",
        "bio": "Temple/shrine architectural expert, narrator of folklore, and traditional arts specialist.",
        "icon": "🎭",
        "system_instruction": "You are Siddharth, a cultural historian. Guide travelers through neighborhood folklore, spiritual meanings of landmarks, and local etiquette rules for visiting sacred places."
    },
    "shopping": {
        "name": "Elena",
        "title": "Shopping Stylist",
        "bio": "Artisan craft seeker and independent designer boutique scout. Avoid cheap plastic tourist traps.",
        "icon": "🛍️",
        "system_instruction": "You are Elena, an artisan shopping curator. Recommend where to find handmade souvenirs, independent design markets, and local artists to support."
    }
}

# -------------------------------------------------------------
# Main Streamlit UI Setup & State Binding
# -------------------------------------------------------------
def main():
    # Elegant custom styling injecting high-contrast accessible guidelines
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
        
        /* High contrast colors and clean modern Inter typeface */
        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
            color: #1f2937;
        }
        
        .brand-title {
            font-size: 2.2rem;
            font-weight: 800;
            color: #047857; /* High contrast emerald-700 */
            margin-bottom: 2px;
            letter-spacing: -0.04em;
        }
        .brand-subtitle {
            font-size: 1rem;
            color: #4b5563; /* High contrast gray-600 */
            margin-top: -5px;
            margin-bottom: 25px;
        }
        
        /* Accessible card block borders with high-contrast text */
        .expert-card {
            background-color: #f0fdf4;
            border: 2px solid #059669;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 15px;
        }
        .timeline-item {
            background-color: #ffffff;
            border-left: 4px solid #059669;
            border-top: 1px solid #e5e7eb;
            border-right: 1px solid #e5e7eb;
            border-bottom: 1px solid #e5e7eb;
            padding: 15px;
            margin-bottom: 12px;
            border-radius: 0 10px 10px 0;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        }
    </style>
    """, unsafe_allowed_code_html=True)

    # State initialization
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "saved_places" not in st.session_state:
        st.session_state.saved_places = []
    if "active_itinerary" not in st.session_state:
        st.session_state.active_itinerary = None

    # Title branding
    st.markdown('<h1 class="brand-title" id="main-title">🧭 NomadCompass</h1>', unsafe_allowed_code_html=True)
    st.markdown('<p class="brand-subtitle">AI Travel Planner & Local Expert Chatbot</p>', unsafe_allowed_code_html=True)

    # Sidebar parameters
    st.sidebar.title("🎒 Plan Your Vacation")
    
    destination = st.sidebar.text_input(
        "Where are we heading?", 
        value="Kyoto",
        help="Type in your vacation city or country destination.",
        key="destination_input"
    )

    days_count = st.sidebar.slider(
        "Trip Duration (Days)", 
        min_value=1, 
        max_value=10, 
        value=3,
        key="days_count_slider"
    )

    traveler_type = st.sidebar.selectbox(
        "Traveler Type",
        ["Solo Explorer", "Romantic Couple", "Family Holiday", "Group of Friends", "Heritage Enthusiasts"],
        key="traveler_style"
    )

    interests = st.sidebar.text_area(
        "Specific Interests", 
        value="Authentic street food, ancient shrines, pottery markets, garden walks",
        placeholder="Enter topics like vegan restaurants, modern art, shopping alleys...",
        key="interests_input"
    )

    # API key setup
    api_key = os.environ.get("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY", "")
    if not api_key:
        st.sidebar.warning("⚠️ GEMINI_API_KEY is not set in environment or Streamlit secrets.")
        api_key_input = st.sidebar.text_input("Enter Gemini API Key:", type="password", key="manual_api_key")
        if api_key_input:
            api_key = api_key_input

    # Client instantiation
    client = None
    if api_key:
        try:
            client = genai.Client(apiKey=api_key)
        except Exception as e:
            st.sidebar.error(f"Failed to load AI client: {e}")

    st.sidebar.markdown("---")
    generate_btn = st.sidebar.button("✨ Draft Custom Itinerary", use_container_width=True, key="generate_btn")

    if generate_btn:
        if not client:
            st.sidebar.error("Error: Please provide a Gemini API Key to run generation.")
        elif not destination.strip():
            st.sidebar.error("Error: Please input a destination first.")
        else:
            with st.spinner(f"Curating your custom travel timeline for {destination}..."):
                try:
                    res_itinerary = generate_itinerary_json(
                        client, 
                        destination=destination, 
                        days_count=days_count, 
                        interests=interests, 
                        traveler_type=traveler_type
                    )
                    st.session_state.active_itinerary = res_itinerary
                    st.success("🎉 Vacation curated successfully! Check out your timeline on the right.")
                except Exception as e:
                    st.error(f"Drafting failure: {str(e)}")

    # Dual Column Layout (Chats | Itinerary Timeline)
    col_chat, col_itinerary = st.columns([5, 7])

    # -------------------------------------------------------------
    # Column 1: Expert Chats (Recommendations, Food, Cultural)
    # -------------------------------------------------------------
    with col_chat:
        st.subheader("💬 Ask Specialized Local Experts")

        expert_choice = st.radio(
            "Select a local expert channel:",
            options=list(LOCAL_EXPERTS.keys()),
            format_func=lambda k: f"{LOCAL_EXPERTS[k]['icon']} {LOCAL_EXPERTS[k]['name']} ({LOCAL_EXPERTS[k]['title']})",
            horizontal=True,
            key="expert_radio"
        )

        selected_expert = LOCAL_EXPERTS[expert_choice]

        # Bio representation card
        st.markdown(f"""
        <div class="expert-card" role="region" aria-label="Expert Bio">
            <strong>{selected_expert['name']} • {selected_expert['title']}</strong><br/>
            <span style="font-size:0.85rem; color:#1f2937;">{selected_expert['bio']}</span>
        </div>
        """, unsafe_allowed_code_html=True)

        # Messages window frame
        chat_container = st.container(height=380)
        with chat_container:
            # Filter chat history for active expert
            expert_messages = [m for m in st.session_state.messages if m.get("expert_id") == expert_choice]
            
            if not expert_messages:
                st.markdown(f"**{selected_expert['name']}**: Hello traveler! Feel free to ask me anything about **{destination}**. Tell me, what kind of food, shopping, or cultural highlights are you hoping to find?")
            
            for msg in expert_messages:
                role_label = "**You**" if msg["role"] == "user" else f"**{selected_expert['name']}**"
                st.markdown(f"{role_label}: {msg['content']}")

        # Message Input text box
        user_msg = st.chat_input(f"Send a message to {selected_expert['name']}...", key="chat_input")
        if user_msg:
            if not client:
                st.error("Please insert a valid Google Gemini API Key in the sidebar.")
            elif not destination.strip():
                st.error("Please define your trip destination in the sidebar before asking questions.")
            else:
                # Store user's message
                st.session_state.messages.append({
                    "role": "user",
                    "expert_id": expert_choice,
                    "content": user_msg
                })

                with st.spinner(f"{selected_expert['name']} is writing recommendations..."):
                    try:
                        reply = generate_chat_response(
                            client=client,
                            destination=destination,
                            expert_instruction=selected_expert["system_instruction"],
                            user_message=user_msg,
                            history=expert_messages
                        )
                        st.session_state.messages.append({
                            "role": "model",
                            "expert_id": expert_choice,
                            "content": reply
                        })
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error fetching response: {e}")

    # -------------------------------------------------------------
    # Column 2: Interactive Day-by-Day Journey Timeline
    # -------------------------------------------------------------
    with col_itinerary:
        st.subheader("📅 Your Personal Guidebook")

        itinerary = st.session_state.active_itinerary
        if not itinerary:
            st.info("💡 Fill out the parameters in the left sidebar and click 'Draft Custom Itinerary' to see your beautiful day-by-day vacation roadmap here!")
        else:
            st.markdown(f"### 📍 {itinerary['destination']}")
            st.markdown(f"*{itinerary['overview']}*")

            # Day switcher tabs
            day_titles = [f"Day {day['dayNumber']}" for day in itinerary['days']]
            day_tabs = st.tabs(day_titles)

            for idx, tab in enumerate(day_tabs):
                day_data = itinerary['days'][idx]
                with tab:
                    st.markdown(f"### {day_data['title']}")
                    for act in day_data['activities']:
                        category_icon = "📍"
                        cat = act.get("category", "").lower()
                        if "food" in cat or "eat" in cat:
                            category_icon = "🍜"
                        elif "shop" in cat or "buy" in cat:
                            category_icon = "🛍️"
                        elif "cultur" in cat or "temple" in cat:
                            category_icon = "🎭"

                        st.markdown(f"""
                        <div class="timeline-item" role="article" aria-label="{act['title']}">
                            <strong style="color:#047857;">{category_icon} {act['time']}</strong> • <strong style="font-size:1.05rem;">{act['title']}</strong><br/>
                            <span style="font-size:0.85rem; color:#4b5563;">📍 Location: {act['locationName']}</span>
                            <p style="margin-top: 6px; font-size:0.9rem; line-height:1.4;">{act['description']}</p>
                            <span style="font-size:0.8rem; font-style:italic; color:#059669;">💡 Expert Tip: {act['expertTip']}</span>
                        </div>
                        """, unsafe_allowed_code_html=True)

                        # Bookmarking Favorites
                        save_key = f"save_{day_data['dayNumber']}_{act['title']}"
                        if st.button(f"📌 Favorite {act['title']}", key=save_key):
                            if act['title'] not in st.session_state.saved_places:
                                st.session_state.saved_places.append(act['title'])
                                st.toast(f"Saved '{act['title']}' to your travel checklist!")

            # Expert Tips Section
            st.markdown("---")
            st.markdown("#### 💡 Transit & Safety Hacks")
            for tip in itinerary.get("expertTips", []):
                st.markdown(f"- {tip}")

    # -------------------------------------------------------------
    # Bottom Section: Saved Spots & Travel Highlights
    # -------------------------------------------------------------
    st.markdown("---")
    st.subheader("📌 Saved Places Checklist")
    
    if not st.session_state.saved_places:
        st.markdown("<p style='color:#6b7280; font-size:0.9rem;'>No places bookmarked yet. Click 'Favorite' on any itinerary recommendation to save them here!</p>", unsafe_allowed_code_html=True)
    else:
        saved_cols = st.columns(min(len(st.session_state.saved_places), 4))
        for p_idx, place in enumerate(st.session_state.saved_places):
            col_idx = p_idx % len(saved_cols)
            with saved_cols[col_idx]:
                st.markdown(f"""
                <div style="background-color:#fffbeb; border:2px solid #b45309; padding:12px; border-radius:8px; margin-bottom:8px;">
                    <span style="font-size:1.1rem;">📍</span> <strong style="font-size:0.85rem; color:#1f2937;">{place}</strong>
                </div>
                """, unsafe_allowed_code_html=True)
                if st.button("🗑️ Remove", key=f"remove_saved_{p_idx}"):
                    st.session_state.saved_places.remove(place)
                    st.rerun()

if __name__ == "__main__":
    main()

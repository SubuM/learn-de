import streamlit as st
import pandas as pd
import requests
import time
import json
import calendar 
import datetime 
import sqlite3 
import hashlib 

# --- 1. CONFIGURATION & DATA ---

# Database configuration
DB_NAME = 'german_progress.db' # SQLite file name

# Text Generation Model (Cost-Free Tier)
GEMINI_MODEL = "gemini-2.5-flash-preview-09-2025"
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

try:
    GEMINI_API_KEY = st.secrets["gemini_api_key"]
except KeyError:
    GEMINI_API_KEY = "PLACEHOLDER_GEMINI_API_KEY"

# Load Static User Credentials from secrets.toml (for DB initialization)
try:
    # This will be a dictionary like {'SMA': 'SecretPassword123', 'AMA': 'AnotherSecretPwd456'}
    STATIC_USERS_DATA = st.secrets["static_users"]
except KeyError:
    st.error("FATAL ERROR: Missing '[static_users]' section in secrets.toml.")
    STATIC_USERS_DATA = {}

# NEW: Load display names from secrets.toml
try:
    # This will be a dictionary like {'SMA': 'Sophia M.', 'AMA': 'Alex M.'}
    USER_DISPLAY_NAMES = st.secrets["user_names"]
except KeyError:
    # Fallback to the username if the section is missing
    USER_DISPLAY_NAMES = {}


# --- 120-DAY STUDY PLAN DATA (REMAINS THE SAME) ---

PHASE_1_DATA = [
    {'Days': '1–6', 'Focus Topic': 'Introduction & Sounds', 'Grammar & Structure': 'The German Alphabet (`Aussprache`), numbers 1–20, basic greetings.', 'Vocabulary (Thematic)': 'Greetings, farewells, courtesy (e.g., `bitte`, `danke`), simple questions.', 'Practice Activities': 'Listen to the German alphabet and sounds. Write out the numbers 1-10 in German daily.'},
    {'Days': '7–14', 'Focus Topic': 'Personal Information', 'Grammar & Structure': 'Subject Pronouns (`ich`, `du`, `er`, etc.), **Verb Conjugation** (regular verbs in the present tense, e.g., `heißen`, `kommen`).', 'Vocabulary (Thematic)': 'Countries, languages, professions (e.g., `Lehrer`, `Student`).', 'Practice Activities': 'Practice conjugating **one** new verb daily. Write 3 sentences daily introducing yourself/others.'},
    {'Days': '15–24', 'Focus Topic': 'Nouns & Articles', 'Grammar & Structure': 'The **Nominative Case**, **Gender** (`der`, `die`, `das`), Plural forms (start recognizing patterns).', 'Vocabulary (Thematic)': 'Family members, objects around the house (`der Tisch`, `das Buch`).', 'Practice Activities': 'Label 5 items in your room daily with their correct German article (Der, Die, Das).'},
    {'Days': '25–32', 'Focus Topic': "The Verb 'Sein' & 'Haben'", 'Grammar & Structure': 'Irregular conjugation of `sein` (to be) and `haben` (to have). Forming simple statement sentences.', 'Vocabulary (Thematic)': 'Adjectives for describing state/feeling (e.g., `alt`, `neu`, `müde`, `gut`).', 'Practice Activities': 'Write 3 sentences using `sein` and 3 sentences using `haben` every day. Focus on correct conjugation.'},
    {'Days': '33–40', 'Focus Topic': 'The Accusative Case', 'Grammar & Structure': 'Definite and Indefinite Articles in Accusative (`den`, `eine`, `keinen`), identifying direct objects.', 'Vocabulary (Thematic)': 'Food and drink (`das Brot`, `der Kaffee`), colors.', 'Practice Activities': 'Practice changing 5 articles from Nominative to Accusative (e.g., `Ich sehe den Hund`).'},
]

PHASE_2_DATA = [
    {'Days': '41–48', 'Focus Topic': 'Negation & Imperative', 'Grammar & Structure': 'Negation (`nicht` and `kein/keine`), simple **Imperative** (commands).', 'Vocabulary (Thematic)': 'Common verbs of movement, everyday tasks (`kaufen`, `machen`).', 'Practice Activities': 'Practice negating 5 sentences written previously (e.g., `Ich habe kein Auto`).'},
    {'Days': '49–56', 'Focus Topic': 'Modal Verbs (Part 1)', 'Grammar & Structure': 'Introduction to `können` (can) and `müssen` (must), main verb goes to the end.', 'Vocabulary (Thematic)': 'Hobbies, abilities, and daily schedules.', 'Practice Activities': 'Write 3 sentences about things you can/must do. Focus on placing the main verb last.'},
    {'Days': '57–64', 'Focus Topic': 'Prepositions of Place', 'Grammar & Structure': 'Introduction to simple **Prepositions of Place** (e.g., `in`, `auf`, `unter`, `neben`).', 'Vocabulary (Thematic)': 'Locations (e.g., `die Bank`, `der Park`).', 'Practice Activities': 'Practice placing objects and describing their location using 3-4 prepositions daily.'},
    {'Days': '65–72', 'Focus Topic': 'Time and Date', 'Grammar & Structure': 'Time (`Es ist...`), Dates, days of the week, months.', 'Vocabulary (Thematic)': 'Days, months, seasons, and time expressions (e.g., `morgen`, `gestern`).', 'Practice Activities': 'Practice telling time. Write down your planned activities for tomorrow using time phrases.'},
    {'Days': '73–80', 'Focus Topic': 'Simple Questions', 'Grammar & Structure': 'W-Questions (`Wer`, `Was`, `Wo`, `Wann`, etc.), forming yes/no questions (verb first).', 'Vocabulary (Thematic)': 'Basic city/travel terms.', 'Practice Activities': 'Practice asking and answering 5 different W-questions about basic facts.'},
]

PHASE_3_DATA = [
    {'Days': '81–88', 'Focus Topic': 'Modal Verbs (Part 2)', 'Grammar & Structure': 'Introduction to `wollen` (want) and `mögen` (like), review all 4 modals.', 'Vocabulary (Thematic)': 'Clothing (`die Hose`, `das Hemd`), shopping terms (`kosten`, `bezahlen`).', 'Practice Activities': 'Practice dialogues for ordering or buying items, focusing on using `möchte` (would like).'},
    {'Days': '89–98', 'Focus Topic': 'The Dative Case', 'Grammar & Structure': 'Dative Articles (`dem`, `der`, `dem`), Dative Prepositions (e.g., `mit`, `nach`, `von`, `zu`). **(Extended period)**', 'Vocabulary (Thematic)': 'Means of transport (`der Zug`, `das Flugzeug`), simple prepositions of movement.', 'Practice Activities': 'Write 3 sentences daily using different Dative prepositions.'},
    {'Days': '99–106', 'Focus Topic': 'Possessive Pronouns', 'Grammar & Structure': 'Possessive Pronouns (`mein/meine`, `dein/deine`), correct use according to gender and case (Nominative/Accusative).', 'Vocabulary (Thematic)': 'Possessions (`der Schlüssel`, `die Tasche`).', 'Practice Activities': 'Describe whose objects belong to whom. Use `mein` and `meine` correctly in 5 sentences daily.'},
    {'Days': '107–114', 'Focus Topic': 'Perfect Tense Introduction', 'Grammar & Structure': 'Introduction to the Perfect Tense (`Perfekt`) using `haben` + Past Participle (for regular verbs).', 'Vocabulary (Thematic)': 'Verbs related to events (`gekauft`, `gemacht`).', 'Practice Activities': 'Describe 3 things you did the day before using the Perfect tense.'},
    {'Days': '115–120', 'Focus Topic': 'Final Review & Dialogue', 'Grammar & Structure': 'Full review of Nominative, Accusative, and Dative articles/pronouns. Review all modal verbs. Practice combining two ideas with `und` and `aber`.', 'Vocabulary (Thematic)': 'Numbers 20–100, common phrases used in restaurants/cafes.', 'Practice Activities': 'Final A1 Assessment: Attempt an official A1 practice test online. Review weak points.'}
]

ALL_PHASE_DATA = PHASE_1_DATA + PHASE_2_DATA + PHASE_3_DATA
# --- END 120-DAY STUDY PLAN DATA ---


# --- 2. HELPER FUNCTIONS AND TRACKER LOGIC ---

def get_current_day_plan(day):
    """Finds the lesson object corresponding to the current study day."""
    for lesson in ALL_PHASE_DATA:
        days_str = lesson['Days'].replace('–', '-')
        if '-' in days_str:
            start, end = map(int, days_str.split('-'))
            if start <= day <= end:
                return lesson
    return None

def check_api_key():
    """Returns True if API key is invalid."""
    if GEMINI_API_KEY == "PLACEHOLDER_GEMINI_API_KEY":
        st.error("⚠️ API Key not configured. Please set 'gemini_api_key' in your secrets.toml.")
        return True
    return False

def call_gemini_api(prompt, system_instruction, url=GEMINI_API_URL, payload_config=None, retries=3):
    """Calls the Gemini API (text only) with exponential backoff."""
    if check_api_key():
        return None

    headers = {'Content-Type': 'application/json'}
    
    # Base payload structure for text generation
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "systemInstruction": {"parts": [{"text": system_instruction}]}
    }

    for i in range(retries):
        try:
            response = requests.post(
                f"{url}?key={GEMINI_API_KEY}",
                headers=headers,
                data=json.dumps(payload),
                timeout=15
            )
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.RequestException as e:
            if i < retries - 1:
                wait_time = 2 ** i
                time.sleep(wait_time)
            else:
                st.error(f"❌ Error: Could not reach Gemini API after {retries} attempts.")
                return None
        except Exception as e:
            st.error(f"❌ Unexpected error during API call: {e}")
            return None
    return None


@st.cache_data(show_spinner=False)
def generate_lesson_content(topic, grammar, vocab):
    """Generates the main lesson (explanation and examples) via the LLM."""
    prompt = (
        f"You are a friendly and clear German language tutor. Your task is to teach the following A1 lesson:\n"
        f"1. **Focus:** {topic}\n"
        f"2. **Grammar:** {grammar}\n"
        f"3. **Vocabulary:** {vocab}\n"
        f"Structure your response with two clear sections:\n"
        f"## 1. Grammatik & Erklärung\n"
        f"Provide a simple, easy-to-understand explanation of the grammar rule with clear tables or bullet points.\n"
        f"## 2. Vokabeln & Beispiele\n"
        f"List the key vocabulary and provide 5 simple German example sentences that use the grammar rule and vocabulary. Provide the English translation below each German sentence."
    )
    result = call_gemini_api(prompt, "You are teaching a German A1 lesson. Be encouraging and concise.")
    return result.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '') if result else "Lesson generation failed."

@st.cache_data(show_spinner=False)
def generate_practice_quiz(topic, grammar):
    """Generates a short practice quiz via the LLM."""
    prompt = (
        f"Create a short, interactive practice quiz based on the German lesson:\n"
        f"**Topic:** {topic}\n"
        f"**Grammar Rule:** {grammar}\n"
        f"Create three (3) fill-in-the-blank questions focusing on the grammar rule. "
        f"Provide the questions clearly, then provide the answers in a separate 'Antworten:' section. "
        f"Questions should be formatted: '1. Ich _____ (sein) müde.' and the Answer should be '1. bin'."
    )
    result = call_gemini_api(prompt, "You are creating a German A1 practice quiz. Ensure questions are numbered, and answers are provided under the exact heading 'Antworten:'.")
    return result.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '') if result else "Quiz generation failed."


# --- AUTHENTICATION & PROGRESS TRACKER FUNCTIONS (SQLITE) ---

def hash_password(password):
    """Simple SHA-256 hash for password storage (local/closed environment)."""
    return hashlib.sha256(password.encode()).hexdigest()

def init_db():
    """Initializes the SQLite database tables (users and progress)."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # 1. User Table Setup
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL
        )
    """)
    
    # 2. Progress Table Setup (MUST include user_id)
    try:
        # Check for the incorrect schema and drop it to prevent the OperationalError.
        cursor.execute("PRAGMA table_info(progress)")
        columns = [info[1] for info in cursor.fetchall()]
        # If the table exists but is missing the user_id column, drop it for recreation.
        if 'user_id' not in columns:
            cursor.execute("DROP TABLE IF EXISTS progress")
    except sqlite3.OperationalError:
        pass 

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS progress (
            user_id TEXT NOT NULL,
            date_str TEXT NOT NULL,
            lesson INTEGER DEFAULT 0,
            quiz INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, date_str)
        )
    """)

    # 3. Insert/Update Static Users from secrets
    for username, password in STATIC_USERS_DATA.items():
        hashed_pwd = hash_password(password)
        cursor.execute("INSERT OR IGNORE INTO users (username, password_hash) VALUES (?, ?)", 
                       (username.upper(), hashed_pwd))
                       
    conn.commit()
    conn.close()

# Initialize DB when the app starts
init_db()

def authenticate_user(username, password):
    """Checks credentials against the stored hash."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT password_hash FROM users WHERE username=?", (username,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        stored_hash = result[0]
        input_hash = hash_password(password)
        return stored_hash == input_hash
    return False


def get_day_status(user_id, date_obj):
    """Retrieves completion status for a specific date and user."""
    if not user_id: return {'lesson': False, 'quiz': False}
    date_str = date_obj.strftime('%Y-%m-%d')
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # QUERY: Select by user_id and date_str (Composite Key)
    cursor.execute("SELECT lesson, quiz FROM progress WHERE user_id=? AND date_str=?", (user_id, date_str))
    result = cursor.fetchone()
    conn.close()
    if result:
        return {'lesson': bool(result[0]), 'quiz': bool(result[1])}
    return {'lesson': False, 'quiz': False}

def update_day_status(user_id, date_obj, part, status):
    """Updates the completion status for a specific date and user."""
    if not user_id: return
    date_str = date_obj.strftime('%Y-%m-%d')
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    value = 1 if status else 0
    
    # Fetch existing status
    current_status = get_day_status(user_id, date_obj)
    
    # Set the new status for the requested part
    if part == 'lesson':
        lesson_val = value
        quiz_val = 1 if current_status['quiz'] else 0
    else: # quiz part
        lesson_val = 1 if current_status['lesson'] else 0
        quiz_val = value
        
    # Use INSERT OR REPLACE to update the record based on the composite key (user_id, date_str)
    cursor.execute(f"""
        INSERT OR REPLACE INTO progress (user_id, date_str, lesson, quiz) 
        VALUES (?, ?, ?, ?)
    """, (user_id, date_str, lesson_val, quiz_val))

    conn.commit()
    conn.close()

def display_progress_calendar(user_id, current_date):
    """Displays a monthly calendar view for progress tracking based on real-world dates."""
    st.sidebar.header("🗓️ Monthly Completion Tracker")
    
    year = current_date.year
    month = current_date.month
    
    cal = calendar.Calendar(firstweekday=calendar.MONDAY) 
    month_days = list(cal.itermonthdates(year, month))
    
    st.sidebar.markdown(f"**{calendar.month_name[month]} {year}**")
    
    # CSS FIX: Injecting robust CSS to eliminate column gaps in the sidebar
    st.sidebar.markdown("""
        <style>
            /* Reset column gaps for the entire calendar grid */
            [data-testid="stSidebar"] [data-testid="stHorizontalBlock"] {
                gap: 0px !important; 
                margin: 0px !important;
                padding: 0px !important;
            }
            /* Target columns inside the sidebar and make them equal and tight */
            [data-testid="stSidebar"] [data-testid^="column"] {
                padding: 0px !important;
                margin: 0px !important;
            }
            /* Specific CSS for the calendar date cells */
            .calendar-cell {
                text-align: center; 
                line-height: 1.1; 
                margin: 1px; 
                height: 35px;
                width: 100%; 
            }
            /* Global font color fix for the dark theme sidebar calendar */
            .calendar-text-dark { 
                color: #000000; /* Explicitly black */
            }
        </style>
    """, unsafe_allow_html=True)
    
    # Calendar Grid Layout (7 columns for 7 days)
    day_labels = st.sidebar.columns(7)
    for i, day in enumerate(["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]):
        with day_labels[i]:
            st.markdown(f"<div class='calendar-cell' style='font-weight: bold; font-size: 0.8em; padding: 2px 0;'>{day}</div>", unsafe_allow_html=True)
            
    # Display the dates
    date_columns = st.sidebar.columns(7)
    col_index = 0
    
    for date in month_days:
        
        with date_columns[col_index]:
            
            # --- Handle Dates Not in Current Month ---
            if date.month != month:
                st.markdown("<div class='calendar-cell'></div>", unsafe_allow_html=True)
                
            # --- Handle Dates IN Current Month ---
            else:
                date_obj = datetime.date(date.year, date.month, date.day)
                
                # Fetch status for the current user and date
                status = get_day_status(user_id, date_obj)
                
                is_completed = status['lesson'] and status['quiz']
                is_partial = status['lesson'] or status['quiz']
                
                if is_completed:
                    bg_color = "#D4EDDA"  # Green-like success
                    icon = "✅"
                elif is_partial:
                    bg_color = "#FFF3CD"  # Yellow-like warning
                    icon = "⚠️"
                else:
                    bg_color = "#F8F9FA"  # Light gray default
                    icon = " "
                    
                # Highlight the current real-world date
                if date_obj == datetime.date.today():
                    border = "2px solid #007bff" # Blue primary color
                else:
                    border = "1px solid #dee2e6"
                
                # HTML for the calendar cell (using the .calendar-cell class)
                # FONT FIX: Applying 'calendar-text-dark' class to ensure date number is visible.
                cell_content = f"""
                <div class='calendar-cell' style='border: {border}; background-color: {bg_color}; border-radius: 4px; padding: 3px 0;'>
                    <span class='calendar-text-dark' style='font-size: 0.9em; font-weight: bold;'>{date.day}</span><br>
                    <span style='font-size: 0.7em;'>{icon}</span>
                </div>
                """
                st.markdown(cell_content, unsafe_allow_html=True)
                
        # Move to the next column
        col_index = (col_index + 1) % 7
    st.sidebar.markdown("---")


# --- 3. STREAMLIT APP LAYOUT ---

# --- STYLING LOGIC FOR CURRENT ROW HIGHLIGHT ---
def highlight_current_phase(s, current_study_day):
    """
    Applies a light blue background and dark text color to the row whose 'Days' range includes the current study day.
    """
    days_str = s['Days'].replace('–', '-')
    
    # Handle single-day and multi-day ranges
    if '-' in days_str:
        start, end = map(int, days_str.split('-'))
    else:
        try:
            start = end = int(days_str)
        except ValueError:
            # Fallback if 'Days' format is unexpected (shouldn't happen with our static data)
            return [''] * len(s)

    # Check if the current study day falls in this row's range
    if start <= current_study_day <= end:
        # Highlighted row: Light blue background AND explicitly set text color to black for readability
        return ['background-color: #E6F3FF; color: #000000'] * len(s) 
    else:
        # Non-highlighted row: Return empty strings to fully defer to the Streamlit theme's default colors
        # (White text on dark background in dark mode). This ensures visibility.
        return [''] * len(s) 


def login_form():
    """Renders the dedicated login screen."""
    
    # Center the login box
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("<h2 style='text-align: center;'>🇩🇪 Login to Dein Deutschlehrer</h2>", unsafe_allow_html=True)
        
        with st.form("login_form"):
            username = st.text_input("Username", key="login_user")
            password = st.text_input("Password", type="password", key="login_pass")
            submitted = st.form_submit_button("Login", type="primary")

            if submitted:
                # Convert username to uppercase to match stored user IDs
                user_id = username.upper()
                if authenticate_user(user_id, password):
                    st.session_state.logged_in = True
                    st.session_state.user_id = user_id
                    st.rerun()
                else:
                    # SECURITY FIX: Generic error message to prevent username fishing
                    st.error("Invalid Username or Password.") 
        st.markdown("---")
        
        # SECURITY FIX: REMOVE DISPLAY OF STATIC_USERS_DATA
        # This section is removed to prevent exposing usernames and passwords.


def main_app_content(current_user_id):
    """Renders the main learning interface after successful login."""
    
    # Get current date object for tracking/calendar
    current_date_obj = datetime.date.today()
    
    # Initialize session state for tracking study day
    if 'study_day' not in st.session_state:
        st.session_state.study_day = 1
    
    # Initialize logout confirmation state
    if 'confirm_logout' not in st.session_state:
        st.session_state.confirm_logout = False

    # Get the personalized display name
    # Fallback to the user ID if the name is not defined in the secrets file
    real_name = USER_DISPLAY_NAMES.get(current_user_id, current_user_id)

    # --- SIDEBAR: PROGRESS TRACKER ---
    with st.sidebar:
        # PERSONALIZATION FIX: Display real name
        st.header(f"👋 Welcome, {real_name}")
        st.markdown("---")
        st.header("🎯 Dein Lernfortschritt")
        
        new_day = st.slider(
            "Current Study Day (1-120)",
            min_value=1,
            max_value=120,
            value=st.session_state.study_day,
            key='day_slider'
        )
        # Ensure day changes trigger cache reset
        if new_day != st.session_state.study_day:
            st.session_state.study_day = new_day
            st.rerun()

        st.metric("Total Days Remaining", 120 - st.session_state.study_day)
        
        # --- Logout Confirmation Logic (NEW) ---
        if st.session_state.confirm_logout:
            st.warning("Are you sure you want to log out? Your progress is saved.")
            col_confirm, col_cancel = st.columns(2)
            
            with col_confirm:
                if st.button("Confirm Logout", key="btn_confirm_logout", type="secondary", use_container_width=True):
                    st.session_state.logged_in = False
                    st.session_state.user_id = None
                    st.session_state.confirm_logout = False 
                    st.rerun()
            
            with col_cancel:
                if st.button("Cancel", key="btn_cancel_logout", use_container_width=True):
                    st.session_state.confirm_logout = False
                    st.rerun()
        else:
            # Initial Logout Button (only visible if not confirming)
            if st.button("Logout", key="btn_logout_initial", use_container_width=True):
                st.session_state.confirm_logout = True
                st.rerun()
        # ----------------------------------------

        if st.button("Reset Cache & Lesson", help="Clears the generated lesson content and quiz."):
            generate_lesson_content.clear()
            generate_practice_quiz.clear()
            st.rerun()
            
        display_progress_calendar(current_user_id, current_date_obj)
        st.caption("Tracking is based on the **real-world date**.")
        st.caption(f"Progress stored for user: **{current_user_id}**")


    # --- MAIN CONTENT ---
    
    current_lesson = get_current_day_plan(st.session_state.study_day)
    
    if not current_lesson:
        st.error("Error: Could not find lesson plan for this day.")
        return

    # Extract current lesson data
    day_range = current_lesson['Days']
    topic = current_lesson['Focus Topic']
    grammar = current_lesson['Grammar & Structure']
    vocab = current_lesson['Vocabulary (Thematic)']
    activity = current_lesson['Practice Activities']
    
    # Fetch status based on the current date object
    lesson_status = get_day_status(current_user_id, current_date_obj)['lesson']
    quiz_status = get_day_status(current_user_id, current_date_obj)['quiz']

    current_study_day = st.session_state.study_day
    
    st.header(f"📅 Lesson Day: {current_study_day} (Topics for Days {day_range})")
    
    tab_lesson, tab_quiz, tab_plan = st.tabs(["📚 Today's Lesson (LLM)", "📝 Practice Quiz (LLM)", "🗓️ Full 120-Day Plan"])

    # TAB 1: LLM-Generated Lesson
    with tab_lesson:
        col_lesson_btn, col_lesson_info = st.columns([1, 4])
        
        # Tracking Button for Lesson (Marks current date complete)
        with col_lesson_btn:
            if st.button("Mark Lesson Complete", disabled=lesson_status, key="mark_lesson_btn", type="primary"):
                update_day_status(current_user_id, current_date_obj, 'lesson', True)
                st.rerun()
            if lesson_status:
                st.success(f"Lesson marked complete for today!")
        
        with col_lesson_info:
            st.markdown(f"#### Focus: {topic}")


        with st.spinner("Generating customized lesson explanation..."):
            lesson_content = generate_lesson_content(topic, grammar, vocab)
        
        st.markdown(lesson_content)
        
        st.markdown("---")
        st.markdown(f"**Actionable Practice:** {activity}")


    # TAB 2: LLM-Generated Quiz
    with tab_quiz:
        col_quiz_btn, col_quiz_info = st.columns([1, 4])
        
        # Tracking Button for Quiz (Marks current date complete)
        with col_quiz_btn:
            if st.button("Mark Quiz Complete", disabled=quiz_status, key="mark_quiz_btn", type="primary"):
                update_day_status(current_user_id, current_date_obj, 'quiz', True)
                st.rerun()
            if quiz_status:
                st.success(f"Quiz marked complete for today!")
                
        with col_quiz_info:
            st.markdown(f"#### Practice for Day {current_study_day}: {topic}")
            st.markdown("Test your understanding with a quick grammar check!")
        
        with st.spinner("Generating practice questions..."):
            quiz_content = generate_practice_quiz(topic, grammar)
            
        SEPARATOR = "Antworten:" 
        
        if SEPARATOR in quiz_content:
            quiz_parts = quiz_content.split(SEPARATOR, 1) 
            
            if len(quiz_parts) == 2:
                questions = quiz_parts[0].strip()
                answers = quiz_parts[1].strip()
                
                # Display questions
                st.markdown(questions)
                
                # Display answers in a simple expander
                with st.expander("Show Answers (Antworten)"):
                    st.markdown(answers)
            else:
                st.warning("The quiz structure was confusing. Displaying raw content:")
                st.markdown(quiz_content)
        else:
            st.error("The language model failed to separate questions and answers correctly. Displaying raw content:")
            st.markdown(quiz_content)


    # TAB 3: Full 120-Day Plan
    with tab_plan:
        
        # --- PHASE 1 DISPLAY ---
        st.header("The Complete 120-Day Sustainable German Plan")
        st.subheader("Phase 1: The Basics & Building Blocks (Days 1-40)")
        st.markdown("**Goal:** Master the alphabet, basic greetings, personal pronouns, verb conjugation, and fundamental sentence structure.")
        st.dataframe(
            pd.DataFrame(PHASE_1_DATA).style.apply(highlight_current_phase, 
                                                   current_study_day=current_study_day,
                                                   axis=1),
            use_container_width=True, 
            hide_index=True
        )

        # --- PHASE 2 DISPLAY ---
        st.subheader("Phase 2: Ordering & Directions (Days 41–80)")
        st.markdown("**Goal:** Understand prepositions, transportation, location, time, and form simple questions/negations.")
        st.dataframe(
            pd.DataFrame(PHASE_2_DATA).style.apply(highlight_current_phase, 
                                                   current_study_day=current_study_day, 
                                                   axis=1),
            use_container_width=True, 
            hide_index=True
        )

        # --- PHASE 3 DISPLAY ---
        st.subheader("Phase 3: Consolidation & Advanced A1 Topics (Days 81–120)")
        st.markdown("**Goal:** Consolidate grammar, understand the Dative case basics, and handle common dialogue situations.")
        st.dataframe(
            pd.DataFrame(PHASE_3_DATA).style.apply(highlight_current_phase, 
                                                   current_study_day=current_study_day, 
                                                   axis=1),
            use_container_width=True, 
            hide_index=True
        )


def app():
    st.set_page_config(
        page_title="120-Day German Teacher",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    st.title("🇩🇪 Dein Deutschlehrer (Your German Teacher)")
    st.markdown("A 120-day plan to reach A1 proficiency in 30 minutes a day.")
    st.markdown("---")

    # Initialize login state
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'user_id' not in st.session_state:
        st.session_state.user_id = None
    if 'confirm_logout' not in st.session_state:
        st.session_state.confirm_logout = False
    
    # Render either the login form or the main app content
    if st.session_state.logged_in and st.session_state.user_id:
        main_app_content(st.session_state.user_id)
    else:
        login_form()


if __name__ == "__main__":
    app()

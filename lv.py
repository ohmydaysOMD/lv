import streamlit as st
import google.generativeai as genai
import json
import os
from datetime import datetime
from docx import Document
import io
import tempfile
import re

# --- Utility to prettify keys ---
def prettify_key(key):
    """Converts a camelCase or snake_case key into a title-cased string."""
    key = key.replace('_', ' ')
    key = re.sub(r'([a-z])([A-Z])', r'\1 \2', key)
    return key.title() + ":"

# --- Lee Valley Golf Club Minutes Generator (Updated) ---
def generate_golf_club_minutes(structured):
    """Generates meeting minutes text based on the Lee Valley Golf Club template."""
    now = datetime.now()

    # UPDATED: Helper to get value or fallback to an empty string for cleaner processing.
    # It now performs a case-insensitive check for "not mentioned".
    def get(val, default=""):
        return val if val and str(val).strip().lower() != "not mentioned" else default

    # UPDATED: Helper for formatting lists. If a section is empty or "Not mentioned",
    # it now returns an empty string, leaving the section blank as requested.
    def format_items(val):
        """Formats a list into bullet points. Returns an empty string if the list is empty."""
        if isinstance(val, list) and val:
            # Filter out any empty or placeholder strings from the list before joining
            items = [item for item in val if str(item).strip() and str(item).strip().lower() != "not mentioned"]
            if items:
                return "".join([f"• {item}\n" for item in items])
        elif isinstance(val, str) and val.strip() and val.strip().lower() != "not mentioned":
            return f"• {val}\n"
        # Return an empty string to leave the section blank if no data is present.
        return ""

    # --- Extract data from the structured JSON using the updated helper ---
    title = get(structured.get("titleOfMeeting"))
    purpose = get(structured.get("purposeOfMeeting"))
    location = get(structured.get("locationOfMeeting"))
    attendees = structured.get("attendees", [])
    apologies = structured.get("apologies", [])
    meeting_date_time = get(structured.get("meetingDateTime"))
    next_meeting_date_time = get(structured.get("nextMeetingDateTime"))
    prepared_by = get(structured.get("minutesPreparedBy"))
    date_circulated = get(structured.get("dateCirculated"))
    circulation = get(structured.get("circulation"))

    # --- Meeting body items ---
    training = format_items(structured.get("training", []))
    health_safety = format_items(structured.get("healthAndSafety", []))
    finance = format_items(structured.get("finance", []))
    issues_risk_discipline = format_items(structured.get("issuesRiskDiscipline", []))
    teams = format_items(structured.get("teams", []))
    projects = format_items(structured.get("projects", []))
    competitions = format_items(structured.get("competitions", []))
    comments = format_items(structured.get("comments", []))
    aob = format_items(structured.get("anyOtherBusiness", []))
    captains_comments = format_items(structured.get("captainsClosingComments", []))

    # --- Compose the minutes string (Updated with defaults for key fields) ---
    template = f"""
Title of Meeting: {title or 'Lee Valley Mens Club Committee Meeting'}
Purpose of Meeting: {purpose}
Location of Meeting: {location or 'Lee Valley'}
Date / Time of Meeting: {meeting_date_time or now.strftime("%d/%m/%Y @ %H:%M")}
Date / Time of Next Meeting: {next_meeting_date_time}
Minutes Prepared By: {prepared_by}
Date Circulated: {date_circulated or now.strftime("%d/%m/%Y")}
Circulation: {circulation}

________________________________________
ATTENDEES:
{format_items(attendees) or '• None listed'}
________________________________________
APOLOGIES:
{format_items(apologies) or '• None listed'}
________________________________________

MEETING MINUTES & ACTIONS
________________________________________

1. Training (First Aid, Programmes, etc.)
{training}
________________________________________
2. Health and Safety
{health_safety}
________________________________________
3. Finance (Status, Projections)
{finance}
________________________________________
4. Issues, Risk, Discipline
{issues_risk_discipline}
________________________________________
5. Teams (Purcell, Bruen, etc.)
{teams}
________________________________________
6. Projects (Defib, Simulator, 5 Year Vision)
{projects}
________________________________________
7. Competitions (Weekly, Matchplays)
{competitions}
________________________________________
8. Comments
{comments}
________________________________________
9. Any Other Business (AOB)
{aob}
________________________________________
10. Captain's Closing Comments
{captains_comments}
"""
    return template.strip()

# --- DOCX Export Functions (No changes needed here) ---
def create_narrative_docx(narrative_text):
    """Creates a DOCX for the narrative summary."""
    doc = Document()
    doc.add_heading("Lee Valley Golf Club - Meeting Summary", level=1)
    doc.add_paragraph(narrative_text)
    output = io.BytesIO()
    doc.save(output)
    output.seek(0)
    return output

def create_keypoints_docx(text):
    """Creates a DOCX for key points and actions."""
    doc = Document()
    doc.add_heading("Lee Valley Golf Club - Key Points & Actions", level=1)
    doc.add_paragraph(text)
    output = io.BytesIO()
    doc.save(output)
    output.seek(0)
    return output

def create_minutes_docx(content):
    """Creates a formatted DOCX for the final minutes."""
    doc = Document()
    doc.add_heading("Lee Valley Golf Club Meeting Minutes", level=1)
    # Simple line-by-line processing, can be enhanced for better formatting
    for line in content.splitlines():
        if line.strip().endswith(":") and not line.startswith("•"):
             # Simple check for headings
            try:
                doc.add_heading(line.strip(), level=2)
            except Exception:
                doc.add_paragraph(line) # Fallback for any heading issues
        elif line.strip() == "________________________________________":
            doc.add_paragraph("--------------------------------------------------")
        elif line.strip():
            doc.add_paragraph(line)

    output = io.BytesIO()
    doc.save(output)
    output.seek(0)
    return output

# --- Configure Gemini API ---
try:
    # It's recommended to use st.secrets for API keys
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel(model_name='gemini-1.5-flash')
except KeyError:
    st.error("GEMINI_API_KEY not found in Streamlit secrets. Please add it to continue.")
    st.stop()
except Exception as e:
    st.error(f"Error configuring Gemini API: {e}")
    st.stop()

st.set_page_config(page_title="LVGC Minutes", layout="wide", page_icon="https://www.leevalleygcc.ie/wp-content/themes/leevalley/favicon.ico")

# --- Logo Data ---
logo_url = "https://kerryseniorgolf.com/wp-content/uploads/2022/02/lee-valley-golf-country-club-logo.png"

# --- Password protection ---
if "password_verified" not in st.session_state:
    st.session_state.password_verified = False

if not st.session_state.password_verified:
    st.title("🔒 LVGC Minutes Recap Access")
    st.warning("This application requires a password to proceed.")
    with st.form("password_form"):
        user_password = st.text_input("Enter password:", type="password", key="password_input")
        submit_button = st.form_submit_button("Submit")
        if submit_button:
            try:
                expected_password = st.secrets["password"]
                if user_password == expected_password:
                    st.session_state.password_verified = True
                    st.rerun()
                else:
                    st.error("Incorrect password. Please try again.")
            except KeyError:
                st.error("Password not configured in Streamlit secrets. Please contact the administrator.")
            except Exception as e:
                st.error(f"An error occurred during password verification: {e}")
    st.stop()

# --- Sidebar ---
with st.sidebar:
    st.image(logo_url, use_container_width=True)
    st.title("📒 LVGC Minutes")
    
    if st.button("🔄 Restart Session"):
        keys_to_clear = ['transcript', 'structured', 'minutes', 'narrative', 'keypoints_summary']
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

    if st.button("About this App", key="about_button_sidebar"):
        st.sidebar.info(
            "**LVGC Minutes Recap** helps generate meeting minutes for the Lee Valley Golf Club committee. "
            "Upload or record audio, and the app will transcribe and summarise it."
        )
    if st.button("Created by Dave Maher", key="creator_button_sidebar"):
        st.sidebar.write("This application's intellectual property belongs to Dave Maher.")
    st.markdown("---")
    st.markdown("Version: 2.1.0 (LVGC)")

# --- Main UI Header ---
col1, col2 = st.columns([1, 6])
with col1:
    st.image(logo_url, width=180)
with col2:
    st.title("📝 LVGC Minutes Recap")
    st.markdown("#### Lee Valley Golf Club Minute-AI (MAI) Generator")

st.markdown("### 📤 Record or Upload Meeting Audio")

# --- Input Method Selection ---
mode = st.radio(
    "Choose input method:",
    ["Record using microphone", "Upload audio file"],
    horizontal=True,
    key="input_mode_radio"
)

audio_bytes = None

if mode == "Upload audio file":
    uploaded_audio = st.file_uploader(
        "Upload an audio file (WAV, MP3, M4A, OGG, FLAC)",
        type=["wav", "mp3", "m4a", "ogg", "flac"],
        key="audio_uploader"
    )
    if uploaded_audio:
        st.audio(uploaded_audio)
        audio_bytes = uploaded_audio

elif mode == "Record using microphone":
    # Using st.audio_input as a placeholder for a recording component
    st.info("Recording functionality is browser-dependent. Please use the upload feature for best results.")
    # This component is not a standard Streamlit widget, you might need a custom component for robust recording.
    # For now, this is a conceptual placeholder.
    recorded_audio = st.file_uploader("Upload your recording here after you finish.", type=["wav", "mp3", "m4a"])
    if recorded_audio:
        st.audio(recorded_audio)
        audio_bytes = recorded_audio

# --- Transcription and Analysis ---
if audio_bytes and st.button("🧠 Transcribe & Analyse", key="transcribe_button"):
    with st.spinner("Processing with Gemini... This may take a few minutes for longer audio."):
        if hasattr(audio_bytes, "read"):
            audio_data_bytes = audio_bytes.read()
        else:
            st.error("Could not read audio data. Please try again.")
            st.stop()
        
        file_extension = ".wav" # Default
        if hasattr(audio_bytes, 'name') and isinstance(audio_bytes.name, str):
            original_extension = os.path.splitext(audio_bytes.name)[1].lower()
            if original_extension:
                file_extension = original_extension

        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp_file:
            tmp_file.write(audio_data_bytes)
            tmp_file_path = tmp_file.name
        
        try:
            st.info(f"Uploading audio to Gemini for processing...")
            audio_file_display_name = f"LVGC_Recap_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            audio_file = genai.upload_file(path=tmp_file_path, display_name=audio_file_display_name)
            st.success(f"Audio uploaded successfully: {audio_file.name}")

            prompt = (
                "You are an expert transcriptionist for Lee Valley Golf Club committee meetings. "
                "Transcribe in UK English the following meeting audio accurately. "
                "For each speaker, if a name is mentioned, use their name (e.g., Captain:, John Smith:). "
                "If not, label generically as Speaker 1:, Speaker 2:, etc., incrementing for each new unidentified voice."
            )
            result = model.generate_content([prompt, audio_file], request_options={"timeout": 1200})
            st.session_state["transcript"] = result.text
            st.success("Transcript generated successfully.")

        except Exception as e:
            st.error(f"An error occurred during transcription: {e}")
        finally:
            if 'audio_file' in locals() and audio_file:
                try:
                    genai.delete_file(audio_file.name)
                    st.info(f"Cleaned up uploaded file: {audio_file.name}")
                except Exception as del_e:
                    st.warning(f"Could not delete uploaded file {audio_file.name} from Gemini: {del_e}")
            if os.path.exists(tmp_file_path):
                os.remove(tmp_file_path)

# --- Display Transcript and Generate Minutes ---
if "transcript" in st.session_state:
    st.markdown("---")
    st.markdown("## 📄 Transcript")
    st.text_area("Full Meeting Transcript:", st.session_state["transcript"], height=300, key="transcript_display_area")

    if st.button("📊 Extract & Format Meeting Minutes", key="summarise_button"):
        with st.spinner("Generating structured meeting minutes..."):
            try:
                current_transcript = st.session_state['transcript']
                # UPDATED PROMPT: More explicit instructions to prevent hallucination.
                prompt_structured = f"""
You are an AI assistant for Lee Valley Golf Club meetings.
Your task is to extract detailed, structured information from the provided meeting transcript and return a single JSON object.
Use UK English. Format all dates as DD/MM/YYYY and all times as HH:MM (24 hour).

CRITICAL INSTRUCTION: Only extract information explicitly present in the transcript. If a topic or key is not mentioned AT ALL, you MUST use an empty list `[]` for its value. Do NOT invent, infer, or fabricate any information. For example, if 'finance' is not discussed, the value for the 'finance' key must be `[]`.

Keys to extract:
- titleOfMeeting
- purposeOfMeeting
- locationOfMeeting
- meetingDateTime
- attendees (list of names)
- apologies (list of names)
- minutesPreparedBy
- dateCirculated
- circulation (string describing who gets the minutes)
- nextMeetingDateTime
- training (list of key points/actions)
- healthAndSafety (list of key points/actions)
- finance (list of key points/actions)
- issuesRiskDiscipline (list of key points/actions)
- teams (list of key points/actions, e.g., Purcell, Bruen)
- projects (list of key points/actions, e.g., Defib, Simulator, 5 Year Vision)
- competitions (list of key points/actions, e.g., weekly, matchplays)
- comments (list of general comments made)
- anyOtherBusiness (list of AOB points)
- captainsClosingComments (list of points)

Transcript:
---
{current_transcript}
---

Provide ONLY the JSON object in your response. Do not include any other text or markdown formatting.
"""
                response = model.generate_content(prompt_structured, request_options={"timeout": 600})
                
                # Clean and parse JSON
                json_text_match = re.search(r"```json\s*([\s\S]*?)\s*```|({[\s\S]*})", response.text, re.DOTALL)
                if json_text_match:
                    json_str = json_text_match.group(1) or json_text_match.group(2)
                    try:
                        structured = json.loads(json_str.strip())
                        st.session_state["structured"] = structured
                        # Generate minutes immediately after successful extraction
                        minutes_text = generate_golf_club_minutes(structured)
                        st.session_state["minutes"] = minutes_text
                        st.success("Meeting minutes generated in Lee Valley Golf Club format.")
                    except json.JSONDecodeError as e:
                        st.error(f"❌ Failed to parse JSON from AI response. Error: {e}")
                        st.code(json_str.strip(), language="json")
                else:
                    st.error("❌ No valid JSON object found in Gemini's response for structured summary.")
                    st.code(response.text)

            except Exception as e:
                st.error(f"An error occurred during summarization: {e}")

# --- Display Formatted Minutes and Download ---
if "minutes" in st.session_state:
    st.markdown("---")
    st.markdown("## ⛳ Lee Valley Golf Club Meeting Minutes (Draft)")
    st.text_area(
        "Drafted Meeting Minutes:",
        st.session_state["minutes"],
        height=900,
        key="minutes_text_area"
    )
    st.download_button(
        label="📥 Download Minutes (DOCX)",
        data=create_minutes_docx(st.session_state["minutes"]),
        file_name=f"LeeValleyGC_Minutes_{datetime.now().strftime('%Y%m%d_%H%M')}.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        key="download_minutes_docx"
    )

# --- Generate, Display, and Download Summaries ---
if "transcript" in st.session_state:
    st.markdown("---")
    st.markdown("## 🔍 Meeting Summaries")
    
    col1, col2 = st.columns(2)

    with col1:
        if st.button("📝 Generate Narrative Summary", key="narrative_button"):
            with st.spinner("Creating a narrative summary..."):
                try:
                    prompt_narrative = f"""
You are an AI assistant creating a professional, concise summary of a Lee Valley Golf Club committee meeting in UK English.
Based on the following transcript, write a coherent, narrative summary. The summary should be well-organized and capture the main points, discussions, and outcomes.

Transcript:
---
{st.session_state['transcript']}
---
Narrative Summary:"""
                    response = model.generate_content(prompt_narrative, request_options={"timeout": 600})
                    st.session_state["narrative"] = response.text
                except Exception as e:
                    st.error(f"Error generating narrative summary: {e}")

    with col2:
        if st.button("🧾 Generate Key Points & Actions", key="keypoints_button"):
            with st.spinner("Summarising for key points and actions..."):
                try:
                    prompt_keypoints = f"""
You are an AI assistant for Lee Valley Golf Club committee meetings.
Summarise the following transcript into concise bullet points, focusing on:
- Key discussion points
- Major decisions made
- All action items (with responsible persons/roles and deadlines, if mentioned)

Be succinct, avoid repetition, and use bullet points.

Transcript:
---
{st.session_state['transcript']}
---"""
                    response = model.generate_content(prompt_keypoints, request_options={"timeout": 600})
                    st.session_state["keypoints_summary"] = response.text
                except Exception as e:
                    st.error(f"Error generating key points summary: {e}")

    if "narrative" in st.session_state:
        st.markdown("### Narrative Summary")
        st.text_area("Meeting Narrative:", st.session_state["narrative"], height=400, key="narrative_text_area")
        st.download_button(
            label="📥 Download Narrative (DOCX)",
            data=create_narrative_docx(st.session_state["narrative"]),
            file_name=f"LVGC_Narrative_Summary_{datetime.now().strftime('%Y%m%d_%H%M')}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            key="download_narrative_docx"
        )

    if "keypoints_summary" in st.session_state:
        st.markdown("### Key Points & Actions")
        st.text_area("Key Points & Actions:", st.session_state["keypoints_summary"], height=400, key="keypoints_text_area")
        st.download_button(
            label="📥 Download Key Points (DOCX)",
            data=create_keypoints_docx(st.session_state["keypoints_summary"]),
            file_name=f"LVGC_KeyPoints_{datetime.now().strftime('%Y%m%d_%H%M')}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            key="download_keypoints_docx"
        )

# --- Footer ---
st.markdown("---")
st.markdown(
    "**Disclaimer:** This implementation is a draft. "
    "Adjustments may be required for optimal performance. "
    "Always verify the accuracy of AI-generated transcriptions and minutes."
)
st.markdown("Created by Dave Maher | For Lee Valley Golf Club internal use.")




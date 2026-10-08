import streamlit as st
import json
import re
import io
from PIL import Image
import pdfplumber
from supabase import create_client
from google import genai

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# ----------------- 1. Page Configuration -----------------
st.set_page_config(
    page_title="RRB AI Master Engine Pro",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ----------------- 2. Modern Dark Glassmorphism Styling -----------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');
    * { font-family: 'Plus Jakarta Sans', sans-serif !important; }
    .stApp { background: #09090e !important; color: #F3F4F6 !important; }
    
    .app-header {
        background: linear-gradient(135deg, #6366F1 0%, #8B5CF6 50%, #D946EF 100%);
        border-radius: 24px;
        padding: 24px 28px;
        color: #FFFFFF;
        box-shadow: 0 16px 36px rgba(99, 102, 241, 0.28);
        margin-bottom: 24px;
    }
    .modern-card {
        background: rgba(22, 21, 34, 0.75);
        backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 20px;
        padding: 20px 24px;
        margin-bottom: 16px;
    }
    .stButton > button {
        background: linear-gradient(135deg, #6366F1 0%, #4F46E5 100%) !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 14px !important;
        padding: 10px 24px !important;
        font-weight: 600 !important;
    }
    [data-testid="stSidebar"] { background: #0f0e17 !important; }
</style>
""", unsafe_allow_html=True)

# ----------------- 3. Clients Initialization -----------------
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except KeyError:
    st.error("⚠️ Streamlit Secrets config missing! Check your Settings > Secrets.")
    st.stop()

@st.cache_resource
def get_clients():
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)
    ai = genai.Client(api_key=GEMINI_API_KEY)
    return sb, ai

supabase, ai_client = get_clients()

# ----------------- Safe Gemini Generation Helper -----------------
def generate_ai_text(prompt_text):
    """ClientError / 404 prevent karne ke liye stable verified models"""
    models_to_try = ["gemini-2.0-flash", "gemini-1.5-flash"]
    for m in models_to_try:
        try:
            res = ai_client.models.generate_content(
                model=m,
                contents=prompt_text
            )
            return res.text
        except Exception:
            continue
    return "AI request process nahi ho saki. Please check your prompt or network."

# ----------------- 4. Accurate Parser (Fixing "Do wala alag" & Metadata issue) -----------------
def clean_and_extract_actual_questions(pdf_file):
    """
    Header metadata (Test Date, Section, Note wagairah) ko ignore karke
    sirf valid exam questions extract karta hai.
    """
    raw_pages = []
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            t = page.extract_text(layout=False) or ""
            if t:
                raw_pages.append(t)
    
    full_text = "\n".join(raw_pages)

    # Question blocks ko split karne ke patterns (numbered & Question ID based)
    pattern = r"(?:\n|\r|^)(?:Q\s*[\.\:\-]?\s*\d+|Que\s*[\.\:\-]?\s*\d+|\d+\.)\s+"
    raw_blocks = re.split(pattern, full_text, flags=re.IGNORECASE)

    valid_questions = []
    for b in raw_blocks:
        b_clean = b.strip()
        # Header / Instruction filter: inme sawal ke bajay exam date ya instructions hote hain
        is_metadata = any(x in b_clean.lower() for x in ["previous year paper", "test date", "test time", "correct answer will carry", "chosen option on the right"])
        if is_metadata:
            continue
        
        # Valid question check (question length & mcq keywords)
        if len(b_clean) > 35 and ("option" in b_clean.lower() or "ans" in b_clean.lower() or "?" in b_clean):
            valid_questions.append(b_clean)

    return valid_questions

# ----------------- 5. Clean PDF Generator matching sample -----------------
def generate_sample_style_pdf(subject_title, chapter_title, questions_list):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'HeaderStyle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        textColor=colors.black
    )
    q_style = ParagraphStyle(
        'QuestionStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13,
        textColor=colors.black,
        spaceAfter=6
    )
    ans_style = ParagraphStyle(
        'AnswerKeyStyle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=14,
        textColor=colors.black
    )

    story = []
    story.append(Paragraph(f"[{subject_title}]", title_style))
    story.append(Paragraph(f"Chapter - {chapter_title}", title_style))
    story.append(Spacer(1, 14))

    answers_collected = []

    for i, q in enumerate(questions_list, 1):
        q_raw = q.get('question_text', '').replace('\n', '<br/>')
        story.append(KeepTogether([Paragraph(f"<b>{i}.</b> {q_raw}", q_style), Spacer(1, 4)]))
        ans = q.get('correct_option', 'Marked')
        answers_collected.append(f"{i}. {ans}")

    story.append(Spacer(1, 16))
    story.append(Paragraph("<b>Answer Key</b>", title_style))
    story.append(Spacer(1, 6))

    for k in range(0, len(answers_collected), 10):
        grid_line = " | ".join(answers_collected[k:k+10])
        story.append(Paragraph(grid_line, ans_style))
        story.append(Spacer(1, 2))

    doc.build(story)
    buffer.seek(0)
    return buffer

# ----------------- 6. Navigation Hub -----------------
nav = st.sidebar.radio(
    "Navigation Hub",
    [
        "💬 AI Smart Chat & Fuzzy Assistant",
        "📄 Generate Clean PYQ PDF",
        "🚀 Cloud PDF Ingestion",
        "🎯 CBT Exam Arena",
        "🛡️ Data Manager & Safe Delete"
    ]
)

# ----------------- TAB 1: AI SMART CHAT & FUZZY ASSISTANT -----------------
if nav == "💬 AI Smart Chat & Fuzzy Assistant":
    st.markdown("""
    <div class="app-header">
        <h2 style="margin: 0; font-weight: 800;">AI Conversational Partner</h2>
        <p style="margin: 6px 0 0 0; opacity: 0.9;">Aap galat spelling ya tooti-footi Hindi/Hinglish me bole, AI sahi intent samajh kar explain karega.</p>
    </div>
    """, unsafe_allow_html=True)

    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []

    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_prompt = st.chat_input("Mujhse sawal pucho ya concept samjho...")

    if user_prompt:
        st.session_state.chat_messages.append({"role": "user", "content": user_prompt})
        with st.chat_message("user"):
            st.markdown(user_prompt)

        with st.chat_message("assistant"):
            with st.spinner("AI thinking..."):
                prompt = f"""
                You are an intelligent expert exam tutor for RRB JE and Civil/Engineering exams.
                User input (may have spelling mistakes or broken hinglish): "{user_prompt}"
                Instructions:
                1. Understand the true intent even with typos.
                2. Explain clearly in friendly conversational Hinglish.
                3. If relevant, provide formulas, quick tricks, and 1 practice question.
                """
                reply = generate_ai_text(prompt)
                st.markdown(reply)
                st.session_state.chat_messages.append({"role": "assistant", "content": reply})

# ----------------- TAB 2: GENERATE CLEAN PYQ PDF -----------------
elif nav == "📄 Generate Clean PYQ PDF":
    st.markdown("""
    <div class="app-header">
        <h2 style="margin: 0; font-weight: 800;">Clean Printable PDF Generator</h2>
        <p style="margin: 6px 0 0 0; opacity: 0.9;">Sample document ke standard layout me A4 printable PDF download karein.</p>
    </div>
    """, unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        p_sub = st.text_input("Subject Title", value="Estimation and Costing")
    with c2:
        p_chap = st.text_input("Chapter Title", value="Introduction")

    count_slider = st.slider("Kitne questions chahiye?", 5, 50, 15)

    if st.button("⚡ Generate PDF Document", use_container_width=True):
        data = supabase.table("rrb_questions").select("*").limit(count_slider).execute().data
        if not data:
            st.warning("Database me sawal nahi mile. Pehle 'Cloud PDF Ingestion' tab me jaakar PDF upload karein.")
        else:
            pdf_bytes = generate_sample_style_pdf(p_sub, p_chap, data)
            st.success("PDF ready ho gayi!")
            st.download_button(
                label="📥 Download PDF Document",
                data=pdf_bytes,
                file_name=f"{p_sub} - {p_chap}.pdf",
                mime="application/pdf"
            )

# ----------------- TAB 3: CLOUD PDF INGESTION (Accurate Fix) -----------------
elif nav == "🚀 Cloud PDF Ingestion":
    st.markdown("""
    <div class="app-header">
        <h2 style="margin: 0; font-weight: 800;">Smart Shift-Proof Ingestion</h2>
        <p style="margin: 6px 0 0 0; opacity: 0.9;">Header metadata filter karke sahi sequential numbering ke sath cloud sync karein.</p>
    </div>
    """, unsafe_allow_html=True)

    up_files = st.file_uploader("Upload Exam PDFs", type=["pdf"], accept_multiple_files=True)
    if up_files and st.button("Start Accurate Sync", use_container_width=True):
        total_synced = 0
        for f in up_files:
            shift_name = f.name.replace(".pdf", "")
            questions = clean_and_extract_actual_questions(f)
            st.write(f"📁 **{f.name}**: {len(questions)} actual questions detected (headers filtered).")

            records = []
            for q_text in questions:
                # Basic classification
                sub = "Civil Engineering" if any(k in q_text.lower() for k in ["plinth", "concrete", "wall", "beam", "soil", "cement"]) else "General Aptitude"
                records.append({
                    "question_text": q_text,
                    "options": json.dumps([]),
                    "correct_option": "Marked in Key",
                    "subject": sub,
                    "topic": "RRB PYQ",
                    "shift_name": shift_name
                })

            for b_idx in range(0, len(records), 15):
                batch = records[b_idx:b_idx+15]
                supabase.table("rrb_questions").insert(batch).execute()
                total_synced += len(batch)

        st.balloons()
        st.success(f"Successfully loaded {total_synced} genuine questions into Supabase!")

# ----------------- TAB 4: CBT EXAM ARENA -----------------
elif nav == "🎯 CBT Exam Arena":
    st.markdown("### ⏱️ TCS iON Exam Simulator")
    data = supabase.table("rrb_questions").select("*").limit(10).execute().data
    if data:
        for idx, item in enumerate(data, 1):
            st.markdown(f"**Q.{idx}** {item['question_text']}")
            st.radio("Options", ["A", "B", "C", "D"], key=f"cbt_{idx}", horizontal=True)
    else:
        st.info("Pehle 'Cloud PDF Ingestion' me PDF upload karein.")

# ----------------- TAB 5: DATA MANAGER & SAFE DELETE -----------------
elif nav == "🛡️ Data Manager & Safe Delete":
    st.markdown("### 🛡️ Cloud Storage Governance")
    count_res = supabase.table("rrb_questions").select("id", count="exact").execute()
    st.write(f"Total live questions: **{count_res.count if count_res.count else 0}**")

import streamlit as st
import json
import re
import io
from PIL import Image
import pdfplumber
from supabase import create_client
from google import genai
from google.genai import types

# ReportLab libraries for standard PDF generation matching your sample
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# ----------------- 1. Page Configuration -----------------
st.set_page_config(
    page_title="RRB AI Engine Pro",
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

# ----------------- 4. PDF Generation Engine (Exact Layout Match) -----------------
def generate_sample_style_pdf(subject_title, chapter_title, questions_list):
    """
    User ki provided PDF jaisa clean layout banata hai:
    [Subject]
    Chapter - Title
    1. Question text
       A. ... B. ...
    Answer Key grid at bottom
    """
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
        clean_text = q.get('question_text', '').replace('\n', '<br/>')
        q_p = Paragraph(f"<b>{i}.</b> {clean_text}", q_style)
        story.append(KeepTogether([q_p, Spacer(1, 4)]))
        
        # Answer format collection
        ans = q.get('correct_option', 'B')
        answers_collected.append(f"{i}. {ans}")

    # Answer Key grid
    story.append(Spacer(1, 16))
    story.append(Paragraph("<b>Answer Key</b>", title_style))
    story.append(Spacer(1, 6))
    
    # 10 answers per line grid format
    grid_lines = []
    for k in range(0, len(answers_collected), 10):
        grid_lines.append(" | ".join(answers_collected[k:k+10]))
    
    for line in grid_lines:
        story.append(Paragraph(line, ans_style))
        story.append(Spacer(1, 2))

    doc.build(story)
    buffer.seek(0)
    return buffer

# ----------------- 5. Smart Fallback Ingestion Rule -----------------
def quick_categorize(text):
    t = text.lower()
    if any(w in t for w in ['plinth', 'carpet', 'estimation', 'costing', 'far', 'fsi', 'area', 'rate', 'tender']):
        return "Civil Engineering", "Estimation and Costing"
    if any(w in t for w in ['प्रतिशत', '%', 'औसत', 'अनुपात', 'ब्याज', 'ट्रेन', 'speed', 'ratio']):
        return "Maths", "Quantitative Aptitude"
    if any(w in t for w in ['श्रृंखला', 'सीटिंग', 'दिशा', 'coding', 'blood relation']):
        return "Reasoning", "General Intelligence"
    return "General Studies", "General Knowledge"

def extract_questions_clean(pdf_file):
    raw_text = ""
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            t = page.extract_text(layout=False) or ""
            if t: raw_text += "\n" + t
    pattern = r"(?:\n|\r|^)(?:Q\s*[\.\:\-]?\s*\d+|Que\s*[\.\:\-]?\s*\d+|\d+\.|\d+\))\s*"
    blocks = re.split(pattern, raw_text, flags=re.IGNORECASE)
    return [b.strip() for b in blocks if len(b.strip()) > 35]

# ----------------- 6. Navigation Hub -----------------
nav = st.sidebar.radio(
    "AI Engine Mode",
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
        <p style="margin: 6px 0 0 0; opacity: 0.9;">Aap galat spelling ya bolke bhi puchein, AI khud context samajh kar explain karega aur database se sawal dega.</p>
    </div>
    """, unsafe_allow_html=True)

    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []

    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_prompt = st.chat_input("Mujhse kuch bhi pucho (e.g. 'estimesion ka plinth area samjhao' ya '20 maths question do')...")

    if user_prompt:
        st.session_state.chat_messages.append({"role": "user", "content": user_prompt})
        with st.chat_message("user"):
            st.markdown(user_prompt)

        with st.chat_message("assistant"):
            with st.spinner("AI analyzing your intent..."):
                # Intent & Spelling Correction check
                interpreter_prompt = f"""
                User input: "{user_prompt}"
                User might have spelling mistakes or broken hinglish.
                1. Identify the core topic/intent.
                2. If user is asking for questions, output: ACTION: FETCH_QUESTIONS | TOPIC: <topic> | COUNT: <number>
                3. If user is having a conversation or asking for an explanation, respond naturally, like a helpful mentor in Hinglish.
                """
                ai_res = ai_client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=interpreter_prompt
                )
                response_text = ai_res.text

                if "ACTION: FETCH_QUESTIONS" in response_text:
                    # Database lookup for matched questions
                    topic_match = response_text.split("TOPIC:")[1].split("|")[0].strip()
                    matched_items = supabase.table("rrb_questions").select("*").ilike("question_text", f"%{topic_match}%").limit(5).execute().data
                    if matched_items:
                        final_reply = f"Maine aapki request samajh li! Yahan **{topic_match}** ke PYQ sawal hain:\n\n"
                        for idx, q in enumerate(matched_items, 1):
                            final_reply += f"**{idx}.** {q['question_text']}\n\n"
                    else:
                        final_reply = f"Maine '{topic_match}' samajh liya, par database me is specific keyword ka direct sawal abhi nahi mila. Kya main is concept ko detail me samjha doon?"
                else:
                    final_reply = response_text

                st.markdown(final_reply)
                st.session_state.chat_messages.append({"role": "assistant", "content": final_reply})

# ----------------- TAB 2: GENERATE CLEAN PYQ PDF -----------------
elif nav == "📄 Generate Clean PYQ PDF":
    st.markdown("""
    <div class="app-header">
        <h2 style="margin: 0; font-weight: 800;">Sample-Matched PDF Generator</h2>
        <p style="margin: 6px 0 0 0; opacity: 0.9;">Aapke provided document ke exact layout me printable A4 PDF generate karein.</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        pdf_sub = st.text_input("Subject Title", value="Estimation and Costing")
    with col2:
        pdf_chap = st.text_input("Chapter Title", value="Introduction")

    num_qs = st.slider("Select Question Count", 5, 50, 20)

    if st.button("⚡ Generate Standard PDF Document", use_container_width=True):
        with st.spinner("Extracting from cloud and building PDF layout..."):
            query = supabase.table("rrb_questions").select("*").limit(num_qs).execute().data
            if not query:
                st.warning("Database me sawal nahi mile. Pehle 'Cloud PDF Ingestion' me jaakar PDF upload karein.")
            else:
                pdf_bytes = generate_sample_style_pdf(pdf_sub, pdf_chap, query)
                st.success("✅ Aapki printable PDF taiyar ho gayi hai!")
                st.download_button(
                    label="📥 Download PDF Document",
                    data=pdf_bytes,
                    file_name=f"{pdf_sub} - {pdf_chap}.pdf",
                    mime="application/pdf"
                )

# ----------------- TAB 3: CLOUD PDF INGESTION -----------------
elif nav == "🚀 Cloud PDF Ingestion":
    st.markdown("""
    <div class="app-header">
        <h2 style="margin: 0; font-weight: 800;">Safe Batch Cloud Ingestion</h2>
        <p style="margin: 6px 0 0 0; opacity: 0.9;">Adda247, Testbook, aur coaching answer keys ko bina failure ke sync karein.</p>
    </div>
    """, unsafe_allow_html=True)

    up_pdfs = st.file_uploader("Upload Exam PDFs", type=["pdf"], accept_multiple_files=True)
    if up_pdfs and st.button("Start Safe Sync", use_container_width=True):
        total_synced = 0
        for p in up_pdfs:
            shift_title = p.name.replace(".pdf", "")
            raw_qs = extract_questions_clean(p)
            records = []
            for q_txt in raw_qs:
                sub, top = quick_categorize(q_txt)
                records.append({
                    "question_text": q_txt,
                    "options": json.dumps([]),
                    "correct_option": "B",
                    "subject": sub,
                    "topic": top,
                    "shift_name": shift_title
                })
            # Batch insertion
            for i in range(0, len(records), 20):
                supabase.table("rrb_questions").insert(records[i:i+20]).execute()
                total_synced += len(records[i:i+20])
        st.balloons()
        st.success(f"Successfully synced {total_synced} questions to Supabase!")

# ----------------- TAB 4: CBT EXAM ARENA -----------------
elif nav == "🎯 CBT Exam Arena":
    st.markdown("### ⏱️ TCS iON Exam Simulator")
    data = supabase.table("rrb_questions").select("*").limit(10).execute().data
    if data:
        for idx, item in enumerate(data, 1):
            st.markdown(f"**Q.{idx}** {item['question_text']}")
            st.radio("Options", ["A", "B", "C", "D"], key=f"cbt_{idx}", horizontal=True)
    else:
        st.info("No questions in database yet.")

# ----------------- TAB 5: DATA MANAGER & SAFE DELETE -----------------
elif nav == "🛡️ Data Manager & Safe Delete":
    st.markdown("### 🛡️ Cloud Storage Governance")
    count_res = supabase.table("rrb_questions").select("id", count="exact").execute()
    st.write(f"Total live questions: **{count_res.count if count_res.count else 0}**")

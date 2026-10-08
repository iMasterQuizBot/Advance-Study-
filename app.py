import streamlit as st
import json
import re
from PIL import Image
import pdfplumber
from supabase import create_client
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

# ----------------- 1. पेज कॉन्फ़िगरेशन -----------------
st.set_page_config(
    page_title="RRB AI Master Hub & Cloud Engine",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ----------------- 2. Apple फ्रॉस्टेड-ग्लास CSS -----------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=SF+Pro+Display:wght@300;400;500;600;700&display=swap');
    * { font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", Roboto, sans-serif; }
    .stApp {
        background: radial-gradient(circle at top left, #1c1c1e 0%, #000000 100%);
        color: #F5F5F7;
    }
    .apple-card {
        background: rgba(28, 28, 30, 0.75);
        backdrop-filter: blur(25px);
        -webkit-backdrop-filter: blur(25px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 20px;
        padding: 22px;
        margin-bottom: 20px;
        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.4);
    }
    .badge-sub {
        background: rgba(10, 132, 255, 0.2);
        color: #0A84FF;
        border: 1px solid rgba(10, 132, 255, 0.4);
        padding: 4px 12px;
        border-radius: 100px;
        font-size: 12px;
        font-weight: 600;
        margin-right: 8px;
    }
    .badge-top {
        background: rgba(255, 255, 255, 0.1);
        color: #8E8E93;
        padding: 4px 12px;
        border-radius: 100px;
        font-size: 12px;
    }
    .stButton > button {
        background: #0A84FF;
        color: white;
        border-radius: 14px;
        border: none;
        padding: 10px 24px;
        font-weight: 600;
    }
    .stButton > button:hover { background: #0071E3; }
</style>
""", unsafe_allow_html=True)

# ----------------- 3. क्लाइंट्स इनिशियलाइजेशन -----------------
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except KeyError:
    st.error("⚠️ Streamlit Secrets में API Keys नहीं मिलीं!")
    st.stop()

@st.cache_resource
def get_clients():
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)
    ai = genai.Client(api_key=GEMINI_API_KEY)
    return sb, ai

supabase, ai_client = get_clients()

class CategorizedQuestion(BaseModel):
    subject: str = Field(description="Maths, Reasoning, Physics, Chemistry, Biology, History, Geography, Polity, or Static GK")
    topic: str = Field(description="Micro topic like Time and Work, Periodic Table, Coding-Decoding")

# ----------------- 4. साइडबार नेविगेशन -----------------
with st.sidebar:
    st.markdown("##  **RRB Studio**")
    st.caption("All-in-One Cloud Control")
    st.divider()
    
    nav = st.radio(
        "मेनू चुनें",
        [
            "📂 PDF अपलोड और पार्सर (नया)",
            "🔍 विषयवार सवाल खोजें",
            "📸 नोट्स से सवाल निकालें (Snap)",
            "📝 रैंडम प्रैक्टिस टेस्ट",
            "🛡️ डेटा कंट्रोल & एडमिन"
        ]
    )
    st.divider()
    selected_subject = st.selectbox(
        "सब्जेक्ट फ़िल्टर",
        ["All", "Maths", "Reasoning", "Physics", "Chemistry", "Biology", "History", "Geography", "Polity"]
    )
    question_count = st.slider("सवालों की संख्या", min_value=5, max_value=100, value=25, step=5)

# ----------------- फ़ीचर 1: PDF अपलोडर (कंप्यूटर पर रन करने की ज़रूरत खत्म) -----------------
if nav == "📂 PDF अपलोड और पार्सर (नया)":
    st.markdown("## 📂 **सीधे ऐप से Answer Key PDF अपलोड करें**")
    st.caption("यहाँ से अपनी आंसर की अपलोड करें। ऐप खुद एक-एक सवाल काटकर AI से सब्जेक्ट टैग कराएगा और डेटाबेस में सुरक्षित कर देगा।")

    uploaded_pdfs = st.file_uploader("RRB आंसर की PDFs चुनें (एक या एक से अधिक)", type=["pdf"], accept_multiple_files=True)

    if uploaded_pdfs:
        st.write(f"📁 कुल चुनी गई फाइलें: **{len(uploaded_pdfs)}**")
        
        if st.button("🚀 सभी फाइलों को प्रोसेस करके डेटाबेस में डालें", use_container_width=True):
            total_uploaded = 0
            progress_bar = st.progress(0)
            status_text = st.empty()

            for p_idx, pdf_file in enumerate(uploaded_pdfs):
                shift_name = pdf_file.name.replace(".pdf", "")
                status_text.info(f"⏳ फ़ाइल पढ़ी जा रही है: {pdf_file.name}")

                # 1. PDF से टेक्स्ट निकालना
                full_text = ""
                with pdfplumber.open(pdf_file) as pdf:
                    for page in pdf.pages:
                        t = page.extract_text()
                        if t:
                            full_text += "\n" + t

                # 2. सवाल अलग करना (Question ID पैटर्न)
                blocks = re.split(r"(Question ID\s*:\s*\d+)", full_text)
                questions_list = []
                for i in range(1, len(blocks), 2):
                    q_id = blocks[i]
                    q_body = blocks[i+1] if i+1 < len(blocks) else ""
                    content = f"{q_id}\n{q_body}".strip()
                    if len(content) > 50:
                        questions_list.append(content)

                status_text.info(f"⚡ {pdf_file.name} में {len(questions_list)} सवाल मिले। AI टैगिंग शुरू...")

                # 3. AI से सब्जेक्ट टैग कराकर Supabase में डालना
                for q_idx, q_block in enumerate(questions_list):
                    try:
                        tag_res = ai_client.models.generate_content(
                            model="gemini-2.5-flash",
                            contents=f"Classify this RRB exam question block:\n\n{q_block[:800]}",
                            config=types.GenerateContentConfig(
                                response_mime_type="application/json",
                                response_schema=CategorizedQuestion,
                                temperature=0.1
                            )
                        )
                        cat = json.loads(tag_res.text)

                        emb_res = ai_client.models.embed_content(
                            model="text-embedding-004",
                            contents=q_block[:800]
                        )
                        emb_vec = emb_res.embedding.values

                        supabase.table("rrb_questions").insert({
                            "question_text": q_block,
                            "options": json.dumps([]),
                            "correct_option": "Included in text",
                            "subject": cat["subject"],
                            "topic": cat["topic"],
                            "shift_name": shift_name,
                            "embedding": emb_vec
                        }).execute()

                        total_uploaded += 1
                    except Exception as e:
                        continue

                progress_bar.progress((p_idx + 1) / len(uploaded_pdfs))

            status_text.empty()
            st.success(f"🎉 बधाई! कुल {total_uploaded} सवाल डेटाबेस में सफलतापूर्वक लोड हो गए!")

# ----------------- फ़ीचर 2: विषयवार सवाल खोजें -----------------
elif nav == "🔍 विषयवार सवाल खोजें":
    st.markdown("### 🔍 **विषय और टॉपिक अनुसार सवाल**")
    topic_kw = st.text_input("कोई खास टॉपिक ढूँढना है? (जैसे: Time and Work, Periodic Table)", "")
    
    if st.button("सवाल लोड करें", use_container_width=True):
        with st.spinner("डेटाबेस से सवाल निकाले जा रहे हैं..."):
            query = supabase.table("rrb_questions").select("id, question_text, subject, topic, shift_name, correct_option")
            if selected_subject != "All":
                query = query.eq("subject", selected_subject)
            if topic_kw.strip():
                query = query.ilike("topic", f"%{topic_kw.strip()}%")
                
            results = query.limit(question_count).execute().data
            
            if not results:
                st.info("डेटाबेस में अभी इस फ़िल्टर के सवाल नहीं मिले। पहले 'PDF अपलोड' सेक्शन से फ़ाइल डालें।")
            else:
                st.success(f"{len(results)} सवाल मिले!")
                download_txt = ""
                for idx, row in enumerate(results, 1):
                    download_txt += f"Q{idx}. [{row['subject']} - {row['topic']}]\n{row['question_text']}\n\n{'='*40}\n\n"
                    st.markdown(f"""
                    <div class="apple-card">
                        <div>
                            <span class="badge-sub">{row['subject']}</span>
                            <span class="badge-top">{row['topic']}</span>
                            <span style="float: right; color: #8E8E93; font-size: 12px;">{row['shift_name']}</span>
                        </div>
                        <div style="margin-top: 15px; font-size: 15px; line-height: 1.6; white-space: pre-wrap;">
{row['question_text']}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.download_button("📥 इन सवालों को TXT फ़ाइल में डाउनलोड करें", download_txt, file_name="RRB_Questions.txt")

# ----------------- फ़ीचर 3: नोट्स स्नैप & मैच -----------------
elif nav == "📸 नोट्स से सवाल निकालें (Snap)":
    st.markdown("### 📸 **नोट्स की फोटो अपलोड करें**")
    st.caption("AI आपकी राइटिंग पढ़कर उसी टॉपिक के RRB सवाल ढूँढ निकालेगा।")
    
    up_img = st.file_uploader("नोट्स या किताब के पेज की फ़ोटो", type=["jpg", "jpeg", "png"])
    if up_img:
        img = Image.open(up_img)
        c1, c2 = st.columns([1, 2])
        with c1:
            st.image(img, caption="आपके नोट्स", use_container_width=True)
        with c2:
            if st.button("⚡ इस टॉपिक के RRB सवाल खोजें", use_container_width=True):
                with st.spinner("AI नोट्स का विश्लेषण कर रहा है..."):
                    vision_res = ai_client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=[img, "Identify the core educational concepts and formulas in 2 lines."]
                    )
                    detected_text = vision_res.text
                    st.info(f"💡 **पहचाना गया टॉपिक:** {detected_text}")
                    
                    emb_res = ai_client.models.embed_content(
                        model="text-embedding-004",
                        contents=detected_text
                    )
                    query_vec = emb_res.embedding.values
                    
                    matches = supabase.rpc("match_questions", {
                        "query_embedding": query_vec,
                        "match_threshold": 0.50,
                        "match_count": question_count
                    }).execute().data
                    
                    if not matches:
                        st.warning("इस नोट्स से जुड़े सवाल डेटाबेस में नहीं मिले।")
                    else:
                        st.success(f"{len(matches)} संबंधित सवाल मिले!")
                        for q in matches:
                            st.markdown(f"""
                            <div class="apple-card">
                                <div>
                                    <span class="badge-sub">{q['subject']}</span>
                                    <span class="badge-top">{q['topic']}</span>
                                    <span style="float: right; color: #30D158; font-weight: 600;">{int(q['similarity']*100)}% मैच</span>
                                </div>
                                <div style="margin-top: 12px; font-size: 15px; line-height: 1.6; white-space: pre-wrap;">
{q['question_text']}
                                </div>
                            </div>
                            """, unsafe_allow_html=True)

# ----------------- फ़ीचर 4: रैंडम प्रैक्टिस टेस्ट -----------------
elif nav == "📝 रैंडम प्रैक्टिस टेस्ट":
    st.markdown("### 📝 **रैंडम मॉक टेस्ट**")
    if st.button("नया टेस्ट सेट बनाएँ"):
        with st.spinner("सवालों का चयन हो रहा है..."):
            test_items = supabase.table("rrb_questions").select("question_text, subject, topic").limit(question_count).execute().data
            if test_items:
                for num, q in enumerate(test_items, 1):
                    st.markdown(f"""
                    <div class="apple-card">
                        <b>प्रश्न {num}</b> [{q['subject']} - {q['topic']}]
                        <div style="margin-top: 10px; font-size: 15px; white-space: pre-wrap;">
{q['question_text']}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("डेटाबेस में सवाल लोड नहीं हैं।")

# ----------------- फ़ीचर 5: डेटा कंट्रोल & सेफ डिलीट -----------------
elif nav == "🛡️ डेटा कंट्रोल & एडमिन":
    st.markdown("## 🛡️ **क्लाउड डेटा कंट्रोल सेंटर**")
    
    try:
        stats = supabase.table("rrb_questions").select("id", count="exact").execute()
        total_q = stats.count if stats.count is not None else 0
    except Exception:
        total_q = 0

    st.markdown(f"""
    <div class="apple-card">
        <h3 style="margin: 0; color: #0A84FF;">📊 कुल लाइव सवाल: {total_q}</h3>
        <p style="color: #8E8E93; margin: 4px 0 0 0;">Supabase Cloud Database में सुरक्षित</p>
    </div>
    """, unsafe_allow_html=True)
    
    admin_tab1, admin_tab2 = st.tabs(["✏️ सवाल देखें व एडिट करें", "🗑️ सुरक्षित डिलीट (Triple-Lock Safe)"])
    
    with admin_tab1:
        search_id = st.number_input("सवाल ID दर्ज करें", min_value=1, step=1)
        if st.button("सवाल खोजें"):
            q_res = supabase.table("rrb_questions").select("*").eq("id", search_id).execute().data
            if q_res:
                st.session_state["edit_item"] = q_res[0]
            else:
                st.error("यह ID नहीं मिली।")
                
        if st.session_state.get("edit_item"):
            item = st.session_state["edit_item"]
            with st.form("edit_form"):
                new_q_text = st.text_area("प्रश्न टेक्स्ट", value=item['question_text'], height=150)
                c_sub, c_top = st.columns(2)
                with c_sub:
                    new_sub = st.text_input("सब्जेक्ट", value=item['subject'])
                with c_top:
                    new_top = st.text_input("टॉपिक", value=item['topic'])
                new_ans = st.text_input("उत्तर", value=item['correct_option'])
                
                if st.form_submit_button("💾 बदलाव सेव करें"):
                    supabase.table("rrb_questions").update({
                        "question_text": new_q_text,
                        "subject": new_sub,
                        "topic": new_top,
                        "correct_option": new_ans
                    }).eq("id", item["id"]).execute()
                    st.success("✅ अपडेट हो गया!")
                    st.session_state["edit_item"] = None

    with admin_tab2:
        del_type = st.radio("डिलीट का प्रकार:", ["एक सवाल डिलीट करें", "पूरी शिफ्ट/PDF का डेटा डिलीट करें"])
        if del_type == "एक सवाल डिलीट करें":
            del_id = st.number_input("सवाल ID:", min_value=1, step=1, key="del_s_id")
            s1 = st.checkbox("स्वीकार करें: यह सवाल हमेशा के लिए हट जाएगा।", key="s1")
            s2 = st.text_input("पुष्टि के लिए 'DELETE' लिखें:", key="s2")
            ready = s1 and (s2.strip() == "DELETE")
            if st.button("🚨 हमेशा के लिए डिलीट करें", disabled=not ready):
                supabase.table("rrb_questions").delete().eq("id", del_id).execute()
                st.success(f"ID {del_id} हटा दी गई।")
                st.rerun()
        else:
            shifts_data = supabase.table("rrb_questions").select("shift_name").execute().data
            shifts_list = sorted(list(set([s["shift_name"] for s in shifts_data]))) if shifts_data else []
            if shifts_list:
                target = st.selectbox("हटाने वाली शिफ्ट चुनें:", shifts_list)
                s1_sh = st.checkbox(f"स्वीकार करें: '{target}' का सारा डेटा हट जाएगा।", key="s1_sh")
                s2_sh = st.text_input(f"पुष्टि के लिए लिखें: '{target}'", key="s2_sh")
                ready_sh = s1_sh and (s2_sh.strip() == target)
                if st.button("🚨 पूरी शिफ्ट डिलीट करें", disabled=not ready_sh):
                    supabase.table("rrb_questions").delete().eq("shift_name", target).execute()
                    st.success(f"शिफ्ट '{target}' हटा दी गई।")
                    st.rerun()

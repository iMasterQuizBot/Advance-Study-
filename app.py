import streamlit as st
import json
from PIL import Image
from supabase import create_client
from google import genai
from datetime import datetime

# ----------------- 1. पेज सेटअप -----------------
st.set_page_config(
    page_title="RRB AI Master Hub & Admin",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ----------------- 2. Apple फ्रॉस्टेड-ग्लास CSS -----------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=SF+Pro+Display:wght@300;400;500;600;700&display=swap');
    
    * {
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", Roboto, sans-serif;
    }
    
    .stApp {
        background: radial-gradient(circle at top left, #1c1c1e 0%, #000000 100%);
        color: #F5F5F7;
    }

    /* Apple फ्रॉस्टेड कार्ड */
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

    .badge-danger {
        background: rgba(255, 69, 58, 0.2);
        color: #FF453A;
        border: 1px solid rgba(255, 69, 58, 0.4);
        padding: 4px 12px;
        border-radius: 100px;
        font-size: 12px;
        font-weight: 600;
    }

    .stButton > button {
        background: #0A84FF;
        color: white;
        border-radius: 14px;
        border: none;
        padding: 10px 24px;
        font-weight: 600;
    }
    .stButton > button:hover {
        background: #0071E3;
    }
</style>
""", unsafe_allow_html=True)

# ----------------- 3. API क्लाइंट्स -----------------
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except KeyError:
    st.error("⚠️ Secrets लोड नहीं हुए! कृपया Streamlit Cloud के Secrets में कीज़ दर्ज करें।")
    st.stop()

@st.cache_resource
def get_clients():
    sb = create_client(SUPABASE_URL, SUPABASE_KEY)
    ai = genai.Client(api_key=GEMINI_API_KEY)
    return sb, ai

supabase, ai_client = get_clients()

# ----------------- 4. साइडबार नेविगेशन -----------------
with st.sidebar:
    st.markdown("##  **RRB Studio**")
    st.caption("AI Smart Bank & Cloud Controller")
    st.divider()
    
    nav = st.radio(
        "मोड चुनें",
        ["🔍 विषयवार सवाल खोजें", "📸 नोट्स से सवाल निकालें (Snap)", "📝 रैंडम प्रैक्टिस सेट", "🛡️ डेटा कंट्रोल & एडमिन"]
    )
    st.divider()
    
    selected_subject = st.selectbox(
        "सब्जेक्ट चुनें",
        ["All", "Maths", "Reasoning", "Physics", "Chemistry", "Biology", "History", "Geography", "Polity"]
    )
    question_count = st.slider("सवालों की संख्या", min_value=5, max_value=100, value=25, step=5)

# ----------------- 5. मोड 1: विषयवार सवाल खोजें -----------------
if nav == "🔍 विषयवार सवाल खोजें":
    st.markdown("### 🔍 **विषय और टॉपिक अनुसार सवाल**")
    topic_kw = st.text_input("कोई खास टॉपिक ढूँढना है? (जैसे: Percentage, Periodic Table, Optics)", "")
    
    if st.button("सवाल लोड करें", use_container_width=True):
        with st.spinner("डेटाबेस से सवाल निकाले जा रहे हैं..."):
            query = supabase.table("rrb_questions").select("id, question_text, subject, topic, shift_name, correct_option")
            
            if selected_subject != "All":
                query = query.eq("subject", selected_subject)
            if topic_kw.strip():
                query = query.ilike("topic", f"%{topic_kw.strip()}%")
                
            results = query.limit(question_count).execute().data
            
            if not results:
                st.info("डेटाबेस में अभी इस फ़िल्टर के सवाल नहीं मिले।")
            else:
                st.success(f"{len(results)} सवाल मिले!")
                download_txt = ""
                for idx, row in enumerate(results, 1):
                    download_txt += f"Q{idx}. [{row['subject']} - {row['topic']}]\n{row['question_text']}\nउत्तर: {row['correct_option']}\n\n"
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
                        <div style="margin-top: 10px; color: #30D158; font-weight: 500;">
                            उत्तर: {row['correct_option']}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.download_button("📥 इन सवालों को TXT फ़ाइल में डाउनलोड करें", download_txt, file_name="RRB_Questions.txt")

# ----------------- 6. मोड 2: नोट्स से सवाल निकालना -----------------
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
            if st.button("⚡ इस टॉपिक के RRB PYQs खोजें", use_container_width=True):
                with st.spinner("Gemini AI नोट्स का विश्लेषण कर रहा है..."):
                    vision_res = ai_client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=[img, "Identify the core educational concepts and formulas in 2 lines."]
                    )
                    detected_text = vision_res.text
                    st.info(f"💡 **पहचाना गया कॉन्सेप्ट:** {detected_text}")
                    
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

# ----------------- 7. मोड 3: रैंडम प्रैक्टिस सेट -----------------
elif nav == "📝 रैंडम प्रैक्टिस सेट":
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

# ----------------- 8. मोड 4: डेटा कंट्रोल & एडमिन (नया फ़ीचर) -----------------
elif nav == "🛡️ डेटा कंट्रोल & एडमिन":
    st.markdown("## 🛡️ **क्लाउड डेटा कंट्रोल सेंटर**")
    st.caption("यहाँ से आप क्लाउड में स्टोर अपने सभी सवालों को देख सकते हैं, सुधार सकते हैं और सुरक्षित डिलीट कर सकते हैं।")
    
    # 1. डेटा स्टैटिस्टिक्स कार्ड्स
    try:
        stats = supabase.table("rrb_questions").select("id", count="exact").execute()
        total_q = stats.count if stats.count is not None else 0
    except Exception:
        total_q = 0

    st.markdown(f"""
    <div class="apple-card">
        <h3 style="margin: 0; color: #0A84FF;">📊 कुल क्लाउड डेटा: {total_q} सवाल सुरक्षित हैं</h3>
        <p style="color: #8E8E93; margin: 4px 0 0 0;">Supabase Cloud Database में लाइव सिंक्रोनाइज़्ड</p>
    </div>
    """, unsafe_allow_html=True)
    
    admin_tab1, admin_tab2 = st.tabs(["✏️ सवाल देखें व एडिट करें", "🗑️ सुरक्षित डिलीट (Triple-Lock Safe)"])
    
    # टैब 1: एडिट और अपडेट
    with admin_tab1:
        st.markdown("#### किसी विशेष सवाल को सुधारें")
        search_id = st.number_input("सवाल ID दर्ज करें", min_value=1, step=1)
        
        if st.button("सवाल खोजें"):
            q_res = supabase.table("rrb_questions").select("*").eq("id", search_id).execute().data
            if q_res:
                st.session_state["edit_item"] = q_res[0]
            else:
                st.error("यह ID डेटाबेस में नहीं मिली।")
                st.session_state["edit_item"] = None
                
        if st.session_state.get("edit_item"):
            item = st.session_state["edit_item"]
            with st.form("edit_form"):
                st.write(f"**शिफ्ट:** {item['shift_name']}")
                new_q_text = st.text_area("प्रश्न टेक्स्ट", value=item['question_text'], height=150)
                c_sub, c_top = st.columns(2)
                with c_sub:
                    new_sub = st.text_input("सब्जेक्ट", value=item['subject'])
                with c_top:
                    new_top = st.text_input("टॉपिक", value=item['topic'])
                new_ans = st.text_input("उत्तर / स्टेटस", value=item['correct_option'])
                
                if st.form_submit_button("💾 क्लाउड में बदलाव सेव करें"):
                    supabase.table("rrb_questions").update({
                        "question_text": new_q_text,
                        "subject": new_sub,
                        "topic": new_top,
                        "correct_option": new_ans
                    }).eq("id", item["id"]).execute()
                    st.success("✅ सवाल सफलतापूर्वक अपडेट हो गया!")
                    st.session_state["edit_item"] = None

    # टैब 2: ट्रिपल-लॉक सेफ डिलीट
    with admin_tab2:
        st.markdown("#### ⚠️ डेटा डिलीट करने का सुरक्षित तरीका")
        st.caption("डेटा गलती से कभी डिलीट न हो, इसलिए 3 स्तरों की पुष्टि अनिवार्य है।")
        
        del_type = st.radio("डिलीट करने का प्रकार चुनें:", ["एक अकेला सवाल डिलीट करें", "पूरी शिफ्ट/PDF का डेटा डिलीट करें"])
        
        st.markdown("---")
        
        if del_type == "एक अकेला सवाल डिलीट करें":
            del_id = st.number_input("डिलीट करने के लिए सवाल ID:", min_value=1, step=1, key="del_single_id")
            
            # स्तर 1: वार्निंग चेकबॉक्स
            step1_check = st.checkbox("स्वीकार करें: मैं समझता हूँ कि यह सवाल हमेशा के लिए हट जाएगा।", key="s1_single")
            
            # स्तर 2: टाइप करके कन्फर्म करना
            step2_text = st.text_input("पुष्टि के लिए बॉक्स में 'DELETE' टाइप करें:", key="s2_single")
            
            # स्तर 3: जब तक दोनों सही न हों, बटन एक्टिव नहीं होगा
            delete_ready = step1_check and (step2_text.strip() == "DELETE")
            
            if st.button("🚨 सवाल हमेशा के लिए डिलीट करें", disabled=not delete_ready):
                supabase.table("rrb_questions").delete().eq("id", del_id).execute()
                st.success(f"ID {del_id} सफलतापूर्वक डिलीट हो गई।")
                st.rerun()

        elif del_type == "पूरी शिफ्ट/PDF का डेटा डिलीट करें":
            # पहले सभी शिफ्ट्स के नाम लोड करें
            shifts_data = supabase.table("rrb_questions").select("shift_name").execute().data
            shifts_list = sorted(list(set([s["shift_name"] for s in shifts_data]))) if shifts_data else []
            
            if not shifts_list:
                st.info("डेटाबेस में कोई शिफ्ट मौजूद नहीं है।")
            else:
                target_shift = st.selectbox("वह शिफ्ट चुनें जिसे डिलीट करना है:", shifts_list)
                
                # स्तर 1: वार्निंग चेकबॉक्स
                step1_check = st.checkbox(f"स्वीकार करें: मैं '{target_shift}' के सभी सवालों को हटाना चाहता हूँ।", key="s1_shift")
                
                # स्तर 2: शिफ्ट का पूरा नाम टाइप करना
                step2_text = st.text_input(f"पुष्टि के लिए ठीक यही नाम टाइप करें: '{target_shift}'", key="s2_shift")
                
                # स्तर 3: कन्फर्मेशन बटन
                delete_ready = step1_check and (step2_text.strip() == target_shift)
                
                if st.button(f"🚨 '{target_shift}' का पूरा डेटा डिलीट करें", disabled=not delete_ready):
                    supabase.table("rrb_questions").delete().eq("shift_name", target_shift).execute()
                    st.success(f"शिफ्ट '{target_shift}' का पूरा डेटा सफलतापूर्वक हटा दिया गया।")
                    st.rerun()

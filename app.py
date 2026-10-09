# -*- coding: utf-8 -*-
"""
PYQ MASTER ENGINE  ·  RRB JE / SSC JE   (single-file Streamlit app)
UI: Hindi / English / Hinglish  |  DB: Supabase (pgvector)  |  AI: Gemini
Run schema.sql once in Supabase, add secrets, deploy.
"""
import streamlit as st
import json, re, io, os, time, random, hashlib, difflib, html, datetime as dt, urllib.request
import pandas as pd
import pdfplumber
from supabase import create_client
from google import genai
from google.genai import types

try:
    from fpdf import FPDF
    HAVE_FPDF = True
except Exception:  # pragma: no cover
    FPDF, HAVE_FPDF = object, False

st.set_page_config(page_title="PYQ Master", page_icon="🎓", layout="centered",
                   initial_sidebar_state="collapsed")

LETTERS = "ABCD"
PAGES = ["home", "practice", "mock", "create", "library", "more"]
ACCENTS = {"blue": ("#0A84FF", "#5E5CE6"), "indigo": ("#5E5CE6", "#BF5AF2"), "purple": ("#BF5AF2", "#FF375F"),
           "pink": ("#FF375F", "#FF9F0A"), "orange": ("#FF9F0A", "#FF453A"), "green": ("#30D158", "#0A84FF"),
           "teal": ("#40C8E0", "#0A84FF")}
DEFAULTS = dict(ui_lang="hn", ai_lang="auto", accent="blue", font_scale=100, radius="round", glass=True,
                amoled=False, pos_mark=1.0, neg_mark=0.33, default_minutes=90, shuffle_q=True,
                shuffle_opts=False, instant=True, daily_goal=20, confirm_submit=True, ai_explain_auto=False)
DEFAULT_MODELS = ["gemini-flash-latest", "gemini-2.5-flash", "gemini-2.0-flash"]
EMBED_MODELS = ["text-embedding-004", "gemini-embedding-001"]

# ═══════════════════════ 1. LANGUAGE PACK  (hi, en, hn) ═══════════════════════
S = {
 "home": ("होम", "Home", "Home"), "practice": ("अभ्यास", "Practice", "Practice"),
 "mock": ("मॉक", "Mock", "Mock"), "create": ("बनाओ", "Create", "Banao"),
 "library": ("लाइब्रेरी", "Library", "Library"), "more": ("और", "More", "More"),
 "hello": ("नमस्ते", "Hello", "Namaste"), "gm": ("सुप्रभात", "Good morning", "Good morning"),
 "ga": ("शुभ दोपहर", "Good afternoon", "Good afternoon"), "ge": ("शुभ संध्या", "Good evening", "Good evening"),
 "gn": ("शुभ रात्रि", "Good night", "Good night"),
 "student": ("विद्यार्थी", "Student", "Student"),
 "daily_goal": ("आज का लक्ष्य", "Today's goal", "Aaj ka goal"),
 "solved": ("{n}/{g} सवाल हल", "{n}/{g} solved", "{n}/{g} sawal solve"),
 "streak": ("दिन की स्ट्रीक", "day streak", "din ki streak"),
 "qbank": ("प्रश्न बैंक", "Question bank", "Question bank"),
 "accuracy": ("सटीकता", "Accuracy", "Accuracy"), "mocks": ("मॉक टेस्ट", "Mock tests", "Mock tests"),
 "quick": ("जल्दी शुरू करें", "Quick start", "Jaldi shuru karo"),
 "q_practice": ("अभ्यास करें", "Practice now", "Practice karo"),
 "q_mock": ("मॉक टेस्ट दें", "Take a mock", "Mock do"),
 "q_tutor": ("AI से पूछें", "Ask AI", "AI se pucho"),
 "q_wrong": ("गलतियाँ दोहराएँ", "Retry mistakes", "Galtiyan repeat karo"),
 "qotd": ("आज का प्रश्न", "Question of the day", "Aaj ka question"),
 "weak": ("कमज़ोर टॉपिक", "Weak topics", "Weak topics"),
 "no_weak": ("अभी पर्याप्त डेटा नहीं है। कुछ अभ्यास करें!", "Not enough data yet. Practice a bit!", "Abhi data kam hai. Thoda practice karo!"),
 "resume_mock": ("चल रहा मॉक जारी रखें", "Resume running mock", "Chalta mock resume karo"),
 "empty_db": ("डेटाबेस में अभी सवाल नहीं हैं। 'और → एडमिन' से PDF अपलोड करें।", "No questions yet. Upload PDFs from More → Admin.", "Database me sawal nahi hain. More → Admin se PDF upload karo."),
 "db_err": ("डेटाबेस त्रुटि: schema.sql चलाई? विवरण:", "Database error — did you run schema.sql? Details:", "Database error — schema.sql chalayi? Details:"),
 "subject": ("विषय", "Subject", "Subject"), "topic": ("टॉपिक", "Topic", "Topic"),
 "shift": ("शिफ्ट / पेपर", "Shift / paper", "Shift / paper"), "difficulty": ("कठिनाई", "Difficulty", "Difficulty"),
 "all": ("सभी", "All", "All"), "count": ("सवालों की संख्या", "Number of questions", "Kitne questions"),
 "start": ("शुरू करें", "Start", "Start"), "next": ("अगला", "Next", "Next"), "prev": ("पिछला", "Previous", "Previous"),
 "check": ("जाँचें", "Check", "Check"), "finish": ("समाप्त", "Finish", "Finish"),
 "src_mode": ("स्रोत", "Source", "Source"),
 "m_random": ("रैंडम", "Random", "Random"), "m_seq": ("क्रम से", "In order", "In order"),
 "m_book": ("बुकमार्क", "Bookmarked", "Bookmarked"), "m_wrong": ("मेरी गलतियाँ", "My mistakes", "Meri galtiyan"),
 "correct": ("सही ✅", "Correct ✅", "Sahi ✅"), "wrong": ("गलत ❌", "Wrong ❌", "Galat ❌"),
 "right_ans": ("सही उत्तर", "Correct answer", "Sahi answer"),
 "no_key": ("इस सवाल की आंसर-की उपलब्ध नहीं है।", "Answer key not available for this question.", "Is question ki answer key available nahi hai."),
 "explain": ("व्याख्या", "Explanation", "Explanation"),
 "ai_explain": ("🤖 AI से समझें", "🤖 Explain with AI", "🤖 AI se samjho"),
 "bookmark": ("बुकमार्क", "Bookmark", "Bookmark"), "bookmarked": ("बुकमार्क ✓", "Bookmarked ✓", "Bookmarked ✓"),
 "no_match": ("इन फ़िल्टर से कोई सवाल नहीं मिला।", "No questions match these filters.", "In filters se koi sawal nahi mila."),
 "done_set": ("सेट पूरा! 🎉", "Set complete! 🎉", "Set complete! 🎉"),
 "score": ("स्कोर", "Score", "Score"), "new_set": ("नया सेट", "New set", "Naya set"),
 "no_opts": ("(इस सवाल के विकल्प सेव नहीं हैं — A/B/C/D में से चुनें)", "(options not stored — pick A/B/C/D)", "(options saved nahi hain — A/B/C/D chuno)"),
 # mock
 "preset_full": ("पूरा मॉक (100 प्र. / 90 मि.)", "Full mock (100 Q / 90 min)", "Full mock (100 Q / 90 min)"),
 "preset_quick": ("क्विक (25 प्र. / 25 मि.)", "Quick (25 Q / 25 min)", "Quick (25 Q / 25 min)"),
 "preset_custom": ("कस्टम", "Custom", "Custom"), "minutes": ("समय (मिनट)", "Time (minutes)", "Time (minutes)"),
 "marking": ("अंकन: सही +{p} · गलत −{n}", "Marking: correct +{p} · wrong −{n}", "Marking: sahi +{p} · galat −{n}"),
 "start_mock": ("टेस्ट शुरू करें", "Start test", "Test shuru karo"),
 "time_left": ("शेष समय", "Time left", "Time left"),
 "save_next": ("सेव और अगला", "Save & Next", "Save & Next"),
 "mark_next": ("रिव्यू के लिए चिह्नित + अगला", "Mark for review & Next", "Mark for review & Next"),
 "clear": ("उत्तर हटाएँ", "Clear response", "Clear response"),
 "palette": ("प्रश्न पैलेट", "Question palette", "Question palette"),
 "submit": ("सबमिट", "Submit", "Submit"), "sure": ("पक्का सबमिट करें?", "Submit the test?", "Pakka submit karna hai?"),
 "yes_submit": ("हाँ, सबमिट", "Yes, submit", "Haan, submit"), "go_back": ("वापस", "Go back", "Go back"),
 "st_na": ("न देखा", "Not visited", "Not visited"), "st_nans": ("बिना उत्तर", "Not answered", "Not answered"),
 "st_ans": ("उत्तर दिया", "Answered", "Answered"), "st_mark": ("रिव्यू", "Review", "Review"),
 "st_am": ("उत्तर+रिव्यू", "Ans+Review", "Ans+Review"),
 "result": ("परिणाम", "Result", "Result"), "attempted": ("प्रयास", "Attempted", "Attempted"),
 "n_correct": ("सही", "Correct", "Sahi"), "n_wrong": ("गलत", "Wrong", "Galat"), "n_skip": ("छोड़े", "Skipped", "Skipped"),
 "n_ungraded": ("की नहीं", "No key", "No key"),
 "neg_total": ("नेगेटिव अंक", "Negative marks", "Negative marks"), "time_used": ("समय लगा", "Time used", "Time laga"),
 "avg_time": ("औसत/प्रश्न", "Avg / question", "Avg / question"),
 "by_subject": ("विषयवार विश्लेषण", "Subject-wise analysis", "Subject-wise analysis"),
 "slow_q": ("सबसे ज़्यादा समय लेने वाले", "Slowest questions", "Sabse slow questions"),
 "review": ("समीक्षा", "Review", "Review"), "your_ans": ("आपका उत्तर", "Your answer", "Aapka answer"),
 "retry_wrong": ("गलत सवाल फिर हल करें", "Retry wrong questions", "Galat sawal dobara karo"),
 "new_test": ("नया टेस्ट", "New test", "Naya test"), "saved_cloud": ("परिणाम क्लाउड में सेव हुआ ✓", "Result saved to cloud ✓", "Result cloud me save ho gaya ✓"),
 "time_up": ("समय समाप्त! टेस्ट अपने आप सबमिट हुआ।", "Time's up! Test auto-submitted.", "Time up! Test auto-submit ho gaya."),
 "download_res": ("परिणाम CSV", "Result CSV", "Result CSV"), "skipped_lbl": ("छोड़ा", "Skipped", "Skipped"),
 # tutor
 "tutor_title": ("AI गुरु", "AI Tutor", "AI Guru"),
 "tutor_sub": ("टूटी-फूटी हिंदी, Hinglish या गलत स्पेलिंग — सब चलेगा।", "Broken Hindi, Hinglish or typos — all fine.", "Tooti-footi Hindi, Hinglish ya galat spelling — sab chalega."),
 "ask_ph": ("कुछ भी पूछें… जैसे: estimesion ka plinth area", "Ask anything… e.g. estimesion ka plinth area", "Kuch bhi pucho… jaise: estimesion ka plinth area"),
 "thinking": ("समझ रहा हूँ…", "Thinking…", "Samajh raha hoon…"),
 "understood": ("मैंने समझा", "I understood", "Maine samjha"),
 "related_pyq": ("डेटाबेस से संबंधित PYQ", "Related PYQs from database", "Database se related PYQ"),
 "voice": ("🎙️ वॉइस", "🎙️ Voice", "🎙️ Voice"), "photo": ("📷 फ़ोटो से सवाल", "📷 Photo doubt", "📷 Photo se doubt"),
 "send": ("भेजें", "Send", "Send"), "clear_chat": ("चैट साफ़ करें", "Clear chat", "Chat clear karo"),
 "ai_fail": ("AI अभी जवाब नहीं दे सका। थोड़ी देर बाद कोशिश करें (एडमिन → डायग्नोस्टिक्स देखें)।", "AI could not answer right now. Try again shortly (see Admin → Diagnostics).", "AI abhi jawab nahi de saka. Thodi der baad try karo (Admin → Diagnostics dekho)."),
 "sugg1": ("estimesion ka plinth area batao", "estimesion ka plinth area batao", "estimesion ka plinth area batao"),
 "sugg2": ("बेंडिंग मोमेंट क्या होता है", "What is bending moment", "bending moment kya hota hai"),
 "sugg3": ("kirchhof law ka formula", "kirchhof law ka formula", "kirchhof law ka formula"),
 "sugg4": ("slump test trick", "slump test trick", "slump test trick"),
 "ai_lang": ("AI के जवाब की भाषा", "AI reply language", "AI reply language"),
 "auto": ("ऑटो (जैसा आप लिखें)", "Auto (match my writing)", "Auto (jaise main likhun)"),
 # library
 "lib_title": ("PDF स्टूडियो", "PDF Studio", "PDF Studio"),
 "lib_sub": ("साफ़ A4 प्रिंटेबल PYQ शीट + आंसर-की।", "Clean printable A4 PYQ sheets + answer key.", "Clean printable A4 PYQ sheet + answer key."),
 "pdf_subject": ("PDF में विषय का नाम", "Subject name in PDF", "PDF me subject ka naam"),
 "pdf_chapter": ("चैप्टर / शीर्षक", "Chapter / title", "Chapter / title"),
 "inc_opts": ("विकल्प छापें", "Print options", "Options print karo"), "inc_key": ("आंसर-की ग्रिड", "Answer key grid", "Answer key grid"),
 "inc_expl": ("व्याख्या जोड़ें", "Include explanations", "Explanations jodo"), "font_sz": ("फ़ॉन्ट साइज़", "Font size", "Font size"),
 "gen_pdf": ("PDF बनाएँ", "Generate PDF", "PDF banao"), "dl_pdf": ("📥 PDF डाउनलोड", "📥 Download PDF", "📥 PDF download"),
 "pdf_ready": ("PDF तैयार! {n} सवाल।", "PDF ready! {n} questions.", "PDF ready! {n} questions."),
 "no_fpdf": ("fpdf2 इंस्टॉल नहीं है — requirements.txt देखें।", "fpdf2 not installed — check requirements.txt.", "fpdf2 install nahi hai — requirements.txt dekho."),
 "font_warn": ("हिंदी फ़ॉन्ट डाउनलोड नहीं हो सका; PDF में हिंदी अक्षर नहीं दिखेंगे। repo में fonts/Hind-Regular.ttf और Hind-Bold.ttf रखें।", "Hindi font could not be fetched; Hindi text won't render in PDF. Put fonts/Hind-Regular.ttf and Hind-Bold.ttf in the repo.", "Hindi font download nahi hua; PDF me Hindi nahi dikhega. Repo me fonts/Hind-Regular.ttf aur Hind-Bold.ttf rakho."),
 "export": ("एक्सपोर्ट", "Export", "Export"),
 # more / settings
 "profile": ("प्रोफ़ाइल", "Profile", "Profile"), "settings": ("सेटिंग्स", "Settings", "Settings"),
 "progress": ("प्रगति", "Progress", "Progress"), "admin": ("एडमिन", "Admin", "Admin"),
 "your_name": ("आपका नाम", "Your name", "Aapka naam"), "profile_code": ("प्रोफ़ाइल कोड (याद रखें)", "Profile code (remember it)", "Profile code (yaad rakho)"),
 "load": ("लोड करें", "Load", "Load"), "save": ("सेव करें", "Save", "Save"), "saved": ("सेव हो गया ✓", "Saved ✓", "Saved ✓"),
 "profile_help": ("कोड डालकर किसी भी फ़ोन पर अपनी प्रगति, बुकमार्क और सेटिंग्स वापस पाएँ।", "Enter your code on any device to restore progress, bookmarks and settings.", "Code dalke kisi bhi phone par progress, bookmarks aur settings wapas pao."),
 "loaded": ("प्रोफ़ाइल लोड हुई", "Profile loaded", "Profile load ho gayi"), "not_found": ("कोड नहीं मिला", "Code not found", "Code nahi mila"),
 "look": ("रूप-रंग", "Appearance", "Appearance"), "accent": ("एक्सेंट रंग", "Accent colour", "Accent colour"),
 "fsize": ("टेक्स्ट साइज़ (%)", "Text size (%)", "Text size (%)"), "corners": ("कोने", "Corners", "Corners"),
 "r_round": ("गोल", "Round", "Round"), "r_sharp": ("सीधे", "Sharp", "Sharp"), "glass": ("ग्लास इफ़ेक्ट", "Glass effect", "Glass effect"),
 "amoled": ("AMOLED काला (डार्क में)", "AMOLED black (dark mode)", "AMOLED black (dark me)"),
 "theme_hint": ("लाइट/डार्क बदलने के लिए ऊपर दाएँ ⋮ → Settings → Theme।", "For light/dark: top-right ⋮ → Settings → Theme.", "Light/dark ke liye: top-right ⋮ → Settings → Theme."),
 "exam_set": ("परीक्षा सेटिंग्स", "Exam settings", "Exam settings"), "pos_mark": ("सही उत्तर के अंक", "Marks per correct", "Sahi answer ke marks"),
 "neg_mark": ("गलत उत्तर पर कटौती", "Negative per wrong", "Galat par negative"), "def_min": ("डिफ़ॉल्ट मॉक समय", "Default mock minutes", "Default mock minutes"),
 "shuf_q": ("सवाल शफ़ल करें", "Shuffle questions", "Questions shuffle karo"), "shuf_o": ("विकल्प शफ़ल करें", "Shuffle options", "Options shuffle karo"),
 "instant": ("अभ्यास में तुरंत उत्तर दिखाएँ", "Instant feedback in practice", "Practice me turant answer dikhao"),
 "goal": ("दैनिक लक्ष्य (सवाल)", "Daily goal (questions)", "Daily goal (questions)"),
 "conf_sub": ("सबमिट से पहले पूछें", "Confirm before submit", "Submit se pehle pucho"),
 "auto_ai": ("गलत होने पर AI व्याख्या अपने आप", "Auto AI explanation on wrong", "Galat par AI explanation auto"),
 "reset": ("सेटिंग्स रीसेट", "Reset settings", "Settings reset"),
 "history": ("टेस्ट इतिहास", "Test history", "Test history"), "no_hist": ("अभी कोई सेव्ड टेस्ट नहीं। प्रोफ़ाइल बनाकर मॉक दें।", "No saved tests yet. Create a profile and take a mock.", "Abhi koi saved test nahi. Profile banao aur mock do."),
 "score_trend": ("स्कोर ट्रेंड", "Score trend", "Score trend"), "need_profile": ("पहले प्रोफ़ाइल बनाएँ/लोड करें (More → Profile)।", "Create/load a profile first (More → Profile).", "Pehle profile banao/load karo (More → Profile)."),
 "admin_pin": ("एडमिन PIN", "Admin PIN", "Admin PIN"), "unlock": ("अनलॉक", "Unlock", "Unlock"), "bad_pin": ("गलत PIN", "Wrong PIN", "Galat PIN"),
 "no_pin_set": ("⚠️ Secrets में ADMIN_PIN सेट नहीं है — एडमिन सबके लिए खुला है।", "⚠️ ADMIN_PIN not set in secrets — admin is open to everyone.", "⚠️ Secrets me ADMIN_PIN set nahi hai — admin sabke liye open hai."),
 "ingest": ("PDF इनजेशन", "PDF ingestion", "PDF ingestion"), "manage": ("डेटा मैनेजर", "Data manager", "Data manager"),
 "ai_tools": ("AI टूल्स", "AI tools", "AI tools"), "diag": ("डायग्नोस्टिक्स", "Diagnostics", "Diagnostics"), "add_one": ("एक सवाल जोड़ें", "Add one question", "Ek question jodo"),
 "up_q": ("प्रश्न-पत्र PDF (एक या अधिक)", "Question-paper PDFs (one or more)", "Question paper PDF (ek ya zyada)"),
 "up_key": ("आंसर-की (PDF/TXT, वैकल्पिक)", "Answer key (PDF/TXT, optional)", "Answer key (PDF/TXT, optional)"),
 "exam": ("परीक्षा", "Exam", "Exam"), "year": ("वर्ष", "Year", "Year"), "parse": ("पार्स करें", "Parse", "Parse karo"),
 "parsed_n": ("{n} सवाल मिले — नीचे सुधारें, फिर सेव करें।", "{n} questions found — fix below, then save.", "{n} sawal mile — neeche sudharo, phir save karo."),
 "save_db": ("डेटाबेस में सेव करें", "Save to database", "Database me save karo"), "embed_now": ("AI खोज के लिए embedding भी बनाएँ", "Also create embeddings for AI search", "AI search ke liye embedding bhi banao"),
 "auto_cls": ("विषय/टॉपिक अपने आप तय करें", "Auto-detect subject/topic", "Subject/topic auto-detect karo"),
 "inserted": ("{n} नए सवाल सेव हुए (डुप्लिकेट छोड़े गए)।", "{n} questions processed (duplicates skipped).", "{n} questions process hue (duplicate skip)."),
 "pending_emb": ("बिना embedding वाले सवाल: {n}", "Questions without embedding: {n}", "Bina embedding ke questions: {n}"),
 "run_emb": ("Embedding बनाएँ (40)", "Create embeddings (40)", "Embedding banao (40)"), "run_cls": ("AI से वर्गीकरण + व्याख्या (15)", "AI classify + explain (15)", "AI classify + explain (15)"),
 "danger": ("खतरनाक ज़ोन", "Danger zone", "Danger zone"), "del_by": ("इस शिफ्ट के सब सवाल हटाएँ", "Delete all questions of this shift", "Is shift ke sab questions delete karo"),
 "type_del": ("पुष्टि के लिए DELETE लिखें", "Type DELETE to confirm", "Confirm ke liye DELETE likho"), "deleted": ("हटाया गया", "Deleted", "Deleted"),
 "total_q": ("कुल सवाल", "Total questions", "Total questions"), "test_ai": ("AI टेस्ट", "Test AI", "AI test"), "test_db": ("DB टेस्ट", "Test DB", "DB test"),
 "q_text": ("सवाल", "Question", "Question"), "opt": ("विकल्प", "Option", "Option"), "ans_letter": ("सही उत्तर", "Correct", "Correct"),
 "back": ("वापस", "Back", "Back"), "secrets_missing": ("Secrets में SUPABASE_URL, SUPABASE_KEY, GEMINI_API_KEY डालें (Settings → Secrets)।", "Add SUPABASE_URL, SUPABASE_KEY, GEMINI_API_KEY in Settings → Secrets.", "Secrets me SUPABASE_URL, SUPABASE_KEY, GEMINI_API_KEY daalo (Settings → Secrets)."),
 "gen_title": ("प्रश्न बनाओ", "Make questions", "Questions banao"),
 "gen_sub": ("कोई भी चैप्टर लिखें या बोलें — AI MCQ बना देगा।", "Type or say any chapter — AI makes MCQs.", "Koi bhi chapter likho ya bolo — AI MCQ bana dega."),
 "chapter_ph": ("चैप्टर लिखें, जैसे: estimesion, बेंडिंग मोमेंट", "Chapter, e.g. estimesion, bending moment", "Chapter likho, jaise: estimesion, bending moment"),
 "gen_go": ("प्रश्न बनाओ", "Generate", "Banao"), "gen_diff": ("कठिनाई", "Level", "Level"),
 "d_mixed": ("मिक्स", "Mixed", "Mixed"), "d_easy": ("आसान", "Easy", "Easy"), "d_medium": ("मध्यम", "Medium", "Medium"), "d_hard": ("कठिन", "Hard", "Hard"),
 "gen_save": ("बने सवाल डेटाबेस में भी सेव करें", "Also save generated questions to database", "Bane sawal database me bhi save karo"),
 "gen_saved": ("{n} सवाल डेटाबेस में सेव हुए", "{n} questions saved to database", "{n} sawal database me save hue"),
 "gen_fail": ("सवाल नहीं बन सके। चैप्टर का नाम बदलकर फिर कोशिश करें।", "Could not generate. Try rephrasing the chapter.", "Sawal nahi bane. Chapter ka naam badal ke try karo."),
 "gen_note": ("⚠️ AI के बनाए उत्तर एक बार जाँच लें।", "⚠️ AI-made answers — please verify.", "⚠️ AI ke answers ek baar verify kar lo."),
 "home_gen_ph": ("कोई भी चैप्टर लिखें → सवाल तैयार", "Type any chapter → get questions", "Koi bhi chapter likho → questions ready"),
 "sec_hint": ("सवाल", "Questions", "Questions"), "of": ("/", "/", "/"),
}
_LI = {"hi": 0, "en": 1, "hn": 2}

def cfg(k):
    return st.session_state.cfg.get(k, DEFAULTS.get(k))

def lang():
    return cfg("ui_lang")

def t(k, **kw):
    v = S.get(k)
    s = v[_LI[lang()]] if v else k
    return s.format(**kw) if kw else s

def e(x):
    return html.escape(str(x if x is not None else ""))

def md_safe(s):
    return str(s).replace("$", "\\$")

def secret(k, default=None):
    try:
        return st.secrets[k]
    except Exception:
        return os.environ.get(k, default)

# ═══════════════════════ 2. APPLE-STYLE CSS ═══════════════════════
def theme_type():
    try:
        return st.context.theme.type or "dark"
    except Exception:
        return "dark"

def _icon(svg):
    svg = ("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2' "
           "stroke-linecap='round' stroke-linejoin='round'>" + svg + "</svg>")
    return 'url("data:image/svg+xml,' + svg.replace("<", "%3C").replace(">", "%3E").replace("#", "%23") + '")'

NAV_ICONS = [
 "<path d='M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z'/><polyline points='9 22 9 12 15 12 15 22'/>",
 "<path d='M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z'/><path d='M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z'/>",
 "<circle cx='12' cy='12' r='10'/><polyline points='12 6 12 12 16 14'/>",
 "<path d='M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9z'/><path d='M19 16l.8 2.2L22 19l-2.2.8L19 22l-.8-2.2L16 19l2.2-.8z'/>",
 "<path d='M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z'/><polyline points='14 2 14 8 20 8'/><line x1='16' y1='13' x2='8' y2='13'/><line x1='16' y1='17' x2='8' y2='17'/>",
 "<line x1='4' y1='6' x2='20' y2='6'/><line x1='4' y1='12' x2='20' y2='12'/><line x1='4' y1='18' x2='20' y2='18'/>",
]

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Hind:wght@400;500;600;700&display=swap');
:root{--acc:__ACC__;--acc2:__ACC2__;--bg:__BG__;--card:__CARD__;--text:__TEXT__;--sub:__SUB__;--line:__LINE__;
--navbg:__NAV__;--r:__R__px;--blur:__BLUR__px;--ok:#30D158;--bad:#FF453A;--warn:#FF9F0A;--fs:__FS__}
.stApp,.stApp p,.stApp label,.stApp button,.stApp input,.stApp textarea,.stApp li,.stApp h1,.stApp h2,.stApp h3,.stApp h4,.stMarkdown{
 font-family:-apple-system,BlinkMacSystemFont,'SF Pro Display','SF Pro Text',Inter,Hind,'Segoe UI',Roboto,sans-serif}
.stApp{background:var(--bg)!important;color:var(--text)}
.stApp p,.stApp label,.stApp li{font-size:calc(1rem*var(--fs))}
header[data-testid="stHeader"]{background:transparent!important}
[data-testid="stSidebar"],[data-testid="stSidebarCollapsedControl"],.stAppDeployButton,[data-testid="stDeployButton"],footer{display:none!important}
.block-container{position:relative;max-width:760px!important;padding:2.2rem 1rem 8rem!important}
h1,h2,h3{letter-spacing:-.02em;font-weight:700}
.apptitle{font-size:1.9rem;font-weight:800;letter-spacing:-.03em;line-height:1.1;margin:0}
.apptitle small{display:block;font-size:.8rem;font-weight:500;color:var(--sub);letter-spacing:0;margin-top:2px}
.card{background:var(--card);backdrop-filter:blur(var(--blur)) saturate(180%);-webkit-backdrop-filter:blur(var(--blur)) saturate(180%);
 border:1px solid var(--line);border-radius:var(--r);padding:16px 18px;margin:0 0 12px}
.hero{background:linear-gradient(135deg,var(--acc),var(--acc2));color:#fff;border-radius:calc(var(--r) + 6px);padding:20px;margin:0 0 14px;
 display:flex;align-items:center;justify-content:space-between;gap:14px;box-shadow:0 14px 34px color-mix(in srgb,var(--acc) 35%,transparent)}
.hero h2{margin:0;font-size:1.45rem;color:#fff}.hero p{margin:4px 0 0;color:rgba(255,255,255,.88);font-size:.92rem}
.ring{--p:0;width:86px;height:86px;border-radius:50%;flex:none;background:conic-gradient(#fff calc(var(--p)*1%),rgba(255,255,255,.28) 0);display:grid;place-items:center}
.ring>div{width:68px;height:68px;border-radius:50%;background:var(--acc2);display:grid;place-items:center;font-weight:800;font-size:1.05rem;color:#fff}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(104px,1fr));gap:10px;margin-bottom:12px}
.stat{background:var(--card);border:1px solid var(--line);border-radius:var(--r);padding:12px 14px;backdrop-filter:blur(var(--blur))}
.stat b{display:block;font-size:1.5rem;font-weight:800;letter-spacing:-.02em;line-height:1.15}.stat span{font-size:.76rem;color:var(--sub);font-weight:500}
.chip{display:inline-block;padding:3px 10px;border-radius:999px;font-size:.72rem;font-weight:600;background:color-mix(in srgb,var(--acc) 16%,transparent);color:var(--acc);margin:0 6px 6px 0}
.chip.g{background:color-mix(in srgb,var(--ok) 16%,transparent);color:var(--ok)}.chip.r{background:color-mix(in srgb,var(--bad) 16%,transparent);color:var(--bad)}
.chip.o{background:color-mix(in srgb,var(--warn) 18%,transparent);color:var(--warn)}.chip.n{background:var(--line);color:var(--sub)}
.sub{color:var(--sub);font-size:.85rem}
.qtext{font-size:calc(1.08rem*var(--fs));line-height:1.65;font-weight:500;margin:6px 0 4px;white-space:pre-wrap}
.banner{border-radius:var(--r);padding:12px 16px;font-weight:600;margin:10px 0}
.banner.ok{background:color-mix(in srgb,var(--ok) 15%,transparent);color:var(--ok);border:1px solid color-mix(in srgb,var(--ok) 40%,transparent)}
.banner.bad{background:color-mix(in srgb,var(--bad) 15%,transparent);color:var(--bad);border:1px solid color-mix(in srgb,var(--bad) 40%,transparent)}
.timer{display:flex;justify-content:space-between;align-items:center;background:var(--navbg);backdrop-filter:blur(20px);border:1px solid var(--line);
 border-radius:999px;padding:8px 18px;font-weight:700;font-variant-numeric:tabular-nums;margin-bottom:10px}
.timer b{font-size:1.25rem}.timer.low b{color:var(--bad)}
.bar{height:6px;border-radius:99px;background:var(--line);overflow:hidden;margin:6px 0 12px}.bar>i{display:block;height:100%;background:linear-gradient(90deg,var(--acc),var(--acc2));border-radius:99px}
.stButton>button,.stDownloadButton>button,.stFormSubmitButton>button{border-radius:999px;border:1px solid var(--line);background:var(--card);color:var(--text);
 font-weight:600;padding:.5rem 1.1rem;transition:transform .12s ease,background .2s,box-shadow .2s}
.stButton>button:hover,.stDownloadButton>button:hover{border-color:var(--acc);color:var(--acc)}
.stButton>button:active,.stDownloadButton>button:active{transform:scale(.95)}
.stButton>button[kind="primary"],button[data-testid="stBaseButton-primary"],.stFormSubmitButton>button[kind="primary"]{
 background:linear-gradient(135deg,var(--acc),var(--acc2))!important;color:#fff!important;border:none!important;box-shadow:0 6px 18px color-mix(in srgb,var(--acc) 35%,transparent)}
.stTextInput input,.stTextArea textarea,.stNumberInput input,[data-baseweb="select"]>div{border-radius:calc(var(--r) - 6px)!important}
[data-testid="stChatInput"]{border-radius:999px}
.stTabs [data-baseweb="tab-list"]{background:var(--card);border-radius:999px;padding:4px;gap:2px;border:1px solid var(--line);overflow-x:auto}
.stTabs [data-baseweb="tab"]{border-radius:999px;padding:6px 14px;height:auto;font-weight:600}
.stTabs [aria-selected="true"]{background:var(--acc);color:#fff!important}
.stTabs [data-baseweb="tab-highlight"],.stTabs [data-baseweb="tab-border"]{display:none}
[data-testid="stExpander"]{border-radius:var(--r);border:1px solid var(--line);background:var(--card)}
[data-testid="stMetric"]{background:var(--card);border:1px solid var(--line);border-radius:var(--r);padding:10px 14px}
[class*="st-key-opts"] [role="radiogroup"]{gap:10px}
[class*="st-key-opts"] label[data-baseweb="radio"]{background:var(--card);border:1.5px solid var(--line);border-radius:var(--r);padding:13px 16px;width:100%;margin:0;transition:all .15s}
[class*="st-key-opts"] label[data-baseweb="radio"]>div:first-child{display:none}
[class*="st-key-opts"] label[data-baseweb="radio"]:has(input:checked){border-color:var(--acc);background:color-mix(in srgb,var(--acc) 14%,transparent)}
[class*="st-key-opts"] label[data-baseweb="radio"]:active{transform:scale(.985)}
.st-key-langbar{position:absolute;top:-6px;right:0;width:auto}
.st-key-langbar [role="radiogroup"]{background:var(--card);border:1px solid var(--line);border-radius:999px;padding:3px;gap:0;flex-wrap:nowrap}
.st-key-langbar label[data-baseweb="radio"]{padding:3px 10px;margin:0;border-radius:999px}
.st-key-langbar label[data-baseweb="radio"]>div:first-child{display:none}
.st-key-langbar label[data-baseweb="radio"] p{font-size:.78rem!important;font-weight:700}
.st-key-langbar label[data-baseweb="radio"]:has(input:checked){background:var(--acc)}
.st-key-langbar label[data-baseweb="radio"]:has(input:checked) p{color:#fff}
.st-key-bottomnav{position:fixed;left:0;right:0;bottom:0;z-index:999;padding:6px 8px calc(8px + env(safe-area-inset-bottom,0px));
 background:var(--navbg);backdrop-filter:blur(24px) saturate(180%);-webkit-backdrop-filter:blur(24px) saturate(180%);border-top:1px solid var(--line)}
.st-key-bottomnav [role="radiogroup"]{display:flex;justify-content:space-around;gap:0;max-width:640px;margin:0 auto;flex-wrap:nowrap}
.st-key-bottomnav label[data-baseweb="radio"]{flex-direction:column;align-items:center;gap:2px;padding:4px 6px;margin:0;border-radius:12px;min-width:50px;flex:1}
.st-key-bottomnav label[data-baseweb="radio"]>div:first-child{display:none}
.st-key-bottomnav label[data-baseweb="radio"] p{font-size:.64rem!important;font-weight:600;color:var(--sub);margin:0;white-space:nowrap}
.st-key-bottomnav label[data-baseweb="radio"]::before{content:'';width:25px;height:25px;background:var(--sub);
 -webkit-mask:var(--ic) center/contain no-repeat;mask:var(--ic) center/contain no-repeat;transition:background .15s,transform .15s}
.st-key-bottomnav label[data-baseweb="radio"]:has(input:checked)::before{background:var(--acc);transform:translateY(-1px) scale(1.08)}
.st-key-bottomnav label[data-baseweb="radio"]:has(input:checked) p{color:var(--acc)}
__NAVICONS__
.st-key-timerbar{position:sticky;top:.5rem;z-index:50}
@media (max-width:640px){.block-container{padding-left:.8rem!important;padding-right:.8rem!important}.hero h2{font-size:1.25rem}}
@media (prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}}
</style>
"""

def inject_css():
    dark = theme_type() != "light"
    a1, a2 = ACCENTS.get(cfg("accent"), ACCENTS["blue"])
    if dark:
        bg = "#000000" if cfg("amoled") else "#0B0B10"
        pal = dict(CARD="rgba(44,44,52,.55)" if cfg("glass") else "#1C1C22", TEXT="#F5F5F7", SUB="#9A9AA5",
                   LINE="rgba(255,255,255,.10)", NAV="rgba(18,18,24,.82)")
    else:
        bg = "#F2F2F7"
        pal = dict(CARD="rgba(255,255,255,.78)" if cfg("glass") else "#FFFFFF", TEXT="#1C1C1E", SUB="#6E6E73",
                   LINE="rgba(0,0,0,.08)", NAV="rgba(249,249,252,.85)")
    nav_icons = "".join(f'.st-key-bottomnav label[data-baseweb="radio"]:nth-of-type({i+1}){{--ic:{_icon(s)}}}'
                        for i, s in enumerate(NAV_ICONS))
    nav_icons = nav_icons.replace("stroke-width='2'", "stroke-width='2'")
    css = (CSS.replace("__ACC__", a1).replace("__ACC2__", a2).replace("__BG__", bg)
           .replace("__CARD__", pal["CARD"]).replace("__TEXT__", pal["TEXT"]).replace("__SUB__", pal["SUB"])
           .replace("__LINE__", pal["LINE"]).replace("__NAV__", pal["NAV"])
           .replace("__R__", "20" if cfg("radius") == "round" else "8").replace("__BLUR__", "22" if cfg("glass") else "0")
           .replace("__FS__", str(cfg("font_scale") / 100)).replace("__NAVICONS__", nav_icons))
    st.markdown(css, unsafe_allow_html=True)

from zoneinfo import ZoneInfo

# ═══════════════════════ 3. STATE · CLIENTS · AI ═══════════════════════
def init_state():
    ss = st.session_state
    ss.setdefault("cfg", dict(DEFAULTS))
    ss.setdefault("profile", None)
    ss.setdefault("bookmarks", set())
    ss.setdefault("wrong", set())
    ss.setdefault("days", {})
    ss.setdefault("nav", "home")
    ss.setdefault("chat", [])
    ss.setdefault("ai_cache", {})
    ss.setdefault("mock", None)
    ss.setdefault("pr", None)
    ss.setdefault("admin_ok", False)
    ss.setdefault("db_err", "")
    ss.setdefault("ai_err", "")

if "cfg" not in st.session_state:
    init_state()
init_state()

SB_URL, SB_KEY, G_KEY = secret("SUPABASE_URL"), secret("SUPABASE_KEY"), secret("GEMINI_API_KEY")

@st.cache_resource(show_spinner=False)
def get_clients(url, key, gkey):
    return create_client(url, key), genai.Client(api_key=gkey)

def sb():
    return get_clients(SB_URL, SB_KEY, G_KEY)[0]

def ai():
    return get_clients(SB_URL, SB_KEY, G_KEY)[1]

def _models():
    raw = str(secret("GEMINI_MODELS", ",".join(DEFAULT_MODELS)))
    lst = [m.strip() for m in raw.split(",") if m.strip()]
    good = st.session_state.get("good_model")
    if good in lst:
        lst.remove(good); lst.insert(0, good)
    return lst

def ai_text(contents, json_mode=False):
    err = None
    for m in _models():
        try:
            conf = types.GenerateContentConfig(response_mime_type="application/json") if json_mode else None
            r = ai().models.generate_content(model=m, contents=contents, config=conf)
            if r.text:
                st.session_state.good_model = m
                return r.text
        except Exception as ex:
            err = ex
    st.session_state.ai_err = f"{type(err).__name__}: {err}"
    return None

def ai_stream(contents):
    err = None
    for m in _models():
        started = False
        try:
            for ch in ai().models.generate_content_stream(model=m, contents=contents):
                if ch.text:
                    started = True
                    yield ch.text
            if started:
                st.session_state.good_model = m
                return
        except Exception as ex:
            err = ex
            if started:
                return
    st.session_state.ai_err = f"{type(err).__name__}: {err}"
    yield "⚠️ " + t("ai_fail")

def parse_json(txt):
    if not txt:
        return None
    s = re.sub(r"^```(?:json)?|```$", "", txt.strip(), flags=re.M).strip()
    try:
        return json.loads(s)
    except Exception:
        pass
    pos = [i for i in (s.find("["), s.find("{")) if i != -1]
    if not pos:
        return None
    i = min(pos); j = max(s.rfind("]"), s.rfind("}"))
    try:
        return json.loads(s[i:j + 1])
    except Exception:
        return None

def lang_rule():
    return {"auto": "Reply in the SAME language and script the student wrote in (Devanagari Hindi -> Hindi; English -> English; Roman-script Hindi -> Hinglish).",
            "hi": "Reply in simple Hindi (Devanagari), keeping technical terms in English in brackets.",
            "en": "Reply in simple English.",
            "hn": "Reply in friendly Hinglish (Hindi written in Roman script, technical terms in English)."}[cfg("ai_lang")]

def embed_texts(texts):
    last = None
    for m in EMBED_MODELS:
        try:
            r = ai().models.embed_content(model=m, contents=texts,
                                          config=types.EmbedContentConfig(output_dimensionality=768))
            return [list(x.values) for x in r.embeddings]
        except Exception as ex:
            last = ex
    raise last

# ═══════════════════════ 4. DATA LAYER ═══════════════════════
COLS = "id,q_no,question_text,options,correct_option,explanation,subject,topic,difficulty,year,shift_name,exam"

def parse_opts(v):
    for _ in range(3):
        if isinstance(v, str):
            try:
                v = json.loads(v)
            except Exception:
                return []
    if isinstance(v, dict):
        v = list(v.values())
    return [str(x) for x in (v or []) if str(x).strip()]

def normc(v):
    if v is None:
        return None
    s = str(v).strip().upper()
    if not s:
        return None
    if s[0] in "1234" and len(s) <= 2:
        return LETTERS["1234".index(s[0])]
    if s[0] in LETTERS and (len(s) == 1 or not s[1].isalpha()):
        return s[0]
    return None

def norm_q(r):
    return dict(id=r.get("id"), q_no=r.get("q_no"), text=r.get("question_text") or "", options=parse_opts(r.get("options")),
                correct=normc(r.get("correct_option")), expl=r.get("explanation") or "",
                subject=r.get("subject") or "General", topic=r.get("topic") or "General",
                difficulty=r.get("difficulty") or "medium", year=r.get("year"), shift=r.get("shift_name") or "", exam=r.get("exam") or "")

@st.cache_data(ttl=300, show_spinner=False)
def fetch_questions(subjects=(), topics=(), shifts=(), diffs=(), ids=(), limit=1500):
    try:
        q = sb().table("rrb_questions").select(COLS)
        if subjects: q = q.in_("subject", list(subjects))
        if topics: q = q.in_("topic", list(topics))
        if shifts: q = q.in_("shift_name", list(shifts))
        if diffs: q = q.in_("difficulty", list(diffs))
        if ids: q = q.in_("id", list(ids))
        rows = q.order("id").range(0, limit - 1).execute().data or []
        return [norm_q(r) for r in rows]
    except Exception as ex:
        return [dict(_error=f"{type(ex).__name__}: {ex}")]

def get_questions(**kw):
    kw = {k: tuple(v) if isinstance(v, (list, set, tuple)) else v for k, v in kw.items()}
    rows = fetch_questions(**kw)
    if rows and "_error" in rows[0]:
        st.session_state.db_err = rows[0]["_error"]
        return []
    st.session_state.db_err = ""
    return rows

@st.cache_data(ttl=300, show_spinner=False)
def fetch_meta():
    try:
        rows = sb().table("rrb_questions").select("subject,topic,shift_name,difficulty").range(0, 9999).execute().data or []
        return pd.DataFrame(rows)
    except Exception as ex:
        return pd.DataFrame([{"_error": str(ex)}])

def meta():
    df = fetch_meta()
    if "_error" in df.columns:
        st.session_state.db_err = str(df["_error"].iloc[0])
        return pd.DataFrame(columns=["subject", "topic", "shift_name", "difficulty"])
    return df

def uniq(df, col):
    return sorted([x for x in df[col].dropna().unique().tolist() if str(x).strip()]) if col in df.columns and len(df) else []

def db_error_box():
    if st.session_state.db_err:
        st.error(t("db_err") + "\n\n`" + st.session_state.db_err[:400] + "`")

def prepare_q(q, shuffle_opts):
    q = dict(q)
    if shuffle_opts and len(q["options"]) >= 2:
        idx = list(range(len(q["options"])))
        random.shuffle(idx)
        corr = LETTERS.index(q["correct"]) if q["correct"] and LETTERS.index(q["correct"]) < len(q["options"]) else None
        q["options"] = [q["options"][i] for i in idx]
        if corr is not None:
            q["correct"] = LETTERS[idx.index(corr)]
    return q

def grade(q, ans):
    if not ans: return None
    if not q.get("correct"): return None
    return ans == q["correct"]

# ── profile / progress ──
def now_ist():
    return dt.datetime.now(ZoneInfo("Asia/Kolkata"))

def today_s():
    return now_ist().date().isoformat()

def bump_today(n=1):
    d = st.session_state.days
    d[today_s()] = d.get(today_s(), 0) + n

def streak():
    d, n, day = st.session_state.days, 0, now_ist().date()
    if d.get(day.isoformat(), 0) == 0:
        day -= dt.timedelta(days=1)
    while d.get(day.isoformat(), 0) > 0:
        n += 1; day -= dt.timedelta(days=1)
    return n

def save_profile():
    p = st.session_state.profile
    if not p: return False
    try:
        sb().table("profiles").upsert(dict(code=p["code"], name=p["name"], settings=st.session_state.cfg,
              data=dict(bookmarks=list(st.session_state.bookmarks), wrong=list(st.session_state.wrong),
                        days=st.session_state.days))).execute()
        return True
    except Exception as ex:
        st.session_state.db_err = f"{type(ex).__name__}: {ex}"
        return False

def load_profile(code):
    try:
        r = sb().table("profiles").select("*").eq("code", code).execute().data
    except Exception as ex:
        st.session_state.db_err = f"{type(ex).__name__}: {ex}"
        return False
    if not r: return False
    r = r[0]; ss = st.session_state
    ss.profile = dict(code=r["code"], name=r.get("name") or "")
    ss.cfg = {**DEFAULTS, **(r.get("settings") or {})}
    d = r.get("data") or {}
    ss.bookmarks, ss.wrong, ss.days = set(d.get("bookmarks", [])), set(d.get("wrong", [])), dict(d.get("days", {}))
    for k in [k for k in ss if k.startswith("w_")]:
        del ss[k]
    try: st.query_params["u"] = code
    except Exception: pass
    return True

def save_attempt(res):
    p = st.session_state.profile
    if not p: return False
    try:
        sb().table("attempts").insert(dict(profile_code=p["code"], mode=res["mode"], score=res["score"], max_score=res["max"],
            correct=res["correct"], wrong=res["wrong"], skipped=res["skipped"], total_time_sec=int(res["time"]),
            details=res["rows"])).execute()
        return True
    except Exception as ex:
        st.session_state.db_err = f"{type(ex).__name__}: {ex}"
        return False

@st.cache_data(ttl=60, show_spinner=False)
def fetch_attempts(code):
    try:
        return sb().table("attempts").select("id,mode,score,max_score,correct,wrong,skipped,total_time_sec,details,created_at") \
            .eq("profile_code", code).order("created_at", desc=True).limit(200).execute().data or []
    except Exception:
        return []

# ═══════════════════════ 5. PDF PARSER  (shift-proof) ═══════════════════════
HDR = [r"previous year paper", r"test date", r"test time", r"correct answer will carry", r"chosen option", r"^\s*section\b",
       r"^\s*note\s*[:\-]", r"page\s*\d+\s*(of|/)\s*\d+", r"^\s*\d+\s*/\s*\d+\s*$", r"www\.", r"adda247", r"testbook",
       r"download (the )?app", r"^\s*question id", r"^\s*status\s*:", r"^\s*option \d+ id", r"^\s*(marks|marking)\b.*:", r"^\s*shift\s*[-:]?\s*\d+\s*$",
       r"^\s*(candidate|roll no|exam date|subject)\s*:?"]
HDR_RE = re.compile("|".join(HDR), re.I)
QS_Q = re.compile(r"^\s*(?:Question|Que|Q)\s*[\.\:\-]?\s*(\d{1,3})\s*[\.\)\:\-]?\s*(.*)$", re.I)
QS_PLAIN = re.compile(r"^\s*(\d{1,3})\s*[\.\)]\s+(\S.*)$")
OPT_A = re.compile(r"^\s*\(?([A-Da-d])[\)\.\:]\s*(\S.*)$")
OPT_N = re.compile(r"^\s*\(?([1-4])[\)\.]\s*(\S.*)$")
OPT_W = re.compile(r"^\s*(?:Ans(?:wer)?|Option|Opt)\s*\.?\s*\(?([A-Da-d1-4])[\)\.\:]?\s+(\S.*)$", re.I)
ANS_L = re.compile(r"^\s*(?:Correct\s*)?(?:Ans(?:wer)?|Right\s*Answer|Correct\s*Option)\s*[:\-\.]?\s*\(?([A-Da-d1-4])\)?\s*\.?\s*$", re.I)
EXP_L = re.compile(r"^\s*(?:Explanation|Solution|Sol|Hint)\s*[:\-]\s*(.*)$", re.I)

def extract_pages(f):
    pages = []
    with pdfplumber.open(f) as pdf:
        for p in pdf.pages:
            pages.append((p.extract_text() or "").replace("\x00", ""))
    return pages

def strip_headers(pages):
    cnt = {}
    norm = lambda l: re.sub(r"\d+", "#", l.strip().lower())
    for p in pages:
        for l in {norm(x) for x in p.splitlines() if 3 < len(x.strip()) < 90}:
            cnt[l] = cnt.get(l, 0) + 1
    lim = max(3, int(len(pages) * 0.6)) if len(pages) >= 4 else 10 ** 9
    out = []
    for p in pages:
        for l in p.splitlines():
            s = l.strip()
            if not s or HDR_RE.search(s) or cnt.get(norm(l), 0) >= lim:
                continue
            out.append(s)
    return out

def split_inline_options(text):
    ms = list(re.finditer(r"(?:(?<=\s)|^)\(?([A-Da-d1-4])[\)\.]\s", text))
    best = None
    for i, m in enumerate(ms):
        if m.group(1) not in "Aa1":
            continue
        chain, want = [m], 1
        for n in ms[i + 1:]:
            nxt = "ABCD"[want] if m.group(1) in "Aa" else "1234"[want]
            if n.group(1).upper() == nxt:
                chain.append(n); want += 1
                if want == 4: break
        if len(chain) >= 2:
            best = chain
    if not best:
        return text, []
    opts = []
    for k, m in enumerate(best):
        end = best[k + 1].start() if k + 1 < len(best) else len(text)
        opts.append(text[m.end():end].strip())
    return text[:best[0].start()].strip(), opts

def parse_questions(pages):
    lines = strip_headers(pages)
    qmode = sum(1 for l in lines if QS_Q.match(l)) >= 3
    qs, cur, expected, in_exp = [], None, 1, False

    def new(no, rest):
        nonlocal cur, expected, in_exp
        cur = dict(q_no=no, stem=[rest] if rest else [], opts=[], style=None, ans=None, exp=[])
        qs.append(cur); expected = no + 1; in_exp = False

    for l in lines:
        m = EXP_L.match(l)
        if cur and m:
            in_exp = True
            if m.group(1): cur["exp"].append(m.group(1))
            continue
        m = ANS_L.match(l)
        if cur and m:
            cur["ans"] = normc(m.group(1)); continue
        if qmode:
            m = QS_Q.match(l)
            if m:
                new(int(m.group(1)), m.group(2).strip()); continue
        else:
            m = QS_PLAIN.match(l)
            if m and int(m.group(1)) == expected:
                n_opts = len(cur["opts"]) if cur else 0
                if cur is None or n_opts == 0 or n_opts >= 4 or cur["style"] == "alpha":
                    new(int(m.group(1)), m.group(2).strip()); continue
        if cur is None:
            continue
        m = OPT_W.match(l) or OPT_A.match(l)
        if m and not in_exp:
            _, inl = split_inline_options(l)
            cur["opts"].extend(inl if len(inl) >= 2 else [m.group(2).strip()]); cur["style"] = cur["style"] or "alpha"; continue
        m = OPT_N.match(l)
        if m and not in_exp and (cur["style"] in (None, "num")) and cur["stem"]:
            _, inl = split_inline_options(l)
            cur["opts"].extend(inl if len(inl) >= 2 else [m.group(2).strip()]); cur["style"] = "num"; continue
        if in_exp:
            cur["exp"].append(l)
        elif cur["opts"]:
            cur["opts"][-1] += " " + l
        else:
            cur["stem"].append(l)
    out = []
    for c in qs:
        stem, opts = " ".join(c["stem"]).strip(), c["opts"]
        if not opts:
            stem, opts = split_inline_options(stem)
        opts = [o for o in opts if o][:4]
        ok = len(stem) >= 8 and (len(opts) >= 2 or "?" in stem or "_" in stem or len(stem) >= 30)
        if ok:
            out.append(dict(q_no=c["q_no"], text=re.sub(r"\s+", " ", stem), options=opts, correct=c["ans"],
                            expl=" ".join(c["exp"]).strip()))
    return out

def parse_answer_key(text):
    keys = {}
    for n, a in re.findall(r"(?<!\d)(\d{1,3})\s*[\.\-\:\)–]\s*\(?([A-Da-d1-4])\)?(?![A-Za-z0-9])", text or ""):
        keys.setdefault(int(n), normc(a))
    return keys

def read_key_file(f):
    name = f.name.lower()
    if name.endswith(".pdf"):
        return "\n".join(extract_pages(f))
    return f.getvalue().decode("utf-8", "ignore")

# ── auto classification (keyword engine; AI optional) ──
TOPIC_KW = {
 ("Civil Engineering", "Estimation & Costing"): ["estimat", "plinth", "carpet area", "bill of quantit", "rate analysis", "specification", "quantity survey", "प्लिंथ", "आकलन"],
 ("Civil Engineering", "Surveying"): ["survey", "theodolite", "levelling", "contour", "traverse", "chain", "compass", "tacheometer", "सर्वे"],
 ("Civil Engineering", "Soil Mechanics"): ["soil", "bearing capacity", "consolidation", "permeability", "foundation", "atterberg", "मिट्टी"],
 ("Civil Engineering", "Concrete Technology"): ["concrete", "cement", "slump", "curing", "water cement", "aggregate", "mortar", "कंक्रीट", "सीमेंट"],
 ("Civil Engineering", "RCC & Steel"): ["rcc", "reinforc", "steel structure", "prestress", "column", "slab", "stirrup"],
 ("Civil Engineering", "Strength of Materials"): ["bending moment", "shear force", "deflection", "stress", "strain", "poisson", "young", "beam", "moment of inertia", "बीम"],
 ("Civil Engineering", "Fluid Mechanics & Hydraulics"): ["fluid", "hydraul", "bernoulli", "manning", "reynolds", "discharge", "weir", "pipe flow", "pump"],
 ("Civil Engineering", "Transportation & Environmental"): ["highway", "pavement", "railway", "traffic", "sewage", "water supply", "bod", "irrigation", "canal"],
 ("Electrical Engineering", "Circuits & Networks"): ["kirchhoff", "ohm", "thevenin", "norton", "resistor", "capacitor", "inductor", "impedance", "ac circuit"],
 ("Electrical Engineering", "Machines"): ["transformer", "induction motor", "dc motor", "alternator", "synchronous", "armature", "generator", "slip"],
 ("Electrical Engineering", "Power Systems"): ["transmission line", "circuit breaker", "relay", "power factor", "fuse", "distribution", "insulator", "earthing"],
 ("Electrical Engineering", "Measurements & Electronics"): ["voltmeter", "ammeter", "wattmeter", "diode", "transistor", "amplifier", "logic gate", "oscillator"],
 ("Mechanical Engineering", "Thermodynamics"): ["thermodynamic", "entropy", "enthalpy", "carnot", "otto", "diesel cycle", "boiler", "refrigerat", "steam"],
 ("Mechanical Engineering", "Machines & Manufacturing"): ["lathe", "milling", "welding", "gear", "bearing", "casting", "heat treatment", "turbine", "pelton", "drilling"],
 ("Mathematics", "Arithmetic & Algebra"): ["profit", "loss", "percentage", "ratio", "average", "interest", "simplif", "equation", "lcm", "hcf", "speed", "प्रतिशत"],
 ("Mathematics", "Geometry & Mensuration"): ["triangle", "circle", "area of", "volume", "perimeter", "trigonometr", "sin ", "cos "],
 ("Reasoning", "Reasoning"): ["series", "coding", "analogy", "odd one", "syllogism", "blood relation", "direction", "venn", "missing number"],
 ("General Science", "General Science"): ["physics", "chemistry", "biology", "acid", "newton", "vitamin", "atom", "electron", "velocity"],
 ("General Awareness", "Current Affairs & GK"): ["capital of", "president", "prime minister", "award", "founded", "national", "constitution", "river", "ministry", "dynasty"],
 ("Computer", "Computer Basics"): ["computer", "ram", "cpu", "software", "internet", "excel", "windows", "binary", "keyboard"],
}

def classify(text):
    low = text.lower(); best, score = ("General", "General"), 0
    for key, kws in TOPIC_KW.items():
        sc = sum(1 for k in kws if k in low)
        if sc > score:
            best, score = key, sc
    return best

def qhash(text, opts):
    return hashlib.sha1(re.sub(r"[^a-z0-9\u0900-\u097f]", "", (text + "".join(opts)).lower()).encode()).hexdigest()

# ═══════════════════════ 6. PDF GENERATOR (A4, Hindi-safe via Hind font + HarfBuzz) ═══════════════════════
FONT_URLS = {"Hind-Regular.ttf": "https://github.com/google/fonts/raw/main/ofl/hind/Hind-Regular.ttf",
             "Hind-Bold.ttf": "https://github.com/google/fonts/raw/main/ofl/hind/Hind-Bold.ttf"}

@st.cache_resource(show_spinner=False)
def ensure_fonts():
    for base in (os.path.join(os.getcwd(), "fonts"), "/tmp/pyq_fonts"):
        p = [os.path.join(base, n) for n in FONT_URLS]
        if all(os.path.exists(x) and os.path.getsize(x) > 10000 for x in p):
            return p
    os.makedirs("/tmp/pyq_fonts", exist_ok=True)
    paths = []
    try:
        for n, u in FONT_URLS.items():
            dst = os.path.join("/tmp/pyq_fonts", n)
            with urllib.request.urlopen(u, timeout=25) as r, open(dst, "wb") as fh:
                fh.write(r.read())
            paths.append(dst)
        return paths
    except Exception:
        return None

class QPDF(FPDF):
    fam, foot = "Helvetica", ""
    def footer(self):
        self.set_y(-12); self.set_font(self.fam, "", 8); self.set_text_color(130)
        self.cell(0, 6, f"{self.foot}   {self.page_no()}", align="C")

def build_pdf(subject, chapter, qs, show_opts=True, show_key=True, show_expl=False, fs=10, footer="PYQ Master"):
    paths = ensure_fonts()
    pdf = QPDF(format="A4", unit="mm")
    pdf.set_margins(14, 14, 14); pdf.set_auto_page_break(True, 16)
    if paths:
        pdf.add_font("Hind", "", paths[0]); pdf.add_font("Hind", "B", paths[1]); pdf.fam = "Hind"
        try: pdf.set_text_shaping(True)
        except Exception: pass
    fam = pdf.fam
    tx = (lambda s: str(s)) if paths else (lambda s: str(s).encode("latin-1", "replace").decode("latin-1"))
    pdf.foot = tx(footer); pdf.add_page()
    pdf.set_font(fam, "B", 13); pdf.set_text_color(0)
    for line in (f"[{subject}]", f"Chapter - {chapter}"):
        pdf.cell(0, 7, tx(line), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    lh = fs * 0.52
    for i, q in enumerate(qs, 1):
        with pdf.unbreakable():
            pdf.set_font(fam, "B", fs); pdf.cell(9, lh, f"{i}.")
            pdf.set_font(fam, "", fs); pdf.multi_cell(0, lh, tx(q["text"]), new_x="LMARGIN", new_y="NEXT")
            if show_opts:
                for k, o in enumerate(q["options"][:4]):
                    pdf.set_x(14 + 9); pdf.multi_cell(0, lh, tx(f"({LETTERS[k]})  {o}"), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2.5)
    if show_key:
        pdf.ln(3); pdf.set_font(fam, "B", 12); pdf.cell(0, 7, "Answer Key", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font(fam, "B", fs)
        items = [f"{i}. {q['correct'] or '-'}" for i, q in enumerate(qs, 1)]
        for k in range(0, len(items), 10):
            pdf.multi_cell(0, lh + 1, " | ".join(items[k:k + 10]), new_x="LMARGIN", new_y="NEXT")
    if show_expl and any(q["expl"] for q in qs):
        pdf.ln(4); pdf.set_font(fam, "B", 12); pdf.cell(0, 7, "Solutions", new_x="LMARGIN", new_y="NEXT")
        for i, q in enumerate(qs, 1):
            if q["expl"]:
                with pdf.unbreakable():
                    pdf.set_font(fam, "B", fs - 1); pdf.cell(9, lh, f"{i}.")
                    pdf.set_font(fam, "", fs - 1); pdf.multi_cell(0, lh, tx(q["expl"]), new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())

# ═══════════════════════ 7. UI HELPERS ═══════════════════════
def cfg_widget(kind, name, label, **kw):
    key = "w_" + name
    if key not in st.session_state:
        st.session_state[key] = cfg(name)
    def _cb():
        st.session_state.cfg[name] = st.session_state[key]
    return getattr(st, kind)(label, key=key, on_change=_cb, **kw)

def go(page, src=None):
    st.session_state.nav = page
    if src:
        st.session_state["pr_src"] = src

def page_head(title, sub=""):
    st.markdown(f'<p class="apptitle">{e(title)}<small>{e(sub)}</small></p>', unsafe_allow_html=True)
    st.write("")

def chips(q, extra=""):
    h = f'<span class="chip">{e(q["subject"])}</span><span class="chip n">{e(q["topic"])}</span>'
    if q.get("shift"): h += f'<span class="chip n">{e(q["shift"])}</span>'
    return h + extra

def q_card(q, head="", extra=""):
    st.markdown(f'<div class="card">{head}<div>{chips(q, extra)}</div><div class="qtext">{e(q["text"])}</div></div>', unsafe_allow_html=True)

def opts_radio(q, key, current=None, ckey="opts", disabled=False, on_change=None, args=()):
    letters = list(LETTERS[:len(q["options"])]) if q["options"] else list(LETTERS)
    if q["options"]:
        fmt = lambda L: f"**{L}.**  {md_safe(q['options'][LETTERS.index(L)])}"
    else:
        fmt = lambda L: L
        st.caption(t("no_opts"))
    with st.container(key=ckey):
        return st.radio("opts", letters, index=letters.index(current) if current in letters else None, key=key,
                        format_func=fmt, label_visibility="collapsed", disabled=disabled, on_change=on_change, args=args)

def ai_explain(q):
    key = f"x{q['id']}_{cfg('ai_lang')}"
    c = st.session_state.ai_cache
    if key not in c:
        opts = "\n".join(f"{LETTERS[i]}. {o}" for i, o in enumerate(q["options"]))
        p = (f"You are an expert RRB/SSC JE exam tutor. Explain why the correct answer is right, give the key formula/concept and a quick trick. "
             f"Max 120 words. {lang_rule()}\n\nQuestion: {q['text']}\n{opts}\nCorrect: {q['correct'] or 'unknown - work it out'}")
        c[key] = ai_text(p) or ("⚠️ " + t("ai_fail"))
    return c[key]

def toggle_bm(qid):
    b = st.session_state.bookmarks
    b.discard(qid) if qid in b else b.add(qid)
    save_profile()

def bm_button(q, key):
    on = q["id"] in st.session_state.bookmarks
    st.button(t("bookmarked") if on else "🔖 " + t("bookmark"), key=key, on_click=toggle_bm, args=(q["id"],))

def stat_grid(items):
    st.markdown('<div class="grid">' + "".join(f'<div class="stat"><b>{e(v)}</b><span>{e(l)}</span></div>' for v, l in items) + "</div>",
                unsafe_allow_html=True)

def fmt_dur(sec):
    sec = int(sec); return f"{sec//60}:{sec%60:02d}"

# ═══════════════════════ 8. HOME ═══════════════════════
def greeting():
    h = now_ist().hour
    return t("gm") if h < 12 else t("ga") if h < 17 else t("ge") if h < 21 else t("gn")

def home_gen():
    v = st.session_state.get("hg_txt", "").strip()
    if v:
        st.session_state.gen_req = v; st.session_state.nav = "create"

def page_home():
    ss = st.session_state
    name = (ss.profile or {}).get("name") or t("student")
    done, goal = ss.days.get(today_s(), 0), max(1, cfg("daily_goal"))
    pct = min(100, int(done * 100 / goal))
    st.markdown(f'<div class="hero"><div><h2>{e(greeting())}, {e(name)} 👋</h2><p>{e(t("daily_goal"))}: {e(t("solved", n=done, g=goal))}</p></div>'
                f'<div class="ring" style="--p:{pct}"><div>{pct}%</div></div></div>', unsafe_allow_html=True)
    df = meta()
    db_error_box()
    hist = fetch_attempts(ss.profile["code"]) if ss.profile else []
    acc = "—"
    if hist:
        c = sum(h["correct"] for h in hist); w = sum(h["wrong"] for h in hist)
        acc = f"{int(100*c/(c+w))}%" if c + w else "—"
    stat_grid([(len(df), t("qbank")), (f"🔥 {streak()}", t("streak")), (acc, t("accuracy")), (len(hist), t("mocks"))])
    if ss.mock and not ss.mock["done"]:
        st.button("⏱ " + t("resume_mock"), type="primary", use_container_width=True, on_click=go, args=("mock",))
    with st.form("homegen", clear_on_submit=True):
        c1, c2 = st.columns([5, 1])
        c1.text_input("c", key="hg_txt", placeholder=t("home_gen_ph"), label_visibility="collapsed")
        c2.form_submit_button("✨", type="primary", use_container_width=True, on_click=home_gen)
    # question of the day
    pool = get_questions(limit=300) if len(df) else []
    if pool:
        q = random.Random(now_ist().date().toordinal()).choice(pool)
        st.markdown(f"##### {t('qotd')}")
        q_card(q)
        a = opts_radio(q, f"qd_{q['id']}", ckey="opts_qd")
        if a:
            ok = grade(q, a)
            if ok is None: st.info(t("no_key"))
            else: st.markdown(f'<div class="banner {"ok" if ok else "bad"}">{t("correct") if ok else t("wrong") + " · " + t("right_ans") + ": " + q["correct"]}</div>', unsafe_allow_html=True)
    elif not ss.db_err:
        st.info(t("empty_db"))
    # weak topics
    if hist:
        rows = [r for h in hist for r in (h.get("details") or []) if isinstance(r, dict)]
        if rows:
            d = pd.DataFrame(rows)
            if {"t", "st"} <= set(d.columns):
                g = d[d["st"].isin(["correct", "wrong"])].groupby("t")["st"].agg(n="count", ok=lambda s: (s == "correct").sum())
                g = g[g["n"] >= 2]; g["acc"] = (g["ok"] * 100 / g["n"]).round()
                g = g.sort_values("acc").head(4)
                st.markdown(f"##### {t('weak')}")
                if len(g):
                    for tp, r in g.iterrows():
                        st.markdown(f'<div class="card" style="padding:10px 16px"><b>{e(tp)}</b> <span class="chip r" style="float:right">{int(r["acc"])}%</span></div>', unsafe_allow_html=True)
                else:
                    st.caption(t("no_weak"))

# ═══════════════════════ 9. PRACTICE ═══════════════════════
def filters_ui(prefix, df, with_count=True, default_n=15, maxn=100):
    subs = uniq(df, "subject")
    c1, c2 = st.columns(2)
    sel_s = c1.multiselect(t("subject"), subs, key=f"{prefix}_s")
    topics = uniq(df[df["subject"].isin(sel_s)] if sel_s and len(df) else df, "topic")
    sel_t = c2.multiselect(t("topic"), topics, key=f"{prefix}_t")
    c3, c4 = st.columns(2)
    sel_h = c3.multiselect(t("shift"), uniq(df, "shift_name"), key=f"{prefix}_h")
    sel_d = c4.multiselect(t("difficulty"), uniq(df, "difficulty") or ["easy", "medium", "hard"], key=f"{prefix}_d")
    n = st.slider(t("count"), 5, maxn, default_n, key=f"{prefix}_n") if with_count else None
    return dict(subjects=sel_s, topics=sel_t, shifts=sel_h, diffs=sel_d), n

def pr_start(flt, n, src):
    ss = st.session_state
    if src == "book": rows = get_questions(ids=list(ss.bookmarks)) if ss.bookmarks else []
    elif src == "wrong": rows = get_questions(ids=list(ss.wrong)) if ss.wrong else []
    else: rows = get_questions(**flt)
    if src != "seq": random.shuffle(rows)
    rows = [prepare_q(q, cfg("shuffle_opts")) for q in rows[:n]]
    if not rows:
        ss.pr_msg = t("no_match"); return
    ss.pr_msg = ""
    ss.pr = dict(qs=rows, i=0, ans={}, checked=set(), ok=0, bad=0, done=False, sid=int(time.time()))

def pr_check(i):
    pr = st.session_state.pr
    if i in pr["checked"]: return
    q, a = pr["qs"][i], pr["ans"].get(i)
    if not a: return
    g = grade(q, a); pr["checked"].add(i); bump_today()
    if g is True:
        pr["ok"] += 1; st.session_state.wrong.discard(q["id"])
    elif g is False:
        pr["bad"] += 1; st.session_state.wrong.add(q["id"])

def pr_pick(i, key):
    pr = st.session_state.pr
    pr["ans"][i] = st.session_state[key]
    if cfg("instant"): pr_check(i)

def pr_move(d):
    pr = st.session_state.pr
    pr["i"] = max(0, min(len(pr["qs"]) - 1, pr["i"] + d))

def pr_finish():
    st.session_state.pr["done"] = True
    save_profile()

def pr_reset():
    st.session_state.pr = None

def page_practice():
    ss = st.session_state
    page_head(t("practice"), t("qbank"))
    pr = ss.pr
    if pr is None:
        df = meta(); db_error_box()
        src = st.radio(t("src_mode"), ["random", "seq", "book", "wrong"], horizontal=True, key="pr_src",
                       format_func=lambda k: {"random": t("m_random"), "seq": t("m_seq"), "book": f"{t('m_book')} ({len(ss.bookmarks)})", "wrong": f"{t('m_wrong')} ({len(ss.wrong)})"}[k])
        flt, n = filters_ui("pf", df)
        if ss.get("pr_msg"): st.warning(ss.pr_msg)
        st.button(t("start"), type="primary", use_container_width=True, on_click=pr_start, args=(flt, n, src))
        return
    qs, i = pr["qs"], pr["i"]
    if pr["done"]:
        tot = pr["ok"] + pr["bad"]
        st.markdown(f'<div class="hero"><div><h2>{t("done_set")}</h2><p>{t("accuracy")}: {int(100*pr["ok"]/tot) if tot else 0}%</p></div></div>', unsafe_allow_html=True)
        stat_grid([(pr["ok"], t("n_correct")), (pr["bad"], t("n_wrong")), (len(qs) - len(pr["checked"]), t("n_skip"))])
        st.button(t("new_set"), type="primary", use_container_width=True, on_click=pr_reset)
        return
    q = qs[i]
    st.markdown(f'<div class="bar"><i style="width:{int(100*(i+1)/len(qs))}%"></i></div>', unsafe_allow_html=True)
    q_card(q, head=f'<div class="sub" style="margin-bottom:6px">{t("sec_hint")} {i+1} {t("of")} {len(qs)}</div>')
    key = f"pr_{pr['sid']}_{i}"
    checked = i in pr["checked"]
    opts_radio(q, key, current=pr["ans"].get(i), ckey="opts_pr", disabled=checked and cfg("instant"), on_change=pr_pick, args=(i, key))
    if not cfg("instant") and not checked and pr["ans"].get(i):
        st.button(t("check"), type="primary", on_click=pr_check, args=(i,), key=f"chk{i}")
    if checked:
        g = grade(q, pr["ans"].get(i))
        if g is None: st.info(t("no_key"))
        else:
            st.markdown(f'<div class="banner {"ok" if g else "bad"}">{t("correct") if g else t("wrong")}'
                        f'{"" if g else " · " + t("right_ans") + ": " + str(q["correct"])}</div>', unsafe_allow_html=True)
        if q["expl"]:
            st.markdown(f"**{t('explain')}**"); st.write(md_safe(q["expl"]))
        want = st.button(t("ai_explain"), key=f"aix{i}") or (g is False and cfg("ai_explain_auto"))
        if want or f"x{q['id']}_{cfg('ai_lang')}" in ss.ai_cache:
            with st.spinner(t("thinking")):
                st.write(ai_explain(q))
    c1, c2, c3 = st.columns([1, 1, 1])
    c1.button("← " + t("prev"), disabled=i == 0, on_click=pr_move, args=(-1,), use_container_width=True, key="pp")
    with c2: bm_button(q, "pbm")
    if i < len(qs) - 1:
        c3.button(t("next") + " →", type="primary", on_click=pr_move, args=(1,), use_container_width=True, key="pn")
    else:
        c3.button(t("finish"), type="primary", on_click=pr_finish, use_container_width=True, key="pf_")

# ═══════════════════════ 10. MOCK TEST (TCS iON style) ═══════════════════════
def mk_start(flt, n, mins, pos, neg):
    ss = st.session_state
    rows = get_questions(**flt)
    if not rows:
        ss.mk_msg = t("no_match"); return
    if cfg("shuffle_q"): random.shuffle(rows)
    rows = [prepare_q(q, cfg("shuffle_opts")) for q in rows[:n]]
    now = time.time()
    ss.mk_msg = ""
    ss.mock = dict(qs=rows, ans={}, mark=set(), visited={0}, cur=0, start=now, end_ts=now + mins * 60, qt={}, qstart=now,
                   done=False, confirm=False, pos=pos, neg=neg, id=int(now), result=None, auto=False, mins=mins)

def mk_go(i):
    m = st.session_state.mock; now = time.time()
    m["qt"][m["cur"]] = m["qt"].get(m["cur"], 0) + now - m["qstart"]
    m["qstart"] = now; m["cur"] = max(0, min(len(m["qs"]) - 1, i)); m["visited"].add(m["cur"]); m["confirm"] = False

def mk_pick(i, key):
    m = st.session_state.mock; m["ans"][i] = st.session_state[key]

def mk_save_next(i):
    st.session_state.mock["mark"].discard(i); mk_go(i + 1)

def mk_mark_next(i):
    st.session_state.mock["mark"].add(i); mk_go(i + 1)

def mk_clear(i, key):
    st.session_state.mock["ans"].pop(i, None); st.session_state.pop(key, None)

def mk_status(m, i):
    a, mk = i in m["ans"], i in m["mark"]
    return 4 if a and mk else 3 if mk else 2 if a else 1 if i in m["visited"] else 0

def compute_result(m):
    m["qt"][m["cur"]] = m["qt"].get(m["cur"], 0) + time.time() - m["qstart"]
    rows, c, w, s, u = [], 0, 0, 0, 0
    for i, q in enumerate(m["qs"]):
        a = m["ans"].get(i); k = q["correct"]
        st_ = "skipped" if not a else "ungraded" if not k else "correct" if a == k else "wrong"
        c += st_ == "correct"; w += st_ == "wrong"; s += st_ == "skipped"; u += st_ == "ungraded"
        rows.append(dict(id=q["id"], s=q["subject"], t=q["topic"], st=st_, a=a, c=k, sec=round(m["qt"].get(i, 0), 1)))
    graded = sum(1 for q in m["qs"] if q["correct"])
    return dict(mode="mock", score=round(c * m["pos"] - w * m["neg"], 2), max=round(graded * m["pos"], 2), correct=c, wrong=w, skipped=s,
                ungraded=u, time=min(time.time(), m["end_ts"]) - m["start"], rows=rows, neg_total=round(w * m["neg"], 2))

def mk_finish(auto=False):
    ss = st.session_state; m = ss.mock
    if not m or m["done"]: return
    res = compute_result(m); m.update(done=True, auto=auto, result=res, saved=False)
    bump_today(res["correct"] + res["wrong"])
    for r, q in zip(res["rows"], m["qs"]):
        if r["st"] == "wrong": ss.wrong.add(q["id"])
        elif r["st"] == "correct": ss.wrong.discard(q["id"])
    m["saved"] = save_attempt(res); save_profile()

def mk_confirm(v):
    st.session_state.mock["confirm"] = v

def mk_new():
    st.session_state.mock = None

def mk_retry_wrong():
    ss = st.session_state; m = ss.mock
    ids = [q["id"] for r, q in zip(m["result"]["rows"], m["qs"]) if r["st"] == "wrong"]
    ss.mock = None
    if ids:
        ss.pr_src = "wrong"; ss.pr = None; ss.nav = "practice"

@st.fragment(run_every=1)
def mk_timer():
    m = st.session_state.mock
    if not m or m["done"]: return
    left = int(m["end_ts"] - time.time())
    if left <= 0:
        mk_finish(auto=True); st.rerun()
    h, r = divmod(left, 3600); mi, s = divmod(r, 60)
    st.markdown(f'<div class="timer{" low" if left < 300 else ""}"><span>⏱ {t("time_left")}</span><b>{h:02d}:{mi:02d}:{s:02d}</b>'
                f'<span>{len(m["ans"])}/{len(m["qs"])}</span></div>', unsafe_allow_html=True)

def mock_setup():
    df = meta(); db_error_box()
    preset = st.radio(t("mock"), ["full", "quick", "custom"], horizontal=True, label_visibility="collapsed", key="mk_preset",
                      format_func=lambda k: {"full": t("preset_full"), "quick": t("preset_quick"), "custom": t("preset_custom")}[k])
    flt, _ = filters_ui("mf", df, with_count=False)
    n, mins = {"full": (100, 90), "quick": (25, 25)}.get(preset, (30, cfg("default_minutes")))
    if preset == "custom":
        c1, c2 = st.columns(2)
        n = c1.slider(t("count"), 5, 100, 30, key="mk_n")
        mins = c2.number_input(t("minutes"), 5, 240, int(cfg("default_minutes")), key="mk_min")
    pos, neg = cfg("pos_mark"), cfg("neg_mark")
    st.markdown(f'<div class="card">📝 <b>{n}</b> × {t("sec_hint")} · ⏱ <b>{mins}</b> min<br><span class="sub">{t("marking", p=pos, n=neg)}</span></div>', unsafe_allow_html=True)
    if st.session_state.get("mk_msg"): st.warning(st.session_state.mk_msg)
    st.button("▶ " + t("start_mock"), type="primary", use_container_width=True, on_click=mk_start, args=(flt, int(n), int(mins), pos, neg))

def mock_run(m):
    i, n = m["cur"], len(m["qs"]); q = m["qs"][i]
    with st.container(key="timerbar"):
        mk_timer()
    q_card(q, head=f'<div class="sub" style="margin-bottom:6px">Q {i+1} / {n}</div>',
           extra=f'<span class="chip g">+{m["pos"]}</span><span class="chip r">−{m["neg"]}</span>' + ('<span class="chip o">⚑</span>' if i in m["mark"] else ""))
    key = f"mk_{m['id']}_{i}"
    opts_radio(q, key, current=m["ans"].get(i), ckey="opts_mk", on_change=mk_pick, args=(i, key))
    c1, c2 = st.columns(2)
    c1.button(t("save_next"), type="primary", use_container_width=True, on_click=mk_save_next, args=(i,), key="mks")
    c2.button("⚑ " + t("mark_next"), use_container_width=True, on_click=mk_mark_next, args=(i,), key="mkm")
    c3, c4, c5 = st.columns(3)
    c3.button("← " + t("prev"), disabled=i == 0, use_container_width=True, on_click=mk_go, args=(i - 1,), key="mkp")
    c4.button(t("clear"), use_container_width=True, on_click=mk_clear, args=(i, key), key="mkc")
    c5.button("→ " + t("next"), disabled=i >= n - 1, use_container_width=True, on_click=mk_go, args=(i + 1,), key="mkn")
    # palette
    cols_css = {0: "#8E8E93", 1: "#FF453A", 2: "#30D158", 3: "#BF5AF2", 4: "#30D158"}
    css = ""
    with st.expander("🧭 " + t("palette"), expanded=False):
        leg = [(0, "st_na"), (1, "st_nans"), (2, "st_ans"), (3, "st_mark"), (4, "st_am")]
        st.markdown("".join(f'<span class="chip" style="background:{cols_css[k]}22;color:{cols_css[k]}">{t(l)}</span>' for k, l in leg), unsafe_allow_html=True)
        per = 6
        for r0 in range(0, n, per):
            cols = st.columns(per)
            for j, col in enumerate(cols):
                k = r0 + j
                if k >= n: break
                s_ = mk_status(m, k)
                css += (f'.st-key-pal{k} button{{background:{cols_css[s_]}{"33" if s_ else "22"}!important;color:{cols_css[s_]}!important;'
                        f'border:{"2px solid var(--acc)" if k == i else "1px solid " + cols_css[s_] + "66"}!important;padding:.3rem 0!important;min-height:2.3rem}}')
                if s_ == 4: css += f'.st-key-pal{k} button{{box-shadow:inset 0 0 0 2px #BF5AF2}}'
                with col.container(key=f"pal{k}"):
                    st.button(str(k + 1), key=f"palb{k}", on_click=mk_go, args=(k,), use_container_width=True)
    if css: st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
    st.write("")
    if cfg("confirm_submit") and m["confirm"]:
        na = n - len(m["ans"])
        st.markdown(f'<div class="card"><b>{t("sure")}</b><br><span class="sub">{t("st_ans")}: {len(m["ans"])} · {t("st_nans")}: {na} · {t("st_mark")}: {len(m["mark"])}</span></div>', unsafe_allow_html=True)
        a, b = st.columns(2)
        a.button(t("yes_submit"), type="primary", use_container_width=True, on_click=mk_finish, key="mky")
        b.button(t("go_back"), use_container_width=True, on_click=mk_confirm, args=(False,), key="mkb")
        return
    if cfg("confirm_submit"):
        st.button("✅ " + t("submit"), use_container_width=True, on_click=mk_confirm, args=(True,), key="mksub")
    else:
        st.button("✅ " + t("submit"), use_container_width=True, on_click=mk_finish, key="mksub")

def mock_result(m):
    res = m["result"]
    if m.get("auto"): st.warning(t("time_up"))
    pct = int(100 * res["score"] / res["max"]) if res["max"] > 0 else 0
    st.markdown(f'<div class="hero"><div><h2>{res["score"]} / {res["max"]}</h2><p>{t("result")} · {t("accuracy")} {int(100*res["correct"]/max(1,res["correct"]+res["wrong"]))}%</p></div>'
                f'<div class="ring" style="--p:{max(0,pct)}"><div>{max(0,pct)}%</div></div></div>', unsafe_allow_html=True)
    stat_grid([(res["correct"], t("n_correct")), (res["wrong"], t("n_wrong")), (res["skipped"], t("n_skip")), (f'−{res["neg_total"]}', t("neg_total")),
               (fmt_dur(res["time"]), t("time_used")), (fmt_dur(res["time"] / max(1, len(m["qs"]))), t("avg_time"))])
    if res["ungraded"]: st.caption(f'{res["ungraded"]} × {t("n_ungraded")}')
    if m.get("saved"): st.success(t("saved_cloud"))
    d = pd.DataFrame(res["rows"])
    g = d[d["st"].isin(["correct", "wrong", "skipped"])].groupby("s").agg(total=("st", "count"), correct=("st", lambda x: (x == "correct").sum()),
        wrong=("st", lambda x: (x == "wrong").sum()), skipped=("st", lambda x: (x == "skipped").sum()), sec=("sec", "sum"))
    g["accuracy"] = (g["correct"] * 100 / (g["correct"] + g["wrong"]).replace(0, pd.NA)).fillna(0).round(0)
    g["score"] = (g["correct"] * m["pos"] - g["wrong"] * m["neg"]).round(2); g["time"] = g["sec"].apply(fmt_dur)
    st.markdown(f"##### {t('by_subject')}")
    st.dataframe(g[["total", "correct", "wrong", "skipped", "accuracy", "score", "time"]], use_container_width=True)
    st.bar_chart(g["accuracy"])
    slow = d.sort_values("sec", ascending=False).head(3)
    st.markdown(f"##### {t('slow_q')}")
    for idx, r in slow.iterrows():
        st.markdown(f'<span class="chip o">Q{idx+1}</span><span class="chip n">{e(r["t"])}</span><span class="chip">{fmt_dur(r["sec"])}</span>', unsafe_allow_html=True)
    st.markdown(f"##### {t('review')}")
    flt = st.radio("f", ["all", "wrong", "skipped"], horizontal=True, label_visibility="collapsed", key="rv_f",
                   format_func=lambda k: {"all": t("all"), "wrong": t("n_wrong"), "skipped": t("n_skip")}[k])
    for idx, (q, r) in enumerate(zip(m["qs"], res["rows"])):
        if flt != "all" and r["st"] != flt: continue
        ico = {"correct": "✅", "wrong": "❌", "skipped": "⚪", "ungraded": "➖"}[r["st"]]
        with st.expander(f"{ico} Q{idx+1} · {q['topic']}"):
            st.write(md_safe(q["text"]))
            for k, o in enumerate(q["options"]):
                mark = " ✅" if LETTERS[k] == q["correct"] else " ❌" if LETTERS[k] == r["a"] else ""
                st.markdown(f"**{LETTERS[k]}.** {md_safe(o)}{mark}")
            st.caption(f'{t("your_ans")}: {r["a"] or "—"} · {t("right_ans")}: {q["correct"] or "—"} · {fmt_dur(r["sec"])}')
            if q["expl"]: st.info(q["expl"])
            if st.button(t("ai_explain"), key=f"rx{idx}"): st.write(ai_explain(q))
    c1, c2 = st.columns(2)
    c1.button("🔁 " + t("retry_wrong"), use_container_width=True, on_click=mk_retry_wrong, disabled=res["wrong"] == 0, key="rtw")
    c2.button(t("new_test"), type="primary", use_container_width=True, on_click=mk_new, key="mnew")
    st.download_button("⬇ " + t("download_res"), d.to_csv(index=False).encode("utf-8-sig"), "result.csv", "text/csv", use_container_width=True)

def page_mock():
    m = st.session_state.mock
    page_head(t("mock"), "TCS iON style CBT")
    if m is None: mock_setup()
    elif m["done"]: mock_result(m)
    else:
        if time.time() >= m["end_ts"]:
            mk_finish(auto=True); st.rerun()
        mock_run(m)

# ═══════════════════════ 11. CREATE: any chapter → MCQs ═══════════════════════
def retrieve(text, kws, k=3):
    out, seen = [], set()
    def add(rows):
        for r in rows or []:
            if r.get("id") not in seen:
                seen.add(r.get("id")); out.append(norm_q(r))
    try:
        v = embed_texts([text])[0]
        add(sb().rpc("match_questions", {"query_embedding": v, "match_count": k, "filter_subject": None}).execute().data)
    except Exception:
        pass
    if len(out) < k:
        try: add(sb().table("rrb_questions").select(COLS).ilike("question_text", f"%{text[:30]}%").limit(k).execute().data)
        except Exception: pass
    return out[:k]

def transcribe(audio):
    p = "Transcribe this speech exactly (Hindi/English/Hinglish). Return only the text."
    return ai_text([types.Part.from_bytes(data=audio.getvalue(), mime_type="audio/wav"), p])

def gen_questions(chapter, n, diff):
    ex = retrieve(chapter, [chapter])
    ctx = "\n".join(f"- {q['text']}" for q in ex) or "(none)"
    out, seen, tries, name = [], set(), 0, chapter
    lvl = "a mix of easy, medium and hard" if diff == "mixed" else diff
    while len(out) < n and tries < 4:
        tries += 1; k = min(15, n - len(out))
        p = (f"You are an expert RRB JE / SSC JE paper setter. The student typed this chapter/topic (may have typos, Hindi or Hinglish): \"{chapter}\".\n"
             f"Create {k} NEW exam-standard MCQs on it, level: {lvl}. {lang_rule().replace('Reply', 'Write the questions')}\n"
             f"Style examples from our PYQ bank:\n{ctx}\n"
             'Return ONLY JSON: {"chapter": "corrected chapter name in English", "questions": [{"question": "...", "options": ["...", "...", "...", "..."], '
             '"answer": "A|B|C|D", "explanation": "max 50 words", "difficulty": "easy|medium|hard"}]}. Exactly 4 options, one correct, '
             "no 'all of the above' unless needed, and do not repeat earlier questions: " + " || ".join(q["text"][:60] for q in out[-10:]))
        js = parse_json(ai_text(p, json_mode=True))
        if isinstance(js, dict):
            name = str(js.get("chapter") or name)[:80]; items = js.get("questions") or []
        else:
            items = js if isinstance(js, list) else []
        for o in items:
            try:
                txt, opts, ans = str(o["question"]).strip(), [str(x).strip() for x in o["options"]][:4], normc(o["answer"])
            except Exception:
                continue
            h = qhash(txt, opts)
            if len(opts) == 4 and ans and txt and h not in seen:
                seen.add(h)
                out.append(dict(id=None, q_no=None, text=txt, options=opts, correct=ans, expl=str(o.get("explanation", "")).strip(),
                                subject=classify(name + " " + txt)[0], topic=name, difficulty=str(o.get("difficulty", "medium")).lower(),
                                year=None, shift="AI: " + name, exam="AI Generated"))
    return name, out[:n]

def gen_save(qs):
    recs = [dict(q_hash=qhash(q["text"], q["options"]), question_text=q["text"], options=q["options"], correct_option=q["correct"],
                 explanation=q["expl"] or None, subject=q["subject"], topic=q["topic"], difficulty=q["difficulty"], exam="AI Generated",
                 year=now_ist().year, shift_name=q["shift"]) for q in qs]
    try:
        for r, v in zip(recs, embed_texts([r["question_text"] + " " + " ".join(r["options"]) for r in recs])): r["embedding"] = v
    except Exception:
        pass
    try:
        sb().table("rrb_questions").upsert(recs, on_conflict="q_hash", ignore_duplicates=True).execute()
        st.cache_data.clear(); return len(recs)
    except Exception as ex:
        st.session_state.db_err = f"{type(ex).__name__}: {ex}"; return 0

def gen_pick(i, key):
    st.session_state.gen["ans"][i] = st.session_state[key]

def page_create():
    ss = st.session_state
    page_head(t("gen_title"), t("gen_sub"))
    c1, c2 = st.columns(2)
    with c1:
        cfg_widget("selectbox", "ai_lang", t("ai_lang"), options=["auto", "hi", "en", "hn"],
                   format_func=lambda k: {"auto": t("auto"), "hi": "हिंदी", "en": "English", "hn": "Hinglish"}[k])
    with c2:
        st.write(""); st.toggle(t("gen_save"), False, key="gen_save_on")
    voice = None
    if hasattr(st, "audio_input"):
        aud = st.audio_input("🎙️", key="gen_aud", label_visibility="collapsed")
        if aud:
            sig = getattr(aud, "file_id", None) or len(aud.getvalue())
            if ss.get("last_aud") != sig:
                ss.last_aud = sig; voice = transcribe(aud)
    with st.form("gen"):
        ch = st.text_input("c", placeholder=t("chapter_ph"), label_visibility="collapsed")
        a, b = st.columns(2)
        n = a.slider(t("count"), 5, 30, 10)
        diff = b.selectbox(t("gen_diff"), ["mixed", "easy", "medium", "hard"], format_func=lambda k: t("d_" + k))
        sent = st.form_submit_button("✨ " + t("gen_go"), type="primary", use_container_width=True)
    req = ss.pop("gen_req", None) or voice or (ch.strip() if sent and ch.strip() else None)
    if req:
        with st.spinner(t("thinking")):
            name, qs = gen_questions(req, n, diff)
        if not qs:
            ss.gen = None; st.error(t("gen_fail") + ("\n\n`" + ss.ai_err[:200] + "`" if ss.ai_err else ""))
        else:
            ss.gen = dict(ch=name, qs=qs, ans={}, gid=int(time.time()))
            if ss.get("gen_save_on"): st.toast(t("gen_saved", n=gen_save(qs)))
    g = ss.get("gen")
    if not g: return
    qs, ok = g["qs"], sum(1 for i, q in enumerate(g["qs"]) if g["ans"].get(i) == q["correct"])
    st.markdown(f'<span class="chip">{e(g["ch"])}</span><span class="chip g">{ok}/{len(g["ans"])}</span><span class="chip n">{len(qs)} Q</span>', unsafe_allow_html=True)
    st.caption(t("gen_note"))
    for i, q in enumerate(qs):
        q_card(q, head=f'<div class="sub" style="margin-bottom:6px">Q {i+1}</div>')
        key = f"g{g['gid']}_{i}"
        a = opts_radio(q, key, current=g["ans"].get(i), ckey=f"opts_g{i}", on_change=gen_pick, args=(i, key))
        if a:
            good = a == q["correct"]
            st.markdown(f'<div class="banner {"ok" if good else "bad"}">{t("correct") if good else t("wrong") + " · " + t("right_ans") + ": " + q["correct"]}</div>', unsafe_allow_html=True)
            if q["expl"]: st.info(q["expl"])
    if HAVE_FPDF:
        st.download_button(t("dl_pdf"), build_pdf(q["subject"], g["ch"], qs), f"{g['ch']}.pdf", "application/pdf", use_container_width=True)

# ═══════════════════════ 12. LIBRARY / PDF STUDIO ═══════════════════════
def page_library():
    ss = st.session_state
    page_head(t("lib_title"), t("lib_sub"))
    if not HAVE_FPDF: st.error(t("no_fpdf"))
    elif ensure_fonts() is None: st.warning(t("font_warn"))
    df = meta(); db_error_box()
    src = st.radio(t("src_mode"), ["filter", "book", "wrong"], horizontal=True, key="lib_src",
                   format_func=lambda k: {"filter": t("m_random"), "book": f"{t('m_book')} ({len(ss.bookmarks)})", "wrong": f"{t('m_wrong')} ({len(ss.wrong)})"}[k])
    flt, n = filters_ui("lf", df, default_n=25, maxn=100)
    c1, c2 = st.columns(2)
    sub_default = (flt["subjects"] or ["Civil Engineering"])[0]
    p_sub = c1.text_input(t("pdf_subject"), value=sub_default, key=f"lib_sub_{sub_default}")
    p_chap = c2.text_input(t("pdf_chapter"), value=(flt["topics"] or ["Introduction"])[0], key=f"lib_ch_{(flt['topics'] or ['x'])[0]}")
    t1, t2, t3 = st.columns(3)
    s_opts = t1.toggle(t("inc_opts"), True, key="lib_o"); s_key = t2.toggle(t("inc_key"), True, key="lib_k"); s_exp = t3.toggle(t("inc_expl"), False, key="lib_e")
    fs = st.slider(t("font_sz"), 8, 13, 10, key="lib_fs"); rnd = st.toggle(t("m_random"), False, key="lib_r")
    if st.button("⚡ " + t("gen_pdf"), type="primary", use_container_width=True, disabled=not HAVE_FPDF):
        if src == "book": rows = get_questions(ids=list(ss.bookmarks)) if ss.bookmarks else []
        elif src == "wrong": rows = get_questions(ids=list(ss.wrong)) if ss.wrong else []
        else: rows = get_questions(**flt)
        if rnd: random.shuffle(rows)
        rows = rows[:n]
        if not rows: st.warning(t("no_match"))
        else:
            with st.spinner("PDF…"):
                ss.lib_pdf = (build_pdf(p_sub, p_chap, rows, s_opts, s_key, s_exp, fs), f"{p_sub} - {p_chap}.pdf", len(rows))
                ss.lib_rows = rows
    if ss.get("lib_pdf"):
        data, name, cnt = ss.lib_pdf
        st.success(t("pdf_ready", n=cnt))
        st.download_button(t("dl_pdf"), data, name, "application/pdf", use_container_width=True)
        st.markdown(f"##### {t('export')}")
        d = pd.DataFrame([{k: (", ".join(v) if k == "options" else v) for k, v in q.items()} for q in ss.lib_rows])
        a, b = st.columns(2)
        a.download_button("CSV", d.to_csv(index=False).encode("utf-8-sig"), "questions.csv", "text/csv", use_container_width=True)
        b.download_button("JSON", json.dumps(ss.lib_rows, ensure_ascii=False, default=str).encode("utf-8"), "questions.json", "application/json", use_container_width=True)

# ═══════════════════════ 13. MORE: PROFILE · SETTINGS · PROGRESS · ADMIN ═══════════════════════
def make_profile(name, code):
    ss = st.session_state
    code = re.sub(r"[^a-z0-9_-]", "", (code or "").lower()) or (re.sub(r"[^a-z0-9]", "", name.lower())[:10] or "user") + str(random.randint(1000, 9999))
    ss.profile = dict(code=code, name=name.strip() or t("student"))
    if save_profile():
        try: st.query_params["u"] = code
        except Exception: pass
        st.toast(t("saved"))

def tab_profile():
    ss = st.session_state
    st.caption(t("profile_help"))
    if ss.profile:
        st.markdown(f'<div class="card"><b>{e(ss.profile["name"])}</b><br><span class="sub">{t("profile_code")}: <code>{e(ss.profile["code"])}</code></span></div>', unsafe_allow_html=True)
        a, b = st.columns(2)
        if a.button(t("save"), type="primary", use_container_width=True, key="pf_save"):
            st.success(t("saved")) if save_profile() else db_error_box()
        if b.button("Logout", use_container_width=True, key="pf_out"):
            ss.profile = None
            try: st.query_params.clear()
            except Exception: pass
            st.rerun()
    else:
        name = st.text_input(t("your_name"), key="pf_name")
        code = st.text_input(t("profile_code"), key="pf_code")
        a, b = st.columns(2)
        if a.button(t("save"), type="primary", use_container_width=True, key="pf_new"):
            make_profile(name, code); st.rerun()
        if b.button(t("load"), use_container_width=True, key="pf_load"):
            if load_profile(re.sub(r"[^a-z0-9_-]", "", code.lower())): st.rerun()
            else: st.error(t("not_found"))
        db_error_box()

def tab_settings():
    st.markdown(f"##### {t('look')}")
    cfg_widget("radio", "accent", t("accent"), options=list(ACCENTS), horizontal=True,
               format_func=lambda k: {"blue": "🔵", "indigo": "🟣", "purple": "🪻", "pink": "🌸", "orange": "🟠", "green": "🟢", "teal": "🩵"}[k])
    cfg_widget("slider", "font_scale", t("fsize"), min_value=85, max_value=130, step=5)
    cfg_widget("radio", "radius", t("corners"), options=["round", "sharp"], horizontal=True, format_func=lambda k: t("r_" + k))
    c1, c2 = st.columns(2)
    with c1: cfg_widget("toggle", "glass", t("glass"))
    with c2: cfg_widget("toggle", "amoled", t("amoled"))
    st.caption(t("theme_hint"))
    st.markdown(f"##### {t('exam_set')}")
    c1, c2 = st.columns(2)
    with c1: cfg_widget("number_input", "pos_mark", t("pos_mark"), min_value=0.25, max_value=10.0, step=0.25)
    with c2: cfg_widget("number_input", "neg_mark", t("neg_mark"), min_value=0.0, max_value=5.0, step=0.01, format="%.2f")
    c1, c2 = st.columns(2)
    with c1: cfg_widget("number_input", "default_minutes", t("def_min"), min_value=5, max_value=240, step=5)
    with c2: cfg_widget("number_input", "daily_goal", t("goal"), min_value=5, max_value=500, step=5)
    cfg_widget("toggle", "shuffle_q", t("shuf_q")); cfg_widget("toggle", "shuffle_opts", t("shuf_o"))
    cfg_widget("toggle", "instant", t("instant")); cfg_widget("toggle", "confirm_submit", t("conf_sub"))
    cfg_widget("toggle", "ai_explain_auto", t("auto_ai"))
    a, b = st.columns(2)
    if a.button(t("save"), type="primary", use_container_width=True, key="set_save"):
        if save_profile(): st.toast(t("saved"))
        else: st.toast(t("need_profile"))
    if b.button(t("reset"), use_container_width=True, key="set_reset"):
        st.session_state.cfg = dict(DEFAULTS)
        for k in [k for k in st.session_state if k.startswith("w_")]: del st.session_state[k]
        st.rerun()

def tab_progress():
    ss = st.session_state
    days = sorted(ss.days.items())[-14:]
    if days:
        st.markdown(f"##### {t('daily_goal')}")
        st.bar_chart(pd.DataFrame(days, columns=["date", "q"]).set_index("date"))
    if not ss.profile:
        st.info(t("need_profile")); return
    h = fetch_attempts(ss.profile["code"])
    if not h:
        st.info(t("no_hist")); return
    d = pd.DataFrame([dict(date=x["created_at"][:16].replace("T", " "), score=x["score"], max=x["max_score"], correct=x["correct"], wrong=x["wrong"],
                           skipped=x["skipped"], mins=round((x["total_time_sec"] or 0) / 60, 1)) for x in h])
    d["pct"] = (d["score"] * 100 / d["max"].replace(0, pd.NA)).fillna(0).round(1)
    st.markdown(f"##### {t('score_trend')}")
    st.line_chart(d.iloc[::-1].set_index("date")["pct"])
    st.markdown(f"##### {t('history')}")
    st.dataframe(d, use_container_width=True)
    st.download_button("CSV", d.to_csv(index=False).encode("utf-8-sig"), "history.csv", "text/csv")

def _s(v):
    return "" if v is None or (isinstance(v, float) and pd.isna(v)) else str(v).strip()

def ingest_save(df, exam, year, embed):
    recs = []
    for r in df.to_dict("records"):
        txt = _s(r.get("question_text"))
        if not r.get("use") or not txt: continue
        opts = [o for o in (_s(r.get(L)) for L in LETTERS) if o]
        try: qn = int(r.get("q_no"))
        except Exception: qn = None
        recs.append(dict(q_hash=qhash(txt, opts), q_no=qn, question_text=txt, options=opts, correct_option=normc(r.get("correct_option")),
                         explanation=_s(r.get("explanation")) or None, subject=_s(r.get("subject")) or "General", topic=_s(r.get("topic")) or "General",
                         difficulty=_s(r.get("difficulty")) or "medium", exam=exam, year=int(year), shift_name=_s(r.get("shift_name"))))
    bar = st.progress(0.0); done = 0
    for i in range(0, len(recs), 15):
        batch = recs[i:i + 15]
        if embed:
            try:
                for b, v in zip(batch, embed_texts([b["question_text"] + " " + " ".join(b["options"]) for b in batch])): b["embedding"] = v
            except Exception as ex:
                st.session_state.ai_err = str(ex)
        for attempt in range(3):
            try:
                sb().table("rrb_questions").upsert(batch, on_conflict="q_hash", ignore_duplicates=True).execute(); break
            except Exception as ex:
                if attempt == 2: st.error(f"{type(ex).__name__}: {ex}"); return done
                time.sleep(1.5 * (attempt + 1))
        done += len(batch); bar.progress(min(1.0, done / max(1, len(recs)))); time.sleep(0.35)
    st.cache_data.clear()
    return done

def admin_ingest():
    ss = st.session_state
    files = st.file_uploader(t("up_q"), type=["pdf"], accept_multiple_files=True, key="ing_files")
    keyf = st.file_uploader(t("up_key"), type=["pdf", "txt"], key="ing_key")
    st.caption("ℹ️ Answer key सभी चुनी हुई फ़ाइलों पर लगेगी — key के साथ एक बार में एक ही पेपर डालें / The key applies to every file selected.")
    c1, c2 = st.columns(2)
    exam = c1.text_input(t("exam"), "RRB JE", key="ing_exam")
    year = c2.number_input(t("year"), 2005, 2035, now_ist().year, key="ing_year")
    auto = st.checkbox(t("auto_cls"), True, key="ing_auto"); emb = st.checkbox(t("embed_now"), True, key="ing_emb")
    if files and st.button(t("parse"), use_container_width=True, key="ing_parse"):
        keys = parse_answer_key(read_key_file(keyf)) if keyf else {}
        rows = []
        with st.spinner("PDF…"):
            for f in files:
                for q in parse_questions(extract_pages(f)):
                    ans = q["correct"] or keys.get(q["q_no"])
                    sub, top = classify(q["text"]) if auto else ("General", "General")
                    o = q["options"] + [""] * (4 - len(q["options"]))
                    rows.append(dict(use=True, q_no=q["q_no"], shift_name=f.name.rsplit(".", 1)[0], subject=sub, topic=top, difficulty="medium",
                                     question_text=q["text"], A=o[0], B=o[1], C=o[2], D=o[3], correct_option=ans, explanation=q["expl"]))
        ss.ing_df = pd.DataFrame(rows)
    df = ss.get("ing_df")
    if df is not None and len(df):
        st.success(t("parsed_n", n=len(df)))
        stat_grid([(int(df["correct_option"].notna().sum()), t("ans_letter")), (int((df["A"] != "").sum()), t("opt")), (len(df), t("q_text"))])
        ed = st.data_editor(df, num_rows="dynamic", use_container_width=True, key="ing_ed", column_config={
            "use": st.column_config.CheckboxColumn("✓", width="small"),
            "correct_option": st.column_config.SelectboxColumn(t("ans_letter"), options=list(LETTERS), width="small"),
            "difficulty": st.column_config.SelectboxColumn(t("difficulty"), options=["easy", "medium", "hard"]),
            "question_text": st.column_config.TextColumn(t("q_text"), width="large")})
        if st.button("💾 " + t("save_db"), type="primary", use_container_width=True, key="ing_save"):
            n = ingest_save(ed, exam, year, emb)
            st.balloons(); st.success(t("inserted", n=n)); ss.ing_df = None
    elif df is not None:
        st.warning("0 questions detected — PDF scanned/image हो सकती है, या फ़ॉर्मेट अलग है। एक sample PDF भेजें ताकि parser tune हो सके।")

def admin_manage():
    df = meta(); db_error_box()
    st.metric(t("total_q"), len(df))
    if len(df):
        st.dataframe(df.groupby(["subject", "shift_name"]).size().rename("n").reset_index(), use_container_width=True)
        st.markdown(f"##### 🛑 {t('danger')}")
        sh = st.selectbox(t("del_by"), uniq(df, "shift_name"), key="del_sh")
        conf = st.text_input(t("type_del"), key="del_conf")
        if st.button("🗑 " + t("del_by"), disabled=conf != "DELETE", key="del_go"):
            sb().table("rrb_questions").delete().eq("shift_name", sh).execute(); st.cache_data.clear(); st.success(t("deleted")); st.rerun()
    rows = get_questions(limit=5000)
    if rows:
        d = pd.DataFrame([{**q, "options": " | ".join(q["options"])} for q in rows])
        st.download_button("⬇ CSV", d.to_csv(index=False).encode("utf-8-sig"), "all_questions.csv", "text/csv")

def admin_ai():
    try:
        pend = sb().table("rrb_questions").select("id", count="exact").is_("embedding", "null").execute().count or 0
    except Exception as ex:
        st.error(str(ex)); return
    st.info(t("pending_emb", n=pend))
    if st.button(t("run_emb"), disabled=pend == 0, use_container_width=True, key="emb_go"):
        rows = sb().table("rrb_questions").select("id,question_text,options").is_("embedding", "null").limit(40).execute().data or []
        bar = st.progress(0.0)
        for i in range(0, len(rows), 15):
            ch = rows[i:i + 15]
            try:
                vecs = embed_texts([r["question_text"] + " " + " ".join(parse_opts(r["options"])) for r in ch])
                for r, v in zip(ch, vecs): sb().table("rrb_questions").update({"embedding": v}).eq("id", r["id"]).execute()
            except Exception as ex:
                st.error(str(ex)); break
            bar.progress(min(1.0, (i + 15) / len(rows))); time.sleep(0.4)
        st.rerun()
    if st.button(t("run_cls"), use_container_width=True, key="cls_go"):
        rows = sb().table("rrb_questions").select(COLS).is_("explanation", "null").limit(15).execute().data or []
        items = [norm_q(r) for r in rows]
        p = ("For each RRB/SSC JE exam question return a JSON array of objects {id, subject, topic, difficulty(easy|medium|hard), explanation(max 60 words, "
             f"{lang_rule()}" + ")}. Use these subject names where they fit: Civil Engineering, Electrical Engineering, Mechanical Engineering, Mathematics, "
             "Reasoning, General Science, General Awareness, Computer. Do NOT invent an answer; base the explanation on the stored correct option if present.\n" +
             json.dumps([dict(id=q["id"], q=q["text"], opts=q["options"], correct=q["correct"]) for q in items], ensure_ascii=False))
        js = parse_json(ai_text(p, json_mode=True)); n = 0
        for o in js if isinstance(js, list) else []:
            try:
                sb().table("rrb_questions").update(dict(subject=o["subject"], topic=o["topic"], difficulty=o.get("difficulty", "medium"),
                                                    explanation=o.get("explanation"))).eq("id", o["id"]).execute(); n += 1
            except Exception: pass
        st.cache_data.clear(); st.success(f"{n} ✓")

def admin_add():
    with st.form("addq", clear_on_submit=True):
        tx = st.text_area(t("q_text"))
        cs = st.columns(2); o = [cs[i % 2].text_input(f"{t('opt')} {LETTERS[i]}") for i in range(4)]
        c1, c2, c3 = st.columns(3)
        ans = c1.selectbox(t("ans_letter"), list(LETTERS)); sub = c2.text_input(t("subject"), "Civil Engineering"); top = c3.text_input(t("topic"), "General")
        ex = st.text_area(t("explain"))
        if st.form_submit_button(t("save"), type="primary") and tx.strip():
            opts = [x for x in o if x.strip()]
            sb().table("rrb_questions").upsert(dict(q_hash=qhash(tx, opts), question_text=tx.strip(), options=opts, correct_option=ans, subject=sub, topic=top,
                                                 explanation=ex or None, exam="RRB JE", shift_name="manual"), on_conflict="q_hash", ignore_duplicates=True).execute()
            st.cache_data.clear(); st.success(t("saved"))

def admin_diag():
    import streamlit
    st.write(f"Streamlit **{streamlit.__version__}** · theme API: **{theme_type()}**")
    st.write({"SUPABASE_URL": bool(SB_URL), "SUPABASE_KEY": bool(SB_KEY), "GEMINI_API_KEY": bool(G_KEY), "ADMIN_PIN": bool(secret("ADMIN_PIN"))})
    st.write("Models:", _models(), "· working:", st.session_state.get("good_model"))
    a, b = st.columns(2)
    if a.button(t("test_db"), use_container_width=True, key="d_db"):
        try: st.success(f"OK · rows: {sb().table('rrb_questions').select('id', count='exact').limit(1).execute().count}")
        except Exception as ex: st.error(f"{type(ex).__name__}: {ex}")
    if b.button(t("test_ai"), use_container_width=True, key="d_ai"):
        r = ai_text("Reply with the single word OK.")
        st.success(f"OK · {r}") if r else st.error(st.session_state.ai_err)
    st.write("PDF fonts:", ensure_fonts() or "❌ not available", "· fpdf2:", HAVE_FPDF)
    if st.session_state.ai_err: st.code(st.session_state.ai_err[:600])

def tab_admin():
    ss = st.session_state; pin = secret("ADMIN_PIN")
    if pin and not ss.admin_ok:
        p = st.text_input(t("admin_pin"), type="password", key="adm_pin")
        if st.button(t("unlock"), key="adm_go"):
            if str(p) == str(pin): ss.admin_ok = True; st.rerun()
            else: st.error(t("bad_pin"))
        return
    if not pin: st.warning(t("no_pin_set"))
    tabs = st.tabs([t("ingest"), t("manage"), t("ai_tools"), t("add_one"), t("diag")])
    with tabs[0]: admin_ingest()
    with tabs[1]: admin_manage()
    with tabs[2]: admin_ai()
    with tabs[3]: admin_add()
    with tabs[4]: admin_diag()

def page_more():
    page_head(t("more"), "PYQ Master")
    tabs = st.tabs([t("profile"), t("settings"), t("progress"), t("admin")])
    with tabs[0]: tab_profile()
    with tabs[1]: tab_settings()
    with tabs[2]: tab_progress()
    with tabs[3]: tab_admin()

# ═══════════════════════ 14. APP SHELL ═══════════════════════
PAGE_FN = dict(home=page_home, practice=page_practice, mock=page_mock, create=page_create, library=page_library, more=page_more)

def set_ui_lang():
    st.session_state.cfg["ui_lang"] = st.session_state["w_ui_lang_q"]

def main():
    ss = st.session_state
    if not (SB_URL and SB_KEY and G_KEY):
        st.error(S["secrets_missing"][1] + "\n\n" + S["secrets_missing"][0]); st.stop()
    if not ss.profile and not ss.get("_qp_done"):
        ss["_qp_done"] = True
        try:
            u = st.query_params.get("u")
            if u: load_profile(u)
        except Exception: pass
    inject_css()
    ss["w_ui_lang_q"] = cfg("ui_lang")
    with st.container(key="langbar"):
        st.radio("lang", ["hi", "en", "hn"], horizontal=True, key="w_ui_lang_q", on_change=set_ui_lang, label_visibility="collapsed",
                 format_func=lambda k: {"hi": "हिं", "en": "EN", "hn": "Hn"}[k])
    if ss.nav not in PAGES: ss.nav = "home"
    with st.container(key="bottomnav"):
        st.radio("nav", PAGES, horizontal=True, key="nav", format_func=lambda k: t(k), label_visibility="collapsed")
    PAGE_FN[ss.nav]()

main()

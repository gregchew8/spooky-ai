import streamlit as st
import google.generativeai as genai
from openai import OpenAI
import requests
import os
import pypdf
import random
import json
from PIL import Image

# ==========================================================
# --- PAGE CONFIGURATION ---
# ==========================================================
st.set_page_config(
    page_title="Spooky AI - Homegrown App",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================================
# --- FIXED CSS: Layout & Styling ---
# ==========================================================
hide_st_style = """
<style>
/* 1. Reset & Basic UI Cleanup */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header { background: none !important; border: none !important; }
[data-testid="stHeader"] { background: none !important; }
[data-testid="stDecoration"] { display: none; }
[data-testid="stMainBlockContainer"] { padding-top: 1.5rem !important; }

/* 2. Sidebar Styling */
[data-testid="stSidebar"] {
    background-color: #614869 !important;
}
[data-testid="stSidebar"] .block-container {
    padding-top: 2rem !important;
    gap: 0.5rem !important;
}

.sidebar-footer {
    position: fixed; bottom: 10px; left: 10px; width: 310px;
    color: #A5B5D1; font-size: 15px; pointer-events: none;
}

/* 3. Chat Input Cleanup */
[data-testid="stChatInput"] > div {
    background-color: #262730 !important;
    border-radius: 12px !important;
    border: 1px solid transparent !important;
}
[data-testid="stChatInput"]:focus-within > div {
    border: 1px solid #614869 !important;
    box-shadow: 0 0 0 0.1rem rgba(97, 72, 105, 0.2) !important;
}

/* 4. HEADER UPLOAD BUTTON STYLING */
div.header-upload-btn button {
    background-color: #614869 !important;
    color: white !important;
    border: 1px solid #4B0082 !important;
    border-radius: 8px !important;
    height: 45px !important;
    width: 100% !important;
    font-weight: bold !important;
    margin-top: 5px !important;
}
div.header-upload-btn button:hover {
    background-color: #4B0082 !important;
    border-color: #9370DB !important;
}

/* 5. CHAT BUBBLES (Purple Theme - Compact Version) */
div[data-testid="stChatMessageAvatarBackground"] {
    border-radius: 8px !important;
}
div[data-testid="stChatMessage"]:has(div[data-testid="stChatMessageAvatarUser"]) div[data-testid="stChatMessageAvatarBackground"] {
    background-color: #4B0082 !important;
}
div[data-testid="stChatMessage"]:has(div[data-testid="stChatMessageAvatarAssistant"]) div[data-testid="stChatMessageAvatarBackground"] {
    background-color: #614869 !important;
}

div[data-testid="stChatMessage"] {
    background-color: rgba(97, 72, 105, 0.05) !important;
    border: 1px solid rgba(97, 72, 105, 0.2) !important;
    border-radius: 12px !important;
    margin-bottom: 8px !important;
    padding: 0.5rem 0.8rem !important;
}

div[data-testid="stChatMessage"] [data-testid="stVerticalBlock"] {
    gap: 0rem !important;
}

/* 6. TOAST NOTIFICATIONS */
div[data-testid="stToastContainer"] {
    visibility: visible !important;
    width: auto !important;
    height: auto !important;
    position: fixed !important;
    top: unset !important;
    bottom: 30px !important;
    right: 30px !important;
    left: unset !important;
    z-index: 9999999 !important;
}

/* 7. CUSTOMIZE CHECKBOX & TOGGLE */
[data-testid="stCheckbox"] label p, [data-testid="stWidgetLabel"] p {
    font-size: 14px !important;
    color: rgb(250, 250, 250) !important;
    font-weight: 400 !important;
}

/* 8. MAIN TITLE STYLING */
h1 {
    font-size: 2.5rem !important;
    padding-top: 0rem !important;
}

/* 9. PINNED HEADER LOGIC */
[data-testid="stVerticalBlock"] > div:has(div.fixed-header-container) {
    position: sticky !important;
    top: 0;
    background-color: #0e1117;
    z-index: 1000;
    padding-bottom: 10px;
    border-bottom: 1px solid rgba(250, 250, 250, 0.1);
}

/* 10. HIDE STREAMLIT BRANDING */
[data-testid="stStatusWidget"] {
    visibility: hidden;
    display: none !important;
}
#stAppViewContainer > section:nth-child(2) > div:nth-child(1) {
    display: none !important;
}
footer {
    display: none !important;
}
</style>
"""
st.markdown(hide_st_style, unsafe_allow_html=True)

# ==========================================================
# --- PROMPT SECURITY GLOBALS ---
# ==========================================================
PS_APP_ID = os.getenv("PS_APP_ID")
PS_GATEWAY_URL = os.getenv("PS_GATEWAY_URL")

if not PS_APP_ID or not PS_GATEWAY_URL:
    st.error("🚨 Critical Error: PS_APP_ID or PS_GATEWAY_URL is missing. Please check your .env file.")
    st.stop()

PS_PROTECT_API = f"{PS_GATEWAY_URL.strip('/')}/api/protect"

# ==========================================================
# --- INITIALIZE SESSION STATES ---
# ==========================================================
if "multi_messages" not in st.session_state:
    st.session_state.multi_messages = {"AI Gateway (OpenAI)": [], "API (Gemini)": []}
if "session_costs" not in st.session_state:
    st.session_state.session_costs = {"AI Gateway (OpenAI)": 0.0, "API (Gemini)": 0.0}
if "security_stats" not in st.session_state:
    st.session_state.security_stats = {"blocks": 0, "redactions": 0}
if "last_latency" not in st.session_state: st.session_state.last_latency = 0
if "last_violation" not in st.session_state: st.session_state.last_violation = "None"
if "current_integration" not in st.session_state: st.session_state.current_integration = "API (Gemini)"
if "show_cost" not in st.session_state: st.session_state.show_cost = False
if "input_text" not in st.session_state: st.session_state.input_text = None
if "last_debug_info" not in st.session_state: st.session_state.last_debug_info = None
if "uploader_key" not in st.session_state: st.session_state.uploader_key = 0
if "last_processed_file" not in st.session_state: st.session_state.last_processed_file = None
if "gemini_available_models" not in st.session_state: st.session_state.gemini_available_models = []
if "selected_gemini_model" not in st.session_state: st.session_state.selected_gemini_model = None

# ==========================================================
# --- HELPERS ---
# ==========================================================
def reset_chat():
    mode = st.session_state.current_integration
    st.session_state.multi_messages[mode] = []
    st.session_state.security_stats = {"blocks": 0, "redactions": 0}
    st.session_state.last_latency = 0
    st.session_state.last_violation = "None"
    st.session_state.session_costs[mode] = 0.0
    st.session_state.last_debug_info = None
    st.session_state.uploader_key += 1
    st.session_state.last_processed_file = None
    st.toast("History cleared.")

def set_prompt(text):
    st.session_state.input_text = text
    st.session_state.uploader_key += 1

def render_debug_box(info):
    if not info: return
    status_type = info.get('status_type', 'safe')
    checked_p = info.get('checked_p', '')
    debug_data = info.get('debug', {})

    if status_type == "blocked":
        label, state = "🚫 Violation Detected", "error"
        content = None
    elif status_type == "redacted":
        label, state = "⚠️ Content Redacted", "complete"
        content = f"Redacted Content: {checked_p}"
    else:
        label, state = "✅ Safe", "complete"
        content = None

    with st.status(label, expanded=False, state=state):
        if content: st.warning(content)
        with st.expander("🔍 View Raw API Response", expanded=False):
            st.json(debug_data)

def get_env_bool(name, default=False):
    value = os.getenv(name, str(default)).strip().lower()
    return value in ("1", "true", "yes", "on")

def get_chat_models():
    models = []
    for model in genai.list_models():
        supported_methods = getattr(model, "supported_generation_methods", []) or []
        if "generateContent" in supported_methods:
            models.append(model.name)
    return sorted(set(models))

def get_gemini_preferred_order():
    default_model = os.getenv("DEFAULT_GEMINI_MODEL", "models/gemini-2.0-flash").strip()
    fallback_models = [
        item.strip() for item in os.getenv(
            "FALLBACK_GEMINI_MODELS",
            "models/gemini-2.0-flash,models/gemini-1.5-flash,models/gemini-1.5-pro",
        ).split(",") if item.strip()
    ]
    ordered_models = []
    for model_name in [default_model] + fallback_models:
        if model_name and model_name not in ordered_models:
            ordered_models.append(model_name)
    return ordered_models

def choose_gemini_model(available_models):
    preferred_order = get_gemini_preferred_order()
    for model_name in preferred_order:
        if model_name in available_models:
            return model_name
    return available_models[0] if available_models else "Unavailable"

def get_runtime_gemini_candidates(selected_model, available_models):
    candidates = []
    for model_name in [selected_model] + get_gemini_preferred_order() + list(available_models):
        if model_name in available_models and model_name not in candidates:
            candidates.append(model_name)
    return candidates

# ==========================================================
# --- SIDEBAR ---
# ==========================================================
with st.sidebar:
    st.header("App Settings")
    st.button("🗑️ Clear Current Chat", use_container_width=True, on_click=reset_chat)

    trigger_data = {}
    try:
        with open("triggers.txt", "r") as f:
            trigger_data = json.load(f)
    except Exception:
        trigger_data = {"System": {"Error": ["Check triggers.txt file"]}}

    with st.popover("💡 Triggers", use_container_width=True):
        col_t, col_r = st.columns([0.7, 0.3])
        col_t.markdown("### Sample Prompts")
        if col_r.button("🔄", help="Reload triggers.txt"):
            st.rerun()

        for group_name, sub_items in trigger_data.items():
            if isinstance(sub_items, dict):
                st.markdown(f"**{group_name}**")
                btn_names = list(sub_items.keys())
                for i in range(0, len(btn_names), 2):
                    cols = st.columns(2)
                    for j in range(2):
                        if i + j < len(btn_names):
                            btn_label = btn_names[i+j]
                            prompt_list = sub_items[btn_label]
                            with cols[j]:
                                if st.button(btn_label, use_container_width=True, key=f"trig_{group_name}_{btn_label}"):
                                    set_prompt(random.choice(prompt_list))

    st.markdown("### Protection Layer")
    ps_enabled = st.toggle("Enable Prompt Security", value=True, help="Toggle real-time security scanning on/off")

    st.divider()
    app_mode = st.radio("Select Prompt Security Integration:", ["API (Gemini)", "AI Gateway (OpenAI)"],
                        index=0 if st.session_state.current_integration == "API (Gemini)" else 1)

    if app_mode != st.session_state.current_integration:
        st.session_state.current_integration = app_mode
        st.session_state.last_debug_info = None
        st.rerun()

    user_email = st.text_input("User Identity", value=os.getenv("DEMO_USER_EMAIL", "john.doe@unknown.com"))
    st.divider()

    if app_mode == "AI Gateway (OpenAI)":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            st.error("🔑 OPENAI_API_KEY is missing in .env")
            selected_model = "Unavailable"
        else:
            selected_model = st.selectbox("Select OpenAI Model", ["gpt-4o-mini", "gpt-4o"], index=0)
        st.caption("Mode: AI Gateway (Reverse Proxy)")
        if st.button("💰"): st.session_state.show_cost = not st.session_state.show_cost
        sidebar_metrics_container = st.empty()
    else:
        api_key = os.getenv("GEMINI_FREE_API_KEY")
        if not api_key:
            st.error("🔑 GEMINI_FREE_API_KEY is missing in .env")
            selected_model = "Unavailable"
            debug_mode = False
        else:
            try:
                genai.configure(api_key=api_key)
                chat_models = get_chat_models()
                st.session_state.gemini_available_models = chat_models
                if not chat_models:
                    selected_model = "Unavailable"
                else:
                    auto_select = get_env_bool("AUTO_SELECT_GEMINI_MODEL", True)
                    preferred_model = choose_gemini_model(chat_models)
                    if st.session_state.selected_gemini_model not in chat_models:
                        st.session_state.selected_gemini_model = preferred_model
                    
                    if auto_select:
                        st.session_state.selected_gemini_model = preferred_model
                        selected_model = preferred_model
                        st.caption(f"Auto-selected Gemini model: `{selected_model}`")
                    else:
                        default_ix = chat_models.index(st.session_state.selected_gemini_model)
                        selected_model = st.selectbox("Select Gemini Model", chat_models, index=default_ix, key="gemini_model_selectbox")
                        st.session_state.selected_gemini_model = selected_model
            except Exception as e:
                st.error(f"⚠️ Gemini Connection Failed: {str(e)}")
                selected_model = "Connection Error"
        
        st.caption("Mode: API Integration")
        debug_mode = st.checkbox("Show Debug Info", value=False)
        st.divider()
        sidebar_metrics_container = st.empty()

def refresh_metrics():
    with sidebar_metrics_container.container():
        if app_mode == "AI Gateway (OpenAI)":
            if st.session_state.show_cost:
                cost = st.session_state.session_costs["AI Gateway (OpenAI)"]
                st.info(f"**Total Approximate Spend:** ${cost:,.6f}")
        else:
            with st.expander("Session Stats [beta]", expanded=False):
                c1, c2 = st.columns(2)
                c1.metric("Blocks", st.session_state.security_stats["blocks"])
                c2.metric("Redactions", st.session_state.security_stats["redactions"])
                st.caption(f"⚡ Latency: {st.session_state.last_latency} ms")
                st.caption(f"🚫 Violation: {st.session_state.last_violation}")

refresh_metrics()

# ==========================================================
# --- MAIN UI: HEADER ---
# ==========================================================
with st.container():
    st.markdown('<div class="fixed-header-container"></div>', unsafe_allow_html=True)
    col_title, col_upload = st.columns([0.85, 0.15])
    with col_title:
        st.title("Spooky 𔓎")
        display_id = f"{PS_APP_ID[:16]}..." if len(PS_APP_ID) > 16 else PS_APP_ID
        status_color = ":green" if ps_enabled else ":red"
        status_text = "Connected ●" if ps_enabled else "Bypassed ○"
        st.caption(f"Active Mode: **{app_mode}** | Model: **{selected_model}**\n\n"
                   f"Prompt Security: {status_color}[**{status_text}**] | App-ID: **{display_id}**")

    with col_upload:
        st.markdown('<div class="header-upload-btn">', unsafe_allow_html=True)
        with st.popover("➕ Upload"):
            st.markdown("### 📎 Scan File")
            uploaded_file = st.file_uploader("Select file", type=["txt", "pdf", "png", "jpg"],
                                           label_visibility="collapsed",
                                           key=f"file_up_{st.session_state.uploader_key}")
        st.markdown('</div>', unsafe_allow_html=True)

# SECURITY LOGIC
def check_security_api(text, context_type="prompt"):
    if not ps_enabled:
        return True, text, {"status": "Security Bypassed by User Toggle"}, "safe"
    try:
        payload = {context_type: text, "user": user_email}
        headers = {"Content-Type": "application/json", "APP-ID": PS_APP_ID}
        response = requests.post(PS_PROTECT_API, json=payload, headers=headers, timeout=10)
        data = response.json()
        result_block = data.get("result", {})
        st.session_state.last_latency = data.get("totalLatency") or result_block.get("latency", 0)
        content_block = result_block.get(context_type, {}) or {}
        violations_list = content_block.get("violations", [])
        if violations_list: st.session_state.last_violation = " + ".join(violations_list)
        elif context_type == "prompt": st.session_state.last_violation = "None"

        action = result_block.get("action", "none")
        findings = content_block.get("findings", {})
        turn_redactions = len(findings.get("Sensitive Data", [])) + len(findings.get("Secrets", [])) + len(findings.get("Regex", []))

        if response.status_code == 403 or action == "block":
            st.session_state.security_stats["blocks"] += 1
            st.toast("Security Block Triggered!", icon="🚨")
            return False, "Blocked due to policy violations", data, "blocked"

        redacted_text = content_block.get("modified_text") or text
        if turn_redactions > 0:
            st.session_state.security_stats["redactions"] += turn_redactions
            st.toast(f"{turn_redactions} item(s) redacted!", icon="⚠️")
            status_type = "redacted"
        else: status_type = "safe"

        return True, redacted_text, data, status_type
    except Exception as e: return True, text, {"error": str(e)}, "safe"

# CHAT DISPLAY
last_user_index = -1
for i, msg in enumerate(st.session_state.multi_messages[app_mode]):
    if msg["role"] == "user": last_user_index = i

debug_box_placeholder = None
for i, msg in enumerate(st.session_state.multi_messages[app_mode]):
    with st.chat_message(msg["role"]): st.write(msg["content"])
    if (i == last_user_index):
        debug_box_placeholder = st.empty()
        if (app_mode == "API (Gemini)" and debug_mode and st.session_state.last_debug_info):
            info = st.session_state.last_debug_info
            with debug_box_placeholder.container(): render_debug_box(info)

# ==========================================================
# --- CHAT INPUT & PROCESSING ---
# ==========================================================
chat_val = st.chat_input("How can I help you safely?")
prompt = st.session_state.input_text if st.session_state.input_text else chat_val
st.session_state.input_text = None

if (chat_val is not None or prompt is not None or uploaded_file) and selected_model not in ["Unavailable", "Connection Error"]:
    file_text_context = ""
    image_content = None
    if uploaded_file:
        file_type = uploaded_file.type
        uploaded_file.seek(0)
        if "text" in file_type or "csv" in file_type:
            try: decoded_text = uploaded_file.read().decode('utf-8', errors='ignore')
            except: decoded_text = "Error reading text"
            file_text_context = f"\n\n[File: {uploaded_file.name}]\n{decoded_text}"
        elif "pdf" in file_type:
            try:
                pdf_reader = pypdf.PdfReader(uploaded_file)
                pdf_text = "".join([page.extract_text() or "" for page in pdf_reader.pages])
                file_text_context = f"\n\n[PDF: {uploaded_file.name}]\n{pdf_text}"
            except: file_text_context = f"\n[Error reading PDF]"
        elif "image" in file_type:
            try: image_content = Image.open(uploaded_file)
            except: pass

    combined_prompt_text = f"{prompt if prompt else ''} {file_text_context}".strip()

    if combined_prompt_text or image_content:
        if debug_box_placeholder: debug_box_placeholder.empty()
        st.session_state.multi_messages[app_mode].append({"role": "user", "content": combined_prompt_text})
        with st.chat_message("user"):
            st.write(combined_prompt_text)
            if image_content: st.image(image_content, width=300)

        active_debug_placeholder = st.empty()

        if app_mode == "AI Gateway (OpenAI)":
            openai_base_url = f"{PS_GATEWAY_URL.strip('/')}/v1" if ps_enabled else "https://api.openai.com/v1"
            client = OpenAI(
                base_url=openai_base_url,
                api_key=api_key,
                default_headers={"ps-app-id": PS_APP_ID, "forward-domain": "api.openai.com", "user": user_email} if ps_enabled else {}
            )
            with st.chat_message("assistant"):
                try:
                    response = client.chat.completions.create(
                        model=selected_model,
                        messages=[{"role": m["role"], "content": m["content"]} for m in st.session_state.multi_messages[app_mode]]
                    )
                    
                    # --- FIXED: COST CALCULATION LOGIC ---
                    u = response.usage
                    if u:
                        rate = 0.15 if "mini" in selected_model else 2.50
                        # Summing prompt and completion spend based on standard rates
                        st.session_state.session_costs["AI Gateway (OpenAI)"] += (u.prompt_tokens * rate / 10**6) + (u.completion_tokens * rate*4 / 10**6)
                    
                    reply = response.choices[0].message.content
                    st.write(reply)
                    st.session_state.multi_messages[app_mode].append({"role": "assistant", "content": reply})
                    refresh_metrics()
                except Exception as e: st.error(str(e))
        else:
            is_safe, checked_p, debug, status_type = check_security_api(combined_prompt_text, "prompt")
            st.session_state.last_debug_info = {"checked_p": checked_p, "original_p": combined_prompt_text, "debug": debug, "status_type": status_type}
            if debug_mode:
                with active_debug_placeholder.container(): render_debug_box(st.session_state.last_debug_info)
            refresh_metrics()
            if not is_safe:
                msg = "Blocked due to policy violations"
                st.session_state.multi_messages[app_mode].append({"role": "assistant", "content": msg})
                with st.chat_message("assistant"): st.write(msg)
            else:
                with st.chat_message("assistant"):
                    with st.spinner("Thinking..."):
                        try:
                            gemini_content = [checked_p]
                            if image_content: gemini_content.append(image_content)
                            history_payload = [{"role": "user" if m["role"] == "user" else "model", "parts": [m["content"]]} for m in st.session_state.multi_messages[app_mode][:-1]]
                            available_models = st.session_state.gemini_available_models
                            candidate_models = get_runtime_gemini_candidates(selected_model, available_models)
                            res = None
                            for model_name in candidate_models:
                                try:
                                    gem_model = genai.GenerativeModel(model_name)
                                    chat = gem_model.start_chat(history=history_payload)
                                    res = chat.send_message(gemini_content)
                                    break
                                except: continue
                            is_res_safe, safe_res, res_debug, res_status_type = check_security_api(res.text, "response")
                            st.write(safe_res)
                            st.session_state.multi_messages[app_mode].append({"role": "assistant", "content": safe_res})
                            if res_status_type in ["redacted", "blocked"]:
                                st.session_state.last_debug_info = {"checked_p": safe_res, "original_p": res.text, "debug": res_debug, "status_type": res_status_type}
                                if debug_mode:
                                    with active_debug_placeholder.container(): render_debug_box(st.session_state.last_debug_info)
                            refresh_metrics()
                        except Exception as e: st.error(str(e))

st.sidebar.markdown('<div class="sidebar-footer">Made by Gastón Z and AI 🤖</div>', unsafe_allow_html=True)

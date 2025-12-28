import streamlit as st
import requests
import json
import time
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re
import io

# Page Config
st.set_page_config(
    page_title="ERPGenie",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Modern Dark Look
st.markdown("""
<style>
    /* Import Inter Font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

    /* Global Styles */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif !important;
    }

    .stApp {
        background-color: #FFFFFF;
        font-family: 'Inter', sans-serif !important;
    }
    
    /* Header/Title */
    h1 {
        color: #31333F;
        font-family: 'Inter', sans-serif;
        font-weight: 700;
    }
    
    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background-color: #714B67; /* Requested Purple */
        border-right: 1px solid #5e3b56;
    }
    
    /* Sidebar Text Overlay */
    section[data-testid="stSidebar"] p, section[data-testid="stSidebar"] span, section[data-testid="stSidebar"] div, section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] h3 {
        color: #FFFFFF !important;
    }

    /* Fixed n8n Webhook opacity/contrast */
    section[data-testid="stSidebar"] code {
        background-color: rgba(255, 255, 255, 0.2) !important;
        color: #FFFFFF !important;
        font-weight: bold;
    }
    
    /* Chat Input Styling */
    .stChatInputContainer {
        padding-bottom: 2rem;
    }
    
    .stChatInputContainer textarea {
        background-color: #31333F !important; /* Dark background */
        color: #FFFFFF !important; /* White text */
        caret-color: #FFFFFF;
        -webkit-text-fill-color: #FFFFFF !important;
        border: 1px solid #555 !important;
        border-radius: 12px !important;
        box-shadow: 0 2px 6px rgba(0,0,0,0.1);
    }

    /* Input Placeholder Color */
    .stChatInputContainer textarea::placeholder {
        color: #DDDDDD !important; /* Light placeholder */
        -webkit-text-fill-color: #DDDDDD !important;
        opacity: 0.8;
    }
    
    /* Hide Streamlit stuff */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Ensure Header is transparent but visible so buttons work */
    header[data-testid="stHeader"] {
        background: transparent;
    }

    /* User Message Bubble */
    .stChatMessage[data-testid="stChatMessage"] {
        background-color: transparent;
        border: none;
    }

    div[data-testid="stChatMessageContent"] {
        background-color: #F0F2F6;
        border-radius: 12px;
        padding: 1rem;
        color: #31333F;
        border: 1px solid #E0E0E0;
    }
    
    /* Visualization Buttons Styling */
    .viz-button {
        margin-right: 8px;
        margin-top: 8px;
    }
</style>
""", unsafe_allow_html=True)

# ===== DATA PARSING & VISUALIZATION HELPERS =====

def clean_numeric_value(value):
    """Clean numeric values by removing currency symbols, commas, etc."""
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        # Remove currency symbols and commas
        cleaned = re.sub(r'[$€£¥,]', '', value.strip())
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None

def parse_table_from_text(text):
    """
    Attempt to parse tabular data from various formats:
    - Markdown tables
    - JSON arrays
    - Pipe-separated values
    - Simple key-value pairs
    """
    # Try to parse as JSON first
    try:
        data = json.loads(text)
        if isinstance(data, list) and len(data) > 0:
            df = pd.DataFrame(data)
            return df
        elif isinstance(data, dict):
            # Single dict - convert to DataFrame
            df = pd.DataFrame([data])
            return df
    except (json.JSONDecodeError, ValueError):
        pass
    
    # Try to parse markdown table
    lines = text.strip().split('\n')
    table_lines = []
    in_table = False
    
    for line in lines:
        stripped = line.strip()
        if '|' in stripped:
            # Skip separator lines (---|---|---)
            if re.match(r'^[\s|:-]+$', stripped):
                in_table = True
                continue
            if stripped.startswith('|') or '|' in stripped:
                in_table = True
                table_lines.append(stripped)
        elif in_table and stripped == '':
            break
    
    if len(table_lines) >= 2:
        try:
            # Parse markdown table
            headers = [h.strip() for h in table_lines[0].split('|') if h.strip()]
            rows = []
            for line in table_lines[1:]:
                row = [cell.strip() for cell in line.split('|') if cell.strip()]
                if len(row) == len(headers):
                    rows.append(row)
            
            if rows:
                df = pd.DataFrame(rows, columns=headers)
                return df
        except Exception:
            pass
    
    # Try to find key-value patterns (e.g., "Product: 100", "Sales: $500")
    kv_pattern = r'^[\s-]*([A-Za-z\s]+):\s*(.+)$'
    kv_pairs = []
    for line in lines:
        match = re.match(kv_pattern, line.strip())
        if match:
            key, value = match.groups()
            kv_pairs.append({'Category': key.strip(), 'Value': value.strip()})
    
    if len(kv_pairs) >= 2:
        df = pd.DataFrame(kv_pairs)
        return df
    
    return None

def is_graphable(df):
    """Check if a DataFrame has numeric columns that can be graphed."""
    if df is None or df.empty:
        return False
    
    # Check if there's at least one numeric column
    for col in df.columns:
        numeric_count = 0
        for val in df[col]:
            if clean_numeric_value(val) is not None:
                numeric_count += 1
        if numeric_count >= len(df) * 0.5:  # At least 50% numeric
            return True
    return False

def get_numeric_columns(df):
    """Get columns that contain numeric data."""
    numeric_cols = []
    for col in df.columns:
        numeric_count = 0
        for val in df[col]:
            if clean_numeric_value(val) is not None:
                numeric_count += 1
        if numeric_count >= len(df) * 0.5:
            numeric_cols.append(col)
    return numeric_cols

def get_label_column(df, numeric_cols):
    """Get the best column to use as labels (non-numeric, first column)."""
    for col in df.columns:
        if col not in numeric_cols:
            return col
    return df.columns[0]

def create_bar_chart(df):
    """Create a bar chart from the DataFrame."""
    numeric_cols = get_numeric_columns(df)
    if not numeric_cols:
        return None
    
    label_col = get_label_column(df, numeric_cols)
    
    # Clean numeric data
    df_clean = df.copy()
    for col in numeric_cols:
        df_clean[col] = df_clean[col].apply(clean_numeric_value)
    
    fig = go.Figure()
    
    colors = px.colors.qualitative.Set2
    for i, col in enumerate(numeric_cols):
        fig.add_trace(go.Bar(
            name=col,
            x=df_clean[label_col],
            y=df_clean[col],
            marker_color=colors[i % len(colors)]
        ))
    
    fig.update_layout(
        title="Data Visualization",
        xaxis_title=label_col,
        yaxis_title="Value",
        barmode='group',
        template='plotly_white',
        font=dict(family="Inter, sans-serif"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    return fig

def create_line_chart(df):
    """Create a line chart from the DataFrame."""
    numeric_cols = get_numeric_columns(df)
    if not numeric_cols:
        return None
    
    label_col = get_label_column(df, numeric_cols)
    
    # Clean numeric data
    df_clean = df.copy()
    for col in numeric_cols:
        df_clean[col] = df_clean[col].apply(clean_numeric_value)
    
    fig = go.Figure()
    
    colors = px.colors.qualitative.Set2
    for i, col in enumerate(numeric_cols):
        fig.add_trace(go.Scatter(
            name=col,
            x=df_clean[label_col],
            y=df_clean[col],
            mode='lines+markers',
            line=dict(color=colors[i % len(colors)], width=2),
            marker=dict(size=8)
        ))
    
    fig.update_layout(
        title="Trend Visualization",
        xaxis_title=label_col,
        yaxis_title="Value",
        template='plotly_white',
        font=dict(family="Inter, sans-serif"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    return fig

def create_pie_chart(df):
    """Create a pie chart from the DataFrame."""
    numeric_cols = get_numeric_columns(df)
    if not numeric_cols:
        return None
    
    label_col = get_label_column(df, numeric_cols)
    value_col = numeric_cols[0]  # Use first numeric column
    
    # Clean numeric data
    df_clean = df.copy()
    df_clean[value_col] = df_clean[value_col].apply(clean_numeric_value)
    
    fig = px.pie(
        df_clean,
        values=value_col,
        names=label_col,
        title="Distribution",
        color_discrete_sequence=px.colors.qualitative.Set2
    )
    
    fig.update_layout(
        template='plotly_white',
        font=dict(family="Inter, sans-serif")
    )
    
    return fig

def convert_df_to_csv(df):
    """Convert DataFrame to CSV for download."""
    return df.to_csv(index=False).encode('utf-8')

# ===== TYPEWRITER EFFECT =====
def stream_data(text):
    for word in text.split(" "):
        yield word + " "
        time.sleep(0.04)

# ===== SIDEBAR =====
with st.sidebar:
    st.title("🧞 ERPGenie")
    st.markdown("---")
    st.markdown("### Status")
    st.markdown("🟢 **Online**")
    st.markdown("Connected to: `n8n Webhook`")
    
    st.markdown("---")
    show_debug = st.checkbox("Show Debug Info", value=False)
    
    st.markdown("---")
    if st.button("Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.parsed_data = {}
        st.rerun()

# Webhook URL
WEBHOOK_URL = "http://localhost:5678/webhook-test/a5fd8415-ce4c-4e62-860c-050437be9d1e"

# Initialize State
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({"role": "assistant", "content": "Hello! I am ERPGenie. How can I assist you today?"})

if "parsed_data" not in st.session_state:
    st.session_state.parsed_data = {}

# ===== MAIN CHAT DISPLAY =====
st.title("ERPGenie Chat")

# Display Chat History with Visualization Options
for idx, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"], avatar="🧞" if message["role"] == "assistant" else "👤"):
        st.markdown(message["content"])
        
        # For assistant messages, check if data is graphable/exportable
        if message["role"] == "assistant":
            msg_key = f"msg_{idx}"
            
            # Parse data if not already cached
            if msg_key not in st.session_state.parsed_data:
                df = parse_table_from_text(message["content"])
                st.session_state.parsed_data[msg_key] = df
            
            df = st.session_state.parsed_data.get(msg_key)
            
            if df is not None and not df.empty:
                st.markdown("---")
                
                # Show action buttons
                col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 2])
                
                with col1:
                    if st.button("📊 Bar Chart", key=f"bar_{idx}"):
                        st.session_state[f"show_bar_{idx}"] = not st.session_state.get(f"show_bar_{idx}", False)
                
                with col2:
                    if st.button("📈 Line Chart", key=f"line_{idx}"):
                        st.session_state[f"show_line_{idx}"] = not st.session_state.get(f"show_line_{idx}", False)
                
                with col3:
                    if st.button("🥧 Pie Chart", key=f"pie_{idx}"):
                        st.session_state[f"show_pie_{idx}"] = not st.session_state.get(f"show_pie_{idx}", False)
                
                with col4:
                    csv_data = convert_df_to_csv(df)
                    st.download_button(
                        label="📥 Export CSV",
                        data=csv_data,
                        file_name=f"erpgenie_data_{idx}.csv",
                        mime="text/csv",
                        key=f"csv_{idx}"
                    )
                
                with col5:
                    if st.button("📋 Show Table", key=f"table_{idx}"):
                        st.session_state[f"show_table_{idx}"] = not st.session_state.get(f"show_table_{idx}", False)
                
                # Display visualizations if toggled
                if st.session_state.get(f"show_bar_{idx}", False):
                    if is_graphable(df):
                        fig = create_bar_chart(df)
                        if fig:
                            st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("No numeric data available for bar chart.")
                
                if st.session_state.get(f"show_line_{idx}", False):
                    if is_graphable(df):
                        fig = create_line_chart(df)
                        if fig:
                            st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("No numeric data available for line chart.")
                
                if st.session_state.get(f"show_pie_{idx}", False):
                    if is_graphable(df):
                        fig = create_pie_chart(df)
                        if fig:
                            st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("No numeric data available for pie chart.")
                
                if st.session_state.get(f"show_table_{idx}", False):
                    st.dataframe(df, use_container_width=True)

# ===== CHAT INPUT & LOGIC =====
if prompt := st.chat_input("Ask ERPGenie..."):
    # Add user message to state
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message immediately
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)
    
    #Assistant Response 
    with st.chat_message("assistant", avatar="🧞"):
        with st.spinner("Genie is thinking..."):
            try:
                # send to n8n webhook
                payload = {"text": prompt} 
                response = requests.post(WEBHOOK_URL, json=payload, timeout=30)
                
                # debyg
                if show_debug:
                    st.json(response.json() if response.status_code == 200 else {"error": response.status_code, "text": response.text})

                if response.status_code == 200:
                    try:
                        data = response.json()
                        ai_response = data.get("output", data.get("text", data.get("response", str(data))))
                        if isinstance(ai_response, (dict, list)):
                             ai_response = json.dumps(ai_response, indent=2)
                    except json.JSONDecodeError:
                        ai_response = response.text
                    
                    st.write_stream(stream_data(ai_response))
                    st.session_state.messages.append({"role": "assistant", "content": ai_response})
                    
                    # cache data for visualization
                    msg_idx = len(st.session_state.messages) - 1
                    msg_key = f"msg_{msg_idx}"
                    df = parse_table_from_text(ai_response)
                    st.session_state.parsed_data[msg_key] = df
                    
                    # show visualization options if data accepts
                    if df is not None and not df.empty:
                        st.markdown("---")
                        st.success(" **Data detected!** Use the buttons above after refresh to visualize or export.")
                        st.rerun()
                    
                else:
                    error_msg = f"rrror: webhook returned status {response.status_code}"
                    st.error(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})
                    
            except requests.exceptions.ConnectionError:
                error_msg = "Error: Could not connect to n8n webhook. Is it running?"
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})
            except Exception as e:
                error_msg = f"Error: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})

import streamlit as st

def set_page_config():
    st.set_page_config(
        page_title="面试姿态分析系统",
        layout="wide",
        initial_sidebar_state="expanded"
    )

def load_custom_css():
    st.markdown("""
    <style>
        .sub-header {
            color: #2C3E50;
            border-bottom: 2px solid #3498DB;
            padding-bottom: 8px;
            margin: 1.5rem 0 1rem;
        }
        .info-box {
            background-color: #ECF0F1;
            padding: 15px;
            border-radius: 5px;
            margin: 10px 0;
        }
        .status-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 5px;
        }
        .recording-blink {
            animation: blink 1.5s infinite;
        }
        @keyframes blink {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }
        .analysis-item {
            margin-bottom: 8px;
            padding: 5px;
            border-radius: 3px;
        }
        .good { background-color: #D4EDDA; }
        .warning { background-color: #FFF3CD; }
        .bad { background-color: #F8D7DA; }
        .feedback-box {
            padding: 10px;
            margin: 10px 0;
            border-radius: 5px;
        }
        .score-card {
            padding: 15px;
            border-radius: 5px;
            margin: 10px 0;
            text-align: center;
        }
        .alert {
            padding: 0.75rem 1.25rem;
            margin-bottom: 1rem;
            border: 1px solid transparent;
            border-radius: 0.25rem;
        }
        .alert-success {
            color: #155724;
            background-color: #d4edda;
            border-color: #c3e6cb;
        }
        .alert-warning {
            color: #856404;
            background-color: #fff3cd;
            border-color: #ffeaa7;
        }
        .alert-danger {
            color: #721c24;
            background-color: #f8d7da;
            border-color: #f5c6cb;
        }
        .alert-info {
            color: #0c5460;
            background-color: #d1ecf1;
            border-color: #bee5eb;
        }
    </style>
    """, unsafe_allow_html=True)
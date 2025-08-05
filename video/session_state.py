import streamlit as st

def init_session_state():
    if 'initialized' not in st.session_state:
        required_states = {
            'initialized': True,
            'recording': False,
            'video_path': None,
            'analysis_results': [],
            'last_video': None,
            'video_scores': None,
            'latest_selected': None,
            'saved_analyses': {},
            'current_analysis': None,
            'show_help': False,
            'analyzing': False,
            'analyzing_video': False,
            'analyzers_loaded': False,
            'last_refresh_time': 0,
            'preview_frame': None,
            'recording_thread': None,
            'show_analysis_detail': False,
            'current_report_path': None,
            'frame_descriptions': []
        }
        for key, value in required_states.items():
            st.session_state[key] = value
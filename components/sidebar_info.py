import streamlit as st

def render_sidebar_user_info():
    """
    Renders user information and a logout button in the sidebar.
    This should be called on every page where the user is logged in.
    """
    if "user_id" in st.session_state:
        with st.sidebar:
            st.markdown("---")
            st.markdown(f"👤 **Kullanıcı:** {st.session_state.get('user_name', 'N/A')}")
            st.markdown(f"""<div style="color: black;">🆔 <strong>ID:</strong> {st.session_state.get('user_id', 'N/A')}</div>""", unsafe_allow_html=True)
            st.markdown(f"📧 **E-posta:** {st.session_state.get('user_email', 'N/A')}")

            if st.button("🔒 Oturumu Kapat", key="sidebar_logout"):
                # Clear the entire session state
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                # Rerun to redirect to the login page via the check in app.py
                st.rerun()

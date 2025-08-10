import streamlit as st
import time
from datetime import datetime, date
import pandas as pd
import firebase_admin
from firebase_admin import credentials, db

# Initialize page config (ONCE at the top)
st.set_page_config(page_title="Sadhu log ka POMO", layout="wide")

# Initialize session state
if "init" not in st.session_state:
    st.session_state.init = True
    st.session_state.session_id = None
    st.session_state.is_host = False
    st.session_state.timer = {
        "start_time": datetime.now(),
        "is_focus": True,
        "remaining": 25 * 60,
        "is_running": False,
        "history": [],
        "focus_minutes": 25,
        "break_minutes": 5,
        "last_completed": None,
        "current_date": str(date.today()),
    }

# Firebase initialization
# Firebase initialization
if not firebase_admin._apps:
    try:
        # For Streamlit Sharing
        if st.secrets:
            cred_dict = dict(st.secrets["firebase"]["credentials"])
            db_url = st.secrets["firebase"]["db_url"]
        # For local development
        else:
            import json

            with open("firebase-key.json") as f:
                cred_dict = json.load(f)
            db_url = "https://pomodoro-cffe9-default-rtdb.firebaseio.com"

        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred, {"databaseURL": db_url})

        # Test connection
        db.reference("connection_test").set(
            {"status": "active", "timestamp": datetime.now().isoformat()}
        )
    except Exception as e:
        st.error(f"Firebase initialization failed: {str(e)}")
        st.stop()

# Enhanced CSS for the flip clock (bigger size)
flip_clock_css = """
<style>
.flip-clock {
    font-family: 'Arial', sans-serif;
    font-size: 10rem;
    font-weight: bold;
    display: flex;
    justify-content: center;
    margin: 20px 0;
}
.flip-clock .digit {
    background: #333;
    color: white;
    border-radius: 10px;
    padding: 0 20px;
    margin: 0 10px;
    box-shadow: 0 4px 8px rgba(0,0,0,0.3);
}
.flip-clock .separator {
    display: flex;
    align-items: center;
    color: #333;
    font-size: 10rem;
}
@media (max-width: 768px) {
    .flip-clock {
        font-size: 5rem;
    }
    .flip-clock .separator {
        font-size: 5rem;
    }
}

/* Perfectly centered history table */
[data-testid="stDataFrame"] {
    width: 100%;
}
[data-testid="stDataFrame"] table {
    margin-left: auto;
    margin-right: auto;
}
[data-testid="stDataFrame"] th, 
[data-testid="stDataFrame"] td {
    text-align: center !important;
    vertical-align: middle !important;
}
[data-testid="stDataFrame"] thead tr th {
    background-color: #f0f2f6;
    position: sticky;
    top: 0;
    z-index: 1;
}

/* Centered titles */
h1, h2, h3, h4, h5, h6 {
    text-align: center !important;
}
</style>
"""
st.markdown(flip_clock_css, unsafe_allow_html=True)


def display_flip_clock(seconds):
    minutes, secs = divmod(seconds, 60)
    time_str = f"{minutes:02d}:{secs:02d}"
    html = '<div class="flip-clock">'
    for char in time_str:
        if char == ":":
            html += f'<div class="separator">{char}</div>'
        else:
            html += f'<div class="digit">{char}</div>'
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


def update_timer():
    if st.session_state.timer["is_running"]:
        elapsed = (
            datetime.now() - st.session_state.timer["start_time"]
        ).total_seconds()
        remaining = max(
            0,
            (
                st.session_state.timer["focus_minutes"] * 60
                if st.session_state.timer["is_focus"]
                else st.session_state.timer["break_minutes"] * 60
            )
            - elapsed,
        )

        if remaining <= 0:
            # Record completion time
            end_time = datetime.now()
            start_time = st.session_state.timer["start_time"]

            # Record history
            session_type = "Focus" if st.session_state.timer["is_focus"] else "Break"
            st.session_state.timer["history"].append(
                {
                    "Session Type": session_type,
                    "Duration (min)": st.session_state.timer["focus_minutes"]
                    if session_type == "Focus"
                    else st.session_state.timer["break_minutes"],
                    "Started At": start_time.strftime("%I:%M %p"),
                    "Ended At": end_time.strftime("%I:%M %p"),
                    "Date": str(date.today()),
                }
            )

            # Switch mode
            st.session_state.timer["is_focus"] = not st.session_state.timer["is_focus"]
            st.session_state.timer["start_time"] = datetime.now()
            remaining = (
                st.session_state.timer["break_minutes"] * 60
                if st.session_state.timer["is_focus"]
                else st.session_state.timer["focus_minutes"] * 60
            )

        st.session_state.timer["remaining"] = remaining


def create_session(focus_minutes, break_minutes):
    session_id = str(int(time.time()))
    st.session_state.session_id = session_id
    st.session_state.is_host = True

    # Initialize timer
    st.session_state.timer = {
        "start_time": datetime.now(),
        "is_focus": True,
        "remaining": focus_minutes * 60,
        "is_running": True,
        "history": st.session_state.timer.get(
            "history", []
        ),  # Preserve existing history
        "focus_minutes": focus_minutes,
        "break_minutes": break_minutes,
        "last_completed": None,
        "current_date": str(date.today()),
    }

    # Save to Firebase
    ref = db.reference(f"sessions/{session_id}")
    ref.set(
        {
            "focus_minutes": focus_minutes,
            "break_minutes": break_minutes,
            "is_focus": True,
            "remaining": focus_minutes * 60,
            "is_running": True,
            "start_time": datetime.now().isoformat(),
            "history": st.session_state.timer["history"],
            "last_completed": None,
            "current_date": str(date.today()),
        }
    )

    # Generate shareable link
    current_url = st.query_params.get("url", ["http://localhost:8501"])[0]
    share_url = f"{current_url}?join={session_id}"

    # Display session ID and share options
    st.success("Session created successfully!")
    st.markdown("### Session Information")
    st.markdown(f"**Session ID:** `{session_id}`")
    st.markdown("Share this link with your friend:")
    st.code(share_url)

    if st.button("📋 Copy Share Link"):
        st.session_state.copied = True
        st.rerun()

    if st.session_state.get("copied", False):
        st.success("Link copied to clipboard!")
        st.session_state.copied = False


def join_session(session_id):
    ref = db.reference(f"sessions/{session_id}")
    session_data = ref.get()

    if session_data:
        st.session_state.session_id = session_id
        st.session_state.is_host = False
        st.session_state.timer = {
            "start_time": datetime.fromisoformat(session_data["start_time"]),
            "is_focus": session_data["is_focus"],
            "remaining": session_data["remaining"],
            "is_running": session_data["is_running"],
            "history": session_data.get("history", []),
            "focus_minutes": session_data["focus_minutes"],
            "break_minutes": session_data["break_minutes"],
            "last_completed": session_data.get("last_completed"),
            "current_date": session_data.get("current_date", str(date.today())),
        }
        return True
    return False


def display_history():
    # Filter history for today's date
    today_history = [
        h
        for h in st.session_state.timer["history"]
        if h.get("Date") == str(date.today())
    ]

    if today_history:
        history_df = pd.DataFrame(today_history)
        history_df.index = history_df.index + 1  # Start numbering from 1

        # Remove Date column from display
        history_df = history_df.drop(columns=["Date"], errors="ignore")

        # Apply custom styling for perfect centering
        st.dataframe(
            history_df.style.set_properties(
                **{"text-align": "center", "vertical-align": "middle"}
            ),
            use_container_width=True,
            height=(len(history_df) * 35 + 38),
        )
    else:
        st.write("No sessions completed today yet.")


def main_app():
    st.title("Sadhu log ka POMO")

    # Check for join parameter
    if "join" in st.query_params and not st.session_state.session_id:
        if join_session(st.query_params["join"]):
            st.rerun()

    if not st.session_state.session_id:
        tab1, tab2 = st.tabs(["New Session", "Join Session"])

        with tab1:
            st.subheader("Create New Session")
            focus = st.slider("Focus Time (minutes)", 1, 60, 25)
            break_time = st.slider("Break Time (minutes)", 1, 30, 5)
            if st.button("Start Session"):
                create_session(focus, break_time)
                st.rerun()

        with tab2:
            st.subheader("Join Existing Session")
            session_id = st.text_input("Enter Session ID")
            if st.button("Join Session"):
                if session_id:
                    if join_session(session_id):
                        st.rerun()
                else:
                    st.warning("Please enter a session ID")
    else:
        update_timer()

        # Display timer
        display_flip_clock(int(st.session_state.timer["remaining"]))
        st.subheader(
            "Focus Time" if st.session_state.timer["is_focus"] else "Break Time"
        )

        # Controls
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button(
                "⏸️ Pause" if st.session_state.timer["is_running"] else "▶️ Resume"
            ):
                st.session_state.timer["is_running"] = not st.session_state.timer[
                    "is_running"
                ]
                st.rerun()
        with col2:
            if st.button("⏹️ End Session"):
                # Save history before ending session
                ref = db.reference(f"sessions/{st.session_state.session_id}")
                ref.update(
                    {"history": st.session_state.timer["history"], "is_running": False}
                )
                st.session_state.session_id = None
                st.session_state.timer["is_running"] = False
                st.rerun()

        # Display history
        st.subheader("Today's Session History")
        display_history()

        # Show session info if host
        if st.session_state.is_host:
            st.markdown("### Session Information")
            st.markdown(f"**Session ID:** `{st.session_state.session_id}`")
            current_url = st.query_params.get("url", ["http://localhost:8501"])[0]
            share_url = f"{current_url}?join={st.session_state.session_id}"
            st.markdown("Share this link to collaborate:")
            st.code(share_url)


if __name__ == "__main__":
    main_app()
    if st.session_state.get("timer", {}).get("is_running", False):
        time.sleep(1)
        st.rerun()

# For working with Streamlit GUI
import streamlit as st
import time
from helpers import language_to_lang_code, _

def css_styling():
    # Customize CSS to change the appearance of upload button
    st.markdown("""
    <style>
    /* Hide all internal elements inside uploader */
    div[data-testid="stFileUploader"] * {
        visibility: hidden;
    }

    /* Remove any inner span content */
    div[data-testid="stFileUploader"] button span {
        display: none !important;
    }

    /* Style the upload button */
    div[data-testid="stFileUploader"] button {
        visibility: visible !important;
        display: inline-flex !important;
        align-items: center;
        justify-content: center;
        padding: 10px 16px;
        background-color: white !important;
        font-weight: bold;
        font-size: 16px;
        border: 1px solid #a2a9b1 !important;
        border-radius: 4px;
        box-shadow: none;
        position: relative;
        cursor: pointer;

        color: transparent !important;
        text-indent: -40px;
        overflow: hidden;
        margin: 0 !important;
    }

    /* Upload icon */
    div[data-testid="stFileUploader"] button::before {
        content: "";
        background-image: url("https://upload.wikimedia.org/wikipedia/commons/thumb/6/6b/OOjs_UI_icon_upload.svg/240px-OOjs_UI_icon_upload.svg.png");
        background-repeat: no-repeat;
        background-size: 18px 18px;
        display: inline-block;
        width: 18px;
        height: 18px;
        margin-right: 8px;
        visibility: visible;
    }


    /* Hide minimal buttons */
    button.stBaseButton.stButton.stBaseButton--minimal {
        display: none !important;
    }

    /* Set left alignment using flex-direction reverse trick */
    section[data-testid="stFileUploaderDropzone"] {
        display: flex !important;
        flex-direction: column-reverse !important;
        justify-content: flex-start !important;
        align-items: center !important;
        width: 100% !important;
    }
    </style>
    """, unsafe_allow_html=True)

    if language_to_lang_code(st.session_state["current_language"]) == "sk":
        st.markdown("""
        <style>
        /* Custom Slovak label */
        div[data-testid="stFileUploader"] button::after {
            content: "Nahrať súbor";
            color: #202122;
            font-weight: bold;
            font-size: 16px;
            visibility: visible;
        }
        </style>
        """, unsafe_allow_html=True)
    elif language_to_lang_code(st.session_state["current_language"]) == "de":
        st.markdown("""
                <style>
                /* Custom German label */
                div[data-testid="stFileUploader"] button::after {
                    content: "Datei hochladen";
                    color: #202122;
                    font-weight: bold;
                    font-size: 16px;
                    visibility: visible;
                }
                </style>
                """, unsafe_allow_html=True)
    else:
        st.markdown("""
                <style>
                /* Custom English label */
                div[data-testid="stFileUploader"] button::after {
                    content: "Upload file";
                    color: #202122;
                    font-weight: bold;
                    font-size: 16px;
                    visibility: visible;
                }
                </style>
                """, unsafe_allow_html=True)

    # Customize progress bar to look like a Codex (Wikimedia UI) one
    st.markdown("""
            <style>
            /* Remove grey background but add black border */
            div.stProgress[data-testid="stProgress"],
            div[data-baseweb="progress-bar"] {
                background: transparent !important;
                padding: 0 !important;
                margin: 0 !important;
                box-shadow: none !important;
            }

            /* Outer container: black border with slight rounding */
            div[data-baseweb="progress-bar"] {
                border: 1px solid #000 !important;  /* black border */
                border-radius: 4px !important;
                height: auto !important;
                overflow: visible !important;
            }

            /* Inner flex container controls bar height */
            div[data-baseweb="progress-bar"] > div > div {
                height: 0.9rem !important;  /* bar height */
                align-items: center !important;
            }

            /* Filled portion */
            div[data-baseweb="progress-bar"] > div > div > div {
                background-color: #36c !important;
                border-right: 1px solid #2a4b8d !important;
                border-radius: 4px !important;
                height: 100% !important;
                transition: width 0.3s ease;
            }
            </style>
        """, unsafe_allow_html=True)

    # To remove streamlit native header and menu
    hide_streamlit_style = """
    <style>
        /* Show the header container itself */
        header {
            visibility: visible !important;
            background-color: inherit !important; /* keeps the original background */
            height: auto !important;
        }
        [data-testid="stAppDeployButton"] {
            display: none !important;
        }
        /* Optionally hide footer */
        .streamlit-footer {
            display: none !important;
        }
    </style>
    """
    st.markdown(hide_streamlit_style, unsafe_allow_html=True)

    # CSS to style the toggle according to Codex (Wikimedia UI)
    st.markdown("""
    <style>
    /* --- CONTAINER SELECTOR --- */
    div[data-testid="stCheckbox"] > label[data-baseweb="checkbox"] {
        display: flex;
        align-items: center;
    }

    /* --- TRACK (the outer pill) --- */
    div[data-testid="stCheckbox"] > label[data-baseweb="checkbox"] > div:first-child {
        width: 40px;
        height: 20px;
        border-radius: 999px;
        border: 1px solid #72777d;
        transition: background-color 0.3s ease;
    }

    /* --- THUMB (the circle knob) --- */
    div[data-testid="stCheckbox"] > label[data-baseweb="checkbox"] > div:first-child > div {
        width: 16px;
        height: 16px;
        background-color: white !important;
        border-radius: 50%;
        border: 1.5px solid black;
        margin: 2px;
        transition: transform 0.3s ease;
    }
    </style>
    """, unsafe_allow_html=True)

    # Custom CSS which makes st.status and st.spinner look like Codex (Wikimedia UI) progress indicator
    st.markdown("""
    <style>
    /* Wikimedia-style loading spinner */
    @keyframes wikimedia-spinner {
      to {
        transform: rotate(360deg);
      }
    }

    /* Spinner for st.spinner() */
    div[data-testid="stSpinner"] i {
      width: 32px;
      height: 32px;
      border: 2px solid #36c;
      border-top-color: transparent;
      border-radius: 50%;
      animation: wikimedia-spinner 0.8s linear infinite;
      vertical-align: middle;
      margin-right: 0.5rem;
    }
    div[data-testid="stSpinner"] {
      display: inline-flex;
      align-items: center;
    }

    /* Spinner for st.expander() */
    i[data-testid="stExpanderIconSpinner"] {
      width: 16px;
      height: 16px;
      border: 2px solid #36c;
      border-top-color: transparent;
      border-radius: 50%;
      animation: wikimedia-spinner 0.8s linear infinite;
      display: inline-block;
      vertical-align: middle;
      margin-left: 0.25rem;
    }

    /* Refined success check icon for st.expander() */
    span[data-testid="stExpanderIconCheck"] {
      font-size: 0; /* hide "check" text */
      position: relative;
      display: inline-block;
      width: 20px;
      height: 20px;
      margin-left: 0;
      vertical-align: middle;
    }

    span[data-testid="stExpanderIconCheck"]::before {
      content: "";
      display: inline-block;
      width: 20px;
      height: 20px;
      border-radius: 50%;
      background-color: #0f9b7f; /* Wikimedia green */
      background-image: url("https://upload.wikimedia.org/wikipedia/commons/thumb/1/13/OOjs_UI_icon_check-invert.svg/240px-OOjs_UI_icon_check-invert.svg.png");
      background-repeat: no-repeat;
      background-position: center;
      background-size: 12px 12px;
    }
    </style>
    """, unsafe_allow_html=True)

    # Custom CSS which turns sidebar grey
    st.markdown(
        """
        <style>
        /* Target the sidebar section by class and data-testid */
        section.stSidebar[data-testid="stSidebar"] {
            background-color: #eaecf0 !important;  /* light grey */
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Custom CSS which replaces the native sidebar icon with hamburger menu
    st.markdown(
        """
        <style>
        /* Hide the text inside the icon span */
        [data-testid="stIconMaterial"] {
            color: transparent !important;  /* hides the text */
            position: relative;
            width: 24px;  /* set width for your image */
            height: 24px; /* set height for your image */
            display: inline-block;
        }
        /* Insert your custom image as a background */
        [data-testid="stIconMaterial"]::after {
            content: "";
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            background-image: url('https://upload.wikimedia.org/wikipedia/commons/thumb/b/b2/Hamburger_icon.svg/240px-Hamburger_icon.svg.png');
            background-size: contain;
            background-repeat: no-repeat;
            background-position: center;
            transform: translateY(2px);  /* moves image 2px down */
        }
        /* Force sidebar toggle button and icon container always visible */
    [data-testid="stSidebarCollapseButton"],
    [data-testid="stSidebarCollapseButton"] > button,
    [data-testid="stSidebarCollapseButton"] [data-testid="stIconMaterial"] {
        display: inline-flex !important;
        opacity: 1 !important;
        visibility: visible !important;
        pointer-events: auto !important;
        color: transparent !important;  /* hide original text */
        position: relative;              /* for ::after positioning */
        width: 24px;
        height: 24px;
    }

        </style>
        """,
        unsafe_allow_html=True,
    )


def app_header():
    # Adds custom nav menu
    st.markdown("""
        <style>
        .reportview-container .main {
          padding-top: 100px;  /* keep padding for taller stripe */
        }

        .top-stripe {
          position: fixed;
          top: 0; left: 0; right: 0;
          background-color: #eaecf0;
          color: #000;
          font-family: 'Gill Sans', 'Gill Sans MT', Calibri, 'Trebuchet MS', sans-serif;
          font-weight: bold;
          font-size: 20px;
          display: flex;
          justify-content: flex-start;  /* since no right section */
          align-items: center;
          padding: 1em 20px;  /* taller stripe */
          z-index: 9999;
          box-shadow: 0 2px 5px rgba(0,0,0,0.1);
          user-select: none;
          white-space: normal;
        }

        .left-text {
          white-space: normal;
          line-height: 1.2;
          flex-grow: 1;
          font-size: 20px;
          margin-left: 70px;
        }
        </style>
        """, unsafe_allow_html=True)

    st.markdown(f"""
        <div class="top-stripe">
          <div class="left-text">
            {_("AddDesc: Semi-automatic addition of descriptions on Wikidata", "page_title")}
          </div>
        </div>
        """, unsafe_allow_html=True)

# Banner displaying maintenance at the bottom of the page
def maintenance_banner():
    # Add custom CSS for bottom sticky banner
    st.markdown("""
            <style>
            .bottom-stripe {
              position: fixed;
              bottom: 0; left: 0; right: 0;
              background-color: #ffcc00;
              color: #000;
              font-family: 'Gill Sans', 'Gill Sans MT', Calibri, 'Trebuchet MS', sans-serif;
              font-weight: bold;
              font-size: 18px;
              display: flex;
              justify-content: center;   /* center the text */
              align-items: center;
              padding: 0.8em 20px;
              z-index: 9999;
              box-shadow: 0 -2px 5px rgba(0,0,0,0.1); /* shadow on top edge */
              user-select: none;
              white-space: normal;
            }
            </style>
            """, unsafe_allow_html=True)


def category_chip(text):
    st.markdown("""
    <style>
.info-chip {
    display: inline-flex;
    align-items: center;
    padding: 0.4em 0.75em;
    font-size: 1.25rem; /* ~ h3 size in Streamlit */
    font-family: "Segoe UI", "Helvetica Neue", sans-serif;
    background-color: #f8f9fa;
    color: #202122;
    border: 1px solid #a2a9b1;
    border-radius: 999px;
    gap: 0.5em;
    line-height: 1.5;
}

.info-chip img {
    width: 1.4rem;
    height: 1.4rem;
    object-fit: contain;
}
</style>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="info-chip">
      <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/a/a3/OOjs_UI_icon_articles-ltr.svg/240px-OOjs_UI_icon_articles-ltr.svg.png" alt="Articles icon">
      {text}
    </div>
    """, unsafe_allow_html=True)
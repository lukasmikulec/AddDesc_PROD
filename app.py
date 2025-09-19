# For the user interface
import streamlit as st
# For working with Wikipedia and Wikidata content
import pywikibot
import time
import pathlib
import json
import base64
import pandas as pd
# For sending OAuth get requests to Meta
import requests
# For generating random values for widget keys which rerun in functions
import uuid

# For creating authentication objects passed in OAuth get requests
from requests_oauthlib import OAuth1

from helpers import _, __

# For creating containers with elements to be styled according to Codex (Wikimedia UI)
from streamlit_extras.stylable_container import stylable_container

# For setting, access, and deleting values in local storage
from streamlit_local_storage import LocalStorage

# For encryption/decryption of tokens which are temporarily saved in local storage
from cryptography.fernet import Fernet

# Functions for description addition process
from helpers import generate_description, generate_table, process_publish_descriptions, change_page_to, show_problems, review_descriptions

from styling_functions import css_styling, category_chip, app_header, maintenance_banner

# Functions for login - authentication process
from login_process import authorization_setup, get_access_token_and_verify_user, login_with_oauth_params, log_out


# Initialize local storage component
localStorage = LocalStorage()
# Give it time to initialize
time.sleep(0.2)

all_local_Storage_items = localStorage.getAll()
if "language" in all_local_Storage_items:
    st.session_state["current_language"] = localStorage.getItem("language")
else:
    st.session_state["current_language"] = "en.wikipedia.org"

# Fetch all the allowed language projects
LANG_OPTIONS_URL = "https://raw.githubusercontent.com/lukasmikulec/AddDesc_Database/refs/heads/main/language_map.json"
response_language_map = requests.get(LANG_OPTIONS_URL)
response_language_map.raise_for_status()
language_map = response_language_map.json()
# Save the language map for language_to_lang_code function
st.session_state["language_map"] = language_map
# Convert the language map to language project list for dropdown menu
language_options = list(language_map.keys())
print(language_options)
print(type(language_options))
#language_options = ["en.wikipedia.org", "de.wikipedia.org", "sk.wikipedia.org"]
language_options.remove(st.session_state["current_language"])
current_language_options = []
current_language_options.append(st.session_state["current_language"])
for i in range(len(language_options)):
    current_language_options.append(language_options[i])
    st.session_state["language_options"] = current_language_options

# Load translations file if it is not loaded yet
if "i18n" not in st.session_state:
    st.session_state["i18n"] = pd.read_csv("https://raw.githubusercontent.com/lukasmikulec/AddDesc_Database/refs/heads/main/i18n.csv", delimiter="|")
    # Set the English column as the index, treating it as the key
    st.session_state["i18n"].set_index("code", inplace=True)

if "i18n_parser" not in st.session_state:
    st.session_state["i18n_parser"] = pd.read_csv("https://raw.githubusercontent.com/lukasmikulec/AddDesc_Database/refs/heads/main/i18n_parser.csv", delimiter="|")
    # Set the English column as the index, treating it as the key
    st.session_state["i18n_parser"].set_index("code", inplace=True)

# Make page wide and set its name
st.set_page_config(layout="wide", page_title=_("AddDesc", "tab_title"), initial_sidebar_state="collapsed", page_icon=":material/edit_note:")

# Customize CSS to change the appearance according to Codex (Wikimedia UI)
css_styling()

app_header()

maintenance_banner()


# Function to load custom css for buttons
def load_css(file_path):
    with open(file_path) as f:
        st.html(f"<style>{f.read()}</style>")


# Load the external CSS
css_path = pathlib.Path("assets/styles.css")
load_css(css_path)

def remove_local_storage_key(localStorage, key_to_remove: str):
    all_items = localStorage.getAll()
    if key_to_remove in all_items:
        localStorage.setItem(key_to_remove, "DELETED", key=str(uuid.uuid4()))


@st.dialog(_("App login", "log_in_popup"), width="large")
def dialog_sign_in():
    st.markdown(f"""
    <div style="text-align: center;">
        <p>{_("You can allow this app to add Wikidata descriptions on your behalf after clicking the button below.", "log_in_item1")}</p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown(f"""
        <div style="text-align: center;">
            <p>{_("This app doesn't need access to your password thanks to Wikimedia login (OAuth).", "log_in_item2")}</p>
        </div>
        """, unsafe_allow_html=True)
    st.markdown(f"""
    <div style="text-align: center;">
        <p>
            {_("You can revoke this app's access to your data at any time at", "log_in_item3")} 
            <a href="https://meta.wikimedia.org/wiki/Special:OAuthManageMyGrants" target="_blank">
                https://meta.wikimedia.org/wiki/Special:OAuthManageMyGrants
            </a>.
        </p>
    </div>
    """, unsafe_allow_html=True)
    with stylable_container(
            key="dialog_sign_in",
            css_styles="""
                            a[data-testid="stBaseLinkButton-secondary"] {
        padding: 0.4em 1em;
        display: inline-block;
        margin: 0 auto;
        font-size: 1rem;
        text-decoration: none;
        background-color: #3366cc;
        border: 1px solid #3366cc;
        border-radius: 0.2em;
        transition: background-color 0.2s, border-color 0.2s;
        white-space: nowrap;
        text-align: center; 
    }

    a[data-testid="stBaseLinkButton-secondary"] p{
    font-family: Arial, sans-serif !important;
    font-weight: bold !important;
    color: #ffffff !important;
    }

    a[data-testid="stBaseLinkButton-secondary"]:hover {
        background-color: #234ea1 !important;
    }

    a[data-testid="stBaseLinkButton-secondary"]:active { /*Defines style of normal buttons when clicked over*/
        background-color: #233566 !important;
        border-color: #233566 !important;
        border: 1px solid #233566 !important;
                            }
    """
    ):
        col10, col11, col12 = st.columns([3, 4, 3])
        with col11:
            # (OAuth 1.0a, Step 2: https://www.mediawiki.org/wiki/OAuth/For_Developers#)
            # Opens the OAuth authorization window on Meta
            st.link_button(_("Login with Wikimedia account", "log_in_popup_button"), st.session_state["AUTHORIZE_URL"], use_container_width=True)


# Function to verify if the inputted category exists on Wikipedia
def verify_category():
    # While the spinner is showing
    with st.spinner(_("Searching through all pages in the category", "cateogry_article_search")):
        # Set the site to Slovak Wikipedia
        site = pywikibot.Site(__("en", "lang"), "wikipedia")
        print("Category: ", st.session_state["category"])
        # Set the inputted category as the category to be accessed
        cat = pywikibot.Category(site, st.session_state["category"])
        # If subcategories are not selected
        if st.session_state["subcategories_enabled"] == False:
            # List only pages in the category
            cat = list(cat.articles())
        # If subcategories are selected
        if st.session_state["subcategories_enabled"] == True:
            # List pages within the category and pages of n-th subcategories
            cat = list(cat.articles(recurse=st.session_state["subcategory_recurse"]))
        print("Category list: ", cat)
        # If there is no page in inputted category
        if len(cat) == 0:
            # Show to user the category does not exist
            st.session_state["category_verified"] = False
            st.session_state["invalid_category"] = st.session_state["category"]
        # If there are pages in inputted category
        else:
            # Show to user the category exists
            st.session_state["category_verified"] = True
            # Save the category
            st.session_state["category_object"] = cat


# If the user returned from OAuth authorization
if "oauth_verifier" in st.query_params:
    # Save the verification token from the URL
    st.session_state["OAUTH_VERIFIER"] = st.query_params["oauth_verifier"]
    # Save the oauth token from the URL
    st.session_state["OAUTH_TOKEN"] = st.query_params["oauth_token"]
    # Make sure the app does not start from the beginning and initialize the authorization process again
    st.session_state["app_start"] = False
    # Load the consumer key and secret again because after returning from user authorization,
    # Streamlit runs in a new session where all previous variables (incl. global ones) have been lost
    st.session_state["CONSUMER_KEY"] = st.secrets["CONSUMER_KEY"]
    st.session_state["CONSUMER_SECRET"] = st.secrets["CONSUMER_SECRET"]

    # While the spinner is showing
    with st.spinner(_("Logging in", "log_in_after_oauth")):
        # Get the encrypted request token and request secret from the temporary local storage
        # as the original variable state was lost
        REQUEST_TOKEN_encrypted = localStorage.getItem("request_token")
        print("REQUEST_TOKEN_APP_encrypted type :", type(REQUEST_TOKEN_encrypted))
        print(REQUEST_TOKEN_encrypted)
        time.sleep(1)
        REQUEST_TOKEN_SECRET_encrypted = localStorage.getItem("request_token_secret")
        time.sleep(1)
        # Set the encryption/decryption key again
        fernet = Fernet(st.secrets["localStorage_key_request"])
        # Encode both encrypted token values (from string to bytes - needed for Fernet to work)
        # Decrypt the token values
        REQUEST_TOKEN_plaintext = fernet.decrypt(REQUEST_TOKEN_encrypted.encode())
        REQUEST_TOKEN_SECRET_plaintext = fernet.decrypt(REQUEST_TOKEN_SECRET_encrypted.encode())

        # Save the plain request token values as global variables
        st.session_state["REQUEST_TOKEN"] = REQUEST_TOKEN_plaintext.decode()
        st.session_state["REQUEST_TOKEN_SECRET"] = REQUEST_TOKEN_SECRET_plaintext.decode()
        # Remove the temporary local storage
        remove_local_storage_key(localStorage, "request_token")
        remove_local_storage_key(localStorage, "request_token_secret")
        print("Request Token APP:", st.session_state["REQUEST_TOKEN"])
        print("Request Secret APP:", st.session_state["REQUEST_TOKEN_SECRET"])
        # Remove the query parameters from URL as they are not useful anymore
        st.query_params.clear()
        # Exchange verify token for access token (OAuth 1.0a, Step 3: https://www.mediawiki.org/wiki/OAuth/For_Developers#)
        get_access_token_and_verify_user(localStorage)

if "privacy_policy" in st.query_params:
    if st.query_params["lang"] == "sk.wikipedia.org":
        st.subheader("Ochrana osobných údajov", divider="grey")
        st.markdown("""
        ### 1. Prístup k údajom

        Aplikácia môže získať prístup k nasledujúcim informáciám spojeným s vaším účtom Wikimedia:

        - **Používateľské meno**  
        - **Počet úprav**  
        - **Stav potvrdenia a overenia e-mailovej adresy**  
        - **Dátum registrácie účtu**  
        - **Stav zablokovania**  
        - **Používateľské skupiny**  
        - **Používateľské práva**

        Tieto údaje sú sprístupňované len v rozsahu nevyhnutnom na zabezpečenie základnej funkcionality aplikácie a **nebudú zdieľané s tretími stranami**.

        ### 2. Ukladanie údajov

        Pri prihlásení aplikácia vygeneruje OAuth tokeny, ktoré sú dočasne uložené **na lokálnom zariadení používateľa**. Tieto tokeny sú šifrované a bez príslušného šifrovacieho kľúča k nim nemajú neoprávnené osoby prístup. Tokeny zostávajú uložené lokálne, kým sa používateľ neodhlási prostredníctvom aplikácie alebo neodstráni údaje webovej stránky vo svojom prehliadači.

        Niektoré OAuth tokeny a obmedzené množstvo údajov môžu byť dočasne uložené na **infrastruktúre Streamlit Community Cloud**. Tieto údaje slúžia výlučne na udržanie globálneho stavu aplikácie počas relácie a sú vymazané po zatvorení karty prehliadača.

        ### 3. Heslo Wikimedia

        Táto aplikácia **nemá prístup k vášmu heslu k účtu Wikimedia**. Overenie používateľa prebieha bezpečne prostredníctvom protokolu Wikimedia OAuth.

        ### 4. Odvolanie prístupu k osobným údajom

        Používateľ môže kedykoľvek odvolať prístup tejto aplikácie k svojim údajom Wikimedia prostredníctvom stránky [Special:OAuthManageMyGrants](https://meta.wikimedia.org/wiki/Special:OAuthManageMyGrants).  
        Odvolanie prístupu znemožní aplikácii naďalej konať v mene používateľa.

        Táto aplikácia **neukladá žiadne používateľské údaje** do externých ani trvalých databáz.  
        Vývojár **nemá prístup** k žiadnym používateľským údajom.

        Všetky dočasne uložené údaje je možné odstrániť vymazaním údajov webovej stránky vo vašom prehliadači a zatvorením karty aplikácie.
        """)
    elif st.query_params["lang"] == "de.wikipedia.org":
        st.subheader("Datenschutzrichtlinie", divider="grey")
        st.markdown("""
        ### 1. Vom Anwendung abgerufene Daten

        Die Anwendung kann auf folgende Informationen Ihres Wikimedia-Kontos zugreifen:

        - **Benutzername**  
        - **Anzahl der Bearbeitungen**  
        - **Bestätigungs- und Verifizierungsstatus der E-Mail-Adresse**  
        - **Registrierungsdatum des Kontos**  
        - **Sperrstatus**  
        - **Benutzergruppen**  
        - **Benutzerrechte**

        Diese Daten werden ausschließlich im erforderlichen Umfang zur Bereitstellung der Kernfunktionen verwendet und **nicht an Dritte weitergegeben**.

        ### 2. Speicherung von Daten

        Beim Anmelden generiert die Anwendung OAuth-Tokens, die **vorübergehend auf dem lokalen Gerät des Nutzers** gespeichert werden. Diese Tokens sind verschlüsselt und können ohne den entsprechenden Schlüssel nicht von unbefugten Dritten gelesen werden.  
        Die Tokens verbleiben lokal gespeichert, bis sich der Nutzer über die Anwendung abmeldet oder die Website-Daten im Browser gelöscht werden.

        Bestimmte OAuth-Tokens und begrenzte Nutzerdaten können vorübergehend in der **Streamlit Community Cloud** gespeichert werden. Diese Daten dienen ausschließlich der Aufrechterhaltung des globalen Anwendungsstatus während der Sitzung und werden gelöscht, sobald der Nutzer den Browser-Tab schließt.

        ### 3. Wikimedia-Passwort

        Diese Anwendung **hat keinen Zugriff auf das Passwort Ihres Wikimedia-Kontos**. Die Authentifizierung erfolgt sicher über das OAuth-Protokoll von Wikimedia.

        ### 4. Widerruf des Zugriffs auf persönliche Daten

        Der Nutzer kann den Zugriff dieser Anwendung auf seine Wikimedia-Daten jederzeit widerrufen, indem er die Seite [Special:OAuthManageMyGrants](https://meta.wikimedia.org/wiki/Special:OAuthManageMyGrants) besucht.  
        Ein Widerruf macht es der Anwendung unmöglich, weiterhin im Namen des Nutzers zu agieren.

        Diese Anwendung **speichert keine Benutzerdaten** in externen oder persistenten Datenbanken.  
        Der Entwickler **hat keinen Zugriff** auf Benutzerdaten.

        Alle eventuell temporär gespeicherten Daten können durch das Löschen der Website-Daten im Browser und das Schließen des Browser-Tabs entfernt werden.
        """)
    else:
        st.subheader("Privacy policy", divider="grey")
        st.markdown("""
            ### 1. Data Accessed by the Application
    
            The application may access the following information associated with your Wikimedia account:
    
            - **Username**  
            - **Edit count**  
            - **Email confirmation and verification status**  
            - **Account registration date**  
            - **Blocking status**  
            - **User groups**  
            - **User rights**
    
            This data is accessed only as needed to provide core functionality and is not shared with third parties.
    
            ### 2. Data storing
            Upon login, the application generates OAuth tokens which are temporarily stored on the **user's local device**. These tokens are encrypted and cannot be accessed by unauthorized parties without the corresponding encryption key. The tokens remain stored locally until the user either logs out through the application or deletes the website data from their browser.
    
            Certain OAuth tokens and limited user data may be temporarily stored on the **Streamlit Community Cloud infrastructure**. This data is used solely to maintain global application state during the session and is deleted
            when the user closes the browser tab.
    
            ### 3. Wikimedia password
            This application does not have access to your Wikimedia account password. User authentication is handled securely
            through the Wikimedia OAuth protocol.
    
            ### 4. Revoking access to personal data
            Users may revoke this application's access to their Wikimedia data at any time by visiting [Special:OAuthManageMyGrants](https://meta.wikimedia.org/wiki/Special:OAuthManageMyGrants).  
            Revoking access will prevent the application from continuing to act on the user's behalf.
    
            This application does **not** store any user data in any external or persistent database.  
            The developer does **not** have access to any user data.
    
            Any temporarily stored data can be removed by deleting the website data from your browser and closing the application tab.
            """)
    st.session_state["app_start"] = True

# If the app just started, show intro interface
if "app_start" not in st.session_state and "logged_out" not in st.session_state:
    with st.spinner(_("Loading the tool", "tool_initial_loading")):
        # Get all saved local storage for this app
        all_local_Storage_items = localStorage.getAll()
        time.sleep(0.5)

        # If the user session is active (stored)
        if "access_token" in all_local_Storage_items and "access_token_secret" in all_local_Storage_items:
            access_token_storage = localStorage.getItem("access_token")
            access_token_secret_storage = localStorage.getItem("access_token_secret")
            if access_token_storage != "DELETED" and access_token_secret_storage != "DELETED":
                print("Access token in local storage found.")
                # Get the encrypted access token and access token secret from the temporary local storage
                ACCESS_TOKEN_encrypted = localStorage.getItem("access_token")
                time.sleep(0.2)
                ACCESS_TOKEN_SECRET_encrypted = localStorage.getItem("access_token_secret")
                time.sleep(0.2)
                ACCESS_TOKEN_WRITE_TIME_encrypted = localStorage.getItem("access_token_write_time")
                time.sleep(0.2)
                # Set the encryption/decryption key again
                fernet = Fernet(st.secrets["localStorage_key_request"])
                # Encode encrypted token values (from string to bytes - needed for Fernet to work)
                # Decrypt the token values
                ACCESS_TOKEN_plaintext = fernet.decrypt(ACCESS_TOKEN_encrypted.encode())
                ACCESS_TOKEN_SECRET_plaintext = fernet.decrypt(ACCESS_TOKEN_SECRET_encrypted.encode())
                ACCESS_TOKEN_WRITE_TIME_plaintext = fernet.decrypt(ACCESS_TOKEN_WRITE_TIME_encrypted.encode())

                # Save the plain access token values as global variables
                st.session_state["ACCESS_TOKEN"] = ACCESS_TOKEN_plaintext.decode()
                st.session_state["ACCESS_TOKEN_SECRET"] = ACCESS_TOKEN_SECRET_plaintext.decode()
                st.session_state["ACCESS_TOKEN_WRITE_TIME"] = int(ACCESS_TOKEN_WRITE_TIME_plaintext.decode())
                # Does not remove local storage as these are only removed once the user logs out

                # Verify if the session data is valid
                IDENTIFY_URL = "https://meta.wikimedia.org/w/index.php?title=Special:OAuth/identify"

                # Sign the request with OAuth1
                oauth = OAuth1(
                    client_key=st.secrets["CONSUMER_KEY"],
                    client_secret=st.secrets["CONSUMER_SECRET"],
                    resource_owner_key=st.session_state["ACCESS_TOKEN"],
                    resource_owner_secret=st.session_state["ACCESS_TOKEN_SECRET"]
                )

                # (OAuth 1.0a, Identifying the user: https://www.mediawiki.org/wiki/OAuth/For_Developers#)
                # Send request
                response = requests.get(IDENTIFY_URL, auth=oauth)

                # If the API responded
                if response.status_code == 200:
                    # Get the response body from the JSON Web Token – a signed JSON object
                    # and remove any leading/trailing whitespace
                    jwt_token = response.text.strip()

                    # Split JWT: header.payload.signature
                    try:
                        header_b64, payload_b64, signature_b64 = jwt_token.split(".")

                        # Base64 decode, with padding fix
                        def decode_segment(segment):
                            segment += "=" * (-len(segment) % 4)
                            return json.loads(base64.urlsafe_b64decode(segment))


                        # Decode a Base64URL-encoded JWT segment (header and payload) and parse it as JSON
                        header = decode_segment(header_b64)
                        payload = decode_segment(payload_b64)

                        print("JWT Header:", json.dumps(header, indent=2))
                        print("User Info:", payload)
                        st.session_state["user_data"] = payload
                        st.session_state["user_data_name"] = payload["username"]
                        print(st.session_state["user_data_name"])

                        # === Optional: validate the JWT ===
                        now = int(time.time())
                        max_session_length = 86400  # 1 day in seconds
                        if (
                                # Issuer (iss) matches the domain name of the wiki
                                payload.get("iss") == "https://meta.wikimedia.org" and
                                # Audience (aud) matches your application key
                                payload.get("aud") == st.secrets["CONSUMER_KEY"] and
                                # Issued-at time (iat) is in the past and reasonably close to current time
                                payload.get("iat", 0) <= now <= payload.get("exp", now + 1) and
                                # The login is not older than a day
                                now - st.session_state["ACCESS_TOKEN_WRITE_TIME"] <= max_session_length
                        ):
                            print("✅ Session was restored.")

                            # User the credentials from OAuth process to sign the user in in pywikibot
                            # and return the family object of the project
                            st.session_state["pywikibot_family"] = login_with_oauth_params(st.secrets["CONSUMER_KEY"],
                                                                                           st.secrets["CONSUMER_SECRET"],
                                                                                           st.session_state["ACCESS_TOKEN"],
                                                                                           st.session_state["ACCESS_TOKEN_SECRET"],
                                                                                           st.session_state["user_data_name"])

                            # Go to the home page of the app
                            st.session_state["page"] = "Choose_method"
                            # Set logged in state to true
                            st.session_state["logged_in"] = True
                            # Set logged in state to true
                            st.session_state["app_start"] = False

                        else:
                            print("❌ JWT validation failed.")
                            print(payload.get("iss") == "https://meta.wikimedia.beta.wmflabs.org")
                            print(payload.get("aud") == st.secrets["CONSUMER_KEY"])
                            print(payload.get("iat", 0) <= now <= payload.get("exp", now + 1))
                            print(payload.get("iss"))
                            # Set logged in state to true
                            st.session_state["authorization_failed"] = True
                            st.session_state["page"] = "homepage"
                            if now - st.session_state["ACCESS_TOKEN_WRITE_TIME"] >= max_session_length:
                                st.session_state["authorization_failed_inactivity"] = True

                            remove_local_storage_key(localStorage, "access_token")
                            remove_local_storage_key(localStorage, "access_token_secret")
                            remove_local_storage_key(localStorage, "access_token_write_time")
                            st.rerun()

                    except Exception as e:
                        print("Failed to decode JWT:", e)

                else:
                    print("Failed to identify user:", response.status_code, response.text)
        else:
            print("Access token in local storage NOT found.")
            st.session_state["homepage"] = True

with st.sidebar:
    if "logged_in" not in st.session_state and "privacy_policy" not in st.query_params:
        st.markdown(f"""
        <div style="
            display: flex;
            align-items: center;
            gap: 10px;
            font-family: 'Arial', sans-serif;
            font-size: 16px;
            color: #202122;
            padding: 10px 0;
        ">
          <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/7/7e/OOjs_UI_icon_userAnonymous.svg/240px-OOjs_UI_icon_userAnonymous.svg.png"
               alt="Anonymous User Icon"
               style="width: 24px; height: 24px;">
          <span>{_("Not logged in", "not_logged_in_label")}</span>
        </div>
        """, unsafe_allow_html=True)
    elif "logged_in" in st.session_state:
        st.markdown(f"""
                <div style="
                    display: flex;
                    align-items: center;
                    gap: 10px;
                    font-family: 'Arial', sans-serif;
                    font-size: 16px;
                    color: #202122;
                    padding: 10px 0;
                ">
                  <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/9/98/OOjs_UI_icon_userAvatar.svg/240px-OOjs_UI_icon_userAvatar.svg.png"
                       alt="Logged In User icon"
                       style="width: 24px; height: 24px;">
                  <span>{st.session_state["user_data_name"]}</span>
                </div>
                """, unsafe_allow_html=True)

        st.button(_("Log out", "logout_button"), on_click=log_out, key="button_70")
        st.divider()
    st.markdown("""
            <style>
            /* Style the container and input */
            div[data-testid="stSelectbox"] > div:first-child {
              position: relative;
              font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            }
            /* Target the selectbox's visible div (first child) */
            div[data-testid="stSelectbox"] > div:nth-child(25) {
                border-top: 1px solid #a2a9b1 !important;
                border-right: 1px solid #a2a9b1 !important;
                border-bottom: 1px solid #a2a9b1 !important;
                border-left-color: rgb(51, 102, 204) !important;
                border-radius: 4px !important;
                padding: 6px 36px 6px 12px !important;
                background-color: #ffffff !important;
                font-size: 16px !important;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif !important;
                color: #202122 !important;
                position: relative;
            }


            /* Target the element inside stSelectbox that includes class "st-ba" */
            div[data-testid="stSelectbox"] div[class*="st-ba"] {
                border-bottom-color: #a2a9b1 !important;
            }
            /* Target the element inside stSelectbox that includes class "st-ba" */
            div[data-testid="stSelectbox"] div[class*="st-b9"] {
                border-top-color: #a2a9b1 !important;
            }

            /* Target the element inside stSelectbox that includes class "st-ba" */
            div[data-testid="stSelectbox"] div[class*="st-b7"] {
                border-left-color: #a2a9b1 !important;
            }

            /* Target the element inside stSelectbox that includes class "st-ba" */
            div[data-testid="stSelectbox"] div[class*="st-b8"] {
                border-right-color: #ffffff !important;
            }

            div[data-testid="stSelectbox"] div[class*="st-cm"] {
                position: relative;
                padding-right: 40px; /* space for the icon */
            }

            /* Style the arrow SVG */
            div[data-testid="stSelectbox"] svg[data-baseweb="icon"] {
                position: absolute;
                right: 0px;           /* 8px inside from the right edge */
                top: 50%;
                transform: translateY(-50%);
                width: 32px;
                height: 32px;
                background-color: #f8f9fa; /* Wikimedia gray */
                border: 1px solid #a2a9b1;
                border-radius: 4px;
                padding: 4px;
                cursor: pointer;
                box-sizing: content-box;
                transition: background-color 0.2s ease;
            }

            /* Hover effect on the icon */
            div[data-testid="stSelectbox"] svg[data-baseweb="icon"]:hover {
                background-color: #d0d4d9;
            }

            div[data-testid="stSelectbox"] {
                margin-top: 0 !important;
                padding-top: 0 !important;
            }
            </style>
            """, unsafe_allow_html=True)

    st.markdown(f"""
                    <div style="
                        display: flex;
                        align-items: center;
                        gap: 10px;
                        font-family: 'Arial', sans-serif;
                        font-size: 16px;
                        color: #202122;
                        padding: 10px 0;
                    ">
                      <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/4/43/OOjs_UI_icon_language-ltr.svg/240px-OOjs_UI_icon_language-ltr.svg.png"
                           alt="Language"
                           style="width: 24px; height: 24px;">
                      <span>Current project: {st.session_state["current_language"]}</span>
                    </div>
                    """, unsafe_allow_html=True)
    try:
        if st.session_state["page"] == "Choose_method":
            pass
    except:
        st.session_state["page"] = "homepage"
    if ("homepage" in st.session_state and "logged_in" not in st.session_state) or ("logged_out" in st.session_state) or (st.session_state["page"] == "Choose_method" and "logged_in" in st.session_state):
        current_lang = st.selectbox(
            "Change to:",
            st.session_state["language_options"])
        if current_lang != st.session_state["current_language"]:
            print("Not equal: box ", current_lang, "session", st.session_state["current_language"])
            st.session_state["current_language"] = current_lang
            localStorage.setItem("language", current_lang, key=str(uuid.uuid4()))
            st.rerun()
    else:
        current_lang = st.selectbox(
             "Change to:",
            st.session_state["language_options"], disabled=True)

    if "privacy_policy" not in st.query_params:
        st.divider()
        with stylable_container(
                key="page_view_tool",
                css_styles="""
                                a[data-testid="stBaseLinkButton-secondary"] {
            padding: 0.4em 1em;
            display: inline-block;
            margin: 1em 0;
            font-size: 1rem;
            text-decoration: none;
            background-color: #f8f9fa;
            border: 1px solid #a2a9b1;
            border-radius: 0.2em;
            transition: background-color 0.2s, border-color 0.2s;
            white-space: nowrap;
        }
    
        a[data-testid="stBaseLinkButton-secondary"] p{
        font-family: Arial, sans-serif !important;
        font-weight: bold !important;
        color: #202122; !important;
        }
    
        a[data-testid="stBaseLinkButton-secondary"]:hover {
            background-color: #ffffff; !important;
            border-color: #a2a9b1 !important;
            border: 1px solid #a2a9b1 !important;
        }
    
        a[data-testid="stBaseLinkButton-secondary"]:active { /*Defines style of normal buttons when clicked over*/
            background-color: #eaecf0 !important;
            border-color: #72777d !important;
            border: 1px solid #a2a9b1 !important;
                                }
        """
        ):
            st.link_button(_("Privacy policy", "privacy_policy"),
                           f"https://adddesc.streamlit.app/?privacy_policy=true&lang={st.session_state["current_language"]}")

if "log_out" in st.session_state:
    # Delete all local storage items
    localStorage.deleteAll()
    # Clear all keys from session_state
    for key in list(st.session_state.keys()):
        del st.session_state[key]

    print(st.session_state)
    st.session_state["logged_out"] = True
    st.rerun()

if "logged_out" in st.session_state:
    st.subheader(_("You logged out", "logged_out_heading"))
    st.write(_("To log in again, refresh the tab.", "logged_out_text"))

if "homepage" in st.session_state and "logged_in" not in st.session_state:
    st.set_page_config(initial_sidebar_state="expanded")
    if "authorization_failed_message" in st.session_state:
        with stylable_container(
                key="error",
                css_styles="""
                                                /* Outer container for st.error() */
                                                div[data-testid="stAlertContainer"] {
                                                    background-color: #ffe9e5 !important;
                                                    border: 1px solid #bd6d61 !important;
                                                    border-radius: 2px !important;
                                                    padding: 16px !important;
                                                    color: #202122 !important;
                                                    font-family: "Segoe UI", "Helvetica Neue", sans-serif !important;
                                                    box-shadow: none !important;
                                                    margin: 1em 0 !important;
                                                }

                                                /* Internal layout: icon + message text */
                                                div[data-testid="stAlertContainer"] > div {
                                                    display: flex !important;
                                                    align-items: center !important;
                                                    gap: 12px !important;
                                                    padding-left: 10px !important;  /* ← Move text to right */
                                                }

                                                /* Hide default SVG icon */
                                                div[data-testid="stAlertContainer"] svg {
                                                    display: none !important;
                                                }

                                                /* Custom Codex success icon with colored circle behind */
                                                div[data-testid="stAlertContainer"]::before {
                                                    content: "";
                                                    width: 28px;
                                                    height: 28px;
                                                    display: inline-block;
                                                    flex-shrink: 0;
                                                    background-image: url("https://upload.wikimedia.org/wikipedia/commons/thumb/4/4e/OOjs_UI_icon_error-destructive.svg/240px-OOjs_UI_icon_error-destructive.svg.png");
                                                    background-repeat: no-repeat;
                                                    background-position: center;
                                                    background-size: 26px 26px;
                                                }
                        """
        ):
            if "authorization_failed_inactivity" in st.session_state:
                st.error(_("You have been logged out due to inactivity. Please log in again.",
                           "session_timeout_message"),
                         width="stretch")
            elif "authorization_failed_registration" in st.session_state:
                st.error(_("You have to be registered at least for 30 days to use this tool.",
                           "registration_issue"),
                         width="stretch")
            elif "authorization_failed_login" in st.session_state:
                st.error(_("Login failed. Please try closing this tab and reopening the application.", "login_failed_info"),
                         width="stretch")
            else:
                st.error(_("There was in issue validating session. Log in again, please.",
                           "issue_validating_session_message"),
                         width="stretch")

    # While the spinner is showing
    with st.spinner(_("Loading the tool", "tool_initial_loading")):

        # Authorize the app by sending consumer tokens and getting request tokens for user initialization
        if "authorization_setup_run_already" not in st.session_state:
            authorization_setup(localStorage)
            st.session_state["authorization_setup_run_already"] = True
        try:
            print(st.session_state["AUTHORIZE_URL"])
            col1, col2 = st.columns(2, vertical_alignment="center")
            with col2:
                with stylable_container(
                        key="centered_h3_example",
                        css_styles="""
                                h3 {
                                    text-align: center
                                }
                            """
                ):
                    st.subheader(_("Add descriptions to Wikidata more efficiently", "landing_page_heading"))
                    st.container(height=10, border=False)

            col4, col5, col6 = col1.columns([3, 8, 1])
            col5.image("front_image_resized.gif")
            col2.button(_("Log in", "log_in_button"), on_click=dialog_sign_in,
                        key="st-key-button-progressive-centered_1")
        except:
            with stylable_container(
                    key="error_request_token",
                    css_styles="""
                                                            /* Outer container for st.error() */
                                                            div[data-testid="stAlertContainer"] {
                                                                background-color: #ffe9e5 !important;
                                                                border: 1px solid #bd6d61 !important;
                                                                border-radius: 2px !important;
                                                                padding: 16px !important;
                                                                color: #202122 !important;
                                                                font-family: "Segoe UI", "Helvetica Neue", sans-serif !important;
                                                                box-shadow: none !important;
                                                                margin: 1em 0 !important;
                                                            }

                                                            /* Internal layout: icon + message text */
                                                            div[data-testid="stAlertContainer"] > div {
                                                                display: flex !important;
                                                                align-items: center !important;
                                                                gap: 12px !important;
                                                                padding-left: 10px !important;  /* ← Move text to right */
                                                            }

                                                            /* Hide default SVG icon */
                                                            div[data-testid="stAlertContainer"] svg {
                                                                display: none !important;
                                                            }

                                                            /* Custom Codex success icon with colored circle behind */
                                                            div[data-testid="stAlertContainer"]::before {
                                                                content: "";
                                                                width: 28px;
                                                                height: 28px;
                                                                display: inline-block;
                                                                flex-shrink: 0;
                                                                background-image: url("https://upload.wikimedia.org/wikipedia/commons/thumb/4/4e/OOjs_UI_icon_error-destructive.svg/240px-OOjs_UI_icon_error-destructive.svg.png");
                                                                background-repeat: no-repeat;
                                                                background-position: center;
                                                                background-size: 26px 26px;
                                                            }
                                    """
            ):
                st.error(
                    _("The app failed to initialize. Make sure you are not using VPN. Error code: REQUEST_TOKEN",
                      "initialization_error"),
                    width="stretch")

# If the user already chose the method
if "logged_in" in st.session_state:
    if st.session_state["page"] == "Choose_method":
        st.subheader(_("I want to add descriptions...", "homepage_heading"))

        col1, col2, col3 = st.columns(3)

        with col1:
            st.button(_("For pages in category", "homepage_option_1"), on_click=lambda: change_page_to(page="Category", page_step=1), use_container_width=True, key="button_1")

        with col2:
            st.button(_("For most viewed pages", "homepage_option_2"), on_click=lambda: change_page_to(page="Popular", page_step=1), use_container_width=True,
                      key="button_2")

        with col3:
            st.button(_("Prepared in a table file", "homepage_option_3"),
                      on_click=lambda: change_page_to(page="File", page_step=1), use_container_width=True,
                      key="button_32")

    # For category method
    if st.session_state["page"] == "Category":
        # For first step
        if "page_step" not in st.session_state or st.session_state["page_step"] == 1:
            st.session_state["page_step"] = 1
            st.subheader(_("Step {current_step} of {all_steps}: Choose category", "choose_category", current_step="1", all_steps="5"), divider="grey")

            col1, col2 = st.columns([9, 1])

            # Do not display verify button after successful category verification
            if "category_verified" in st.session_state and st.session_state["category_verified"] == True:
                pass
            # Display verify button if verification has not happened yet or failed
            else:
                st.session_state["category"] = col1.text_input("", placeholder=_("eg. Political parties by country", "inputbox_category_placeholder"),
                                                               key="text-input_1")
                st.session_state["subcategories_enabled"] = st.toggle(_("Include subcategories", "category_toggle"), key="toggle")
                if len(st.session_state["category"]) > 0:

                    col2.button(_("Continue", "continue"), on_click=lambda: verify_category(), key="button_3")
                elif len(st.session_state["category"]) == 0:
                    col2.button(_("Continue", "continue"), disabled=True, key="button-disabled_1")
                if st.session_state["subcategories_enabled"]:
                    st.text(_("Category depth", "subcategories_number"))
                    st.session_state["subcategory_recurse"] = st.number_input(_("Category depth", "subcategories_number"), value=1, min_value=1, max_value=5,
                                                                   key="text-input_3")

            # If category exists
            if "category_verified" in st.session_state and st.session_state["category_verified"] == True:
                with stylable_container(
                        key="success",
                        css_styles="""
                        /* Outer container for st.success() */
                        div[data-testid="stAlertContainer"] {
                            background-color: #dbf3eb !important;
                            border: 1px solid #14866d !important;
                            border-radius: 2px !important;
                            padding: 16px !important;
                            color: #202122 !important;
                            font-family: "Segoe UI", "Helvetica Neue", sans-serif !important;
                            box-shadow: none !important;
                            margin: 1em 0 !important;
                        }
                        
                        /* Internal layout: icon + message text */
                        div[data-testid="stAlertContainer"] > div {
                            display: flex !important;
                            align-items: center !important;
                            gap: 12px !important;
                            padding-left: 10px !important;  /* ← Move text to right */
                        }
                        
                        /* Hide default SVG icon */
                        div[data-testid="stAlertContainer"] svg {
                            display: none !important;
                        }
                        
                        /* Custom Codex success icon with colored circle behind */
                        div[data-testid="stAlertContainer"]::before {
                            content: "";
                            background-color: #0f9b7f;
                            border-radius: 50%;
                            width: 28px;
                            height: 28px;
                            display: inline-block;
                            flex-shrink: 0;
                            background-image: url("https://upload.wikimedia.org/wikipedia/commons/thumb/1/13/OOjs_UI_icon_check-invert.svg/240px-OOjs_UI_icon_check-invert.svg.png");
                            background-repeat: no-repeat;
                            background-position: center;
                            background-size: 16px 16px;
                        }
"""
                ):
                    st.success(_("Category **{category}** exists.", "category_exists", category=st.session_state["category"]))
                # Show continue button
                st.button(_("Continue", "continue"), on_click=lambda: change_page_to(page="Category", page_step=2), key="button_4")
            # If category does not exist
            if "category_verified" in st.session_state and st.session_state["category_verified"] == False:
                with stylable_container(
                        key="error",
                        css_styles="""
                                        /* Outer container for st.error() */
                                        div[data-testid="stAlertContainer"] {
                                            background-color: #ffe9e5 !important;
                                            border: 1px solid #bd6d61 !important;
                                            border-radius: 2px !important;
                                            padding: 16px !important;
                                            color: #202122 !important;
                                            font-family: "Segoe UI", "Helvetica Neue", sans-serif !important;
                                            box-shadow: none !important;
                                            margin: 1em 0 !important;
                                        }

                                        /* Internal layout: icon + message text */
                                        div[data-testid="stAlertContainer"] > div {
                                            display: flex !important;
                                            align-items: center !important;
                                            gap: 12px !important;
                                            padding-left: 10px !important;  /* ← Move text to right */
                                        }

                                        /* Hide default SVG icon */
                                        div[data-testid="stAlertContainer"] svg {
                                            display: none !important;
                                        }

                                        /* Custom Codex success icon with colored circle behind */
                                        div[data-testid="stAlertContainer"]::before {
                                            content: "";
                                            width: 28px;
                                            height: 28px;
                                            display: inline-block;
                                            flex-shrink: 0;
                                            background-image: url("https://upload.wikimedia.org/wikipedia/commons/thumb/4/4e/OOjs_UI_icon_error-destructive.svg/240px-OOjs_UI_icon_error-destructive.svg.png");
                                            background-repeat: no-repeat;
                                            background-position: center;
                                            background-size: 26px 26px;
                                        }
                """
                ):
                    st.error(_("Category **{category}** does not exist. Check your input.", "category_does_not_exist", category=st.session_state["invalid_category"]))

            st.button(_("Back", "back"), on_click=lambda: change_page_to(page="Choose_method", delete_1="category", delete_2="category_verified"), key="button_62")
        if st.session_state["page_step"] == 2:
            st.session_state["container_category_step_2"] = st.container()
            with st.session_state["container_category_step_2"]:
                st.subheader(_("Step {current_step} of {all_steps}: Mode choice", "choose_category_mode", current_step="2", all_steps="5"), divider="grey")
                category_chip(st.session_state["category"])
                st.container(height=25, border=False)
                #with col_category:
                #st.text(_("I want to...","choose_mode"))

                col1, col2 = st.columns(2)
                with col1:
                    st.button(_("Get generated descriptions", "category_mode1"), on_click=lambda: change_page_to(generation_type="category", page_step=3, empty="container_category_step_2"), use_container_width=True, key="button_5")
                with col2:
                    st.button(_("Add the same description to all pages", "category_mode2"), on_click=lambda: change_page_to(set_category_description=True, page_step="2a", empty="container_category_step_2"), use_container_width=True, key="button_6")

                st.session_state["max_rows_in_table_enabled"] = st.toggle(_("Limit amount of rows in table", "max_rows_table_toggle"),
                                                                      key="toggle_2")
                if st.session_state["max_rows_in_table_enabled"]:
                    st.text(_("Maximal amount of rows in table", "max_rows_table_text"))
                    st.session_state["max_rows_in_table"] = st.number_input(_("Maximal amount of rows in table", "max_rows_table_text"),
                                                                              value=100, min_value=1, max_value=1000,
                                                                              key="text-input_4")

                st.button(_("Back", "back"),
                          on_click=lambda: change_page_to(page="Category", page_step=1, delete="category_verified"),
                          key="button_61")

        if st.session_state["page_step"] == "2a":
            st.session_state["container_category_step_2a"] = st.container()
            with st.session_state["container_category_step_2a"]:
                st.subheader(_("Step 2a of 5: Enter description for all pages in category", "category_same_description"), divider="grey")
                category_chip(st.session_state["category"])
                st.container(height=25, border=False)
                col8, col9 = st.columns([8, 2])
                st.session_state["category_description"] = col8.text_input(
                    f"", key="text-input_2")
                print("Category description: ", st.session_state["category_description"])
                if len(st.session_state["category_description"]) == 0:
                    col9.button(_("Generate table", "generate_table_button"), on_click=lambda: change_page_to(generation_type="category no generation", page_step=3, empty="container_category_step_2a"), disabled=True, key="button-disabled_2")
                elif len(st.session_state["category_description"]) != 0:
                    col9.button(_("Generate table", "generate_table_button"), on_click=lambda: change_page_to(generation_type="category no generation", page_step=3, empty="container_category_step_2a"), key="button_15")
                st.button(_("Back", "back"), on_click=lambda: change_page_to(page="Category", page_step=2), key="button_63")

        if st.session_state["page_step"] == 3:
            st.subheader(_("Step {current_step} of {all_steps}: Prepare descriptions", "prepare_descriptions", current_step="3", all_steps="5"), divider="grey")
            category_chip(st.session_state["category"])
            st.container(height=25, border=False)
            if "program_run_already" not in st.session_state:
                if st.session_state["generation_type"] == "category":
                    generate_table(st.session_state["category_object"], "category")
                else:
                    generate_table(st.session_state["category_object"], "category no generation")
                st.rerun()
            else:
                st.text(
                    _("Double-click the cell with the suggested description and enter the final version.", "prepare_descriptions_instruction"))
                # Display the resulting dataframe in a form where the description is editable
                edited_table = st.data_editor(st.session_state["table"], column_config={
                    "Page name": st.column_config.TextColumn(
                        _("Page name", "table_column1"),
                        disabled=True, width="medium"
                    ),
                    "Wikidata Object": st.column_config.LinkColumn(
                        _("Wikidata", "table_column2"),
                        disabled=True, display_text=_("Item", "table_column2_show"), width="small"
                    ),
                    "Wikipedia article": st.column_config.TextColumn(
                        _("Suggested description", "table_column3"), width="large"
                    ),
                    "URL": st.column_config.LinkColumn(
                        _("Wikipedia", "table_column4"), disabled=True, display_text=_("Page", "table_column4_show"), width="small"
                    )
                }, num_rows="dynamic", column_order=("Page name", "Wikipedia article", "URL", "Wikidata Object"))
                col1, col2 = st.columns(2)
                with col1:
                    st.button(_("Back", "back"),
                              on_click=lambda: change_page_to(page="Category", page_step=2, delete="program_run_already"),
                              key="button_65")
                with col2:
                    # Create stylable container to align the button in it to the right of the column (and the page)
                    with stylable_container(
                            key="Publikovat_podpisy_category",
                            css_styles="""
                                                        button{
                                                            float: right;
                                                        }
                                                        """
                    ):
                        st.button(_("Review descriptions", "review_descriptions_button"), on_click=lambda: change_page_to(page="Category", page_step=4, table=edited_table), key="button_9")

        if st.session_state["page_step"] == 4:
            st.subheader(_("Step {current_step} of {all_steps}: Review descriptions", "review_descriptions", current_step="4", all_steps="5"), divider="grey")
            category_chip(st.session_state["category"])
            st.container(height=25, border=False)

            st.session_state["matched_descriptions_changing_information"], st.session_state["matched_descriptions_full_stop"], st.session_state["matched_descriptions_capitalized"], st.session_state["matched_descriptions_too_long"], st.session_state["matched_descriptions_first_word"], st.session_state["matched_descriptions_opinionated"] = review_descriptions()
            if (
                    len(st.session_state["matched_descriptions_changing_information"]) != 0 or
                    len(st.session_state["matched_descriptions_full_stop"]) != 0 or
                    len(st.session_state["matched_descriptions_capitalized"]) != 0 or
                    len(st.session_state["matched_descriptions_too_long"]) != 0 or
                    len(st.session_state["matched_descriptions_first_word"]) != 0 or
                    len(st.session_state["matched_descriptions_opinionated"]) != 0
            ):
                st.subheader(_("Check these potential issues","check_desc_issues"))

                container = st.container()

                st.button(_("Recheck the errors","recheck_issues_button"),
                          on_click=lambda: change_page_to(page="Category", page_step=4, table=edited_table),
                          key="button_76")

                with container:
                    show_problems()

            edited_table = st.data_editor(st.session_state["table"], column_config={
                "Page name": st.column_config.TextColumn(
                    _("Page name", "table_column1"),
                    disabled=True, width="medium"
                ),
                "Wikidata Object": st.column_config.LinkColumn(
                    _("Wikidata", "table_column2"),
                    disabled=True, display_text=_("Item", "table_column2_show"), width="small"
                ),
                "Wikipedia article": st.column_config.TextColumn(
                    _("Suggested description", "table_column3"), width="large"
                ),
                "URL": st.column_config.LinkColumn(
                    _("Wikipedia", "table_column4"), disabled=True, display_text=_("Page", "table_column4_show"),
                    width="small"
                )
            }, num_rows="dynamic", column_order=("Page name", "Wikipedia article", "URL", "Wikidata Object"))

            col1, col2 = st.columns(2)
            with col1:
                st.button(_("Edit descriptions", "edit_descriptions_button"), on_click=lambda: change_page_to(page="Category", page_step=3), key="button_10")
            with col2:
                # Create stylable container to align the button in it to the right of the column (and the page)
                with stylable_container(
                        key="publish_descriptions_category",
                        css_styles="""
                                    button{
                                        float: right;
                                    }
                                    """
                ):
                    st.button(_("Publish descriptions", "publish_descriptions_button"), on_click=lambda: change_page_to(page="Category", page_step=5), key="button-progressive_1")

        if st.session_state["page_step"] == 5:
            st.subheader(_("Step {current_step} of {all_steps}: Publishing descriptions", "publishing_descriptions", current_step="5", all_steps="5"), divider="grey")
            category_chip(st.session_state["category"])
            st.container(height=25, border=False)
            process_publish_descriptions()

    # For popular method
    if st.session_state["page"] == "Popular":
        # For first step
        if "page_step" not in st.session_state or st.session_state["page_step"] == 1:
            st.session_state["page_step"] = 1
            # Create container for widgets of step 1 page to remove them immediately after going to page 2 but before
            # finishing generating the table process
            st.session_state["container_popular_step_1"] = st.container()
            with st.session_state["container_popular_step_1"]:
                st.subheader(_("Step 1 of 4: Get list of most viewed pages", "popular_step1"), divider="grey")
                st.text(_("From the Page View Tool page, download the CSV file of the most viewed pages from the past month and upload it here.", "popular_step1_instruction"))
                with stylable_container(
                        key="page_view_tool_2",
                        css_styles="""
                                        a[data-testid="stBaseLinkButton-secondary"] {
                    padding: 0.4em 1em;
                    display: inline-block;
                    margin: 1em 0;
                    font-size: 1rem;
                    text-decoration: none;
                    background-color: #f8f9fa;
                    border: 1px solid #a2a9b1;
                    border-radius: 0.2em;
                    transition: background-color 0.2s, border-color 0.2s;
                    white-space: nowrap;
                }

                a[data-testid="stBaseLinkButton-secondary"] p{
                font-family: Arial, sans-serif !important;
                font-weight: bold !important;
                color: #202122; !important;
                }

                a[data-testid="stBaseLinkButton-secondary"]:hover {
                    background-color: #ffffff; !important;
                    border-color: #a2a9b1 !important;
                    border: 1px solid #a2a9b1 !important;
                }

                a[data-testid="stBaseLinkButton-secondary"]:active { /*Defines style of normal buttons when clicked over*/
                    background-color: #eaecf0 !important;
                    border-color: #72777d !important;
                    border: 1px solid #a2a9b1 !important;
                                        }
                """
                ):
                    st.link_button(_("Open Page View Tool", "page_view_tool_button"), f"https://pageviews.wmcloud.org/topviews/?project={__("en", "lang")}.wikipedia.org&platform=all-access&date=last-month&excludes=")

            # Add csv upload button
                st.session_state["csv"] = st.file_uploader(" ", accept_multiple_files=False, type="csv")

                st.session_state["max_rows_in_table_enabled"] = st.toggle(
                    _("Limit amount of rows in table", "max_rows_table_toggle"),
                    key="toggle_2")
                if st.session_state["max_rows_in_table_enabled"]:
                    st.text(_("Maximal amount of rows in table", "max_rows_table_text"))
                    st.session_state["max_rows_in_table"] = st.number_input(
                        _("Maximal amount of rows in table", "max_rows_table_text"),
                        value=100, min_value=1, max_value=1000,
                        key="text-input_4")
                st.button(_("Back", "back"), on_click=lambda: change_page_to(page="Choose_method"), key="button_64")

            # If user uploaded csv file
            if st.session_state["csv"] is not None and "review_descriptions" not in st.session_state:
                # Remove content of step 1 page
                st.session_state["container_popular_step_1"].empty()
                # Change to step 2 of the process so that the step 2 page gets shown
                st.session_state["page_step"] = 2
                # Rerun the code so that it goes to the page step 2
                st.rerun()

        if st.session_state["page_step"] == 2:
            st.subheader(_("Step {current_step} of {all_steps}: Prepare descriptions", "prepare_descriptions", current_step="2", all_steps="4"), divider="grey")
            # And the method has not run ýet
            if "program_run_already" not in st.session_state:
                generate_table(st.session_state["csv"], "table")
                st.rerun()
            else:
                st.text(
                    _("Double-click the cell with the suggested description and enter the final version.", "prepare_descriptions_instruction"))
                # Display the resulting dataframe in a form where the description is editable
                edited_table = st.data_editor(st.session_state["table"], column_config={
                    "Page name": st.column_config.TextColumn(
                        _("Page name", "table_column1"),
                        disabled=True, width="medium"
                    ),
                    "Wikidata Object": st.column_config.LinkColumn(
                        _("Wikidata", "table_column2"),
                        disabled=True, display_text=_("Item", "table_column2_show"), width="small"
                    ),
                    "Wikipedia article": st.column_config.TextColumn(
                        _("Suggested description", "table_column3"), width="large"
                    ),
                    "URL": st.column_config.LinkColumn(
                        _("Wikipedia", "table_column4"), disabled=True, display_text=_("Page", "table_column4_show"), width="small"
                    )
                }, num_rows="dynamic", column_order=("Page name", "Wikipedia article", "URL", "Wikidata Object"))
                # , on_change=lambda:save_edited_dataframe(edited_table)
                col1, col2 = st.columns(2)
                with col1:
                    st.button(_("Back", "back"),
                              on_click=lambda: change_page_to(page="Popular", page_step=1,
                                                              delete="program_run_already"),
                              key="button_72")
                with col2:
                    # Create stylable container to align the button in it to the right of the column (and the page)
                    with stylable_container(
                            key="review_descriptions_category",
                            css_styles="""
                                                                        button{
                                                                            float: right;
                                                                        }
                                                                        """
                    ):
                        st.button(_("Review descriptions", "review_descriptions_button"), on_click=lambda: change_page_to(page="Popular", page_step=3, table=edited_table), key="button_12")



        if st.session_state["page_step"] == 3:
            st.subheader(_("Step {current_step} of {all_steps}: Review descriptions", "review_descriptions", current_step="3", all_steps="4"), divider="grey")

            st.dataframe(st.session_state["table"], column_config={
                "Page name": st.column_config.TextColumn(
                    _("Page name", "table_column1"),
                    disabled=True, width="medium"
                ),
                "Wikidata Object": st.column_config.LinkColumn(
                    _("Wikidata", "table_column2"),
                    disabled=True, display_text=_("Item", "table_column2_show"), width="small"
                ),
                "Wikipedia article": st.column_config.TextColumn(
                    _("Suggested description", "table_column3"), width="large"
                ),
                "URL": st.column_config.LinkColumn(
                    _("Wikipedia", "table_column4"), disabled=True, display_text=_("Page", "table_column4_show"), width="small"
                )
            }, column_order=("Page name", "Wikipedia article", "URL", "Wikidata Object"))

            col1, col2 = st.columns(2)
            with col1:
                st.button(_("Edit descriptions", "edit_descriptions_button"), on_click=lambda: change_page_to(page="Popular", page_step=2), key="button_13")
            with col2:
                # Create stylable container to align the button in it to the right of the column (and the page)
                with stylable_container(
                        key="publish_descriptions_container",
                        css_styles="""
                    button{
                        float: right;
                    }
                    """
                ):
                    st.button(_("Publish descriptions", "publish_descriptions_button"), on_click=lambda: change_page_to(page="Popular", page_step=4), key="button-progressive_2")

        if st.session_state["page_step"] == 4:
            st.subheader(_("Step {current_step} of {all_steps}: Publishing descriptions", "publishing_descriptions", current_step="4", all_steps="4"), divider="grey")
            process_publish_descriptions()

    # For file method
    if st.session_state["page"] == "File":
        # For first step
        if "page_step" not in st.session_state or st.session_state["page_step"] == 1:
            st.session_state["page_step"] = 1
            # Create container for widgets of step 1 page to remove them immediately after going to page 2 but before
            # finishing generating the table process
            st.session_state["container_file_step_1"] = st.container()
            with st.session_state["container_file_step_1"]:
                st.subheader(_("Step 1 of 4: Upload table file with descriptions", "file_step1"), divider="grey")
                st.text(
                    _("The column with Wikipedia page names has to have a title 'Page' and description column 'Description'. The table has to be saved as a csv file with comma (,) as a delimiter and UTF-8 encoding.",
                      "file_step1_instruction"))

                # Add csv upload button
                st.session_state["csv"] = st.file_uploader(" ", accept_multiple_files=False, type="csv")

                st.button(_("Back", "back"), on_click=lambda: change_page_to(page="Choose_method"), key="button_64")
            st.session_state["max_rows_in_table_enabled"] = False

            # If user uploaded csv file
            if st.session_state["csv"] is not None and "review_descriptions" not in st.session_state:
                try:
                    # Check if Pandas can read the file
                    pd.read_csv(st.session_state["csv"], encoding='utf-8')
                    # Reset the file pointer to the beginning so it can be read again by pandas when generating table
                    st.session_state["csv"].seek(0)
                    # Remove content of step 1 page
                    st.session_state["container_file_step_1"].empty()
                    # Change to step 2 of the process so that the step 2 page gets shown
                    st.session_state["page_step"] = 2
                except:
                    st.session_state["page_step"] = "1error"
                # Rerun the code so that it goes to the page step 2
                st.rerun()

        if st.session_state["page_step"] == "1error":
            with stylable_container(
                    key="file_upload_error",
                    css_styles="""
                                                            /* Outer container for st.error() */
                                                            div[data-testid="stAlertContainer"] {
                                                                background-color: #ffe9e5 !important;
                                                                border: 1px solid #bd6d61 !important;
                                                                border-radius: 2px !important;
                                                                padding: 16px !important;
                                                                color: #202122 !important;
                                                                font-family: "Segoe UI", "Helvetica Neue", sans-serif !important;
                                                                box-shadow: none !important;
                                                                margin: 1em 0 !important;
                                                            }

                                                            /* Internal layout: icon + message text */
                                                            div[data-testid="stAlertContainer"] > div {
                                                                display: flex !important;
                                                                align-items: center !important;
                                                                gap: 12px !important;
                                                                padding-left: 10px !important;  /* ← Move text to right */
                                                            }

                                                            /* Hide default SVG icon */
                                                            div[data-testid="stAlertContainer"] svg {
                                                                display: none !important;
                                                            }

                                                            /* Custom Codex success icon with colored circle behind */
                                                            div[data-testid="stAlertContainer"]::before {
                                                                content: "";
                                                                width: 28px;
                                                                height: 28px;
                                                                display: inline-block;
                                                                flex-shrink: 0;
                                                                background-image: url("https://upload.wikimedia.org/wikipedia/commons/thumb/4/4e/OOjs_UI_icon_error-destructive.svg/240px-OOjs_UI_icon_error-destructive.svg.png");
                                                                background-repeat: no-repeat;
                                                                background-position: center;
                                                                background-size: 26px 26px;
                                                            }
                                    """
            ):
                st.error(_("The file you uploaded does not meet the requirements shown below. Refresh the page and try again.",
                                   "file_upload_error"),
                                 width="stretch")
                st.text(_("The column with Wikipedia page names has to have a title 'Page' and description column 'Description'. The table has to be saved as a csv file with comma (,) as a delimiter and UTF-8 encoding.",
                              "file_step1_instruction"))
                st.button(_("Back", "back"), on_click=lambda: change_page_to(page="Choose_method"), key="button_66")
        if st.session_state["page_step"] == 2:
            st.subheader(_("Step {current_step} of {all_steps}: Prepare descriptions", "prepare_descriptions",
                           current_step="2", all_steps="4"), divider="grey")
            # And the method has not run ýet
            if "program_run_already" not in st.session_state:
                generate_table(st.session_state["csv"], "file_with_descriptions")
                st.rerun()
            else:
                st.text(
                    _("Double-click the cell with the suggested description and enter the final version.",
                      "prepare_descriptions_instruction"))
                # Display the resulting dataframe in a form where the description is editable
                edited_table = st.data_editor(st.session_state["table"], column_config={
                    "Page name": st.column_config.TextColumn(
                        _("Page name", "table_column1"),
                        disabled=True, width="medium"
                    ),
                    "Wikidata Object": st.column_config.LinkColumn(
                        _("Wikidata", "table_column2"),
                        disabled=True, display_text=_("Item", "table_column2_show"), width="small"
                    ),
                    "Wikipedia article": st.column_config.TextColumn(
                        _("Suggested description", "table_column3"), width="large"
                    ),
                    "URL": st.column_config.LinkColumn(
                        _("Wikipedia", "table_column4"), disabled=True,
                        display_text=_("Page", "table_column4_show"), width="small"
                    )
                }, num_rows="dynamic", column_order=("Page name", "Wikipedia article", "URL", "Wikidata Object"))
                # , on_change=lambda:save_edited_dataframe(edited_table)
                col1, col2 = st.columns(2)
                with col1:
                    st.button(_("Back", "back"),
                              on_click=lambda: change_page_to(page="File", page_step=1,
                                                              delete="program_run_already"),
                              key="button_72")
                with col2:
                    # Create stylable container to align the button in it to the right of the column (and the page)
                    with stylable_container(
                            key="review_descriptions_category",
                            css_styles="""
                                                                        button{
                                                                            float: right;
                                                                        }
                                                                        """
                    ):
                        st.button(_("Review descriptions", "review_descriptions_button"),
                                  on_click=lambda: change_page_to(page="File", page_step=3, table=edited_table),
                                  key="button_12")

        if st.session_state["page_step"] == 3:
            st.subheader(_("Step {current_step} of {all_steps}: Review descriptions", "review_descriptions",
                           current_step="3", all_steps="4"), divider="grey")

            st.dataframe(st.session_state["table"], column_config={
                "Page name": st.column_config.TextColumn(
                    _("Page name", "table_column1"),
                    disabled=True, width="medium"
                ),
                "Wikidata Object": st.column_config.LinkColumn(
                    _("Wikidata", "table_column2"),
                    disabled=True, display_text=_("Item", "table_column2_show"), width="small"
                ),
                "Wikipedia article": st.column_config.TextColumn(
                    _("Suggested description", "table_column3"), width="large"
                ),
                "URL": st.column_config.LinkColumn(
                    _("Wikipedia", "table_column4"), disabled=True, display_text=_("Page", "table_column4_show"),
                    width="small"
                )
            }, column_order=("Page name", "Wikipedia article", "URL", "Wikidata Object"))

            col1, col2 = st.columns(2)
            with col1:
                st.button(_("Edit descriptions", "edit_descriptions_button"),
                          on_click=lambda: change_page_to(page="File", page_step=2), key="button_13")
            with col2:
                # Create stylable container to align the button in it to the right of the column (and the page)
                with stylable_container(
                        key="publish_descriptions_container",
                        css_styles="""
                    button{
                        float: right;
                    }
                    """
                ):
                    st.button(_("Publish descriptions", "publish_descriptions_button"),
                              on_click=lambda: change_page_to(page="File", page_step=4),
                              key="button-progressive_2")

        if st.session_state["page_step"] == 4:
            st.subheader(_("Step {current_step} of {all_steps}: Publishing descriptions", "publishing_descriptions",
                           current_step="4", all_steps="4"), divider="grey")
            process_publish_descriptions()

if "authorization_failed" in st.session_state:
    # Delete all local storage items
    localStorage.deleteAll()
    # Clear all keys from session_state
    for key in list(st.session_state.keys()):
        if key not in ["authorization_failed_inactivity", "authorization_failed_registration", "authorization_failed_login"]:
            del st.session_state[key]

    print(st.session_state)
    st.session_state["homepage"] = True
    st.session_state["authorization_failed_message"] = True
    st.rerun()

# URL to GitHub-hosted JSON with maintenance data
maintenance_url = "https://raw.githubusercontent.com/lukasmikulec/AddDesc_Database/refs/heads/main/maintenance.json"

# Fetch the JSON file
try:
    maintenance_response = requests.get(maintenance_url)
    data = maintenance_response.json()
    print(data)
    show_maintenance = data.get("maintenance", False)
    maintenance_date_start = data.get("date_start", "")
    maintenance_time_start = data.get("time_start", "")
    maintenance_date_end = data.get("date_end", "")
    maintenance_time_end = data.get("time_end", "")
except Exception as e:
    show_maintenance = False



# Display the banner if maintenance mode is active
if show_maintenance:
    # Add banner div
    st.markdown(f"""
        <div class="bottom-stripe">
            {_("Maintenance: from {maintenance_date_start} {maintenance_time_start} GMT until {maintenance_date_end} {maintenance_time_end} GMT. Please finish your work before as your progress will be lost.", "maintenance_text", maintenance_date_start=maintenance_date_start, maintenance_time_start=maintenance_time_start, maintenance_date_end=maintenance_date_end, maintenance_time_end=maintenance_time_end)}
        </div>
        """, unsafe_allow_html=True)
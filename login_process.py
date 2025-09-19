# For accessing st.secrets
import streamlit as st

# For logging the user in
import pywikibot

# For generating random values for widget keys which rerun in functions
import uuid

# For sending OAuth get requests to Meta
import requests

import base64
import json
import time

# For creating authentication objects passed in OAuth get requests
from requests_oauthlib import OAuth1

# For encryption/decryption of tokens which are temporarily saved in local storage
from cryptography.fernet import Fernet

from helpers import _

# For setting, accessing, and deleting local storage in the browser
from streamlit_local_storage import LocalStorage

# For creating the project object for pywikibot login
from pywikibot.family import Family

from datetime import datetime, timedelta


# Function which runs when the app is first initialized (opened in browser)
def authorization_setup(localStorage):

    # Set URL for initiating OAuth process and getting the request token and request token secret
    st.session_state["OAUTH_INITIATE_URL"] = \
        "https://meta.wikimedia.org/w/index.php?title=Special:OAuth/initiate"

    # Set URL to which the user will return after authenticating themselves
    st.session_state["CALLBACK_URL"] = "https://adddesc.streamlit.app/"

    # OAuth1 signing setup for getting the request token and request token secret
    oauth = OAuth1(
        client_key=st.secrets["CONSUMER_KEY"],
        client_secret=st.secrets["CONSUMER_SECRET"],
        callback_uri="oob"
    )

    # callback_uri=st.session_state["CALLBACK_URL"]

    # Get all local storage for this app
    all_local_Storage_items = localStorage.getAll()
    request_token_storage = localStorage.getItem("request_token")
    # Run the request for Step 1 only if this has not run before already
    # (if the process has not run yet, local storage with encrypted request token will not be saved in browser as it was
    # not yet generated)

    # (OAuth 1.0a, Step 1: https://www.mediawiki.org/wiki/OAuth/For_Developers#)
    # Make the request
    response = requests.get(st.session_state["OAUTH_INITIATE_URL"], auth=oauth, headers=st.session_state["headers"])
    print(response.text)
    # If the get request was successful
    if response.status_code == 200:
        try:
            # Extract the values (Response format: key=value&key=value)
            request_data = dict(x.split("=") for x in response.text.split("&"))
            print("Request Token PROCESS:", request_data.get("oauth_token"))
            print("Request Secret PROCESS:", request_data.get("oauth_token_secret"))
            # Store the request token and request token secret in session state (global variable)
            st.session_state["REQUEST_TOKEN"] = request_data.get("oauth_token")  # From step 1
            st.session_state["REQUEST_TOKEN_SECRET"] = request_data.get("oauth_token_secret")

            # Load encryption key from st.secrets to Fernet
            fernet = Fernet(st.secrets["localStorage_key_request"])
            print("st.session_state[REQUEST_TOKEN] type: ", type(st.session_state["REQUEST_TOKEN"]))

            # time.sleep(1)

            # Encode the token data (from string to bytes which are necessary for Fernet to work)
            # Encrypt the request token
            REQUEST_TOKEN_encrypted = fernet.encrypt(st.session_state["REQUEST_TOKEN"].encode())
            print("REQUEST_TOKEN_encrypted: ", REQUEST_TOKEN_encrypted)
            print("REQUEST_TOKEN_encrypted type: ", type(REQUEST_TOKEN_encrypted))
            # Decode the token (from bytes to string to save successfully in local storage)
            REQUEST_TOKEN_encrypted = REQUEST_TOKEN_encrypted.decode()
            print("REQUEST_TOKEN_encrypted: ", REQUEST_TOKEN_encrypted)
            print("REQUEST_TOKEN_encrypted type: ", type(REQUEST_TOKEN_encrypted))
            # Encode the token data (from string to bytes which are necessary for Fernet to work)
            # Encrypt the request token
            REQUEST_TOKEN_SECRET_encrypted = fernet.encrypt(st.session_state["REQUEST_TOKEN_SECRET"].encode())
            # Decode the token (from bytes to string to save successfully in local storage)
            REQUEST_TOKEN_SECRET_encrypted = REQUEST_TOKEN_SECRET_encrypted.decode()
            # Save encrypted request token and request token secret temporarily in local storage
            localStorage.setItem("request_token", REQUEST_TOKEN_encrypted, key=str(uuid.uuid4()))
            # time.sleep(1)
            localStorage.setItem("request_token_secret", REQUEST_TOKEN_SECRET_encrypted, key=str(uuid.uuid4()))
            # time.sleep(1)

        except Exception as e:
            print("Error parsing token response:", e)
            print(response.text)
    else:
        print("Failed to get request token:", response.status_code, response.text)

    try:
        # Construct the authorization URL which the user will be redirected to
        st.session_state["AUTHORIZE_URL"] = (
            "https://meta.wikimedia.org/wiki/Special:OAuth/authorize"
            f"?oauth_consumer_key={st.secrets["CONSUMER_KEY"]}"
            f"&oauth_token={st.session_state["REQUEST_TOKEN"]}"
        )
    except:
        pass


# Function which will get access token and use it to verify the user's identity
def get_access_token_and_verify_user(localStorage):
    # URL for get request to exchange request token for access token
    OAUTH_TOKEN_URL = "https://meta.wikimedia.org/w/index.php?title=Special:OAuth/token"

    # OAuth1 with verifier from the URL query
    oauth = OAuth1(
        client_key=st.secrets["CONSUMER_KEY"],
        client_secret=st.session_state["CONSUMER_SECRET"],
        resource_owner_key=st.session_state["REQUEST_TOKEN"],
        resource_owner_secret=st.session_state["REQUEST_TOKEN_SECRET"],
        verifier=st.session_state["OAUTH_VERIFIER"]
    )

    print("----------------------------")
    print(st.secrets["CONSUMER_KEY"])
    print(st.secrets["CONSUMER_SECRET"])
    print(st.session_state["REQUEST_TOKEN"])
    print(st.session_state["REQUEST_TOKEN_SECRET"])
    print(st.session_state["OAUTH_VERIFIER"])

    # (OAuth 1.0a, Step 3: https://www.mediawiki.org/wiki/OAuth/For_Developers#)
    # Make the request
    response = requests.get(OAUTH_TOKEN_URL, auth=oauth, headers=st.session_state["headers"])

    # If the get request was successful
    if response.status_code == 200:
        try:
            # Access the values from the API response
            access_data = dict(x.split("=") for x in response.text.split("&"))
            print("Access Token:", access_data.get("oauth_token"))
            print("Access Token Secret:", access_data.get("oauth_token_secret"))
            # Save access token and access token secret as a global variable
            st.session_state["ACCESS_TOKEN"] = access_data.get("oauth_token")
            st.session_state["ACCESS_TOKEN_SECRET"] = access_data.get("oauth_token_secret")
        except Exception as e:
            print("Error parsing access token response:", e)
    else:
        print("Failed to get access token:", response.status_code, response.text)

    # Endpoint
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
    response = requests.get(IDENTIFY_URL, auth=oauth, headers=st.session_state["headers"])

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
            registered = payload.get("registered")
            registered_time = datetime.strptime(registered, "%Y%m%d%H%M%S")

            # === Optional: validate the JWT ===
            now = int(time.time())
            now_registration = datetime.now()
            if (
                    # Issuer (iss) matches the domain name of the wiki
                    payload.get("iss") == "https://meta.wikimedia.org" and
                    # Audience (aud) matches your application key
                    payload.get("aud") == st.secrets["CONSUMER_KEY"] and
                    # Issued-at time (iat) is in the past and reasonably close to current time
                    payload.get("iat", 0) <= now <= payload.get("exp", now + 1) and
                    now_registration >= registered_time + timedelta(days=5)

            ):
                print("✅ JWT is valid.")

                # User the credentials from OAuth process to sign the user in in pywikibot and return the family object
                # of the project
                #st.session_state["pywikibot_family"] =
                login_with_oauth_params_1(st.secrets["CONSUMER_KEY"], st.secrets["CONSUMER_SECRET"], st.session_state["ACCESS_TOKEN"], st.session_state["ACCESS_TOKEN_SECRET"], st.session_state["user_data_name"])

                # Save the user session until the user logs out or the user session expires
                # Load encryption key from st.secrets to Fernet
                fernet = Fernet(st.secrets["localStorage_key_request"])

                # Encode the time at which the access token was verified when logging in
                # Encrypt this time
                ACCESS_TOKEN_WRITE_TIME_encrypted = fernet.encrypt(str(now).encode())
                # Decode the time (from bytes to string to save successfully in local storage)
                ACCESS_TOKEN_WRITE_TIME_encrypted = ACCESS_TOKEN_WRITE_TIME_encrypted.decode()

                # Encode the token data (from string to bytes which are necessary for Fernet to work)
                # Encrypt the access token
                ACCESS_TOKEN_encrypted = fernet.encrypt(st.session_state["ACCESS_TOKEN"].encode())
                # Decode the token (from bytes to string to save successfully in local storage)
                ACCESS_TOKEN_encrypted = ACCESS_TOKEN_encrypted.decode()

                # Encode the token data (from string to bytes which are necessary for Fernet to work)
                # Encrypt the access token secret
                ACCESS_TOKEN_SECRET_encrypted = fernet.encrypt(st.session_state["ACCESS_TOKEN_SECRET"].encode())
                # Decode the token (from bytes to string to save successfully in local storage)
                ACCESS_TOKEN_SECRET_encrypted = ACCESS_TOKEN_SECRET_encrypted.decode()

                # Save encrypted access token, access token secret, and write time temporarily in local storage
                localStorage.setItem("access_token", ACCESS_TOKEN_encrypted, key=str(uuid.uuid4()))
                time.sleep(0.2)
                localStorage.setItem("access_token_secret", ACCESS_TOKEN_SECRET_encrypted, key=str(uuid.uuid4()))
                time.sleep(0.2)
                localStorage.setItem("access_token_write_time", ACCESS_TOKEN_WRITE_TIME_encrypted, key=str(uuid.uuid4()))
                time.sleep(0.2)

                # Go to the home page of the app
                st.session_state["page"] = "Choose_method"
                # Set logged in state to true
                st.session_state["logged_in"] = True

            else:
                print("❌ JWT validation failed.")
                print(payload.get("iss") == "meta.wikimedia.org")
                print(payload.get("aud") == st.secrets["CONSUMER_KEY"])
                print(payload.get("iat", 0) <= now <= payload.get("exp", now + 1))
                print(payload.get("iss"))
                # Set logged in state to true
                st.session_state["authorization_failed"] = True
                if now_registration - registered_time < timedelta(days=30):
                    print("Yes")
                    st.session_state["authorization_failed_registration"] = True
                else:
                    st.session_state["authorization_failed_login"] = True

        except Exception as e:
            print("Failed to decode JWT:", e)

    else:
        print("Failed to identify user:", response.status_code, response.text)


def login_with_oauth_params(consumer_key: str, consumer_secret: str, access_token: str, access_secret: str, username: str) -> Family:
    # Step 1: Define custom family
    class MyFamily(Family):
        name = "customwiki"
        langs = {
            "en": "meta.wikimedia.beta.wmcloud.org",
        }

        def scriptpath(self, code):
            return "/w"

        def protocol(self, code):
            return "https"

    # Set config values in code
    pywikibot.config.family = "customwiki"
    pywikibot.config.mylang = "en"
    pywikibot.config.authenticate = {
        "meta.wikimedia.beta.wmcloud.org": (
            consumer_key,
            consumer_secret,
            access_token,
            access_secret
        )
    }

    # Define username for the project
    pywikibot.config.usernames["customwiki"]["en"] = username
    # Step 4: Create site and login (no browser)
    family = MyFamily()
    site = pywikibot.Site(code="en", fam=family)

    # Triggers the OAuth login
    site.login()

    # Confirm login
    print("✅ Logged in as:", site.user())

    return family

def login_with_oauth_params_1(consumer_key: str, consumer_secret: str, access_token: str, access_secret: str, username: str) -> Family:
    # Set config values in code
    pywikibot.config.family = "wikidata"
    pywikibot.config.mylang = "wikidata"
    pywikibot.config.authenticate = {
        "www.wikidata.org": (
            consumer_key,
            consumer_secret,
            access_token,
            access_secret
        )
    }

    # Define username for the project
    pywikibot.config.usernames["wikidata"]["wikidata"] = username
    site = pywikibot.Site()

    # Triggers the OAuth login
    site.login()

    # Confirm login
    print("✅ Logged in as:", site.user())

    #return family


def log_out():
    st.session_state["log_out"] = True
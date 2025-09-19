# For working with Wikipedia and Wikidata
import pywikibot
# For cleaning the wikitext from Wikipedia pages
import wikitextparser
# For working with tables
import pandas as pd
# For working with the GUI
import streamlit as st
# For styling components for them to look like Codex (Wikimedia UI)
from streamlit_extras.stylable_container import stylable_container
# For finding the end of a sentence
import regex
import re

def language_to_lang_code(current_language: str) -> str:
    #language_map = {
    #     "en.wikipedia.org": "en",
    #   "de.wikipedia.org": "de",
    #   "sk.wikipedia.org": "sk",
    #   "cs.wikipedia.org": "cs"
    #}
    language_map = st.session_state["language_map"]
    return language_map.get(current_language)

def _(en_text: str, code: str, **kwargs) -> str:
    """
    Given English text, return the translated text in the selected language.
    Falls back to English if translation is missing or empty.
    """
    lang = language_to_lang_code(st.session_state["current_language"])
    # If the current language does not have any interface translation
    if lang not in st.session_state["i18n"].columns:
        # Show the English interface
        lang = "en"  # fallback
    # Define fallback language for languages which have at least some part of interface translate
    fallback_lang = "en"

    if code in st.session_state["i18n"].index:
        # If the selected language is English, return the original text
        if lang == fallback_lang:
            return en_text.format(**kwargs)
        # Try to get the translation from the table
        translated = st.session_state["i18n"].at[code, lang]
        # If missing or blank, fall back to English
        if pd.isna(translated) or translated.strip() == "":
            return en_text
        return translated.format(**kwargs)
    # If the English text is not in the table at all, return it unchanged
    return en_text.format(**kwargs)

def __(en_text: str, code: str, **kwargs) -> str:
    """
    Given English text, return the translated text in the selected language.
    Falls back to English if translation is missing or empty.
    """
    lang = language_to_lang_code(st.session_state["current_language"])
    # Define fallback language
    fallback_lang = "en"

    if code in st.session_state["i18n_parser"].index:
        # If the selected language is English, return the original text
        if lang == fallback_lang:
            return en_text.format(**kwargs)
        # Try to get the translation from the table
        translated = st.session_state["i18n_parser"].at[code, lang]
        # If missing or blank, fall back to English
        if pd.isna(translated) or translated.strip() == "":
            return en_text
        return translated.format(**kwargs)
    # If the English text is not in the table at all, return it unchanged
    return en_text.format(**kwargs)


def change_page_to(**kwargs):
    delete_keys = {"delete", "delete_1", "delete_2", "delete_3", "delete_4", "delete_5"}
    empty_keys = {"empty", "empty_1", "empty_2", "empty_3", "empty_4", "empty_5"}
    for key, value in kwargs.items():
        if key in delete_keys:
            if value in st.session_state:
                del st.session_state[value]
        elif key in empty_keys:
            st.session_state[value].empty()

        else:
            st.session_state[key] = value

# Function to stop the loop which publishes the descriptions
def stop_adding_descriptions():
    st.session_state["stop_adding_descriptions"] = True


# Function to change number of seconds remaining to minutes and seconds
def seconds_to_minutes_and_seconds(total_seconds):
    # get number of minutes and seconds remaining with the highest possible seconds being 50
    minutes, seconds = divmod(total_seconds, 60)
    if minutes > 4:
        return _("Publishing descriptions. {minutes} minutes and {seconds} seconds remaining.", "publishing_remaining_time_5+min", minutes=minutes, seconds=seconds)
    elif minutes > 1:
        return _("Publishing descriptions. {minutes} minutes and {seconds} seconds remaining.", "publishing_remaining_time_4-2min", minutes=minutes, seconds=seconds)
    elif minutes == 1:
        return _("Publishing descriptions. {minutes} minute and {seconds} seconds remaining.", "publishing_remaining_time_1min", minutes=minutes, seconds=seconds)
    else:
        return _("Publishing descriptions. {seconds} seconds remaining.", "publishing_remaining_time_0min", seconds=seconds)


# Function for removing the Wikipedia page text after full stop
def extract_text(after_word_string, text):
    # Find the index of "je"
    start_index = text.find(after_word_string)

    if start_index != -1:
        # Add the length of "je" to get the starting point after "je"
        start_index += len(after_word_string)

        # Find the index of the first full stop after "je"
        end_index = text.find(".", start_index)

        #if end_index != -1:
            # Extract the substring
        extracted_text = text[start_index:].strip()
        if extracted_text[-1] == ".":
            extracted_text = extracted_text[:-1]
        print(extracted_text)
        return extracted_text
    #else:
            #print(f"No full stop found after '{after_word_string}'.")
            #return "Error"
    else:
        print(f"'{after_word_string}' not found in the text.")
        return "Error"


# Function for generating descriptions from Wikipedia article
def generate_description(page_name: str) -> str:
    # Defines site to get texts from
    site = pywikibot.Site(__("en", "lang"), "wikipedia")
    # Get the page based on its name
    page = pywikibot.Page(site, page_name)
    # Get page's text
    text = page.text

    # Get the clean text, strips the wikitext away
    text = wikitextparser.parse(text).sections[0].plain_text()
    # Selects only the first 400 characters
    text = text[:400]
    sentences = regex.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=[.!?])\s+(?=[A-Z])', text)
    text = sentences[0]

    extracted_text = extract_text(__(" is ", "is"), text)
    if extracted_text == "Error":
        extracted_text = extract_text(__(" was ", "was_male"), text)
        if extracted_text == "Error":
            extracted_text = extract_text(__(" was ", "was_female"), text)
            if extracted_text == "Error":
                extracted_text = extract_text(__(" was ", "was_neutrum"), text)
                if extracted_text == "Error":
                    extracted_text = extract_text(__(" are ", "are"), text)
                    if extracted_text == "Error":
                        extracted_text = extract_text(__(" were ", "were"), text)
                        if extracted_text == "Error":
                            extracted_text = text

    print(extracted_text)
    return extracted_text


# Function for generating the table with Wikipedia articles, links to them, their Wikidata entities,
# and suggested or user-inputted description
def generate_table(input: list, type_of_input: str):
    # Work with sk wikipedia
    site = pywikibot.Site(__("en", "lang"), "wikipedia")

    # For file with descriptions input
    if type_of_input == "file_with_descriptions":
        # Get dataframe from csv file
        file_df = pd.read_csv(input)
        # Get a list of article names in a list
        print(file_df.columns)
        article_list = file_df["Page"].tolist()
        # Get a list of descriptions in a list
        st.session_state["descriptions_list"] = file_df["Description"].tolist()

        # Create a list for Wikipedia Page objects
        page_list = []

        # For every page from the table
        for i in range(len(article_list)):
            # Get the pywikibot Page object of it and add it to the list of all pywikibot page objects
            page_list.append(pywikibot.Page(site, article_list[i]))


    # For table input
    if type_of_input == "table":
        # Get dataframe from csv file
        file_df = pd.read_csv(input)
        # Get a list of article names in a list
        article_list = file_df["Page"].tolist()

        # Create a list for Wikipedia Page objects
        page_list = []

        # For every page from the table
        for i in range(len(article_list)):
            # Get the pywikibot Page object of it and add it to the list of all pywikibot page objects
            page_list.append(pywikibot.Page(site, article_list[i]))

    # If the generation happens for category,
    # get the list of pages which was already generated when verifying the category
    if type_of_input == "category" or type_of_input == "category no generation":
        page_list = input

    # Define structure for the dataframe
    df_structure = {
        "Page name": [],
        "URL"
        "Wikidata Object": [],
        "Wikidata description": []}
    # Create dataframe that will store the information in a table
    processed_df = pd.DataFrame(df_structure)

    # Create lists for storing ordered information from the dataframe
    list_of_page_names = []
    list_of_URLs = []
    list_of_wikidata_objects = []
    list_of_wikidata_descriptions = []

    no_desc_list_of_page_names = []
    no_desc_list_of_wikidata_objects = []
    no_desc_list_of_wikidata_descriptions = []

    no_desc_df_structure = {
        "Page name": [],
        "Wikidata Object": []}

    # Table in which all items without Wikidata descriptions will be stored
    no_description_df = pd.DataFrame(no_desc_df_structure)

    # Add progress bar for the loading
    progress_bar = st.progress(0, text=_("Getting data and preparing table.", "getting_data_table"))

    # For every item in the uploaded csv file
    for i in range(len(page_list)):
        # Show the current table generaton progress with progress bar
        progress_bar.progress(i/(len(page_list)*2), text=_("Getting data and preparing table.", "getting_data_table"))
        # Get the page based on the article name
        page = page_list[i]
        # Get the page URL
        page_URL = page.full_url()
        # Get the Wikidata item of the Wikipedia page
        try:
            item = pywikibot.ItemPage.fromPage(page)
            # Format the Wikidata item into readable format
            item_name = str(item).replace("[[wikidata:", "")
            item_name = item_name.replace("]]", "")
            item_URL = f"https://www.wikidata.org/wiki/{item_name}"
            item_dict = item.get()
            # Get the descriptions of the Wikidata item
            item_descriptions = item_dict["descriptions"]
            # Check if there is a current project lang description in the Wikidata item
            if __("en", "lang") in item_descriptions:
                # Save it
                description = item_descriptions[__("en", "lang")]
            # If there is no current project lang description in the Wikidata item
            else:
                # Save blank description
                description = ""
            # Add article name, URL, Wikidata object and description to the lists
            list_of_page_names.append(page_list[i].title())
            list_of_URLs.append(page_URL)
            list_of_wikidata_objects.append(item_URL)
            list_of_wikidata_descriptions.append(description)

            # Add article name, URL, Wikidata object and description to the dataframe
            row = [{"Page name": page_list[i].title(), "URL": page_URL, "Wikidata Object": item,
                    "Wikidata description": description}]
            processed_df = pd.concat([processed_df, pd.DataFrame(row)], ignore_index=True)
        # If the Wikipedia page does not have a Wikidata item, show error message
        except:
            # Container to make the error message look according to Codex (Wikimedia UI)
            with stylable_container(key=f"warning_{i}",
                                    css_styles="""
                                                                    /* Outer container for st.warning() */
                                                                    div[data-testid="stAlertContainer"] {
                                                                        background-color: #fdf2d5 !important;
                                                                        border: 1px solid #b7985d !important;
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
                                                                        background-image: url("https://upload.wikimedia.org/wikipedia/commons/thumb/9/99/OOjs_UI_icon_alert-yellow.svg/240px-OOjs_UI_icon_alert-yellow.svg.png");
                                                                        background-repeat: no-repeat;
                                                                        background-position: center;
                                                                        background-size: 26px 26px;
                                                                    }
                                            """
                                    ):
                st.warning(_("The page **{page_title}** ({page_URL}) does not have a Wikidata entry. It will not be included in the table.",
                  "page_without_wikidata_object", page_title=page_list[i].title(), page_URL=page_URL), width="stretch")

    # Set row counter
    row_number = 1
    # Get dataframe of only those Wikipedia articles which have no Wikidata description
    for i in range(len(list_of_page_names)):
        # If the page has no current lang description
        if list_of_wikidata_descriptions[i] == "":
            # Show the progress using progressbar
            progress_bar.progress(0.5+i / (len(list_of_page_names)*2), text=_("Suggesting descriptions", "suggesting_descriptions"))
            # If the user already set the description, just use theirs
            if type_of_input == "category no generation":
                wikipedia_article = st.session_state["category_description"]
            # If the user already set the description in a file, just use theirs
            elif type_of_input == "file_with_descriptions":
                wikipedia_article = st.session_state["descriptions_list"][i]
            # If the user asked for automatic suggested descriptions based on the Wikipedia page
            else:
                # Get the suggested description for an item from its Wikipedia article
                wikipedia_article = generate_description(list_of_page_names[i])
            # Get all the information in a row format
            row = [{"Page name": list_of_page_names[i], "URL": list_of_URLs[i],
                    "Wikidata Object": list_of_wikidata_objects[i], "Wikipedia article": wikipedia_article}]
            # If the user set the maximum amount of rows in generated table
            if st.session_state["max_rows_in_table_enabled"]:
                # Check if there is fewer rows in the table right now than the maximum number
                if st.session_state["max_rows_in_table"] >= row_number:
                    # Add the row to the dataframe for items without Wikidata description
                    no_description_df = pd.concat([no_description_df, pd.DataFrame(row)], ignore_index=True)
                    no_desc_list_of_page_names.append(list_of_page_names[i])
                    no_desc_list_of_wikidata_objects.append(list_of_wikidata_objects[i])
                    no_desc_list_of_wikidata_descriptions.append(list_of_wikidata_descriptions[i])
                    # Increase the row counter by 1
                    row_number += 1
            # If the user did not set the maximum amount of rows in generated table,
            # add every item without current lang description
            else:
                # Add the row to the dataframe for items without Wikidata description
                no_description_df = pd.concat([no_description_df, pd.DataFrame(row)], ignore_index=True)
                no_desc_list_of_page_names.append(list_of_page_names[i])
                no_desc_list_of_wikidata_objects.append(list_of_wikidata_objects[i])
                no_desc_list_of_wikidata_descriptions.append(list_of_wikidata_descriptions[i])

    # Save that the process run and the lists into global variables
    st.session_state["program_run_already"] = True
    st.session_state["list_of_page_names"] = no_desc_list_of_page_names
    st.session_state["list_of_wikidata_objects"] = no_desc_list_of_wikidata_objects
    st.session_state["list_of_wikidata_descriptions"] = no_desc_list_of_wikidata_descriptions
    st.session_state["table"] = no_description_df


# Function for publishing the descriptions as the last step
def process_publish_descriptions():
    # Get table with descriptions for Wikidata items
    publishing_dataframe = st.session_state["table"]
    # Define site to publish the descriptions to
    site = pywikibot.Site("wikidata", "wikidata")
    # Define the repository of the site
    repo = site.data_repository()

    # If the process of publishing descriptions has not been stopped
    if "stop_adding_descriptions" not in st.session_state:
        # Display button for stopping the process of publishing descriptions
        st.button(_("Stop adding descriptions", "stop_publishing_button"), on_click=stop_adding_descriptions, key="button-destructive_1")
        # Create log for pages which were added
        st.session_state["added_descriptions_log"] = []

    # The process of adding descriptions
    # Show the process in a status box
    with st.status(_("Publishing descriptions", "publishing_text"), expanded=True, state="running") as status:
        # For each Wikidata item in the descriptions table
        for i in range(len(publishing_dataframe)):
            # If the user requested the stop of the publishing process
            if "stop_adding_descriptions" in st.session_state:
                # Skip the items left to be published
                pass
            # If the user did not request the stop of the publishing process
            else:
                # Get the Wikidata item for the item
                wikidata_item = str(publishing_dataframe["Wikidata Object"].loc[publishing_dataframe.index[i]])
                print(wikidata_item)
                # Get the defined description for the Wikidata item
                description = publishing_dataframe["Wikipedia article"].loc[publishing_dataframe.index[i]]
                # Get the page name on Wikipedia of the Wikidata item
                page_name = str(publishing_dataframe["Page name"].loc[publishing_dataframe.index[i]])

                # Compute how much time is remaining
                status_label = seconds_to_minutes_and_seconds((((len(publishing_dataframe))-i) * 10))
                # Text informing of the currently published description
                st.markdown(
                    _("Adding description **{description}** for page **{page_name}** (Wikidata item: **{wikidata_item}**)", "publishing_item", description=description, page_name=page_name, wikidata_item=wikidata_item))
                st.session_state["added_descriptions_log"].append(_("Added description **{description}** for page **{page_name}** (Wikidata item: **{wikidata_item}**)", "publishing_item_log", description=description, page_name=page_name, wikidata_item=wikidata_item))
                # Update the status box
                status.update(
                    label=status_label)
                # Get only the Q.... identifier of a Wikidata item
                wikidata_item = wikidata_item.split("/")[-1]
                # Get the Wikidata item from pywikibot
                item = pywikibot.ItemPage(repo, wikidata_item)
                # Define the new description in the right format
                new_descr = {__("en", "lang"): description}
                # Publish the description
                try:
                    #item.editDescriptions(new_descr, summary=__("en description sourced from en wiki", "summary"))
                    print(__("en description sourced from en wiki", "summary"))
                    site = pywikibot.Site("en", st.session_state["pywikibot_family"])
                    page = pywikibot.Page(site, "Test page 2")
                    text = page.text
                    text += "\n\nThis is an automated test edit, part 5."
                    page.text = text
                    page.save(summary="Adding fifth test line with Pywikibot")
                # If there occurs an error when adding the description with pywikibot
                except:
                    # Inform the user and tell them to add the description themselves
                    with stylable_container(key=f"warning_desc_add_failed_{i}",
                                            css_styles="""
                                                            /* Outer container for st.warning() */
                                                            div[data-testid="stAlertContainer"] {
                                                                background-color: #fdf2d5 !important;
                                                                border: 1px solid #b7985d !important;
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
                                                                background-image: url("https://upload.wikimedia.org/wikipedia/commons/thumb/9/99/OOjs_UI_icon_alert-yellow.svg/240px-OOjs_UI_icon_alert-yellow.svg.png");
                                                                background-repeat: no-repeat;
                                                                background-position: center;
                                                                background-size: 26px 26px;
                                                            }
                                    """
                                            ):
                        st.warning(_("Failed adding description **{description}** for page **{page_name}** (Wikidata item: **{wikidata_item}**. Add it manually, please.", "publishing_item_failed_warning", description=description, page_name=page_name, wikidata_item=wikidata_item), width="stretch")
        # If the descriptions publishing process was stopped
        if "stop_adding_descriptions" in st.session_state:
            # Inform the user in the status box
            status.update(label=_("All descriptions before the interruption were published.", "descriptions_published_stopped"), expanded=True, state="error")
            # Write all the pages which were publishing up to the point of stopping the publishing prodess
            for i in range(len(st.session_state["added_descriptions_log"])):
                st.markdown(st.session_state["added_descriptions_log"][i])
        # If the descriptions publishing process was completed
        else:
            # Inform the user
            status.update(label=_("All descriptions were published.", "all_descriptions_published"), expanded=True, state="complete")
        st.button(_("To homepage", "to_homepage"), on_click=lambda: change_page_to(page="Choose_method"), key="button_68")

def review_descriptions():
    # List of words to match
    words_changing_information = __("current,incumbent,expected,next year's,upcoming,future","words_changing_information")
    words_changing_information_list = [word.strip() for word in words_changing_information.split(",")]
    words_opinionated = ['best', 'greatest', 'luckiest']
    first_word_list = ["a", "an", "the"]

    # Build the regex pattern to match whole words
    pattern = r'\b(' + '|'.join(words_changing_information_list) + r')\b'

    # Build the regex pattern to match whole words
    pattern_opinionated = r'\b(' + '|'.join(words_opinionated) + r')\b'

    # Dictionary to store matches
    matched_descriptions_changing_information = {}
    matched_descriptions_full_stop = {}
    matched_descriptions_capitalized = {}
    matched_descriptions_too_long = {}
    matched_descriptions_first_word = {}
    matched_descriptions_opinionated = {}
    for index, row in st.session_state["table"].iterrows():
        # Case-insensitive whole word search
        if re.search(pattern, row["Wikipedia article"], re.IGNORECASE):
            matched_descriptions_changing_information[str(index)] = row["Wikipedia article"]

    for index, row in st.session_state["table"].iterrows():
        # Case-insensitive whole word search
        if re.search(pattern_opinionated, row["Wikipedia article"], re.IGNORECASE):
            matched_descriptions_opinionated[str(index)] = row["Wikipedia article"]

    for index, row in st.session_state["table"].iterrows():
        if row["Wikipedia article"][-1] == ".":
            matched_descriptions_full_stop[str(index)] = row["Wikipedia article"]

    for index, row in st.session_state["table"].iterrows():
        if row["Wikipedia article"][0].isupper():
            if st.session_state["current_language"] == "sk.wikipedia.org" or "en.wikipedia.org":
                matched_descriptions_capitalized[str(index)] = row["Wikipedia article"]

    for index, row in st.session_state["table"].iterrows():
        if len(row["Wikipedia article"].split()) > 12:
            matched_descriptions_too_long[str(index)] = row["Wikipedia article"]

    for index, row in st.session_state["table"].iterrows():
        first_word = row["Wikipedia article"].split()[0].lower()
        if first_word in first_word_list:
            matched_descriptions_first_word[str(index)] = row["Wikipedia article"]


    return matched_descriptions_changing_information, matched_descriptions_full_stop, matched_descriptions_capitalized, matched_descriptions_too_long, matched_descriptions_first_word, matched_descriptions_opinionated

def show_problems():
    if len(st.session_state["matched_descriptions_changing_information"]) != 0:
        with st.expander(_("Descriptions containing information likely to change ({count})", "description_changing_information", count=len(st.session_state["matched_descriptions_changing_information"])), icon=":material/alarm:"):
            for i in range(len(st.session_state["matched_descriptions_changing_information"])):
                key, value = list(st.session_state["matched_descriptions_changing_information"].items())[i]
                key = int(key) + 1
                st.write(_("Row {row_number}: {description}", "row_with_error", row_number=key, description=value))

    if len(st.session_state["matched_descriptions_full_stop"]) != 0:
        with st.expander(_("Descriptions with full stop at the end ({count})", "description_full_stop", count=len(st.session_state["matched_descriptions_full_stop"])), icon=":material/line_end:"):
            for i in range(len(st.session_state["matched_descriptions_full_stop"])):
                key, value = list(st.session_state["matched_descriptions_full_stop"].items())[i]
                key = int(key) + 1
                st.write(_("Row {row_number}: {description}", "row_with_error", row_number=key, description=value))

    if len(st.session_state["matched_descriptions_capitalized"]) != 0:
        with st.expander(_("Descriptions beginning with capital letter ({count})", "description_capital_letter", count=len(st.session_state["matched_descriptions_capitalized"])), icon=":material/uppercase:"):
            for i in range(len(st.session_state["matched_descriptions_capitalized"])):
                key, value = list(st.session_state["matched_descriptions_capitalized"].items())[i]
                key = int(key) + 1
                st.write(_("Row {row_number}: {description}", "row_with_error", row_number=key, description=value))

    if len(st.session_state["matched_descriptions_too_long"]) != 0:
        with st.expander(_("Lengthy descriptions with more than 12 words ({count})", "description_too_long", count=len(st.session_state["matched_descriptions_too_long"])), icon=":material/arrow_range:"):
            for i in range(len(st.session_state["matched_descriptions_too_long"])):
                key, value = list(st.session_state["matched_descriptions_too_long"].items())[i]
                key = int(key) + 1
                st.write(_("Row {row_number}: {description}", "row_with_error", row_number=key, description=value))

    if len(st.session_state["matched_descriptions_first_word"]) != 0:
        with st.expander(_("Words which usually do not appear in the beginning of a description ({count})", "description_first_word", count=len(st.session_state["matched_descriptions_first_word"])), icon=":material/text_select_move_forward_character:"):
            for i in range(len(st.session_state["matched_descriptions_first_word"])):
                key, value = list(st.session_state["matched_descriptions_first_word"].items())[i]
                key = int(key) + 1
                st.write(_("Row {row_number}: {description}", "row_with_error", row_number=key, description=value))

    if len(st.session_state["matched_descriptions_opinionated"]) != 0:
        with st.expander(_("Descriptions with opinionated, biased or promotional wording ({count})", "description_opinionated", count=len(st.session_state["matched_descriptions_opinionated"])), icon=":material/campaign:"):
            for i in range(len(st.session_state["matched_descriptions_opinionated"])):
                key, value = list(st.session_state["matched_descriptions_opinionated"].items())[i]
                key = int(key) + 1
                st.write(_("Row {row_number}: {description}", "row_with_error", row_number=key, description=value))


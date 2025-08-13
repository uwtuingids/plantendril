import streamlit as st
import pandas as pd
import random

##############################################
# GLOBAL CONFIGURATION
##############################################
st.set_page_config(page_title="Planten Driller", layout="wide")
EXCEL_PATH = "PlantenDrill.xlsx"  # Excel file in the same folder

##############################################
# HELPER FUNCTIONS FOR "PLANTEN" SHEET
##############################################
def _combine_scientific_name(row: pd.Series) -> str:
    """
    Combines Geslacht, Soort, Varieteit, Cultivar into a single scientific name.
    Example: "Geslacht Soort var. Varieteit 'Cultivar'"
    """
    parts = []
    if pd.notnull(row.get('Geslacht')):
        parts.append(str(row['Geslacht']).strip())
    if pd.notnull(row.get('Soort')):
        parts.append(str(row['Soort']).strip())
    if pd.notnull(row.get('Varieteit')):
        parts.append(f"var. {str(row['Varieteit']).strip()}")
    if pd.notnull(row.get('Cultivar')):
        parts.append(f"'{str(row['Cultivar']).strip()}'")
    return " ".join(parts).strip()

def _append_familie_to_extra_info(familie: str, extra_info: str) -> str:
    """
    Adds the Familie name into the Extra info field.
    """
    familie_str = f"Familie: {familie}."
    if pd.notnull(extra_info):
        return f"{familie_str} {extra_info}"
    else:
        return familie_str

@st.cache_data
def load_planten_data(excel_path: str, sheet_name: str = "Planten") -> pd.DataFrame:
    """
    Loads and transforms the 'Planten' sheet.
    """
    df = pd.read_excel(excel_path, sheet_name=sheet_name)
    df['Wetenschappelijke naam'] = df.apply(_combine_scientific_name, axis=1)
    if 'Nederlandse naam' in df.columns:
        df.rename(columns={'Nederlandse naam': 'Nederlands'}, inplace=True)
    if 'Familie' in df.columns and 'Extra info' in df.columns:
        df['Extra info'] = df.apply(
            lambda row: _append_familie_to_extra_info(row['Familie'], row['Extra info']),
            axis=1
        )
    if 'Nummer' not in df.columns:
        df.reset_index(drop=True, inplace=True)
        df['Nummer'] = df.index + 1
    df['Nummer'] = pd.to_numeric(df['Nummer'], errors='coerce')
    df.dropna(subset=['Nummer'], inplace=True)
    df['Nummer'] = df['Nummer'].astype(int)
    df.sort_values('Nummer', inplace=True)
    return df

def _show_photos(plant_row: pd.Series):
    """
    Displays up to 3 photos from columns "Foto 1", "Foto 2", "Foto 3",
    using the online URL base.
    """
    base_url = "http://www.symbiosa.be/Plantendrill/"
    for foto_col in ["Foto 1", "Foto 2", "Foto 3"]:
        if foto_col in plant_row.index and pd.notnull(plant_row[foto_col]):
            photo_filename = str(plant_row[foto_col]).strip()
            if photo_filename:
                photo_url = base_url + photo_filename
                st.image(photo_url, use_container_width=True, width=300)

##############################################
# FUNCTIONS FOR THE "PLANTEN DRILLER" PAGE
##############################################
def initialiseer_vraag(gefilterde_plantenlijst: pd.DataFrame):
    """
    Initializes a new question for the quiz modes.
    """
    geselecteerde_plant = gefilterde_plantenlijst.sample(1).iloc[0]
    vraagtype = random.choice(["Nederlandse naam", "Wetenschappelijke naam"])
    if vraagtype == "Nederlandse naam":
        juiste_antwoord = geselecteerde_plant["Nederlands"]
        vraag = f"Wat is de Nederlandse naam van '<i>{geselecteerde_plant['Wetenschappelijke naam']}</i>'?"
        opties = [juiste_antwoord]
        while len(opties) < 3:
            distractor = gefilterde_plantenlijst.sample(1)["Nederlands"].values[0]
            if distractor not in opties:
                opties.append(distractor)
    else:
        juiste_antwoord = geselecteerde_plant["Wetenschappelijke naam"]
        vraag = f"Wat is de wetenschappelijke naam van '{geselecteerde_plant['Nederlands']}'?"
        opties = [juiste_antwoord]
        while len(opties) < 3:
            distractor = gefilterde_plantenlijst.sample(1)["Wetenschappelijke naam"].values[0]
            if distractor not in opties:
                opties.append(distractor)
    random.shuffle(opties)
    st.session_state.update({
        'geselecteerde_plant': geselecteerde_plant,
        'vraagtype': vraagtype,
        'vraag': vraag,
        'opties': ["Selecteer een optie"] + opties,
        'juiste_antwoord': juiste_antwoord,
        'beantwoord': False,
        'gekozen_optie': "Selecteer een optie",
        'radiobutton_disabled': False
    })

def quiz_multiple_choice(gefilterde_plantenlijst: pd.DataFrame):
    """
    Multiple choice quiz mode.
    """
    if "geselecteerde_plant" not in st.session_state or st.session_state.beantwoord:
        initialiseer_vraag(gefilterde_plantenlijst)
    geselecteerde_plant = st.session_state.geselecteerde_plant
    opties = st.session_state.opties
    vraag = st.session_state.vraag
    st.title("Test kennis (Multiple choice)")
    totaal = len(gefilterde_plantenlijst)
    voortgang = st.session_state.correcte_antwoorden / (totaal if totaal else 1)
    st.progress(voortgang)
    st.write(f"Reeks correcte antwoorden: {st.session_state.correcte_antwoorden} / {totaal}")
    st.markdown(f"<h4>{vraag}</h4>", unsafe_allow_html=True)

    gebruikersantwoord = st.radio(
        "Selecteer de juiste optie:",
        opties,
        key="radio",
        disabled=st.session_state.radiobutton_disabled
    )
    if gebruikersantwoord != "Selecteer een optie" and not st.session_state.beantwoord:
        st.session_state.radiobutton_disabled = True
        juiste_antwoord = st.session_state.juiste_antwoord
        if gebruikersantwoord == juiste_antwoord:
            st.success("🎉 Correct!")
            st.session_state.correcte_antwoorden += 1
        else:
            st.error(f"❌ Fout! Het juiste antwoord was **{juiste_antwoord}**")
            st.session_state.correcte_antwoorden = 0
        st.session_state.beantwoord = True
    if st.session_state.beantwoord:
        if st.button("Volgende plant"):
            initialiseer_vraag(gefilterde_plantenlijst)
            st.session_state.radio = "Selecteer een optie"
            st.session_state.radiobutton_disabled = False
            st.session_state.beantwoord = False
    _show_photos(geselecteerde_plant)

def expert_mode(gefilterde_plantenlijst: pd.DataFrame):
    """
    Expert mode: user types in the answer.
    """
    st.title("Test kennis (Expert)")
    if "geselecteerde_plant" not in st.session_state or st.session_state.beantwoord:
        initialiseer_vraag(gefilterde_plantenlijst)
        st.session_state.expert_input = ''
    geselecteerde_plant = st.session_state.geselecteerde_plant
    vraag = st.session_state.vraag
    juiste_antwoord = st.session_state.juiste_antwoord
    totaal = len(gefilterde_plantenlijst)
    voortgang = st.session_state.correcte_antwoorden / (totaal if totaal else 1)
    st.progress(voortgang)
    st.write(f"Reeks correcte antwoorden: {st.session_state.correcte_antwoorden} / {totaal}")
    st.markdown(f"<h4>{vraag}</h4>", unsafe_allow_html=True)

    def check_antwoord():
        gebruikersantwoord = st.session_state.expert_input.strip().lower()
        juiste_norm = juiste_antwoord.strip().lower()
        if gebruikersantwoord == juiste_norm:
            st.success("🎉 Correct!")
            st.session_state.correcte_antwoorden += 1
        else:
            st.error(f"❌ Fout! Het juiste antwoord was **{juiste_antwoord}**")
            st.session_state.correcte_antwoorden = 0
        st.session_state.beantwoord = True
        st.session_state.expert_input = ''
        st.session_state.beantwoord = False
        initialiseer_vraag(gefilterde_plantenlijst)
    st.text_input(
        "Typ uw antwoord en druk op Enter:",
        value=st.session_state.expert_input,
        key='expert_input',
        on_change=check_antwoord
    )
    _show_photos(geselecteerde_plant)

def oefen_planten(gefilterde_plantenlijst: pd.DataFrame):
    """
    Practice mode: cycle through the filtered plant list.
    """
    st.title("Oefen planten")
    if gefilterde_plantenlijst.empty:
        st.warning("Geen planten gevonden in het opgegeven bereik.")
        return
    if st.session_state.reset_oefening or st.session_state.oefen_planten is None or not gefilterde_plantenlijst.equals(st.session_state.oefen_planten):
        st.session_state.oefen_planten = gefilterde_plantenlijst
        st.session_state.oefen_index = 0
        st.session_state.reset_oefening = False
    huidige_plant = st.session_state.oefen_planten.iloc[st.session_state.oefen_index]
    totaal = len(st.session_state.oefen_planten)
    st.write(f"Plant {st.session_state.oefen_index + 1} van {totaal}")
    st.markdown(f"<h2 style='font-style: italic; color: #2b7a78;'>{huidige_plant['Wetenschappelijke naam']}</h2>",
                unsafe_allow_html=True)
    st.markdown(f"<h3 style='color: #00652d;'>{huidige_plant['Nederlands']}</h3>", unsafe_allow_html=True)
    extra_info = huidige_plant.get('Extra info')
    if pd.notnull(extra_info) and extra_info.strip():
        st.info(extra_info)
    col_nav = st.columns([2, 1])
    with col_nav[1]:
        if st.button("Volgende plant"):
            if st.session_state.oefen_index < totaal - 1:
                st.session_state.oefen_index += 1
            else:
                st.session_state.oefen_index = 0
    _show_photos(huidige_plant)

def volledige_planten_lijst(gefilterde_plantenlijst: pd.DataFrame):
    """
    Displays the full (filtered) plant list.
    """
    st.title("Volledige plantenlijst")
    aantal = len(gefilterde_plantenlijst)
    st.write(f"Aantal planten in de lijst: {aantal}")
    st.dataframe(gefilterde_plantenlijst[["Nederlands", "Wetenschappelijke naam", "Familie"]])

def show_planten_driller():
    """
    The 'Planten driller' page.
    """
    df = load_planten_data(EXCEL_PATH, sheet_name="Planten")

    filter_columns = ["Inheems in West-Europa", "Invasieve exoot", "Signaalplant", "Boom", "Struik",
                      "Vaste plant", "Kruid", "Gras", "Bolgewas", "Knolgewas", "Opmerkelijke wortels"]
    chosen_plantenlijst_filter = st.sidebar.selectbox(
        "Kies een plantenlijst",
        ["Alle planten"] + filter_columns,
        key="plantenlijst_selectie"
    )
    families = sorted(df["Familie"].dropna().unique().tolist()) if "Familie" in df.columns else []
    chosen_familie_filter = st.sidebar.selectbox(
        "Kies een familie",
        ["Alle"] + families,
        key="familie_filter"
    )
    filtered_df = df.copy()
    if chosen_plantenlijst_filter != "Alle planten":
        filtered_df = filtered_df[filtered_df[chosen_plantenlijst_filter] == 'x'].copy()
    if chosen_familie_filter != "Alle":
        filtered_df = filtered_df[filtered_df["Familie"] == chosen_familie_filter].copy()
    total_plants = len(filtered_df)
    if total_plants == 0:
        st.error("Geen planten gevonden met de geselecteerde filters.")
        return
    start_nummer = st.sidebar.number_input(
        "Start bij plantnummer:",
        min_value=1,
        max_value=total_plants,
        value=1,
        step=1,
        key='start_nummer'
    )
    eind_nummer = st.sidebar.number_input(
        "Eindig bij plantnummer:",
        min_value=start_nummer,
        max_value=total_plants,
        value=total_plants,
        step=1,
        key='eind_nummer'
    )
    gefilterde_plantenlijst = filtered_df.reset_index(drop=True).iloc[start_nummer - 1 : eind_nummer]
    if 'correcte_antwoorden' not in st.session_state:
        st.session_state.correcte_antwoorden = 0
    if 'oefen_planten' not in st.session_state:
        st.session_state.oefen_planten = None
    if 'oefen_index' not in st.session_state:
        st.session_state.oefen_index = 0
    if 'reset_oefening' not in st.session_state:
        st.session_state.reset_oefening = False
    if 'expert_plant' not in st.session_state:
        st.session_state.expert_plant = None
    if 'expert_beantwoord' not in st.session_state:
        st.session_state.expert_beantwoord = False
    if 'expert_input' not in st.session_state:
        st.session_state.expert_input = ''
    st.markdown("""
        <style>
        .stProgress > div > div > div > div {
            background-color: #00652d;
        }
        [role=radiogroup]{
            gap: 1rem;
            font-size:18px;
        }
        </style>
        """, unsafe_allow_html=True)
    keuze = st.sidebar.selectbox(
        "Maak uw keuze",
        ["Oefen planten", "Bekijk volledige plantenlijst", "Test kennis (Multiple choice)", "Test kennis (Expert)"]
    )
    if keuze == "Oefen planten":
        oefen_planten(gefilterde_plantenlijst)
    elif keuze == "Bekijk volledige plantenlijst":
        volledige_planten_lijst(gefilterde_plantenlijst)
    elif keuze == "Test kennis (Multiple choice)":
        quiz_multiple_choice(gefilterde_plantenlijst)
    elif keuze == "Test kennis (Expert)":
        expert_mode(gefilterde_plantenlijst)

##############################################
# FUNCTIONS FOR THE "PLANTEN FAMILIES" PAGE
##############################################
@st.cache_data
def load_families_data(excel_path: str, sheet_name: str = "Families") -> pd.DataFrame:
    """
    Loads the 'Families' sheet.
    """
    df = pd.read_excel(excel_path, sheet_name=sheet_name)
    return df

def display_family_info(row: pd.Series):
    """
    Displays a single family's data using Streamlit's default styling.
    Each content item is placed in its own info box.
    """
    #st.write(f"Reeks correcte antwoorden: {st.session_state.correcte_antwoorden} / {totaal}")
    st.markdown(f"<h3 style='font-style: italic; color: #2b7a78;'>{row['Familie']}</h3>",
                unsafe_allow_html=True)
    st.write(f"**Beschrijving:** {row['Beschrijving']}")
    st.write(f"**Bladeren:** {row['Bladeren']}")
    st.write(f"**Bloemen:** {row['Bloemen']}")
    st.write(f"**Vruchten:** {row['Vruchten']}")


def show_planten_families():
    """
    The 'Planten families' page.
    """
    st.title("Planten Families")
    df_fam = load_families_data(EXCEL_PATH, sheet_name="Families")
    unique_families = sorted(df_fam["Familie"].dropna().unique().tolist())
    chosen_fam = st.sidebar.selectbox(
        "Kies een familie",
        ["Alle families"] + unique_families,
        key="familie_filter_families"
    )
    if chosen_fam == "Alle families":
        if "family_index" not in st.session_state:
            st.session_state.family_index = 0
        total_families = len(df_fam)
        if total_families == 0:
            st.warning("Geen families gevonden.")
            return
        current_index = st.session_state.family_index
        row = df_fam.iloc[current_index]
        display_family_info(row)
        col_left, col_right = st.columns(2)
        with col_left:
            if st.button("Vorige familie"):
                st.session_state.family_index = max(0, current_index - 1)
        with col_right:
            if st.button("Volgende familie"):
                st.session_state.family_index = min(total_families - 1, current_index + 1)
        st.write(f"Familie {current_index + 1} van {total_families}")
    else:
        subset = df_fam[df_fam["Familie"] == chosen_fam]
        if subset.empty:
            st.warning("Geen data voor deze familie.")
            return
        for idx, row in subset.iterrows():
            display_family_info(row)
            st.markdown("---")

##############################################
# MAIN APP: MENU SWITCH
##############################################
def main():
    menu_choice = st.sidebar.radio(
        "Navigatie",
        ["Planten driller", "Planten families"],
        index=0
    )
    if menu_choice == "Planten driller":
        show_planten_driller()
    else:
        show_planten_families()

if __name__ == "__main__":
    main()

import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import time

conn = st.connection('gsheets', type=GSheetsConnection)

@st.cache_data(ttl=0)
def get_scores():
    return conn.read(worksheet='Scores')

@st.cache_data(ttl=5) 
def get_players():
    df = conn.read(worksheet='Scores')
    if df.empty or 'player' not in df.columns:
        return []
    return df['player'].unique().tolist()

st.title('Scoreboard for Flip7')

tab1, tab2, tab3, tab4 = st.tabs(['Setup', 'Scoring', 'Scoreboard', 'New Game'])

@st.fragment(run_every='5s')
def display_current_players():
    players = get_players()
    if players:
        for player in players:
            st.markdown(f'👤 {player}')
        if st.button('Clear Players'):
            conn.update(
                worksheet='Scores',
                data=pd.DataFrame(columns=['player', 'score'])
            )
            st.cache_data.clear()
            st.rerun()
    else:
        st.info('No players have joined yet.')

with tab1:
    with st.form('player_form', clear_on_submit=True):
        st.subheader('Add Players')
        name = st.text_input('Enter player name:', key='add_player')
        submitted = st.form_submit_button('Add Player')

        if submitted and name:
            current_df = get_scores()
            
            if name not in current_df['player'].values:
                new_player_row = pd.DataFrame({'player': [name], 'score': [0]})
                updated_df = pd.concat([current_df, new_player_row], ignore_index=True)
                conn.update(worksheet='Scores', data=updated_df)
                st.cache_data.clear()
                st.toast(f'{name} has been added!')
            else:
                st.error(f'{name} is already playing!')

    st.subheader('Current Players')
    display_current_players()

with tab2:
    with st.form('score_form', clear_on_submit=True):
        st.subheader('Add Scores')
        player = st.selectbox(
            'Please select a player:', 
            options=get_players(), 
            index=None,
            key='select_player'
        )
        score = st.number_input('Please enter score:', value=None, key='add_score')
        submitted = st.form_submit_button('Submit Score')

        if submitted:
            if not player:
                st.error('Please select a player!')
            elif score is None:
                st.error('Please enter a score!')
            else:
                current_df = get_scores()
                row = pd.DataFrame({'player': [player], 'score': [score]})
                conn.update(
                    worksheet='Scores',
                    data=pd.concat([current_df, row], ignore_index=True)
                )
                st.cache_data.clear()
                st.toast(f'{score} added for {player}!')

@st.fragment(run_every='5s')
def live_scoreboard():
    current_scores = get_scores() 
    if not current_scores.empty:
        sum_scores = current_scores.groupby('player')['score'].sum().reset_index()
        fig, ax = plt.subplots()
        sns.barplot(
            data=sum_scores, 
            x='score', 
            y='player', 
            ax=ax,
            order=sum_scores.sort_values('score', ascending=False).player,
            hue='player',
            palette='viridis'
        )
        for container in ax.containers:
            ax.bar_label(container)
        ax.margins(x=0.075)
        plt.xlabel('Game Score')
        plt.ylabel('Player Name')
        st.pyplot(fig)
        plt.close(fig)
    else:
        st.error('Please start scoring first!')

with tab3:
    st.subheader('Scoreboard')
    live_scoreboard()

    if st.button('VICTORY'):
        st.balloons()

with tab4:
    st.subheader('New Game')

    if st.button('New Players'):
        conn.update(
            worksheet='Scores',
            data=pd.DataFrame(columns=['player', 'score'])
        )
        st.cache_data.clear()
        st.success('Game reset!')
        time.sleep(1)
        st.rerun()

    st.text(' ')

    if st.button('Same Players'):
        players = get_players()
        reset_df = pd.DataFrame({'player': players, 'score': [0] * len(players)})
        
        conn.update(worksheet='Scores', data=reset_df)
        st.cache_data.clear()
        st.success('Game reset!')
        time.sleep(1)
        st.rerun()

st.markdown('#')
st.markdown('#')
st.markdown('#')
st.markdown('##### Disclaimer')
st.write("""
    Flip7 is a trademark of USAopoly LLC. This app is an independent project 
     and is not affiliated with or endorsed by the creators of Flip7.
""")
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

@st.cache_data(ttl=0)
def get_wins():
    return conn.read(worksheet='Wins')

@st.cache_data(ttl=5) 
def get_players():
    df = conn.read(worksheet='Scores')
    if df.empty or 'player' not in df.columns:
        return []
    return df['player'].unique().tolist()

st.title('Scoreboard for Flip7')

tab1, tab2, tab3, tab4, tab5 = st.tabs(['Setup', 'Scoring', 'Scoreboard', 'Podium', 'Reset'])

@st.fragment(run_every='5s')
def display_current_players():
    players = get_players()
    if players:
        for player in players:
            st.markdown(f'👤 {player}')
        if st.button('Clear Players'):
            for sheet in ['Scores', 'Wins']:
                conn.update(
                    worksheet=sheet,
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
                for sheet in ['Scores', 'Wins']:
                    conn.update(worksheet=sheet, data=updated_df)
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
            key='select_player_score'
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
    if (current_scores['score'] != 0).any():
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
        plt.xlabel('')
        plt.ylabel('')
        st.pyplot(fig)
        plt.close(fig)

        if (sum_scores['score'] >= 200).any():
            with st.form('add_round_win', clear_on_submit=True):
                st.subheader('Add Round Win')
                player = st.selectbox(
                    'Please select a player:', 
                    options=get_players(), 
                    index=None,
                    key='select_player_win'
                )
                submitted = st.form_submit_button('Add Win')

                if submitted:
                    if not player:
                        st.error('Please select a player!')
                    else:
                        current_df = get_wins()
                        row = pd.DataFrame({'player': [player], 'score': 1})
                        conn.update(
                            worksheet='Wins',
                            data=pd.concat([current_df, row], ignore_index=True)
                        )
                        st.cache_data.clear()
                        st.toast(f'Round win added for {player}!')
    else:
        st.error('Please start scoring first!')

with tab3:
    st.subheader('Round Scoreboard')
    live_scoreboard()

@st.fragment(run_every='5s')
def live_podium():
    current_wins = get_wins() 
    sum_wins = current_wins.groupby('player')['score'].sum().reset_index()
    active_wins = sum_wins[sum_wins['score'] > 0]
    
    if not active_wins.empty:
        top_scores = active_wins['score'].nlargest(3).unique()
        podium_wins = active_wins[active_wins['score'].isin(top_scores)]
        podium_wins = podium_wins.sort_values(by='score', ascending=False)

        podium_colours = {1: '#D4AF37', 2: '#C0C0C0', 3: '#AD8A56'}
        podium_wins['rank'] = podium_wins['score'].rank(
            method='dense', ascending=False
        ).astype(int)
        current_palette = [podium_colours[r] for r in podium_wins['rank']]

        if len(podium_wins) == 3:
            podium_wins = podium_wins.iloc[[1, 0, 2]]
            current_palette = [current_palette[1], current_palette[0], current_palette[2]]
        else:
            pass

        fig, ax = plt.subplots(figsize=(6, 4))
        sns.barplot(
            data=podium_wins, 
            x='player', 
            y='score', 
            ax=ax,
            hue='player',
            legend=False,
            palette=current_palette
        )
        for container in ax.containers:
            ax.bar_label(container)
        ax.margins(y=0.075)
        plt.xlabel('')
        plt.ylabel('')
        ax.get_yaxis().set_visible(False)
        
        st.pyplot(fig)
        plt.close(fig)
    else:
        st.error('Please complete a round first!')

with tab4:
    st.subheader('Game Podium')
    live_podium()

with tab5:
    st.subheader('New Round')

    if st.button('Same Players'):
        players = get_players()
        reset_df = pd.DataFrame({'player': players, 'score': [0] * len(players)})
        
        conn.update(worksheet='Scores', data=reset_df)
        st.cache_data.clear()
        st.success('Round reset!')
        time.sleep(1)
        st.rerun()

    st.subheader('New Game')

    if st.button('New Players'):
        for sheet in ['Scores', 'Wins']:
            conn.update(
                worksheet=sheet,
                data=pd.DataFrame(columns=['player', 'score'])
            )
        st.cache_data.clear()
        st.success('Game reset!')
        time.sleep(1)
        st.rerun()

    st.text(' ')

    if st.button('Same Players', key='same_players_rnd'):
        players = get_players()
        reset_df = pd.DataFrame({'player': players, 'score': [0] * len(players)})
        
        for sheet in ['Scores', 'Wins']:
            conn.update(worksheet=sheet, data=reset_df)
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
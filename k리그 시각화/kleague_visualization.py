from flask import Flask, render_template, request
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import json
import numpy as np
import matplotlib.font_manager as fm

app = Flask(__name__)

# 한글 폰트 설정
font_path = "/Library/Fonts/Arial Unicode.ttf"  # Windows 시스템의 맑은 고딕 폰트 경로
font_name = fm.FontProperties(fname=font_path).get_name()

# 데이터 로드 및 전처리
file_path = r"/Users/yuyeoeun/Downloads/k리그 시각화/kleague_ratings.csv"
kleague_ratings = pd.read_csv(file_path, encoding='cp949')

# NaN 값을 빈 딕셔너리로 변환
kleague_ratings['Elo_Ratings_Basic'] = kleague_ratings['Elo_Ratings_Basic'].apply(lambda x: '{}' if pd.isna(x) else x)
kleague_ratings['Elo_Ratings_Attack'] = kleague_ratings['Elo_Ratings_Attack'].apply(lambda x: '{}' if pd.isna(x) else x)
kleague_ratings['Elo_Ratings_Defense'] = kleague_ratings['Elo_Ratings_Defense'].apply(lambda x: '{}' if pd.isna(x) else x)
kleague_ratings['Player_Stats_포지션'] = kleague_ratings['Player_Stats_포지션'].apply(lambda x: '{}' if pd.isna(x) else x)

# JSON 변환
kleague_ratings['Elo_Ratings_Basic'] = kleague_ratings['Elo_Ratings_Basic'].apply(lambda x: json.loads(x.replace("'", '"')))
kleague_ratings['Elo_Ratings_Attack'] = kleague_ratings['Elo_Ratings_Attack'].apply(lambda x: json.loads(x.replace("'", '"')))
kleague_ratings['Elo_Ratings_Defense'] = kleague_ratings['Elo_Ratings_Defense'].apply(lambda x: json.loads(x.replace("'", '"')))
kleague_ratings['Player_Stats_포지션'] = kleague_ratings['Player_Stats_포지션'].apply(lambda x: json.loads(x.replace("'", '"')))

def quantile_score(value, series):
    return (series < value).mean()

def plot_top_n_players(year, round, top_n):
    filtered_data = kleague_ratings[(kleague_ratings['year'] == year) & (kleague_ratings['Rnd'] == round)]

    # 모든 선수들의 기본, 공격, 수비 레이팅을 하나의 데이터프레임으로 변환
    ratings_data = []
    for idx, row in filtered_data.iterrows():
        for player, basic_rating in row['Elo_Ratings_Basic'].items():
            attack_rating = row['Elo_Ratings_Attack'].get(player, np.nan)
            defense_rating = row['Elo_Ratings_Defense'].get(player, np.nan)
            ratings_data.append([player, basic_rating, attack_rating, defense_rating])

    ratings_df = pd.DataFrame(ratings_data, columns=['Player', 'Basic_Rating', 'Attack_Rating', 'Defense_Rating'])

    # 기본 레이팅으로 상위 N명 선택
    top_n_players = ratings_df.nlargest(top_n, 'Basic_Rating')

    # 시각화
    fig = px.bar(top_n_players, x='Player', y=['Basic_Rating', 'Attack_Rating', 'Defense_Rating'],
                 title=f'{year}년 {round} 라운드 상위 {top_n}명의 플레이어 레이팅',
                 labels={'value': 'Rating', 'variable': 'Rating Type'},
                 barmode='group')

    fig.update_layout(
        title={'x':0.5, 'xanchor': 'center'},
        xaxis_title='Player',
        yaxis_title='Rating',
        font=dict(family=font_name, size=16)
    )

    graph_html = fig.to_html(full_html=False)
    return graph_html, None

def plot_player_ratings(player_name, year, round):
    filtered_data = kleague_ratings[(kleague_ratings['year'] == year) & (kleague_ratings['Rnd'] == round)]

    player_position = None
    for stats in filtered_data['Player_Stats_포지션']:
        if player_name in stats:
            player_position = stats[player_name]
            break

    if not player_position:
        return None, "선수 데이터를 찾을 수 없습니다."

    # 동일 포지션의 선수들만 필터링
    same_position_data = filtered_data[filtered_data['Player_Stats_포지션'].apply(lambda x: player_position in x.values())]

    # 동일 포지션 선수들의 레이팅 데이터 모으기
    all_basic_ratings = []
    all_attack_ratings = []
    all_defense_ratings = []

    for idx, row in same_position_data.iterrows():
        for player, rating in row['Elo_Ratings_Basic'].items():
            if row['Player_Stats_포지션'][player] == player_position:
                all_basic_ratings.append(rating)
        for player, rating in row['Elo_Ratings_Attack'].items():
            if row['Player_Stats_포지션'][player] == player_position:
                all_attack_ratings.append(rating)
        for player, rating in row['Elo_Ratings_Defense'].items():
            if row['Player_Stats_포지션'][player] == player_position:
                all_defense_ratings.append(rating)

    all_basic_ratings = pd.Series(all_basic_ratings)
    all_attack_ratings = pd.Series(all_attack_ratings)
    all_defense_ratings = pd.Series(all_defense_ratings)

    if all_basic_ratings.empty or all_attack_ratings.empty or all_defense_ratings.empty:
        return None, "동일 포지션의 선수 데이터를 찾을 수 없습니다."

    current_basic_rating = None
    current_attack_rating = None
    current_defense_rating = None

    for stats in filtered_data['Elo_Ratings_Basic']:
        if player_name in stats:
            current_basic_rating = stats[player_name]
            break

    for stats in filtered_data['Elo_Ratings_Attack']:
        if player_name in stats:
            current_attack_rating = stats[player_name]
            break

    for stats in filtered_data['Elo_Ratings_Defense']:
        if player_name in stats:
            current_defense_rating = stats[player_name]
            break

    basic_quantile = quantile_score(current_basic_rating, all_basic_ratings) * 10
    attack_quantile = quantile_score(current_attack_rating, all_attack_ratings) * 10
    defense_quantile = quantile_score(current_defense_rating, all_defense_ratings) * 10

    fig = go.Figure()

    categories = ['Attack', 'Defense', 'Basic']
    values = [attack_quantile, defense_quantile, basic_quantile]

    fig.add_trace(go.Scatterpolar(
        r=values,
        theta=categories,
        fill='toself',
        line=dict(color='rgba(44, 160, 44, 0.8)')
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 10]
            )),
        showlegend=False,
        title=f'{player_name}의 레이팅',
        font=dict(family=font_name, size=16)
    )

    graph_html = fig.to_html(full_html=False)
    return graph_html, None

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/top-players', methods=['POST'])
def top_players():
    year = int(request.form['year'])
    round = int(request.form['round'])
    top_n = int(request.form['top_n'])
    graph_html, error = plot_top_n_players(year, round, top_n)
    
    if error:
        return render_template('error.html', error=error)
    
    return render_template('top_players.html', graph_html=graph_html, year=year, round=round, top_n=top_n)

@app.route('/player-rating', methods=['POST'])
def player_rating():
    player_name = request.form['player_name']
    year = int(request.form['year'])
    round = int(request.form['round'])
    graph_html, error = plot_player_ratings(player_name, year, round)
    
    if error:
        return render_template('error.html', error=error)
    
    return render_template('player_rating.html', graph_html=graph_html, player_name=player_name, year=year, round=round)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5005)


from flask import Flask, request, render_template
from flask_cors import CORS
import pymysql
import pandas as pd
from sqlalchemy import create_engine, text
import time
import re

#local로 돌릴려면 컴터에 미리 docker를 깔고 docker compose up -d mariadb 쳐야함
#리눅스에서는 docker compose up -d --build 치면 firefox로 웹 확인가능

app = Flask(__name__)   #플라스크 앱 생성
CORS(app)

def get_db_connection():
    return pymysql.connect(        #************중요************ 로컬/도커 마다 host 바꿔주기
        host='mariadb',    #도커에서 실행할 때
        #host='127.0.0.1',    #python에서 실행할 때
        port=3307,
        user='root',
        password='1234',
        db='recipe_db',
        charset='utf8'
    )

def init_db():
    for i in range(5):
        try:                                                             #***********중요********** 로컬/도커마다 주소 바꿔주기
            engine = create_engine('mysql+pymysql://root:1234@mariadb:3306/recipe_db')     #docker에서 돌릴 때 사용
            #engine = create_engine('mysql+pymysql://root:1234@127.0.0.1:3307/recipe_db')      #로컬에서 돌릴 때 사용
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            break
        except:
            print(f"DB 대기 중...({i}/5)")
            time.sleep(3)

    with engine.connect() as conn:
        try:
            count = conn.execute(text("SELECT COUNT(*) FROM recipe")).scalar()
            if count > 0:
                print("이미 데이터 있음 -스킵")
                return engine
        except:
            pass


    df0 = pd.read_csv("recipe_data.csv")
    df = df0.drop(axis=1,labels=["링크", "기본 조리도구", "추가 조리도구"], inplace=False)
    df.dropna(axis=1, how='all', inplace=True)
    df.drop(axis=0, labels=74, inplace=True)        #마지막행 NaN 지우기 

    df.to_sql(name='recipe', con=engine, if_exists='append', index=False)
    return engine

engine = init_db()


@app.route('/')
def home():
    return render_template('init.html')

# 1. 재료 선택 페이지 라우팅
@app.route('/select_ingredients')
def select_ingredients():
    ingredients_list = []
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT 재료 FROM recipe")
        result_rows = cursor.fetchall()
        
        ingredients_set = set()
        for row in result_rows:
            if row and row.get('재료'):
                for item in row['재료'].split(','):
                    cleaned = item.strip()
                    if cleaned:
                        ingredients_set.add(cleaned)
        ingredients_list = [{'id': idx, 'name': name} for idx, name in enumerate(sorted(list(ingredients_set)))]
        conn.close()
    except Exception as e:
        print(f"❌ 재료 목록 로드 중 에러 발생: {e}")
        ingredients_list = []

    return render_template('select_ingredients.html', ingredients=ingredients_list)

# 2. 💡 추천 레시피 결과 페이지 라우팅 (/recipe_list로 매핑 완료)
@app.route('/recipe_list')
def recipe_list_page():
    recipes_list = []
    try:
        # select_ingredients.html의 form 태그를 통해 넘어온 체크된 재료 리스트를 받습니다.
        selected_ingredients = request.args.getlist('ingredients')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 실시간 필터링을 위한 전체 레시피 명단과 세부 열 정보 가져오기
        cursor.execute("SELECT 레시피명, 재료, 조리도구, `식사/간식`, 링크 FROM recipe")
        all_recipes = cursor.fetchall()
        
        for row in all_recipes:
            if row:
                recipe_ingredients = row.get('재료', '')
                
                # 💡 필터링 조건: 사용자가 재료를 하나도 선택하지 않았으면 전체 출력, 
                # 재료를 선택했다면 그 중 하나라도 레시피 재료 열에 포함되어 있는 경우에만 리스트에 추가합니다.
                is_matched = False
                if len(selected_ingredients) == 0:
                    is_matched = True
                else:
                    for ing in selected_ingredients:
                        if ing in recipe_ingredients:
                            is_matched = True
                            break
                
                if is_matched:
                    recipes_list.append({
                        'name': row.get('레시피명', '이름 없는 레시피'),
                        'ingredients': recipe_ingredients,
                        'tools': row.get('조리도구', '-'),
                        'category': row.get('식사/간식', '식사'),
                        'link': row.get('링크', '#')
                    })
        conn.close()
    except Exception as e:
        print(f"❌ 레시피 목록 로드 중 에러 발생: {e}")
        recipes_list = []

    return render_template('recipe_list.html', recipes=recipes_list)

if __name__ == '__main__':
  app.run(host='0.0.0.0', port = 5000, debug = True)    #이미 점유되어 있으면 5001로 돌려보기

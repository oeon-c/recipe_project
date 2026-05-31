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
def index():
    return render_template('init.html')

@app.route('/select_ingredients')
def select_ingredients():
    ingredients_set = set()
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 재료 FROM recipe"))
        for row in result:
            if row[0]: 
                items = row[0].split(',')
                for item in items:
                    cleaned = item.strip()
                    cleaned = re.sub(r'\s*\d+(\.\d+)?(스푼|개|모|봉|g|컵|T|장|알|주먹|봉지|줄|큰술|티스푼|줌|단|대)?$', '', cleaned)
                    cleaned = cleaned.strip()
                    if cleaned and not cleaned.startswith('*'):
                        ingredients_set.add(cleaned)
    ingredients_list = [{'id': idx, 'name': name} for idx, name in enumerate(sorted(list(ingredients_set)))]

    return render_template('recipe_ingredients.html', ingredients=ingredients_list)

if __name__ == '__main__':
  app.run(host='0.0.0.0', port = 5000, debug = True)    #이미 점유되어 있으면 5001로 돌려보기

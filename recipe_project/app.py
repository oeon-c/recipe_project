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

@app.route('/select_ingredients')
def select_ingredients():
    ingredients_list = []
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. 단수형 테이블(recipe)에서 데이터 조회
        cursor.execute("SELECT DISTINCT 재료 FROM recipe")
        result_rows = cursor.fetchall()
        
        # 가상머신 터미널에서 데이터가 제대로 넘어오는지 실시간 확인용 로그
        print(f"=== [디버깅] DB 원본 데이터 추출 결과: {result_rows} ===")
        
        ingredients_set = set()
        for row in result_rows:
            # 💡 DictCursor 특성상 대소문자나 공백에 의해 키값이 다를 수 있으므로 검증
            # row가 딕셔너리 형태가 맞는지, '재료' 키가 존재하는지 체크합니다.
            if row and isinstance(row, dict) and row.get('재료'):
                # 쉼표(,)로 구분된 재료들을 분리하여 공백을 제거하고 세트에 추가
                for item in row['재료'].split(','):
                    cleaned = item.strip()
                    if cleaned:
                        ingredients_set.add(cleaned)
                        
        # 2. 💡 HTML 템플릿의 {% for ingredient in ingredients %} 문법과 100% 일치하도록 딕셔너리 리스트 구조화
        ingredients_list = [{'id': idx, 'name': name} for idx, name in enumerate(sorted(list(ingredients_set)))]
        conn.close()
        
        print(f"=== [디버깅] HTML로 전달할 최종 가공 데이터: {ingredients_list} ===")
        
    except Exception as e:
        # 💡 화면이 비어있을 때 터미널에서 진짜 원인을 잡아내기 위한 구문
        print(f"❌ [에러 리포트] 전체 재료 목록 로드 중 치명적 실패: {e}")
        ingredients_list = []

    # 3. HTML 템플릿의 변수명 'ingredients'와 정확히 매치하여 렌더링 리턴
    return render_template('select_ingredients.html', ingredients=ingredients_list)

@app.route('/recipe_list')
def recipe_list_page():
    recipes_list = []
    try:
        # 💡 HTML 주소창 뒤에 붙어온 선택 재료 리스트를 파이썬 리스트로 안전하게 수집합니다.
        selected_ingredients = request.args.getlist('ingredients')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 전체 레시피 명단과 세부 정보 조회 (단수형 테이블 recipe 반영 완료)
        cursor.execute("SELECT 레시피명, 재료, 조리도구, `식사/간식`, 링크 FROM recipe")
        all_recipes = cursor.fetchall()
        
        for row in all_recipes:
            if row:
                recipe_ingredients = row.get('재료', '')
                
                # 사용자가 재료를 하나도 선택하지 않은 상태로 넘어왔다면 조건 없이 전체 출력 처리,
                # 재료를 골랐다면 그 중 하나라도 포함된 요리만 매핑 처리
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
        print(f"❌ 레시피 목록 로드 중 진짜 에러 발생: {e}")
        recipes_list = []

    # 최종 필터링 완료된 명단을 결과 페이지(recipe_list.html)로 전달합니다.
    return render_template('recipe_list.html', recipes=recipes_list)

if __name__ == '__main__':
  app.run(host='0.0.0.0', port = 5000, debug = True)    #이미 점유되어 있으면 5001로 돌려보기

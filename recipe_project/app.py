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
    return pymysql.connect(
        host='mariadb',
        #host='127.0.0.1',
        port=3306,
        user='root',
        password='1234',
        database='recipe_db',
        charset='utf8',  # 💡 쉼표(,) 추가 완료
        cursorclass=pymysql.cursors.DictCursor
    )

def init_db():
    engine = None
    db_url = 'mysql+pymysql://root:1234@mariadb:3306/recipe_db'

    for i in range(5):
        try:
            engine = create_engine(db_url)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("✅ 데이터베이스 엔진 연결 성공!")
            break
        except Exception as conn_err:
            print(f"DB 대기 중...({i+1}/5) 원인: {conn_err}")
            time.sleep(3)

    if engine is None:
        print("❌ DB 연결에 최종 실패했습니다.")
        return None

    try:
        with engine.connect() as conn:
            count = conn.execute(text("SELECT COUNT(*) FROM recipe")).scalar()
            if count > 0:
                print("이미 데이터 있음 - 스킵")
                return engine
    except Exception as table_err:
        print(f"테이블 체크 중 참고사항: {table_err}")

    try:
        df0 = pd.read_csv("recipe_data.csv")
        
        # 💡 지우거나 이름을 바꾸지 않고 불필요한 행 정돈 및 전체 열 유지
        df = df0.dropna(axis=1, how='all', inplace=False)
        df = df.dropna(subset=['레시피명'])

        # 테이블을 새로 생성하면서 데이터 적재
        df.to_sql(name='recipe', con=engine, if_exists='replace', index=False)
        print("✅ 원본 열 구조 그대로 recipe 테이블 적재 완료!")
        
    except Exception as data_err:
        print(f"❌ CSV 데이터 가공 및 적재 중 에러 발생: {data_err}")
        
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
    selected_ingredients = []
    try:
        # GET 요청으로 넘어온 선택 재료 리스트 수집
        selected_ingredients = request.args.getlist('ingredients')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT 레시피명, 재료, `기본 조리도구`, `추가 조리도구`, `식사/간식`, 링크 FROM recipe")
        all_recipes = cursor.fetchall()
        
        for row in all_recipes:
            if row:
                # DB의 값이 NULL(None)일 경우 파이썬 에러를 막기 위해 'or' 구문으로 빈 문자열 대체
                recipe_ingredients = row.get('재료') or ''
                
                is_matched = False
                if len(selected_ingredients) == 0:
                    is_matched = True
                else:
                    for ing in selected_ingredients:
                        # 재료가 포함되어 있는지 검사
                        if ing in recipe_ingredients:
                            is_matched = True
                            break
                            
                if is_matched:
                    recipes_list.append({
                        'name': row.get('레시피명') or '이름 없는 레시피',
                        'ingredients': recipe_ingredients,
                        'basic_tools': row.get('기본 조리도구') or '-',
                        'extra_tools': row.get('추가 조리도구') or '-',
                        'category': row.get('식사/간식') or '식사',
                        'link': row.get('링크') or '#'
                    })
        conn.close()
        
        # 터미널 디버깅용 로그
        print(f"=== [디버깅] 선택된 재료 수신: {selected_ingredients} ===")
        print(f"=== [디버깅] 매칭된 레시피 갯수: {len(recipes_list)} ===")

    except Exception as e:
        print(f"❌ 레시피 목록 로드 중 진짜 에러 발생: {e}")
        recipes_list = []

    # HTML 템플릿으로 레시피 목록과 사용자가 선택한 재료 목록을 함께 전달합니다.
    return render_template('recipe_list.html', recipes=recipes_list, selected_ingredients=selected_ingredients)

if __name__ == '__main__':
  app.run(host='0.0.0.0', port = 5000, debug = True)    #이미 점유되어 있으면 5001로 돌려보기

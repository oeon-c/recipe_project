from flask import Flask, request, render_template
from flask_cors import CORS
import pymysql
import pandas as pd
from sqlalchemy import create_engine, text
import time
import re
import json

app = Flask(__name__)   #플라스크 앱 생성
CORS(app)


#==========데이터 불러오기=============
#1. mariadb 가져오기
def get_db_connection():
    return pymysql.connect(
        host='mariadb',    #도커에서 실행할 때
        #host='127.0.0.1',    #python에서 
        port=3307,
        user='root',
        password='1234',
        db='recipe_db',
        charset='utf8'
    )


def init_db():
    #2. 엔진 만들기 
    for i in range(5):
        try:
            engine = create_engine('mysql+pymysql://root:1234@mariadb:3306/recipe_db')     #docker에서 돌릴 때 사용
            #engine = create_engine('mysql+pymysql://root:1234@127.0.0.1:3307/recipe_db')      #로컬에서 돌릴 때 사용
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            break
        except:
            print(f"DB 대기 중...({i}/5)")
            time.sleep(3)
            

    #3. csv를 판다스 dataframe으로 불러오기
    df = pd.read_csv("recipe_data6.csv")
    df.to_sql(name='recipe', con=engine, if_exists='replace', index=False)

    
    #4. 엔진으로 df와 db 연결
    with engine.connect() as conn:
        try:
            count = conn.execute(text("SELECT COUNT(*) FROM recipe")).scalar()
            if count > 0:
                print("이미 데이터 있음 -스킵")
                return engine
        except:
            pass
    return engine        #engine 반환

engine = init_db()

#==============재료 판다스 데이터 프레임 만들기==================

df_ingre = pd.read_sql_query("SELECT 레시피명, 재료 FROM recipe", engine)
#engine으로 불러온 mariadb의 데이터베이스에서 레시피명, 재료 열만 판다스 dataframe으로 불러오기

#print(df_ingre)

new_ingre_columns = []    #이후에 데이터프레임을 대체할 리스트 선언

for row_text in df_ingre["재료"]:                #df_ingre["재료"]에서 행 단위로 불러오기 -> row_text
    comma_split = row_text.split(",")          #row_text를 ", "단위로 나눠 comma_split 리스트로 만들기
    
    one_recipe_list = []                        #["계란", "1개"] 단위의 리스트 선언
    for item in comma_split:                     #comma_split을 " "단위로 나눠 space_split 리스트로 만들기 
        space_split = item.split(" ")
        one_recipe_list.append(space_split)    #space_split을 모아 one_recipe_columns 리스트 만들기
    
    new_ingre_columns.append(one_recipe_list)    #one_recipe_columns 모아 new_ingre_columns 리스트 만들기
df_ingre["재료"] = new_ingre_columns                #리스트로 column 대체

#print(df_ingre)

ingre_set = set()                #개수 없는 재료 들어갈 집합 선언

for i in df_ingre["재료"]:        #집합 만들기(중복제거)
    for j in i:
        ingre_set.add(j[0])


ingre_list = list(ingre_set)    #집합을 리스트로 만들기


#================메인페이지('/')=========================

@app.route('/')
def home():
    return render_template('init.html')

#============레시피 선택('/select_ingredients')============

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

#============갖고있는 재료 선택 페이지==============

@app.route('/recipe_list')
def recipe_list_page():
    recipes_list = []
    selected_ingredients = []
    try:
        #사용자가 화면에서 선택한 재료 목록 가져오기
        selected_ingredients = request.args.getlist('ingredients')

        #마리아 디비 연결
        conn = get_db_connection()
        cursor = conn.cursor()

        #마리아디비에서 csv가져오기
        cursor.execute("SELECT * FROM recipe")
        all_recipes = cursor.fetchall()

        #디비에서 재료 칼럼 가져와 선택 목록과 비교
        for row in all_recipes:
            if row:
                recipe_ingredients = str(row.get('재료', ''))
                
                is_matched = False
                if len(selected_ingredients) == 0:
                    is_matched = True
                else:
                    for ing in selected_ingredients:
                        if ing in recipe_ingredients:
                            is_matched = True
                            break

                #만약 둘이 같다면 해당 레시피를 화면에 보낼 리스트에 담기
                if is_matched:
                    recipes_list.append({
                        'name': row.get('레시피명') or '-',
                        'ingredients': recipe_ingredients,
                        'tool': row.get('조리도구') or '-',
                        'recipe_desc': row.get('레시피') or '-',
                        'category': row.get('식사/간식') or '식사',
                        'link': row.get('링크') or '#',
                        'basic_tools': row.get('기본 조리도구') or '-',
                        'extra_tools': row.get('추가 조리도구') or '-'
                    })
                    
                   # 열 이름에 공백이 포함된 경우를 대비해 '링크'라는 단어가 포함된 키를 동적으로 탐색
                    raw_link = None
                    for key, val in row.items():
                        if '링크' in key:
                            raw_link = val
                            break

                    #링크 오타 및 결측치 정제 작업
                    final_link = '#'
                    if raw_link:
                        clean_link = str(raw_link).strip()
                        # nan, None 등 결측치가 문자열로 들어온 경우와 불필요한 따옴표 제거
                        if clean_link and clean_link.lower() not in ['nan', 'none', 'null', '#']:
                            clean_link = clean_link.replace('"', '').replace("'", "")
                            if not clean_link.startswith('http'):
                                final_link = 'https://' + clean_link
                            else:
                                final_link = clean_link
        conn.close()

    except Exception as e:
        print(f"레시피 목록 로드 중 에러 발생: {e}")
        recipes_list = []

    return render_template('recipe_list.html', recipes=recipes_list, selected_ingredients=selected_ingredients)


#======================================

if __name__ == '__main__':
  app.run(host='0.0.0.0', port = 5000, debug = True)    #이미 점유되어 있으면 5001로 돌려보기

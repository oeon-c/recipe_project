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
        port=3306,        #도커에서 실행할 떄
        #port=3307,
        user='root',
        password='1234',
        db='recipe_db',
        charset='utf8',
        cursorclass=pymysql.cursors.DictCursor
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
    ingredients_list = [{'id': idx, 'name': name} for idx, name in enumerate(sorted(ingre_list))]
    # HTML 템플릿의 변수명 'ingredients'와 정확히 매치하여 렌더링 리턴
    return render_template('select_ingredients.html', ingredients=ingredients_list)

#============갖고있는 재료 선택 페이지==============

@app.route('/recipe_list')
def recipe_list_page():
    recipes_list = []
    selected_ingredients = []
    try:
        selected_ingredients = request.args.getlist('ingredients')

        # ✅ 수정: DB 전체 조회 + 재료 비교 로직 삭제하고 아래로 대체
        # 1. df_ingre로 재료 비교해서 매칭된 레시피명 추출
        matched_names = []
        for idx, row in df_ingre.iterrows():
            if len(selected_ingredients) == 0:
                matched_names.append(row['레시피명'])
            else:
                for ing in selected_ingredients:
                    for ingre_group in row['재료']:
                        if ing == ingre_group[0]:
                            matched_names.append(row['레시피명'])
                            break
        print(f"선택 재료: {selected_ingredients}")      # ← 추가
        print(f"매칭된 레시피: {matched_names}")          # ← 추가
        print(f"df_ingre 재료 샘플: {df_ingre['재료'][0]}")  # ← 추가

        # 2. 매칭된 레시피명으로 DB에서 상세정보 조회
        conn = get_db_connection()
        cursor = conn.cursor()
        placeholders = ', '.join(['%s'] * len(matched_names))
        cursor.execute(f"SELECT * FROM recipe WHERE 레시피명 IN ({placeholders})", matched_names)
        all_recipes = cursor.fetchall()

        for row in all_recipes:
            recipes_list.append({
                'name': row.get('레시피명') or '-',
                'ingredients': row.get('재료') or '-',
                'tool': row.get('조리도구') or '-',
                'recipe_desc': row.get('레시피') or '-',
                'category': row.get('식사/간식') or '식사',
                'link': row.get('링크') or '#',
                'basic_tools': row.get('기본 조리도구') or '-',
                'extra_tools': row.get('추가 조리도구') or '-'
            })
        conn.close()

    except Exception as e:
        print(f"레시피 목록 로드 중 에러 발생: {e}")
        recipes_list = []

    return render_template('recipe_list.html', recipes=recipes_list, selected_ingredients=selected_ingredients)
    
#==================레시피 상세화면====================

@app.route('/recipe_show')
def recipe_detail_page():
    # 1. HTML의 a 태그에서 보낸 '?name=레시피이름' 데이터를 수집합니다.
    recipe_name = request.args.get('name')
    
    # 만약 이름이 전달되지 않고 비정상적으로 접근했다면 에러 메시지를 띄웁니다.
    if not recipe_name:
        return "레시피 이름이 전달되지 않았습니다.", 400
        
    recipe_info = {}
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 2. 데이터베이스 조회
        # WHERE 조건절을 사용하여 '레시피명' 열이 전달받은 이름과 정확히 일치하는 데이터만 찾습니다.
        # %s를 사용하는 이유는 SQL 인젝션(해킹)을 방지하기 위한 안전한 파라미터 바인딩 방식입니다.
        cursor.execute("SELECT * FROM recipe WHERE 레시피명 = %s", (recipe_name,))
        
        # 목록을 띄울 때는 fetchall()로 전부 가져왔지만, 
        # 상세 페이지는 레시피 1개만 필요하므로 fetchone()을 사용하여 단일 행만 가져옵니다.
        row = cursor.fetchone()
        conn.close()
        
        if row:
            # 3. 링크 전처리 과정 (목록 페이지와 동일하게 깨진 링크를 복구합니다)
            raw_link = None
            # 딕셔너리의 키(열 이름) 중에서 '링크'라는 단어가 포함된 것을 찾습니다.
            for key, val in row.items():
                if '링크' in key:
                    raw_link = val
                    break
                    
            final_link = '#'
            if raw_link:
                clean_link = str(raw_link).strip()
                # nan, None 등 데이터베이스의 빈 값이 문자열로 넘어온 경우를 걸러냅니다.
                if clean_link and clean_link.lower() not in ['nan', 'none', 'null', '#']:
                    # 잘못 들어간 따옴표를 제거합니다.
                    clean_link = clean_link.replace('"', '').replace("'", "")
                    # 주소가 http로 시작하지 않으면 강제로 https:// 를 붙여 외부 링크 이동이 가능하게 만듭니다.
                    if not clean_link.startswith('http'):
                        final_link = 'https://' + clean_link
                    else:
                        final_link = clean_link

            # 4. HTML로 넘겨줄 하나의 딕셔너리(객체)로 데이터를 예쁘게 포장합니다.
            recipe_info = {
                'name': row.get('레시피명') or '-',
                'ingredients': row.get('재료') or '-',
                'tool': row.get('조리도구') or '-',
                'recipe_desc': row.get('레시피') or '-',
                'category': row.get('식사/간식') or '식사',
                'basic_tools': row.get('기본 조리도구') or '-',
                'extra_tools': row.get('추가 조리도구') or '-',
                'link': final_link
            }
        else:
            # DB에서 이름을 찾지 못한 경우
            return "해당 레시피를 찾을 수 없습니다.", 404
            
    except Exception as e:
        print(f"상세 페이지 데이터 조회 중 에러: {e}")
        return "서버 오류가 발생했습니다.", 500

    # 5. 최종 가공된 recipe_info 데이터를 recipe_detail.html 파일로 넘겨주며 화면을 그립니다.
    return render_template('recipe_show.html', recipe=recipe_info)

if __name__ == '__main__':
  app.run(host='0.0.0.0', port = 5000, debug = True)    #이미 점유되어 있으면 5001로 돌려보기

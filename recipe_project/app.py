from flask import Flask, request, render_template
from flask_cors import CORS
import pymysql
import pandas as pd
from sqlalchemy import create_engine, text
import time
import re
import json
import csv

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

engine = init_db()

# ============== 재료 데이터 최신화 함수 생성 ==============
# 서버 시작 시 1번만 실행되던 코드를 함수로 만들어, 필요할 때마다 호출하도록 변경
def get_current_recipe_data():
    df_ingre = pd.read_sql_query("SELECT 레시피명, 재료 FROM recipe", engine)

    new_ingre_columns = []
    for row_text in df_ingre["재료"]:
        comma_split = row_text.split(",")
        one_recipe_list = []
        for item in comma_split:
            space_split = item.split(" ")
            one_recipe_list.append(space_split)
        new_ingre_columns.append(one_recipe_list)
    
    df_ingre["재료"] = new_ingre_columns

    ingre_set = set()
    for i in df_ingre["재료"]:
        for j in i:
            ingre_set.add(j[0])
            
    ingre_list = list(ingre_set)
    
    # 처리된 데이터프레임과 재료 리스트를 반환
    return df_ingre, ingre_list

#================메인페이지('/')=========================

@app.route('/')
def home():
    return render_template('init.html')

#============레시피 선택('/select_ingredients')============

@app.route('/select_ingredients')
def select_ingredients():
    # 실시간으로 최신 재료 리스트를 불러오기 (첫 번째 반환값은 사용하지 않으므로 _ 처리)
    _, current_ingre_list = get_current_recipe_data()
    
    ingredients_list = [{'id': idx, 'name': name} for idx, name in enumerate(sorted(current_ingre_list))]
    return render_template('select_ingredients.html', ingredients=ingredients_list)

#============갖고있는 재료 선택 페이지==============

@app.route('/recipe_list')
def recipe_list_page():
    recipes_list = []
    selected_ingredients = []
    try:
        selected_ingredients = request.args.getlist('ingredients')

        # 실시간 최신 데이터프레임 불러오기
        current_df_ingre, _ = get_current_recipe_data()

        matched_names = []
        # df_ingre 대신 방금 불러온 current_df_ingre 사용
        for idx, row in current_df_ingre.iterrows():
            if len(selected_ingredients) == 0:
                matched_names.append(row['레시피명'])
            else:
                for ing in selected_ingredients:
                    for ingre_group in row['재료']:
                        if ing == ingre_group[0]:
                            matched_names.append(row['레시피명'])
                            break
        
        print(f"선택 재료: {selected_ingredients}")
        print(f"매칭된 레시피: {matched_names}")

        # 이하 코드는 기존과 동일
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # (이하 생략 - 기존 하단 코드 그대로 유지)
        if matched_names: # 매칭된 이름이 있을 때만 DB 조회하도록 안전장치 추가 권장
            placeholders = ', '.join(['%s'] * len(matched_names))
            cursor.execute(f"SELECT * FROM recipe WHERE 레시피명 IN ({placeholders})", matched_names)
            all_recipes = cursor.fetchall()
            # ...

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
# ================= 레시피 추가 기능 =================

@app.route('/add_recipe', methods=['GET', 'POST'])
def add_recipe():
    # 1. 사용자가 [등록하기] 버튼을 눌러서 데이터를 보냈을 때 (POST 방식)
    if request.method == 'POST':
        name = request.form.get('recipe_name', '')
        ingredients = request.form.get('ingredients', '')
        tool = request.form.get('tool', '')
        category = request.form.get('category', '')
        desc = request.form.get('recipe_desc', '')
        link = request.form.get('link', '')
        
        try:
            # DB 창고 문 열기
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # DB에 데이터 밀어넣기 (INSERT)
            sql = """
                 INSERT INTO recipe (레시피명, 재료, 조리도구, `식사/간식`, 레시피, 링크) 
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            # 기존 코드 에러 수정: SQL의 %s 개수(6개)에 맞게 desc 변수를 추가로 전달합니다.
            cursor.execute(sql, (name, ingredients, tool, category, desc, link))
            
            # 저장 확정 짓고 문 닫기
            conn.commit()
            conn.close()
            
            # CSV 파일에 데이터 추가 (Append 모드)
            # 파일 구조: 레시피명, 재료, 조리도구, 레시피, 식사/간식, 링크, (빈열), (빈열)
            with open('recipe_data6.csv', mode='a', encoding='utf-8-sig', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([name, ingredients, tool, desc, category, link, '', ''])
            
            # 성공했다는 팝업창을 띄우고 메인 화면('/')으로 튕겨냅니다.
            return "<script>alert('레시피가 성공적으로 추가되었습니다!'); window.location.href='/';</script>"
            
        except Exception as e:
            print(f"레시피 추가 중 DB/CSV 에러: {e}")
            return f"데이터를 저장하는 중 에러가 발생했습니다: {e}"

    # 2. 그냥 링크를 타고 처음 접속했을 때 (GET 방식) -> 빈 폼 화면 보여주기
    return render_template('add_recipe.html')

if __name__ == '__main__':
  app.run(host='0.0.0.0', port = 5000, debug = True)    #이미 점유되어 있으면 5001로 돌려보기

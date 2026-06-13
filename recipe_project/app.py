from flask import Flask, request, render_template   #파이썬 코드를 웹서버로 만들고, html을 브라우저에 띄워 페이지에서 요청을 받기 위한 모율 가져오기
from flask_cors import CORS                         #html과 flask가 자유롭게 데이터 주고받을 수 있게 해주는 모듈 가져오기
import pymysql                                      #파이썬과 마리아디비를 물리적으로 연결하기 위한 통로
import pandas as pd                                 #csv를 판다스 데이터프레임으로 불러오기위한 모듈 가져오기
from sqlalchemy import create_engine, text          #파이썬 언어를 마리아 db에게 번역
import time                                         #마리아db 켜질 떄까지 기다릴 때 사용
import re                                           #텍스트 안에서 원하는 패턴만 뽑을 때 사용
import json
import csv

app = Flask(__name__)   #플라스크 앱 생성
CORS(app)


#==========데이터 불러오기=============
#1. mariadb 가져오기
def get_db_connection():
    return pymysql.connect(        #pymysql로 mariadb 연결하기
        host='mariadb',    #도커에서 실행할 때
        #host='127.0.0.1',    #python에서 
        port=3306,        #도커에서 실행할 떄
        #port=3307,
        user='root',
        password='1234',
        db='recipe_db',
        charset='utf8',
        cursorclass=pymysql.cursors.DictCursor    #딕셔너리 형태로 데이터베이스 가져오기
    )


def init_db():                #웹 서버 가동 시 csv 데이터 읽어와 마리아 DB를 자동으로 세팅하는 초기화 함수
    #2. 엔진 만들기 
    for i in range(5):        #mariadb가 연결되기 전 flask가 실행되어 발생하는 오류 방지
        try:
            #pymysql 위에서 파이썬 명령 번역하는 sqlalchemy engine 만들기
            engine = create_engine('mysql+pymysql://root:1234@mariadb:3306/recipe_db')     #docker에서 돌릴 때 사용
            #engine = create_engine('mysql+pymysql://root:1234@127.0.0.1:3307/recipe_db')      #로컬에서 돌릴 때 사용
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))    #engine.connect() 함수로 db가 켜졌는지 확인
            break
        except:
            print(f"DB 대기 중...({i}/5)")          #아직 켜지지 않았다면 대기
            time.sleep(3)
            

    #3. csv를 판다스 dataframe으로 불러오기
    df = pd.read_csv("recipe_data6.csv")                                        #csv를 판다스 데이터프레임으로 가져오기
    df.to_sql(name='recipe', con=engine, if_exists='replace', index=False)      #데이터프레임을 mariadb 데이터베이스로 가져오기

    
    #4. 엔진으로 df와 db 연결
    with engine.connect() as conn:
        try:
            #마리아db의 행 개수 세어보기
            count = conn.execute(text("SELECT COUNT(*) FROM recipe")).scalar()
            if count > 0:
                print("이미 데이터 있음 -스킵")
                return engine
        except:
            pass
    return engine        #engine 반환

engine = init_db()       #init_db()호출해 반환받은 engine을 engine에 저장

# ============== 재료 데이터 최신화 함수 생성 ==============
# 서버 시작 시 1번만 실행되던 코드를 함수로 만들어, 필요할 때마다 호출하도록 변경
def get_current_recipe_data():
    #db에서 데이터를 쿼리문으로 조회해 판다스로 가져오기
    df_ingre = pd.read_sql_query("SELECT 레시피명, 재료 FROM recipe", engine)

    new_ingre_columns = []
    for row_text in df_ingre["재료"]:                #df_ingre["재료"]를 한 줄씩 읽어
        comma_split = row_text.split(",")           #콤마 단위로 나눈 것을 comma_split 리스트로 저장
        one_recipe_list = []
        for item in comma_split:                    #comma_split 리스트의 원소 하나씩 읽어
            space_split = item.split(" ")           #공백 단위로 나눈 것을 one_recipe_list에 저장
            one_recipe_list.append(space_split)
        new_ingre_columns.append(one_recipe_list)   #new_ingre_columns 리스트에 완성된 ["계란", "1개"] 형태 데이터를 하나씩 넣기
    
    df_ingre["재료"] = new_ingre_columns             #리스트로 df 재료열 덮어씌우기  

    ingre_set = set()
    for i in df_ingre["재료"]:
        for j in i:
            ingre_set.add(j[0])                    #재료 집합 만들어 중복 제거
            
    ingre_list = list(ingre_set)
    
    # 처리된 데이터프레임과 재료 리스트를 반환
    return df_ingre, ingre_list

#================메인페이지('/')=========================

@app.route('/')
def home(): #메인초기 화면 init.html을 렌더링
    return render_template('init.html')

#============레시피 선택('/select_ingredients')============

@app.route('/select_ingredients')
def select_ingredients(): #사용자가 재료를 선택할 수 있는 화면을 렌더링하는 라우트
    # 실시간으로 최신 재료 리스트를 불러오기 (첫 번째 반환값은 사용하지 않으므로 _ 처리)
    _, current_ingre_list = get_current_recipe_data()
    # 2)재료 리스트를 가다가 순으로 정렬 후, 프론트엔드 전송용 딕셔너리 리스트 생성 ({id, namae})
    ingredients_list = [{'id': idx, 'name': name} for idx, name in enumerate(sorted(current_ingre_list))]
    return render_template('select_ingredients.html', ingredients=ingredients_list)

#============갖고있는 재료 선택 페이지==============

@app.route('/recipe_list')
def recipe_list_page():
    recipes_list = []
    selected_ingredients = []
    try: #1) url 파라미터에서 사용자가 선택한 재료 리스트 가져오기 
        selected_ingredients = request.args.getlist('ingredients')

        # 2) 데이터프레임으로 부터 실시간 최신 레시피-재료 매팅 데이터 불러오기
        current_df_ingre, _ = get_current_recipe_data()
        # 3) 사용자가 선택한 재료를 포함하는 레시피명 필터링
        matched_names = []
        for idx, row in current_df_ingre.iterrows(): #선택한 재료가 없는 경우 모든 레시피를 매칭 목록에 추가
            if len(selected_ingredients) == 0:
                matched_names.append(row['레시피명'])
            else: #선택한 재료 중 하나라도 레시피의 재료 그룹에 퐘되어 있는지 확인 
                for ing in selected_ingredients:
                    for ingre_group in row['재료']: #INGRE_GROUP[0]이 재료명인 경우 매칭 성공 
                        if ing == ingre_group[0]:
                            matched_names.append(row['레시피명'])
                            break #중복 추가 방지를 위해 가장 안쪽 LOOP 탈출
        #디버깅을 위한 콘솔  로그 출력
        print(f"선택 재료: {selected_ingredients}")
        print(f"매칭된 레시피: {matched_names}")
        # 4) DB 연결 및 매칭된 레시피 데이터 상세 조회
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if matched_names: #매칭된 레시피명이 하나라도 존재하는 경우 sql 쿼리 실행
            placeholders = ', '.join(['%s'] * len(matched_names)) #SQL injection 방지를 위한 동적 placeholder 생성 
            cursor.execute(f"SELECT * FROM recipe WHERE 레시피명 IN ({placeholders})", matched_names)
            all_recipes = cursor.fetchall()
            #db 조회 결과를 프론트 엔드 전송용 딕셔너리 리스트로 변환, none 값 대응 예외 처리
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
        conn.close() #db연결 종료

    except Exception as e: #오류 발생시 에러 메세지 출력 및 안전한 예외 처리 + 필요에 따른 로깅 추가 기능
        print(f"레시피 목록 로드 중 에러 발생: {e}")
        recipes_list = []
    # 5) 최종 매칭된 레시피 리스트를 템플릿에 전달하여 화면 렌더링
    return render_template('recipe_list.html', recipes=recipes_list, selected_ingredients=selected_ingredients)

#==================레시피 상세화면====================

@app.route('/recipe_show')
def recipe_detail_page():
    # 1) url 파라미터에서 특정 레시피 이름 수집 
    recipe_name = request.args.get('name')
    
    # 예외 처리: 레시피 이름이 누락된 채 비정상적으로 접근한 경우 400 에러 반환 
    if not recipe_name:
        return "레시피 이름이 전달되지 않았습니다.", 400
        
    recipe_info = {}
    try: #2) db연결 및 단일 레시피 조회 
        conn = get_db_connection()
        cursor = conn.cursor()
        
        #SQL injection 방지를 위해 피라미터 바인딩 방식을 사용하여 쿼리 실행
        cursor.execute("SELECT * FROM recipe WHERE 레시피명 = %s", (recipe_name,))
        
       # 상세 페이지는 1개의 레시피 정보만 필요하므로 fetchone() 사용
        row = cursor.fetchone()
        conn.close()
        
        if row:
            #3) 데이터 전처리 및 링크 복구 과정 
            raw_link = None
            # DB 딕셔너리의 키 중 링크라는 단어가 포함된 컴럼 확인 및 데이터 추출 
            for key, val in row.items():
                if '링크' in key:
                    raw_link = val
                    break
                    
            final_link = '#' #데이터베이스 내의 빈 값이 문자열로 잘못 들어온 경우 전처리 
            if raw_link:
                clean_link = str(raw_link).strip()
                # 주소에 잘못 포함된 따옴표 제거 
                if clean_link and clean_link.lower() not in ['nan', 'none', 'null', '#']:
                    clean_link = clean_link.replace('"', '').replace("'", "")
                    # 주소가 http로 시작하지 않으면 강제로 https:// 를 붙여 외부 링크 이동이 가능하게 만듭니다.
                    if not clean_link.startswith('http'):
                        final_link = 'https://' + clean_link
                    else:
                        final_link = clean_link

            # 4) 프론트엔드로 전달할 최종 레시피 데이터 객처 생성
            recipe_info = {
                'name': row.get('레시피명') or '-',
                'ingredients': row.get('재료') or '-',
                'tool': row.get('조리도구') or '-',
                'recipe_desc': row.get('레시피') or '-',
                'category': row.get('식사/간식') or '식사',
                'basic_tools': row.get('기본 조리도구') or '-',
                'extra_tools': row.get('추가 조리도구') or '-',
                'link': final_link # 전처리가 완료된 안전한 링크 대입 
            }
        else:
            # DB 오류 발생 시 디버깅을 위한 콘솔 에러 로그 출력 
            return "해당 레시피를 찾을 수 없습니다.", 404
            
    except Exception as e:
        print(f"상세 페이지 데이터 조회 중 에러: {e}")
        return "서버 오류가 발생했습니다.", 500

    # 5) 상세 페이지 템플릿에 데이터 전달 및 화면 렌더링 
    return render_template('recipe_show.html', recipe=recipe_info)
# ================= 레시피 추가 기능 =================

@app.route('/add_recipe', methods=['GET', 'POST'])
def add_recipe():
    # 1) 사용자가 작성한 데이터를 전송했을 때(post 요청 처리)
    if request.method == 'POST': # 프론트엔드 Form 태그 내부의 name 속성값을 기반으로 데이터 수집
        name = request.form.get('recipe_name', '')
        ingredients = request.form.get('ingredients', '')
        tool = request.form.get('tool', '')
        category = request.form.get('category', '')
        desc = request.form.get('recipe_desc', '')
        link = request.form.get('link', '')
        
        try:
            # [DB 저장 과정} DB 창고 연결 및 커서 생성 
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # 레시피 테이블에 새로운 레코드를 삽입하는 SQL 퀴리문
            sql = """
                 INSERT INTO recipe (레시피명, 재료, 조리도구, `식사/간식`, 레시피, 링크) 
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            # SQL의  플레이스홀더 개수와 순서에 맞춰 데이터 매핑 및 실행 
            cursor.execute(sql, (name, ingredients, tool, category, desc, link))
            
            # DB 변경 사항을 최종 확정하고 연결 종료 
            conn.commit()
            conn.close()
            
            # CSV 동기화 과정 로컬 CSV 파일 데이터 누적 추가 ( Append 모드)
            with open('recipe_data6.csv', mode='a', encoding='utf-8-sig', newline='') as file:
                writer = csv.writer(file) #데이터프레임 구조와 일치하도록 데이터 배열 작성 
                writer.writerow([name, ingredients, tool, desc, category, link, '', ''])
            
            # 등록 성공 시 사용자 알림 팝업을 띄운 뒤, 자바스크립트를 이용해 메인 홈으로 리다이렉트
            return "<script>alert('레시피가 성공적으로 추가되었습니다!'); window.location.href='/';</script>"
            
        except Exception as e: #예외 처리: 데이터베이스 반영 혹인 CSV 파일 저장 중 오류 발생 시 에러 로깅 
            print(f"레시피 추가 중 DB/CSV 에러: {e}")
            return f"데이터를 저장하는 중 에러가 발생했습니다: {e}"

    # 2) 사용자가 주소를 입력해 단순히 처음 진입했을 때 (GET요청 처리)
    return render_template('add_recipe.html')
#6. Flask 웹 애플리케이션 실행 메인 함수 
if __name__ == '__main__':
  app.run(host='0.0.0.0', port = 5000, debug = True)    #debug=True 설정을 통해 코드 변경 시 서버가 자동 재시작되도록 디버그 모드 활성화

from flask import Flask, render_template, request
import pymysql

app = Flask(__name__)

# DB 연결을 도와주는 함수
def get_db_connection():
    return pymysql.connect(
        host='127.0.0.1',
        user='root',
        password='rootpassword',
        db='recipe_db',
        cursorclass=pymysql.cursors.DictCursor # DB 검색 결과를 파이썬 딕셔너리로 깔끔하게 가져오기 위한 설정
    )

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search_ingredient():
    user_input = request.form['ingredient']
    
    # 1. DB 연결하기
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 2. SQL 쿼리 실행 (입력한 재료가 포함된 레시피 찾기)
    # LIKE '%재료%' 를 사용하면 해당 단어가 포함된 모든 데이터를 찾습니다.
    # DISTINCT: 겹치는 결과가 있으면 알아서 하나로 합쳐서 가져오라는 SQL 명령어입니다.
    sql = "SELECT DISTINCT recipe_name FROM recipes WHERE ingredients LIKE %s"
    cursor.execute(sql, (f"%{user_input}%",))
    
    # 3. 검색된 결과 모두 가져오기
    result_rows = cursor.fetchall()
    
    # 4. DB 연결 안전하게 닫기
    conn.close()
    
    print(f"=== DB에서 가져온 원본 데이터: {result_rows} ===")

    # 5. 결과를 깔끔한 파이썬 리스트로 변환
    recommended_recipes = [row['recipe_name'] for row in result_rows]
    print(f"=== HTML로 넘어갈 리스트: {recommended_recipes} ===")

    # 6. HTML로 결과 넘겨주기
    return render_template('index.html', result_data=user_input, recipes=recommended_recipes)

if __name__ == '__main__':
    app.run(debug=True)
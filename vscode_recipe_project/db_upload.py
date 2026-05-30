import pandas as pd
import pymysql

# 1. pandas를 이용해 csv데이터로 데이터프레임 만들기
print("CSV 파일 읽는 중...")
df = pd.read_csv('recipes.csv')

# 2. PyMySQL 이용해서 MariaDB에 연결하기
# 주의: 이 코드가 작동하려면 MariaDB 서버가 켜져 있어야 합니다!
print("MariaDB 연결 중...")
conn = pymysql.connect(
    host='127.0.0.1', 
    user='root',
    password='rootpassword', # 우리가 설정할 DB 비밀번호
    db='recipe_db',          # 우리가 만들 DB 이름
    charset='utf8mb4'
)

cursor = conn.cursor()

# 3. 데이터를 저장할 '테이블' 만들기 (C언어의 구조체 배열을 만든다고 생각하시면 됩니다)
cursor.execute('''
    CREATE TABLE IF NOT EXISTS recipes (
        id INT AUTO_INCREMENT PRIMARY KEY,
        recipe_name VARCHAR(255),
        ingredients TEXT
    )
''')

# 4. pandas 데이터프레임의 내용을 한 줄씩 뽑아서 DB에 넣기
for index, row in df.iterrows():
    sql = "INSERT INTO recipes (recipe_name, ingredients) VALUES (%s, %s)"
    cursor.execute(sql, (row['recipe_name'], row['ingredients']))

# 5. DB에 저장 확정(commit)하고 연결 끊기
conn.commit()
conn.close()
print("MariaDB에 데이터 업로드 완전 성공!")
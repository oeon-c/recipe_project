import pandas as pd
import numpy as np
from flask import Flask
from sqlalchemy import create_engine

app = Flask(__name__)   #플라스크 앱 생성

df0 = pd.read_csv("recipe_data.csv")

df = df0.drop(axis=1,labels=["링크", "기본 조리도구", "추가 조리도구"], inplace=False)
df.dropna(axis=1, how='all', inplace=True)

df.drop(axis=0, labels=74, inplace=True)        #마지막행 NaN 지우기 
print(df)


engine = create_engine('mysql+pymysql://root:1234@mariadb:3306/recipe_db')
                #password:ubuntu, service명:mariadb, 데이터베이스명: recipe_db
df.to_sql(name='recipe', con=engine, if_exists='append', index=False)
                #데이터베이스 속 테이블 명: recipe

@app.route('/')
def index():
    return render_template('init.html')

@app.route('/select-ingredients')
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
  app.run(host='0.0.0.0', port = 5000, debug = True)

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


engine = create_engine('mysql+pymysql://root:ubuntu@mariadb:3306/recipe_db')
                #password:ubuntu, service명:mariadb, 데이터베이스명: recipe_db
df.to_sql(name='recipe', con=engine, if_exists='append', index=False)
                #데이터베이스 속 테이블 명: recipe



topics = [
    {'id':1, 'title':'html', 'body':'html is ...'},
    {'id':2, 'title':'css', 'body':'css is ...'}, 
    {'id':3, 'title':'javascript', 'body':'favascript is ...'}
]

@app.route('/')
def index():
    liTags = ''
    for topic in topics:
        liTags += f'<li><a href = "/read/{topic["id"]}">{topic["title"]}</a></li>'

    return f'''<!doctype html>
    <html>
        <body>
            <h1><a href="/">WEB</a></h1>
            <ol>
                {liTags}
            </ol>
            <h2>Welcome</h2>
            Hello, Web
        </body>
    </html>
    '''

@app.route('/read/<id>/')
def read(id):
    print(id)
    return id +'. ' + topics[(int(id)-1)]['body']

app.run(debug=True)

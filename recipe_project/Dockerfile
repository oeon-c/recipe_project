FROM python:3.10-slim

WORKDIR /app

COPY app.py .
COPY templates/ ./templates/
COPY static/ ./static/ 

RUN pip install flask pymysql flask-cors pandas sqlalchemy

## 패키지 명단 먼저 복사하고 설치
#COPY requirements.txt .
#RUN pip install --no-cache-dir -r requirements.txt
#RUN pup install pymysql


## 나머지 내 소스코드와 CSV 파일들을 통째로 복사
#COPY . .

# 실행할 파일 이름 지정
CMD ["python", "app.py"]

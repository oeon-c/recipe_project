FROM python:3.10-slim

WORKDIR /app

COPY app.py .
COPY templates/ ./templates/

RUN pup install flask pymysql
RUN pup install flask-cors

## 패키지 명단 먼저 복사하고 설치
#COPY requirements.txt .
#RUN pip install --no-cache-dir -r requirements.txt
#RUN pup install pymysql


## 나머지 내 소스코드와 CSV 파일들을 통째로 복사
#COPY . .

# 실행할 파일 이름 지정
CMD ["python", "app.py"]

FROM python:3.10-slim

##/app 디렉토리를 만들고 작업실로 설정
WORKDIR /app

##파이썬 파일, templates 폴더, static 폴더를 현재 디렉토리로(.)로 가져오기
COPY app.py .
COPY templates/ ./templates/
COPY static/ ./static/

##필요한 패키지를 컨테이너에 설치
RUN pip install flask pymysql flask-cors pandas sqlalchemy

##실행할 프로그램과 파일 지정
CMD ["python", "app.py"]

# recipe_project

docker-compose.yml: flask와 mariadb 컨테이너 연결용 설정 파일<br>
init.sql: mariadb 초키 데이터베이스 파일로, 현재 데이터 저장해둔 파일 사용<br>
app.py: flask 벡엔드 소스코드 저장용 파일<br>
requirements.txt: 구동을 위해 파이썬 환경에 설치되어야 하는 라이브러리 명시된 텍스트 파일입니다.(Dockerfile 빌드 시 이 파일을 읽어 필요한 패키지를 자동으로 설치하게 되어 있습니다.)<br>
index.html: 웹페이지 기본 레이아웃이 될 html 기본 페이지입니다. 차후 여기서 페이지별로 이동할 html 문서를 작성하면 됩니다.

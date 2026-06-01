# recipe_project

docker-compose.yml: flask와 mariadb 컨테이너 연결용 설정 파일<br>
init.sql: mariadb 초키 데이터베이스 파일로, 현재 데이터 저장해둔 파일 사용<br>
app.py: flask 벡엔드 소스코드 저장용 파일<br>
requirements.txt: 구동을 위해 파이썬 환경에 설치되어야 하는 라이브러리 명시된 텍스트 파일입니다.(Dockerfile 빌드 시 이 파일을 읽어 필요한 패키지를 자동으로 설치하게 되어 있습니다.)<br>
templates: 이 폴더 안에 페이지 구성에 필요한 html 파일을 모두 넣으면 됩니다. 현재 서연님의 파일 기준 1, 2 페이지까지 대략적으로 완료되어 있습니다.
static: html 파일 구동에 필요한 css 파일을 넣어두었습니다. 이 파일 안으로 필요한 내용을 넣어두시면 됩니다.
test

# Korean FGI Agent 배포 가이드

## 추천 경로: Streamlit Community Cloud

이 프로젝트는 Streamlit 서버 앱입니다. Netlify 같은 정적 호스팅에는 그대로 배포할 수 없고, 가장 간단한 데모 배포는 Streamlit Community Cloud입니다.

1. GitHub에 이 폴더를 새 저장소로 올립니다.
2. `venv/`, 백업 파일, 로컬 secret은 올리지 않습니다. `.gitignore`가 기본 제외합니다.
3. https://share.streamlit.io 에서 `Create app`을 누릅니다.
4. Repository, branch, main file path를 선택합니다.
   - Main file path: `app.py`
5. App secrets에 아래 값을 추가합니다.

```toml
LLM_PROVIDER = "openai"
OPENAI_API_KEY = "sk-..."
OPENAI_MODEL = "gpt-4o-mini"
```

6. Deploy를 누르고 `*.streamlit.app` URL을 공유합니다.

## 대안: Render

Render에서 새 Web Service를 만들고 GitHub 저장소를 연결하면 `render.yaml` 설정으로 배포할 수 있습니다.

필수 환경변수:

```text
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
```

## Netlify를 꼭 쓰고 싶은 경우

Netlify는 Streamlit 서버 프로세스를 직접 실행하는 용도가 아니라 정적 사이트/JAMstack 배포에 맞습니다. 이 앱을 Netlify에 그대로 올리면 Python Streamlit 서버가 실행되지 않습니다.

현실적인 Netlify 활용법은 두 가지입니다.

1. Netlify에는 소개/랜딩 페이지를 올리고 CTA 버튼을 Streamlit Cloud URL로 연결합니다.
2. Streamlit 앱을 API 서버로 분리하고, Netlify에는 별도 프론트엔드를 새로 만듭니다.

이번 데모 목적에는 1번보다 Streamlit Community Cloud 단독 배포가 가장 빠릅니다.

# K-Persona Panel Studio

상품, 광고 문구, 서비스 콘셉트를 입력하면 한국형 합성 페르소나 패널을 구성하고 FGI 응답, 인사이트, Journey Map을 생성하는 Streamlit 데모 앱입니다.

## 로컬 실행

```bash
pip install -r requirements.txt
streamlit run app.py
```

로컬에서는 기본적으로 Ollama를 사용합니다. Ollama 없이 온라인 데모를 하려면 OpenAI API 키를 설정하세요.

```toml
# .streamlit/secrets.toml
LLM_PROVIDER = "openai"
OPENAI_API_KEY = "sk-..."
OPENAI_MODEL = "gpt-4o-mini"
```

그 다음 실행합니다.

```bash
streamlit run app.py
```

## 온라인 배포

가장 간단한 방법은 Streamlit Community Cloud입니다.

1. GitHub 저장소에 업로드
2. https://share.streamlit.io 에서 새 앱 생성
3. main file path를 `app.py`로 지정
4. Secrets에 아래 값 추가

```toml
LLM_PROVIDER = "openai"
OPENAI_API_KEY = "sk-..."
OPENAI_MODEL = "gpt-4o-mini"
```

자세한 내용은 [DEPLOYMENT.md](DEPLOYMENT.md)를 참고하세요.

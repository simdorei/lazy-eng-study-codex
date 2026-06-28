# Lazy Eng Study Codex

한국어로 자연스럽게 Codex에 입력하면서 영어 공부도 같이 하고 싶은 사람을 위한
Codex 앱 플러그인입니다.

이 플러그인은 각 Codex 턴이 시작되기 전에 실행됩니다. 한국어 프롬프트는 Codex가
이해할 영어 요청으로 번역되고, 어색한 영어는 필요할 때 자연스럽게 교정됩니다.
`$gram <English request>`를 쓰면 `교정: ...` 줄을 보여준 뒤, Codex는 그 교정된
요청을 기준으로 답합니다.

## Spark가 필수가 아닌 이유

OpenAI는 현재 `gpt-5.3-codex-spark`를 ChatGPT Pro 사용자를 위한 연구 미리보기
Codex 모델로 설명합니다. Plus 플랜에는 일반 Codex 모델이 나열되어 있고 Spark는
포함되어 있지 않습니다. 그래서 이 플러그인은 Spark를 필수로 요구하지 않습니다.

기본 번역 경로는 다음과 같습니다.

```text
gpt-5.4-mini + medium reasoning effort
```

계정에서 Spark를 사용할 수 있다면 설치 후 이렇게 선택하세요.

```text
$kortoeng-model spark
```

또는 플러그인 루트에서 실행할 수 있습니다.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\bootstrap.ps1 kortoeng_control.py model spark
```

Spark를 사용할 수 없다면 기본값을 그대로 두면 됩니다.

참고:

- https://developers.openai.com/codex/models
- https://developers.openai.com/codex/pricing
- https://openai.com/index/introducing-gpt-5-3-codex-spark/

## Codex에 설치하기

이 저장소는 로컬 플러그인 마켓플레이스 형태입니다. 공개 저장소 이름은
`lazy-eng-study-codex`이고, 실제 플러그인 경로는
`plugins/lazy-eng-study-codex`입니다.

저장소 루트에서 실행합니다.

```powershell
codex plugin marketplace add .
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1
```

그 다음 Codex 앱을 열고 Plugins로 이동한 뒤 `Lazy Eng Study Codex`를 설치하고,
훅이 로드되도록 Codex를 재시작하세요.

Apple Silicon macOS에서는 이렇게 실행합니다.

```sh
codex plugin marketplace add .
sh ./install.sh
```

설치 후 Codex 안에서 사용할 수 있는 명령은 다음과 같습니다.

| 명령 | 용도 |
| --- | --- |
| `$kortoeng-on` | 한국어 자동 번역을 켭니다. |
| `$kortoeng-off` | 한국어 자동 번역을 끕니다. |
| `$kortoeng-model` | `mini`, `spark`, `gpt55` 중 번역 모델을 고릅니다. |
| `$kortoeng-bin` | 현재 Codex 실행 파일을 찾아 고정 경로로 저장합니다. |
| `$kortoeng` | 번역이 깨졌을 때 경로 탐색 상태를 진단합니다. |
| `$kor <한국어 요청>` | 자동 번역이 꺼져 있어도 이번 한국어 프롬프트만 번역합니다. |
| `$gram <request>` | `교정: ...`을 Codex가 이해한 요청으로 보여주고 그대로 처리합니다. |

이 명령들은 하나의 전역 설정 파일을 수정합니다. 이미 열려 있었지만 플러그인 훅을
로드하지 못한 Codex 스레드에 훅을 새로 주입하지는 않습니다. `$kortoeng-on` 뒤에도
`번역:` 줄이 보이지 않는 스레드가 있다면, Codex를 재시작하거나 다시 열어서
`UserPromptSubmit` 훅이 로드되게 하세요.

### `$kor` 일회성 번역

`$kortoeng-off` 상태에서도 이번 프롬프트만 영어로 번역하고 싶을 때
`$kor <한국어 요청>`을 사용합니다. 훅은 `$kor`를 제거하고 남은 한국어를 번역한
뒤 `번역: ...` 줄을 보여주며, 저장된 자동 번역 on/off 설정은 바꾸지 않습니다.

훅은 버전이 들어간 Codex 앱 폴더를 하드코딩하지 않습니다. 탐색 순서는 다음과
같습니다.

1. `CODEX_KOR_TO_ENG_CODEX_BIN`: 파일이 실제로 존재할 때만 사용합니다.
2. `PATH`에 있는 `codex`
3. Windows 또는 macOS의 Codex 앱 설치 폴더

훅은 Python이 이미 설치되어 있다고 가정하지 않습니다. Windows에서는
`scripts/bootstrap.ps1`, macOS에서는 `scripts/bootstrap.sh`를 통해 시작합니다.
부트스트랩은 먼저 Python 3.11 이상을 찾고, 없으면 플러그인 전용 portable Python
런타임을 내려받아 사용합니다. 운영체제에 Python을 설치하지는 않습니다.

Portable Python 지원 대상은 Windows x64/ARM64와 Apple Silicon macOS입니다. Intel
macOS는 의도적으로 지원하지 않습니다.

## 설정

이 플러그인은 Discord 없이 동작합니다. 필요한 것은 Codex입니다. Python 3.11 이상이
호스트에 없다면 부트스트랩이 준비합니다.

Python 제어 스크립트는 작은 JSON 설정 파일을 씁니다. 기본 위치는 Codex 홈 폴더
아래입니다. 테스트나 특수한 환경에서는 `CODEX_KOR_TO_ENG_SETTINGS_FILE`을 지정할
수 있습니다.

훅은 실행될 때마다 이 설정 파일을 읽습니다. 그래서 on/off/model 변경은 훅이
로드된 모든 기존/새 스레드에 전역으로 적용됩니다. 어떤 스레드가 애초에 훅을
로드하지 못했다면 플러그인 코드가 호출되지 않는 상태이므로 Codex 앱이 플러그인
목록을 다시 로드해야 합니다.

### 이번에 확인한 훅 이슈

Windows에서는 `C:\Program Files\WindowsApps` 아래의 `codex_bin` 경로를 저장하지
마세요. 해당 패키지 경로는 파일처럼 보여도, 훅이 자식 Codex 번역 프로세스를
시작할 때 `WinError 5` 접근 거부로 실패할 수 있습니다. 대신 사용자 로컬 Codex
CLI 경로인 `%LOCALAPPDATA%\OpenAI\Codex\bin\...\codex.exe`를 사용하세요.

성공한 훅 출력에는 보이는 `systemMessage`뿐 아니라 내부 `additionalContext`도
들어 있어야 합니다. 보이는 줄은 Codex 화면에 먼저 보이는 내용이고,
`additionalContext`는 assistant가 번역된 영어 요청을 실제 사용자 요청으로 다루게
하는 내부 문맥입니다.

플러그인 루트에서 실행할 수 있는 예시는 다음과 같습니다.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\bootstrap.ps1 kortoeng_control.py off
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\bootstrap.ps1 kortoeng_control.py on
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\bootstrap.ps1 kortoeng_control.py model mini
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\bootstrap.ps1 kortoeng_control.py codex-bin
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\configure_model.ps1 -Model mini
```

Apple Silicon macOS에서는 `sh ./scripts/bootstrap.sh ...`를 사용합니다.

```sh
sh ./scripts/bootstrap.sh kortoeng_control.py on
sh ./scripts/bootstrap.sh kortoeng_control.py model mini
```

유용한 환경 변수는 다음과 같습니다.

| 변수 | 기본값 | 의미 |
| --- | --- | --- |
| `CODEX_KOR_TO_ENG_MODEL` | `gpt-5.4-mini` | 설정 파일에 저장된 모델이 없을 때만 쓰는 기본 모델입니다. |
| `CODEX_KOR_TO_ENG_EFFORT` | `medium` | 설정 파일에 저장된 reasoning effort가 없을 때만 쓰는 기본값입니다. |
| `CODEX_KOR_TO_ENG_CODEX_BIN` | 자동 탐색 | 특수한 Codex CLI 설치를 위한 수동 경로입니다. 사라진 오래된 경로는 무시됩니다. |
| `CODEX_KOR_TO_ENG_RUNTIME_DIR` | `$CODEX_HOME/lazy-eng-study-codex/runtime` | portable Python 로컬 캐시 루트입니다. |
| `CODEX_KOR_TO_ENG_PYTHON_DOWNLOAD_ROOT` | Python standalone release URL | portable Python 아카이브 다운로드 루트입니다. |
| `CODEX_KOR_TO_ENG_PYTHON_BIN` | 자동 탐색 | 관리형 환경에서 Python 실행 파일을 직접 지정할 때 사용합니다. |
| `CODEX_KOR_TO_ENG_TIMEOUT_SECONDS` | `45` | 설정 파일에 timeout이 없을 때만 쓰는 최대 대기 시간입니다. |
| `CODEX_KOR_TO_ENG_TRANSLATOR_COMMAND` | 비어 있음 | 커스텀 번역 명령입니다. 번역 프롬프트를 stdin으로 받고 영어를 stdout으로 출력해야 합니다. |

훅은 자식 Codex 프로세스를 호출할 때 `CODEX_KOR_TO_ENG_DISABLED=1`을 설정합니다.
이 값은 번역용 Codex 실행이 다시 같은 번역 훅을 호출하는 무한 루프를 막습니다.

## 교정 범위

`$gram`은 명시적인 명령이므로, 남은 영어 요청이 대충 이해 가능한 문장이어도
rewrite 모델에 자연스러운 영어로 고치게 합니다. 여기서 "이해 가능"은 대략적인
의미를 추측할 수 있다는 뜻일 뿐이고, 어색하거나 오타가 있거나 모호하면 여전히
교정 대상입니다.

`$gram`은 다음을 교정할 수 있습니다.

- `implimented`를 `implemented`로 고치는 철자와 오타
- `readme`를 `README`로 고치는 대소문자와 용어
- `number2`를 `number 2`로 고치는 띄어쓰기와 번호 표현
- 문법, 구두점, 어순
- 영어 화자가 자연스럽게 쓰지 않는 어색한 표현
- 새 정보를 만들어내지 않고 개선할 수 있는, 이해는 되지만 모호한 표현

교정은 사용자의 의도, 파일 경로, 명령어, 코드, URL, ID, @mention을 보존해야
합니다. 이미 자연스럽고 명확한 문장이라면 결과가 같거나 아주 조금만 바뀔 수
있습니다. `$gram` 없이 자동으로 들어오는 영어 다듬기는 더 보수적으로 동작하며,
명확히 어색한 표지만 잡습니다.

## 화면에 보이는 것

한국어 입력 예시:

```text
테스트 스레드 상태 확인해줘
```

훅 출력에는 다음과 같은 보이는 `systemMessage` 줄이 포함됩니다.

```text
번역: Check the test thread status.
```

유창한 영어만 들어오면 훅은 아무것도 출력하지 않습니다. 명시적으로 영어 공부용
교정을 원하면 이렇게 씁니다.

```text
$gram is number2 implimented now?
```

보이는 교정 결과는 다음과 같습니다.

```text
교정: Is number 2 implemented now?
```

그 다음 Codex는 보이는 `교정:` 줄을 답해야 할 요청으로 다룹니다. assistant가 두
번째 교정 패스를 다시 돌리지 않습니다. 훅이 이미 이해한 요청을 보여줬기 때문입니다.

번역이나 교정이 실패하면, 훅은 조용히 원문으로 넘어가지 않고 실제 실패 내용을
보고합니다.

## 테스트

이 저장소에는 런타임 Python 패키지 의존성이 없습니다. 현재 Windows 테스트 명령은
다음과 같습니다.

```powershell
py -3 -m unittest discover -s tests -v
py -3 -m compileall plugins tests
```

커스텀 번역기를 이용한 수동 훅 smoke test는 다음과 같습니다.

```powershell
$env:CODEX_KOR_TO_ENG_TRANSLATOR_COMMAND = 'py -3 .\tests\fixtures\fake_translator.py'
@'
{"hook_event_name":"UserPromptSubmit","prompt":"\ud14c\uc2a4\ud2b8 \uc2a4\ub808\ub4dc \uc0c1\ud0dc \ud655\uc778\ud574\uc918","cwd":".","session_id":"manual"}
'@ | powershell -NoProfile -ExecutionPolicy Bypass -File .\plugins\lazy-eng-study-codex\scripts\bootstrap.ps1
```

출력은 `systemMessage`가 들어 있는 JSON이어야 합니다. 번역이나 교정에 성공하면
`hookSpecificOutput.additionalContext`에는 보이는 줄과 Codex가 답해야 할 영어
요청이 함께 들어 있어야 합니다.

## 하지 않는 것

- Discord 의존성 없음
- Codex 안에서 원래 프롬프트 텍스트를 자동으로 바꿔치기하지 않음
- 번역 실패 시 조용히 원문으로 대체하지 않음

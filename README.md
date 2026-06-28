# Lazy Eng Study Codex

한국어로 Codex에 말하면서 영어 표현도 같이 보고 싶은 사람을 위한 Codex 플러그인입니다.

예를 들어 Codex에 이렇게 입력하면:

```text
테스트 스레드 상태 확인해줘
```

Codex가 먼저 이런 줄을 보여줍니다.

```text
번역: Check the test thread status.
```

그 다음 Codex는 영어로 이해한 요청을 기준으로 답합니다.

## 가장 쉬운 설치 방법

Codex 앱에서 새 대화를 열고, 아래 문장을 그대로 붙여넣으세요.

```text
이 GitHub 저장소를 Codex 플러그인 마켓플레이스로 추가하고 Lazy Eng Study Codex를 설치해줘:
https://github.com/simdorei/lazy-eng-study-codex.git
```

Codex가 명령 실행을 물어보면 허용하세요. 설치가 끝나면 Codex 앱을 한 번 껐다가 다시 켜세요.

확인한 내용:

- Codex는 GitHub 저장소 주소로 플러그인 마켓플레이스를 추가할 수 있습니다.
- 이 저장소 주소로 추가하는 것도 실제로 확인했습니다.

## 직접 설치하기

Codex에게 시키는 방법이 잘 안 되면 아래 방법을 쓰세요.

### Windows

1. 키보드에서 `Windows` 키를 누릅니다.
2. `PowerShell`을 입력합니다.
3. `Windows PowerShell`을 엽니다.
4. 아래 줄을 복사해서 PowerShell 창에 붙여넣고 `Enter`를 누릅니다.

```powershell
codex plugin marketplace add https://github.com/simdorei/lazy-eng-study-codex.git
```

5. Codex 앱을 엽니다.
6. Plugins 화면으로 갑니다.
7. `Lazy Eng Study Codex`를 찾아 설치합니다.
8. Codex 앱을 껐다가 다시 켭니다.

### macOS

1. Terminal 앱을 엽니다.
2. 아래 줄을 복사해서 붙여넣고 `Enter`를 누릅니다.

```sh
codex plugin marketplace add https://github.com/simdorei/lazy-eng-study-codex.git
```

3. Codex 앱을 엽니다.
4. Plugins 화면에서 `Lazy Eng Study Codex`를 설치합니다.
5. Codex 앱을 껐다가 다시 켭니다.

## 설치 확인하기

Codex에 아래처럼 한국어로 입력해 보세요.

```text
테스트 스레드 상태 확인해줘
```

정상이라면 답변 첫 줄 근처에 이런 번역 줄이 보입니다.

```text
번역: Check the test thread status.
```

`번역:` 줄이 보이면 설치된 것입니다.

## 사용하는 명령

| 명령 | 뜻 |
| --- | --- |
| `$kortoeng-on` | 한국어 자동 번역을 켭니다. |
| `$kortoeng-off` | 한국어 자동 번역을 끕니다. |
| `$kor <한국어 요청>` | 자동 번역이 꺼져 있어도 이번 요청만 번역합니다. |
| `$gram <영어 요청>` | 영어 문장을 자연스럽게 고쳐서 `교정: ...`으로 보여줍니다. |
| `$kortoeng` | 번역이 안 될 때 현재 상태를 확인합니다. |
| `$kortoeng-model` | 번역에 사용할 모델을 고릅니다. |
| `$kortoeng-bin` | Codex 실행 파일 경로를 다시 찾습니다. |

쉽게 말해, `$kortoeng-on/off`는 번역 설정만 바꿉니다. 이미 열려 있던 대화가
플러그인을 처음부터 못 읽은 상태라면, 설정을 켜도 그 대화에는 번역기가 붙지 않을
수 있습니다. `$kortoeng-on` 뒤에도 `번역:` 줄이 보이지 않으면 Codex를 재시작하거나
대화를 새로 열어 주세요.

## `$kor`는 언제 쓰나요?

자동 번역을 꺼 둔 상태에서도 이번 한 번만 번역하고 싶을 때 씁니다.

```text
$kor 이 문장만 번역해서 처리해줘
```

이 명령은 저장된 자동 번역 on/off 설정을 바꾸지 않습니다.

## `$gram`은 언제 쓰나요?

내가 쓴 영어가 자연스러운지 보고 싶을 때 씁니다.

```text
$gram is number2 implimented now?
```

그러면 Codex가 먼저 이런 식으로 보여줍니다.

```text
교정: Is number 2 implemented now?
```

그 다음 Codex는 교정된 영어 문장을 기준으로 답합니다.

`$gram`은 다음을 고칠 수 있습니다.

- 철자와 오타
- 대소문자
- 띄어쓰기
- 문법
- 어색한 표현
- 너무 흐릿한 영어 표현

파일 경로, 명령어, 코드, URL, ID, @mention은 바꾸면 안 되므로 최대한 보존합니다.

## 모델

기본 번역 모델은 다음입니다.

```text
gpt-5.4-mini + medium reasoning effort
```

계정에서 Spark를 사용할 수 있다면 이렇게 바꿀 수 있습니다.

```text
$kortoeng-model spark
```

Spark를 사용할 수 없다면 기본값을 그대로 두면 됩니다.

## 문제가 생겼을 때

### `$kortoeng-on`을 했는데도 `번역:` 줄이 안 보여요

Codex 앱을 껐다가 다시 켜세요. 그래도 안 되면 새 대화를 열어서 다시 시도하세요.

### Windows에서 `WinError 5`가 보여요

Codex 실행 파일 경로가 WindowsApps 쪽으로 잡혔을 수 있습니다. 이 경로는 파일처럼
보여도 실행이 막힐 수 있습니다.

그럴 때는 Codex에서 아래 명령을 입력하세요.

```text
$kortoeng-bin
```

그 다음 Codex 앱을 다시 시작하세요.

### 번역이 너무 오래 걸려요

잠시 기다렸다가 다시 시도하세요. 계속 느리면 모델을 기본값으로 두는 것이 가장
안정적입니다.

## 개발자용 확인 명령

아래 명령은 이 저장소를 수정하거나 테스트하는 사람을 위한 것입니다. 일반 사용자는
실행하지 않아도 됩니다.

```powershell
py -3 -m unittest discover -s tests -v
py -3 -m compileall plugins tests
```

커스텀 번역기를 이용한 수동 훅 테스트:

```powershell
$env:CODEX_KOR_TO_ENG_TRANSLATOR_COMMAND = 'py -3 .\tests\fixtures\fake_translator.py'
@'
{"hook_event_name":"UserPromptSubmit","prompt":"\ud14c\uc2a4\ud2b8 \uc2a4\ub808\ub4dc \uc0c1\ud0dc \ud655\uc778\ud574\uc918","cwd":".","session_id":"manual"}
'@ | powershell -NoProfile -ExecutionPolicy Bypass -File .\plugins\lazy-eng-study-codex\scripts\bootstrap.ps1
```

## 하지 않는 것

- Discord가 없어도 됩니다.
- Codex 입력창에 쓴 원문을 자동으로 바꿔치기하지 않습니다.
- 번역 실패를 숨기고 원문으로 대충 넘어가지 않습니다.

## 참고

- https://developers.openai.com/codex/plugins
- https://developers.openai.com/codex/plugins/build
- https://developers.openai.com/codex/cli/reference

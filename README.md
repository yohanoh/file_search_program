# 파일 및 디렉토리 검색 프로그램(FileSearch)

## 업데이트 내역

### 2020-04-09
#### 기능
- `manager_observer_thread` 의 시작도 `start_thread`로 시작하도록 수정
- `UI` 클래스의 인스턴스 변수 `first_displayed_flag` 제거 (초기 DB 생성 후, 입력값을 기준으로 테이블을 표시하도록)
- 파일 변경 감지 동작 구현(이름 바꾸기, 이동)
- `UIthread` 모듈 내 `handler` 클래스 내에서 중복된 코드를 제거하여 `insert_file` 과 `delete_file` 메소드 구현
- `ReadDBThread` 의 `finish_read_signal`을 `finish_read` 메소드와 연결

#### 에러
- ManagerObserverThread가 CPU 부하를 많이 잡아먹는 현상 해결(무한루프 상태에서 sleep 을 줌)
  
### 2020-04-08
#### 기능
- 파일 생성 이벤트 발생 시, 정보를 테이블에 갱신하고 DB에도 넣는 과정 추가
- `search` 함수의 내부 함수 호출 및 . 연산을 줄여 속도 개선(약 1초 가량의 속도 개선)
- 파일 변경 감지에 따른 쓰레드 클래스 구현(`InsertDBThread`, `DeleteDBThread`)
- UI 클래스 내에 쓰레드를 시작하는 메소드를 `start_thread`로 통합(0: read, 1: scan, 2:insert, 3:delete)
- 파일 변경 감지(생성, 삭제) 시, 해당 테이블을 바로 갱신하도록 개선

#### 에러
- UI 창이 종료되어도, 백그라운드 프로세스들이 종료되지 않는 에러 해결(UI 프로세스의 PID을 통해 자식까지 모두 종료)
- 파일 변화 감지에서 "db-journal" 파일명을 가진 파일은 수집하지 않도록 수정(본 프로그램에 의해 수시로 삭제 및 생성됨)

### 2020-04-07
#### 기능
- `ScanThread`가 스캔 후, DB 저장 전에 파일 목록을 UI로 시그널을 보내도록 수정
- 드라이브 별로 스캔을 수행하는 멀티 프로세스 구현(사용자 시스템의 모든 드라이브 검색)
- 각 드라이브 별로 파일 변경(생성)을 감지하는 쓰레드 구현(`FileObserverThread`)
- 권한 상승 코드 추가

#### 에러
- 정렬 기능을 검색 결과에 대해 수행하도록 수정

### 2020-04-06
#### 기능
- 파일 크기 형식을 KB로 변경
- 파일 스캔 방식을 `os.walk`을 이용하도록 다시 수정
- 초기에 DB에서 정보를 가져오고, 메모리에 해당 정보를 올리고, 입력일 발생할 때마다 메모리에서 검색하도록 수정
- `pandas`의 `DataFrame` 형성 시 시간이 오래걸려, `TableView`에 나타나는 데이터 타입을 리스트로 변경
- `TableView`에서 사용하는 데이터 타입 변경에 따른 정렬 기능 재구현

#### 에러
- 일부 파일 누락 현상 해결 (주키를 파일과 경로 조합으로 구성 -> 기존에는 경로가 유일한 값이였지만, 경로에서 파일명을 제하면서 중복된 값이 가능해짐)
  
### 2020-04-05
#### 기능
- 파일 경로를 파일명을 제외한 값으로 수정
- 파일 경로 더블 클릭 시, 해당 경로의 디렉토리를 열도록 수정

### 2020-04-02
#### 기능
- `setTableData` 메소드의 내용을 `displayFiles` 메소드에 넣어서 불필요한 함수 호출을 줄임

#### 에러
- 문자열 비교 시 대소문자 구분을 하지 않기 위해 `instr` 문에서 `like` 문으로 변경
- `os.walk`가 수집하지 않는 디렉토리가 있어 사용하지 않고, 반복문을 통해 구현

### 2020-04-01
#### 에러
- DB 파일이 생성되지 않고, 초기 스캔을 거쳐 DB 파일이 생성되었을 때, 그 후에 파일 검색은 `QtableView`에 표시되지 않는 문제 해결(데이터 변경 후 시그널을 발생시키도록 수정)
- `read_db_thread`와 `scan_thread`가 동시에 실행될 때, UI 가 멈추는 현상 해결(db 접속할 때마다 새로운 `connection` 객체와 `cursor` 객체를 생성하도록 수정)

### 2020-03-31
#### 기능

- `QtableView` 파일 정보 클릭 시 해당 파일 또는 디렉토리 실행되도록 기능 구현
- `Data` 디렉토리가 없을 경우, 생성해주는 로직 추가
- `QtableView` 정렬 기능 구현

#### 에러

- `setTableData` 메소드 내에서 table에 데이터 표시 전 이전 값을 clear하도록 수정(`tableview.clearSpans()`)
- 초기 루트 디렉토리 내에 포함된 디렉토리 및 파일은 수집하지 않는 에러 해결
- `QtableView` 상에 표시되지 않던 데이터(파일의 사이즈) 를 올바르게 표시하도록 수정

### 2020-03-30
#### 기능 
- `QtableWidget` -> `QtableView` 로 테이블 형태 변환(속도 문제)
- thread 동기화 과정 수정(DB에 실질적으로 접근할 때 동기화를 수행하도록)




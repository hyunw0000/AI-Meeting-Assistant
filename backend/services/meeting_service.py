def generate_meeting_result(transcript):
    return {
        "title": "회의록 테스트",
        "summary": "오늘 회의에서는 프로젝트 기능 구현 방향을 논의했습니다.",
        "decisions": [
            "음성 파일 업로드 기능을 구현하기로 했습니다.",
            "회의록은 캘린더 날짜별로 조회할 수 있도록 하기로 했습니다."
        ],
        "tasks": [
            {
                "content": "음성 업로드 API 구현",
                "assignee": "백엔드 담당자",
                "due_date": "2026-05-10"
            },
            {
                "content": "캘린더 UI 구현",
                "assignee": "프론트엔드 담당자",
                "due_date": "2026-05-11"
            }
        ]
    }